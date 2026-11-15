#!/usr/bin/env python3
"""Read-only, evidence-limited suggestions using the existing whole-resource checker."""
import argparse
import importlib.util
import json
from pathlib import Path
_spec = importlib.util.spec_from_file_location('gles_graph_checker', Path(__file__).resolve().parents[1] / 'benchmarks/pipeline/rendergraph.py')
_checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_checker)


def advise(graph, synchronization_verified=False):
    checked = _checker.check(graph)
    result = {'schema_version': 1, 'valid': checked['valid'], 'checker': checked,
              'status': 'REJECTED' if not checked['valid'] else 'RECOMMENDED_FOR_EXPERIMENT',
              'device_performance': 'NOT_RUN', 'suggestions': [], 'mutates_graph': False}
    if not checked['valid']:
        return result
    # The inherited model cannot express SSBO/image barriers or external consumers.
    # Refuse to silently treat omitted synchronization evidence as verified.
    if synchronization_verified is not True:
        result.update(status='INSUFFICIENT_EVIDENCE', required_evidence=['Verify resource barriers, external consumers and final output lifetimes'])
        return result
    resources = graph['resources']
    passes = {p['id']: p for p in graph['passes']}
    ordered = [passes[p] for p in checked['order']]
    def add(kind, targets, preconditions, risk):
        result['suggestions'].append(dict(kind=kind, targets=targets, status='RECOMMENDED_FOR_EXPERIMENT',
            preconditions=preconditions, benefit_hypothesis='May reduce attachment traffic or state changes; NOT_MEASURED',
            risk=risk, fallback='Keep original graph and resource allocation',
            validation='python3 benchmarks/pipeline/rendergraph.py GRAPH.json; then compare actual GLES captures and interleaved device A/B'))
    for a, b in checked.get('alias_candidates', []):
        add('FBO_STORAGE_REUSE', [a, b], ['Non-overlapping whole-resource lifetimes', 'No external consumers or outstanding asynchronous work', 'Recheck framebuffer completeness'], 'Hidden users or subresources invalidate aliasing')
    for name, r in resources.items():
        writers = [p for p in ordered if name in p.get('writes', [])]
        readers = [p for p in ordered if name in p.get('reads', [])]
        if writers and not readers and not r.get('imported') and not r.get('transient'):
            add('TRANSIENT_ATTACHMENT_CANDIDATE', [name], ['Prove not a presented/exported/captured output', 'Contents dead after final writer', 'Invalidate only after last use'], 'Dropping final or external output is data loss')
    for p in ordered:
        if p.get('resolve'):
            add('MSAA_RESOLVE_REVIEW', [p['id']], ['Keep identical source/destination format and size', 'Probe supported resolve path on target device'], 'No assumed free resolve or extension support')
    for first, second in zip(ordered, ordered[1:]):
        if first.get('writes') and first.get('writes') == second.get('writes') and not first.get('discard') and not second.get('reads') and first['id'] in second.get('depends_on', []):
            add('PASS_FUSION_CANDIDATE', [first['id'], second['id']], ['Prove load/blend/depth/stencil semantics unchanged', 'Preserve command order and synchronization', 'No query/readback/external boundary'], 'Checker lacks pipeline state; fusion is not proven safe')
    if not result['suggestions']:
        result['status'] = 'NO_CANDIDATE'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('graph', type=Path)
    p.add_argument('--synchronization-reviewed', action='store_true', help='Explicit caller attestation, not automatic verification')
    a = p.parse_args()
    result = advise(json.loads(a.graph.read_text()), a.synchronization_reviewed)
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
