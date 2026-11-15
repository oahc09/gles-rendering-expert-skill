#!/usr/bin/env python3
"""Read-only, evidence-limited suggestions using the existing whole-resource checker."""
import argparse
import importlib.util
import json
import math
from pathlib import Path
_spec = importlib.util.spec_from_file_location('gles_graph_checker', Path(__file__).resolve().parents[1] / 'benchmarks/pipeline/rendergraph.py')
_checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_checker)


POSTFX_EXPERIMENTS = {'postfx-resolution-loss-v1': 'python3 benchmarks/pipeline/postfx_quality.py --config DRIVER_JSON --output REPORT_JSON'}


def advise(graph, synchronization_verified=False, postfx_contracts=None):
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
    result['postfx_reviews'] = review_postfx(graph, postfx_contracts)
    for review in result['postfx_reviews']:
        if review['status'] != 'RECOMMENDED_FOR_EXPERIMENT':
            continue
        add('POSTFX_SCALE_CANDIDATE', [review['pass_id']],
            ['Caller-supplied semantic contract must be independently reviewed',
             'Rescale kernels and normalized UVs for every candidate',
             'Preserve downstream reconstruction and original graph fallback',
             'Execute baseline/candidate image tests against declared quality budget before acceptance'],
            'Reduced sampling can lose thin features, HDR energy and temporal stability; no performance is established')
        result['suggestions'][-1].update(scale=review['scale'], proposed_sizes=review['proposed_sizes'],
            quality_budget=review['quality_budget'], experiment_id=review['experiment_id'],
            semantic_proof='NOT_PROVEN', estimated_pixel_ratio=review['scale'] ** 2,
            validation=POSTFX_EXPERIMENTS[review['experiment_id']])
    if not result['suggestions']:
        result['status'] = 'NO_CANDIDATE'
    return result


def review_postfx(graph, contracts):
    """Validate explicit sidecar constraints; never infer semantic safety from pass names."""
    if contracts is None:
        return []
    if not isinstance(contracts, list):
        return [{'status': 'REJECTED', 'reason': 'PostFX contracts must be an array'}]
    reviews = []
    seen = set()
    passes = {p['id']: p for p in graph['passes']}
    resources = graph['resources']
    fields = {'pass_id','scale','experiment_id','normalized_uv','kernel_rescaling',
              'downstream_resampling','external_output','temporal_history','quality_budget'}
    for c in contracts:
        row = {'status': 'REJECTED', 'pass_id': c.get('pass_id') if isinstance(c,dict) else None}
        def reject(reason):
            reviews.append(dict(row, reason=reason))
        if not isinstance(c,dict) or set(c) != fields:
            reject('Require complete, known PostFX contract fields');continue
        name = c['pass_id']
        if not isinstance(name,str) or name not in passes or name in seen:
            reject('Unknown or duplicate pass');continue
        seen.add(name)
        if not isinstance(c['experiment_id'],str) or c['experiment_id'] not in POSTFX_EXPERIMENTS:
            reject('A registered runnable experiment reference is required');continue
        scale = c['scale']
        if type(scale) not in (int,float) or not math.isfinite(scale) or not 0 < scale < 1:
            reject('Scale must be finite, positive and less than one');continue
        booleans = ('normalized_uv','kernel_rescaling','downstream_resampling','external_output','temporal_history')
        if any(type(c[k]) is not bool for k in booleans):
            reject('Semantic flags must be explicit booleans');continue
        if not all(c[k] for k in booleans[:3]) or c['external_output'] or c['temporal_history']:
            reject('Unresolved UV/kernel/downstream, external-output or temporal-history semantics');continue
        budget = c['quality_budget']
        if not isinstance(budget,dict) or set(budget) != {'max_abs_rgba_error','max_silhouette_error','max_temporal_error','golden_id'}:
            reject('Full image/silhouette/temporal quality budget required');continue
        if not isinstance(budget['golden_id'],str) or not budget['golden_id'].strip() or any(type(budget[k]) not in (int,float) or not math.isfinite(budget[k]) or not 0<=budget[k]<=1 for k in ('max_abs_rgba_error','max_silhouette_error','max_temporal_error')):
            reject('Quality thresholds require finite normalized values and a golden reference');continue
        p = passes[name]
        outputs = p.get('writes',[])
        if not outputs or not p.get('reads') or p.get('resolve') or p.get('discard'):
            reject('Require a sampled color PostFX pass, without resolve/discard');continue
        if any(resources[r]['format'] not in ('RGBA8','SRGB8_ALPHA8','RGBA16F') or resources[r].get('samples',1)!=1 or resources[r].get('imported') for r in outputs):
            reject('Only private single-sample color attachments are supported');continue
        if any(not any(r in other.get('reads',[]) for other in graph['passes'] if other['id']!=name) for r in outputs):
            reject('Final output cannot be silently resized');continue
        sizes={r:[math.floor(v*scale) for v in resources[r]['size']] for r in outputs}
        if any(min(size)<1 or size==resources[r]['size'] for r,size in sizes.items()):
            reject('Scaled sizes must remain positive and actually change');continue
        reviews.append(dict(row,status='RECOMMENDED_FOR_EXPERIMENT',scale=scale,
                            proposed_sizes=sizes,quality_budget=dict(budget),experiment_id=c['experiment_id']))
    return reviews


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('graph', type=Path)
    p.add_argument('--synchronization-reviewed', action='store_true', help='Explicit caller attestation, not automatic verification')
    p.add_argument('--postfx-contracts', type=Path, help='Explicit semantic/quality sidecar; caller assertions are not proof')
    a = p.parse_args()
    result = advise(json.loads(a.graph.read_text()), a.synchronization_reviewed, json.loads(a.postfx_contracts.read_text()) if a.postfx_contracts else None)
    print(json.dumps(result, indent=2))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
