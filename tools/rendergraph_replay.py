"""Bounded RGBA8 framebuffer->nearest-sample graph transform; not a general graph compiler."""
import copy
import hashlib
import json
from rendergraph_optimizer import _checker

def digest(graph):return hashlib.sha256(json.dumps(graph,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(graph):
    checked=_checker.check(graph)
    if not checked['valid']:raise ValueError('Inherited graph checker rejected graph')
    # Closed executable vocabulary: no hidden external, compute, image, depth or MSAA work.
    if set(graph['resources'])!={'scene','intermediate','screen'}:raise ValueError('unsupported resources')
    for name,r in graph['resources'].items():
        if set(r)!={'format','size'} or r['format']!='RGBA8' or any(n>64 for n in r['size']):
            raise ValueError('only bounded private RGBA8 allocations')
    if graph['resources']['scene']['size']!=[4,4] or graph['resources']['screen']['size']!=[4,4]:
        raise ValueError('fixed source and output extent required')
    if graph['resources']['intermediate']['size'] not in ([4,4],[2,2]):raise ValueError('unsupported intermediate extent')
    expected=[{'id':'source','writes':['scene']},
        {'id':'sample','reads':['scene'],'writes':['intermediate'],'depends_on':['source']},
        {'id':'present','reads':['intermediate'],'writes':['screen'],'depends_on':['sample']}]
    if graph['passes']!=expected:raise ValueError('unsupported commands or missing explicit producer dependency')
    return {'status':'PASS','order':checked['order'],'invariants':[
        'one context, sequential draw submission','producer dependency before each consumer',
        'each sampled texture differs from active framebuffer attachment',
        'private whole-resource storage; no alias/subrange/external consumers',
        'framebuffer writes followed by texture fetch use GLES coherent command ordering'],
        'memory_barrier_bits':0,'barrier_reason':'No incoherent shader writes in this closed vocabulary; glMemoryBarrier is not required',
        'excluded':['SSBO','imageStore','compute','cross-context','async external access','depth','blending','MSAA']}

def transform(graph):
    validate(graph)
    if graph['resources']['intermediate']['size']!=[4,4]:raise ValueError('baseline already transformed')
    candidate=copy.deepcopy(graph);candidate['resources']['intermediate']['size']=[2,2]
    invariants=validate(candidate)
    return {'baseline_sha256':digest(graph),'candidate_sha256':digest(candidate),'candidate':candidate,
        'fallback':copy.deepcopy(graph),'transformation':'intermediate_extent_4_to_2','synchronization':invariants,
        'quality':'REQUIRES_ACTUAL_REPLAY','performance':'NOT_MEASURED','general_equivalence':'NOT_PROVEN'}

def baseline():
    return {'resources':{n:{'format':'RGBA8','size':[4,4]} for n in ('scene','intermediate','screen')},
        'passes':[{'id':'source','writes':['scene']},{'id':'sample','reads':['scene'],'writes':['intermediate'],'depends_on':['source']},{'id':'present','reads':['intermediate'],'writes':['screen'],'depends_on':['sample']}]}
