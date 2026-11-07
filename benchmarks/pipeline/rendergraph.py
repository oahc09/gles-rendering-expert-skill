"""Standalone GLES planning model; not a GL state validator or performance measurement."""
import argparse
import json
from pathlib import Path

FORMATS = {'RGBA8', 'SRGB8_ALPHA8', 'RGBA16F', 'R32UI', 'DEPTH24_STENCIL8', 'DEPTH_COMPONENT24'}

def check(graph):
    errors, warnings = [], []
    def issue(rule, path, message):
        errors.append(dict(rule=rule, path=path, message=message))
    if not isinstance(graph, dict) or 'resources' not in graph or 'passes' not in graph:
        return dict(valid=False, errors=[dict(rule='RG_SCHEMA', path='/', message='Graph object requires resources and passes')], warnings=[], order=[])
    resources = graph.get('resources', {})
    passes = graph.get('passes', [])
    if not isinstance(resources, dict) or not isinstance(passes, list):
        return dict(valid=False, errors=[dict(rule='RG_SCHEMA', path='/', message='resources object and passes array required')], warnings=[], order=[])
    if set(graph) - {'resources', 'passes'}:
        issue('RG_SCHEMA', '/', 'Unknown graph fields')
    for name, r in resources.items():
        if not isinstance(r, dict) or not isinstance(r.get('format'), str) or r.get('format') not in FORMATS or not isinstance(r.get('size'), list) or len(r['size']) != 2 or any(type(x) is not int or x < 1 for x in r['size']) or type(r.get('samples', 1)) is not int or r.get('samples', 1) < 1:
            issue('RG_RESOURCE', '/resources/' + name, 'Unknown format or invalid positive size/sample count')
    for name, r in resources.items():
        if isinstance(r, dict) and (set(r) - {'format','size','samples','imported','transient'} or any(k in r and type(r[k]) is not bool for k in ('imported','transient'))):
            issue('RG_SCHEMA', '/resources/' + name, 'Unknown resource fields or invalid boolean')
    for i, p in enumerate(passes):
        if not isinstance(p, dict):
            issue('RG_SCHEMA', '/passes/' + str(i), 'Pass must be an object')
            continue
        if set(p) - {'id','depends_on','reads','writes','discard','expected_formats','resolve','subranges'}:
            issue('RG_SCHEMA', '/passes/' + str(i), 'Unknown pass fields')
        for field in ('depends_on', 'reads', 'writes', 'discard'):
            value = p.get(field, [])
            if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value) or len(value) != len(set(x for x in value if isinstance(x, str))):
                issue('RG_SCHEMA', '/passes/' + str(i) + '/' + field, 'Unique resource/pass name array required')
        if not isinstance(p.get('expected_formats', {}), dict) or ('resolve' in p and (not isinstance(p['resolve'], dict) or any(not isinstance(p['resolve'].get(k), str) for k in ('src', 'dst')))):
            issue('RG_SCHEMA', '/passes/' + str(i), 'Invalid format map or resolve object')
    if errors:
        return dict(valid=False, errors=errors, warnings=warnings, order=[])
    ids = [p.get('id') if isinstance(p, dict) else None for p in passes]
    if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(x for x in ids if isinstance(x, str))):
        issue('RG_PASS_ID', '/passes', 'Unique nonempty pass IDs required')
    if errors:
        return dict(valid=False, errors=errors, warnings=warnings, order=[])
    by_id = dict(zip(ids, passes))
    for p in passes:
        for dependency in p.get('depends_on', []):
            if dependency not in by_id:
                issue('RG_DEPENDENCY', '/passes/' + p['id'], 'Unknown dependency: ' + str(dependency))
    order, active, done = [], [], set()
    def visit(name):
        if name in active:
            issue('RG_CYCLE', '/passes/' + name, ' -> '.join(active[active.index(name):] + [name]))
            return
        if name in done or name not in by_id:
            return
        active.append(name)
        for dep in by_id[name].get('depends_on', []):
            visit(dep)
        active.pop()
        done.add(name)
        order.append(name)
    for name in ids:
        visit(name)
    if errors:
        return dict(valid=False, errors=errors, warnings=warnings, order=[])
    defined = {n for n, r in resources.items() if r.get('imported', False)}
    lifetimes = {}
    for i, name in enumerate(order):
        p = by_id[name]
        reads, writes = p.get('reads', []), p.get('writes', [])
        path = '/passes/' + name
        if p.get('subranges'):
            issue('RG_SUBRANGE_UNSUPPORTED', path, 'Whole-resource model: split disjoint mip/layer allocations explicitly')
        for r in set(reads) | set(writes):
            if r not in resources:
                issue('RG_UNKNOWN_RESOURCE', path, str(r))
            else:
                lifetimes.setdefault(r, [i, i])[1] = i
        for r in set(reads) & set(writes):
            issue('RG_FEEDBACK', path, 'Simultaneous attachment/sample feedback: ' + r)
        for r in reads:
            if r in resources and resources[r].get('samples', 1) > 1 and (not p.get('resolve') or p['resolve'].get('src') != r):
                issue('RG_UNRESOLVED_MSAA', path, 'Sampled reads require single-sample resource or explicit resolve: ' + r)
            if r not in defined:
                issue('RG_UNDEFINED_READ', path, 'Read before initialized write or after discard: ' + r)
        attachments = [resources[r] for r in writes if r in resources]
        if attachments and any((r['size'], r.get('samples', 1)) != (attachments[0]['size'], attachments[0].get('samples', 1)) for r in attachments):
            issue('RG_ATTACHMENT_SHAPE', path, 'Attachment dimensions/sample counts differ (planner contract)')
        for r, fmt in p.get('expected_formats', {}).items():
            if r not in resources or resources[r]['format'] != fmt:
                issue('RG_FORMAT', path, 'Attachment contract mismatch: ' + r)
        resolve = p.get('resolve')
        if resolve:
            src, dst = resolve.get('src'), resolve.get('dst')
            if src not in resources or dst not in resources or src not in reads or dst not in writes:
                issue('RG_RESOLVE', path, 'Resolve source/destination must be declared read/write resources')
            else:
                a, b = resources[src], resources[dst]
                if a.get('samples', 1) <= 1 or b.get('samples', 1) != 1 or a['size'] != b['size'] or a['format'] != b['format'] or resolve.get('filter', 'NEAREST') != 'NEAREST':
                    issue('RG_RESOLVE', path, 'MSAA resolve requires multisample source, single sample target, equal size/format and NEAREST')
        for r in writes:
            if r in resources:
                defined.add(r)
        for r in p.get('discard', []):
            if r not in writes:
                issue('RG_DISCARD', path, 'Discard must name a written attachment: ' + r)
            defined.discard(r)
    for r, (start, end) in lifetimes.items():
        if resources[r].get('transient') and not any(r in p.get('discard', []) for p in passes):
            warnings.append(dict(rule='RG_INVALIDATE_HINT', path='/resources/' + r, message='Consider invalidate after last use; bandwidth benefit NOT_RUN'))
    alias_candidates = [[a, b] for a in lifetimes for b in lifetimes if a < b and resources[a].get('transient') and resources[b].get('transient') and not resources[a].get('imported') and not resources[b].get('imported') and resources[a]['format'] == resources[b]['format'] and resources[a]['size'] == resources[b]['size'] and resources[a].get('samples', 1) == resources[b].get('samples', 1) and (lifetimes[a][1] < lifetimes[b][0] or lifetimes[b][1] < lifetimes[a][0])]
    return dict(valid=not errors, errors=errors, warnings=warnings, order=order, lifetimes=lifetimes, alias_candidates=alias_candidates, device_performance='NOT_RUN')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph', type=Path)
    args = parser.parse_args()
    result = check(json.loads(args.graph.read_text()))
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
