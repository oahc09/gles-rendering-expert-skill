#!/usr/bin/env python3
"""Adversarial overlays on v1.0.7 validators, not a second render graph."""
import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))
import material
import rendergraph
import hazards
import variants


def graph_check(graph, aliases=()):
    """Require alias safety under every topological ordering, not one listing."""
    if not isinstance(graph, dict) or not isinstance(graph.get('passes'), list) or not isinstance(graph.get('resources'), dict):
        return rendergraph.check(graph)
    if len(graph['passes']) > 128 or len(graph['resources']) > 256:
        raise ValueError('bounded graph: at most128 passes and256 resources')
    result = rendergraph.check(graph)
    result['alias_proofs'] = []
    if not result['valid']:
        return result
    passes = {p['id']: p for p in graph['passes']}
    ancestors = {}
    for name in result['order']:
        ancestors[name] = set(passes[name].get('depends_on', []))
        for parent in tuple(ancestors[name]):
            ancestors[name].update(ancestors[parent])
    uses = {r: {p['id'] for p in graph['passes'] if r in p.get('reads', []) + p.get('writes', [])}
            for r in graph['resources']}
    if not isinstance(aliases, (list, tuple)) or len(aliases) > 128:
        raise ValueError('aliases must be an array of at most128 pairs')
    components=[]
    for pair in aliases:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2 or any(not isinstance(x, str) for x in pair):
            raise ValueError('alias pair requires two resource names')
        merged=set(pair)
        for group in list(components):
            if merged & group:
                merged.update(group);components.remove(group)
        components.append(merged)
    # Alias equivalence is transitive: a~b and b~c imply a~c, even if not requested
    # as a separate pair. Every pair in a backing-allocation class must be safe.
    expanded=set(tuple(sorted(pair)) for pair in aliases)
    for group in components:
        expanded.update((a,b) for a in group for b in group if a<b)
    for pair in sorted(expanded):
        a, b = pair
        rule = None
        if a == b or a not in uses or b not in uses:
            rule = 'RG_ALIAS_RESOURCE'
        else:
            ar, br = graph['resources'][a], graph['resources'][b]
            if (not ar.get('transient') or not br.get('transient') or ar.get('imported') or br.get('imported')):
                rule = 'RG_ALIAS_OWNERSHIP'
            elif any(ar.get(k, 1 if k == 'samples' else None) != br.get(k, 1 if k == 'samples' else None)
                     for k in ('format', 'size', 'samples')):
                rule = 'RG_ALIAS_SHAPE'
            elif not uses[a] or not uses[b]:
                rule = 'RG_ALIAS_UNUSED'
            else:
                before = all(x in ancestors[y] for x in uses[a] for y in uses[b])
                after = all(y in ancestors[x] for x in uses[a] for y in uses[b])
                if not (before or after):
                    rule = 'RG_ALIAS_UNORDERED_OR_OVERLAPPING'
                else:
                    result['alias_proofs'].append(dict(resources=[a,b], earlier=a if before else b,
                        later=b if before else a, uses={a: sorted(uses[a]), b: sorted(uses[b])},
                        basis='Every use of earlier resource reaches every use of later resource through explicit dependency edges'))
        if rule:
            result['errors'].append(dict(rule=rule, path='/aliases', resources=[a,b],
                message='No safe allocation reuse proof for resources '+a+' / '+b,
                repair='Use separate allocations or add correct dependency edges after the last use'))
    result['valid'] = not result['errors']
    return result


def abi_check(manifest, *, reflection=None, capability=None, active_uniforms=None, required_uniforms=()):
    errors = material.validate(manifest, reflection=reflection)
    if capability is not None:
        if capability.get('gles') not in variants.VERSIONS:
            raise ValueError('capability GLES version required')
        if manifest['gles'] > capability['gles']:
            errors.append('MATERIAL_SHADER_VERSION_EXCEEDS_CONTEXT')
        errors.extend(variants.validate(dict(gles=capability['gles'], quality='high', features=[],
            extensions=capability.get('extensions', []), required_extensions=manifest.get('required_extensions', []))))
    if active_uniforms is not None:
        if not isinstance(active_uniforms, list) or any(not isinstance(x, str) for x in active_uniforms):
            raise ValueError('active_uniforms string array required')
        for name in required_uniforms:
            if name not in active_uniforms:
                errors.append('REQUIRED_ACTIVE_UNIFORM_MISSING:'+name)
    return errors


def synchronization_proof(events, share_groups):
    """Prove one write generation via explicit fence/flush/wait/rebind events.

    This strengthens, and does not replace, hazards.check. It proves command
    ordering and shared-object visibility, not intra-dispatch race freedom.
    """
    if not isinstance(events,list) or len(events)>256 or not isinstance(share_groups,dict):
        raise ValueError('bounded events and share_groups required')
    ids=set();writes={};fences={};waits={};rebinds={};proofs=[];errors=[]
    for i,e in enumerate(events):
        if not isinstance(e,dict) or not all(isinstance(e.get(k),str) and e[k] for k in ('id','context','op')):
            raise ValueError('named event/context/op required')
        if e['id'] in ids or e['context'] not in share_groups:
            raise ValueError('unique event ID and known context required')
        ids.add(e['id']);c=e['context'];op=e['op'];r=e.get('resource');f=e.get('fence')
        if op=='write':
            if not isinstance(r,str):raise ValueError('write resource required')
            writes[r]=(c,e['id'],i)
        elif op=='fence':
            if not isinstance(f,str) or f in fences:raise ValueError('unique fence identity required')
            fences[f]=dict(context=c,event=e['id'],index=i,flush=None,writes=dict(writes))
        elif op=='flush':
            for v in fences.values():
                if v['context']==c and v['flush'] is None:v['flush']=e['id']
        elif op=='wait':
            v=fences.get(f)
            if v is None or not v['flush'] or share_groups[c]!=share_groups[v['context']]:
                errors.append(dict(rule='HB_WAIT_WITHOUT_PUBLISHED_SHARED_FENCE',event=e['id'],fence=f))
            else:waits[(c,f)]=(i,e['id'])
        elif op=='rebind':rebinds[(c,r)]=(i,e['id'])
        elif op=='read':
            old=writes.get(r)
            if old is None:
                errors.append(dict(rule='HB_NO_PRODUCER',event=e['id'],resource=r));continue
            if old[0]==c:continue
            v=fences.get(f);wait=waits.get((c,f));rebind=rebinds.get((c,r))
            if not(v and v['writes'].get(r)==old and v['context']==old[0] and wait and rebind and rebind[0]>wait[0]):
                errors.append(dict(rule='HB_UNPROVED_CROSS_CONTEXT_READ',event=e['id'],resource=r,fence=f))
            else:proofs.append(dict(resource=r,write=old[1],fence=v['event'],flush=v['flush'],wait=wait[1],rebind=rebind[1],read=e['id']))
        else:raise ValueError('unknown event operation')
    return dict(valid=not errors,errors=errors,proofs=proofs,scope='explicit static synchronization contract; runtime fence completion not asserted')


def reduce_graph(graph, aliases, target_rule, max_attempts=100):
    """Reuse v1.0.6 line-ddmin, preserving the graph error classification."""
    spec=importlib.util.spec_from_file_location('v106_reducer', ROOT/'benchmarks/reducer/reduce.py')
    reducer=importlib.util.module_from_spec(spec);spec.loader.exec_module(reducer)
    def oracle(source):
        try:
            candidate=dict(resources=graph['resources'], passes=[json.loads(s) for s in source.splitlines()])
            result=graph_check(candidate,aliases)
            matches=any(e['rule']==target_rule for e in result['errors'])
            return dict(matches=matches,diagnostic=target_rule if matches else 'predicate not reproduced',exit_code=1 if matches else 0)
        except (ValueError,TypeError,KeyError,RecursionError):
            return dict(matches=False,diagnostic='outside graph reduction domain',exit_code=None)
    result=reducer.minimize(''.join(json.dumps(p,sort_keys=True)+'\n' for p in graph['passes']),oracle,max_attempts=max_attempts)
    result['graph']=dict(resources=copy.deepcopy(graph['resources']),passes=[json.loads(s) for s in result.pop('source').splitlines()])
    result['aliases']=aliases
    result['predicate']=target_rule
    result['minimality_domain']='pass deletion, fixed resource descriptors and alias requests; not globally smallest graph'
    return result


def base_graph():
    resource=dict(format='RGBA8', size=[16,16],samples=1,transient=True)
    return dict(resources={k:copy.deepcopy(resource) for k in ('a','b')},passes=[
        dict(id='make_a',writes=['a']),dict(id='read_a',depends_on=['make_a'],reads=['a']),
        dict(id='make_b',depends_on=['read_a'],writes=['b']),dict(id='read_b',depends_on=['make_b'],reads=['b'])])


def graph_cases():
    cases=[]
    def add(name,edit=lambda g:None,rule=None,alias=True):
        g=base_graph();edit(g);cases.append(dict(id='AG%02d'%(len(cases)+1),name=name,graph=g,
            aliases=[['a','b']] if alias else [],expected_rule=rule))
    add('ordered alias proof')
    add('independent passes cannot prove alias',lambda g:g['passes'][2].update(depends_on=[]),'RG_ALIAS_UNORDERED_OR_OVERLAPPING')
    add('late reuse overlaps',lambda g:g['passes'][3]['reads'].append('a'),'RG_ALIAS_UNORDERED_OR_OVERLAPPING')
    add('imported resource must not alias',lambda g:g['resources']['a'].update(imported=True),'RG_ALIAS_OWNERSHIP')
    add('persistent resource must not alias',lambda g:g['resources']['a'].update(transient=False),'RG_ALIAS_OWNERSHIP')
    add('alias formats differ',lambda g:g['resources']['b'].update(format='RGBA16F'),'RG_ALIAS_SHAPE')
    add('alias dimensions differ',lambda g:g['resources']['b'].update(size=[8,16]),'RG_ALIAS_SHAPE')
    add('cycle insertion',lambda g:g['passes'][0].update(depends_on=['read_b']),'RG_CYCLE')
    add('unknown dependency insertion',lambda g:g['passes'][0].update(depends_on=['missing']),'RG_DEPENDENCY')
    add('deleted producer',lambda g:g['passes'][0].update(writes=[]),'RG_UNDEFINED_READ')
    add('discard before use',lambda g:g['passes'][0].update(discard=['a']),'RG_UNDEFINED_READ')
    add('framebuffer sampling feedback',lambda g:g['passes'][1].update(writes=['a']),'RG_FEEDBACK')
    add('linear/sRGB contract mismatch',lambda g:g['passes'][0].update(expected_formats={'a':'SRGB8_ALPHA8'}),'RG_FORMAT')
    add('unresolved multisample read',lambda g:g['resources']['a'].update(samples=4),'RG_UNRESOLVED_MSAA')
    add('mixed attachment sizes',lambda g:(g['resources']['b'].update(size=[8,16]),g['passes'][0].update(writes=['a','b'])),'RG_ATTACHMENT_SHAPE')
    add('resource name typo',lambda g:g['passes'][1].update(reads=['missing']),'RG_UNKNOWN_RESOURCE')
    add('invalid discard target',lambda g:g['passes'][0].update(discard=['b']),'RG_DISCARD')
    add('subrange not proved',lambda g:g['passes'][0].update(subranges={'a':[0,1]}),'RG_SUBRANGE_UNSUPPORTED')
    add('bool sample count',lambda g:g['resources']['a'].update(samples=True),'RG_RESOURCE')
    add('duplicate pass identity',lambda g:g['passes'][1].update(id='make_a'),'RG_PASS_ID')
    add('separate allocations allow independent writes',lambda g:g['passes'][2].update(depends_on=[]),alias=False)
    add('inserting transitive dependency remains valid',lambda g:g['passes'][3]['depends_on'].append('make_a'))
    add('declaration order is not execution order',lambda g:g['passes'].reverse())
    add('same format sRGB alias legal',lambda g:[r.update(format='SRGB8_ALPHA8') for r in g['resources'].values()])
    return cases


def base_material():
    return json.loads((HERE.parent/'manifests/pbr-material.json').read_text())


def reflection_for(m):
    blocks=[]
    for b in m['blocks']:
        members,_=material.layout_members(b['members'],b['layout'])
        blocks.append(dict(name=b['name'],size=b['size'],binding=b['binding'],members=members))
    return dict(blocks=blocks,samplers=[{k:s[k] for k in ('name','type','unit')} for s in m['samplers']])


def abi_cases():
    cases=[]
    def add(name,edit=lambda m,r,c,u:None,rule=None):
        m=base_material();r=reflection_for(m);c=dict(gles='3.0',extensions=[]);u=['baseColorTex']
        edit(m,r,c,u);cases.append(dict(id='AA%02d'%(len(cases)+1),name=name,manifest=m,reflection=r,capability=c,
            active_uniforms=u,required_uniforms=['baseColorTex'],expected_rule=rule))
    add('valid linked material')
    add('wrong member offset',lambda m,r,c,u:m['blocks'][0]['members'][1].update(offset=12),'OFFSET')
    add('wrong block size',lambda m,r,c,u:m['blocks'][0].update(size=24),'BLOCK_SIZE')
    add('reflected binding mismatch',lambda m,r,c,u:r['blocks'][0].update(binding=1),'REFLECTION_BINDING')
    add('reflected block missing',lambda m,r,c,u:r.update(blocks=[]),'REFLECTION_BLOCK_MISSING')
    add('required member missing',lambda m,r,c,u:r['blocks'][0]['members'].pop(),'REFLECTION_TYPE')
    add('same offset different type',lambda m,r,c,u:r['blocks'][0]['members'][1].update(type='uint'),'REFLECTION_TYPE')
    add('array extent mismatch',lambda m,r,c,u:r['blocks'][0]['members'][0].update(array=2),'REFLECTION_ARRAY')
    add('matrix orientation mismatch',lambda m,r,c,u:r['blocks'][0]['members'][0].update(row_major=True),'REFLECTION_ROW_MAJOR')
    add('array stride mismatch',lambda m,r,c,u:r['blocks'][0]['members'][0].update(array_stride=16),'REFLECTION_ARRAY_STRIDE')
    add('matrix stride mismatch',lambda m,r,c,u:r['blocks'][0]['members'][0].update(matrix_stride=16),'REFLECTION_MATRIX_STRIDE')
    add('sampler metadata missing',lambda m,r,c,u:r.pop('samplers'),'REFLECTION_SAMPLERS_MISSING')
    add('sampler unit changed',lambda m,r,c,u:r['samplers'][0].update(unit=1),'REFLECTION_UNIT')
    add('sampler type changed',lambda m,r,c,u:r['samplers'][0].update(type='usampler2D'),'REFLECTION_TYPE')
    add('incompatible sampler sharing unit',lambda m,r,c,u:m['samplers'].append(dict(name='integerMap',type='usampler2D',format='R32UI',unit=0)),'SAMPLER_TYPE_COLLISION')
    add('unit out of range',lambda m,r,c,u:m['samplers'][0].update(unit=16),'TEXTURE_UNIT_LIMIT')
    add('integer format on float sampler',lambda m,r,c,u:m['samplers'][0].update(format='R32UI'),'TEXTURE_FORMAT_MISMATCH')
    add('required extension absent',lambda m,r,c,u:m.update(required_extensions=['GL_EXT_nonexistent_fixture']),'MISSING_EXTENSION')
    add('shader exceeds context',lambda m,r,c,u:m.update(gles='3.1'),'MATERIAL_SHADER_VERSION_EXCEEDS_CONTEXT')
    add('required active uniform absent',lambda m,r,c,u:u.clear(),'REQUIRED_ACTIVE_UNIFORM_MISSING')
    add('SSBO in ES3.0',lambda m,r,c,u:m['blocks'][0].update(kind='ssbo'),'SSBO_REQUIRES_GLES_3.1')
    add('descriptor sets not GLES',lambda m,r,c,u:m['blocks'][0].update(set=0),'DESCRIPTOR_SET_NOT_GLES')
    add('linked location changes are not ABI changes',lambda m,r,c,u:r['samplers'][0].update(location=7))
    add('higher context version remains legal',lambda m,r,c,u:c.update(gles='3.2'))
    return cases


def hazard_cases():
    rows=[]
    for kind in ('vertex','index','indirect','uniform','sample'):
        for correct in (True,False):
            trace=dict(gles='3.1',events=[dict(context='main',accesses=[dict(resource='shared',kind='ssbo',mode='write',stage='compute')]),
                dict(context='main',barrier=[hazards.BITS[kind] if correct else 'GL_SHADER_STORAGE_BARRIER_BIT'],
                     accesses=[dict(resource='shared',kind=kind,mode='read',stage='consumer')])])
            result=hazards.check(trace)
            passed=result['valid'] if correct else any(e['rule']=='HZ_BARRIER' for e in result['errors'])
            rows.append(dict(id='AH%02d'%(len(rows)+1),consumer=kind,expected_valid=correct,trace=trace,result=result,status='PASS' if passed else 'FAIL'))
    return rows


def run(output):
    output.mkdir(parents=True,exist_ok=True);graphs=[];abis=[]
    for c in graph_cases():
        result=graph_check(c['graph'],c['aliases']);rule=c['expected_rule']
        ok=result['valid'] if rule is None else any(e['rule']==rule for e in result['errors'])
        row=dict(**c,result=result,status='PASS' if ok else 'FAIL')
        if rule:
            row['reduction']=reduce_graph(c['graph'],c['aliases'],rule)
        graphs.append(row)
    for c in abi_cases():
        errors=abi_check(c['manifest'],reflection=c['reflection'],capability=c['capability'],
            active_uniforms=c['active_uniforms'],required_uniforms=c['required_uniforms'])
        ok=not errors if c['expected_rule'] is None else any(c['expected_rule'] in e for e in errors)
        abis.append(dict(**c,errors=errors,status='PASS' if ok else 'FAIL',reflection_evidence='authored contract fixture, not GL reflection'))
    hazard_rows=hazard_cases()
    result=dict(schema_version=1,status='PASS' if all(r['status']=='PASS' for r in graphs+abis+hazard_rows) else 'FAIL',
        scope='Static adversarial contracts reusing actual v1.0.7 implementations',graphs=graphs,abis=abis,hazards=hazard_rows,
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    (output/'report.md').write_text('# Pipeline adversarial contracts\n\n'+result['status']+
        '\n\n24 graph cases;24 ABI cases. This is static/model evidence. Runtime-derived reflection is reported separately.\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=run(a.output);print(json.dumps(dict(status=r['status'],graphs=len(r['graphs']),abis=len(r['abis']))));raise SystemExit(r['status']!='PASS')
