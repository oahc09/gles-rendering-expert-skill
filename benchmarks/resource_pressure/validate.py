"""Fail-closed validation of actual resource stress rows; not an alternate renderer."""
def validate_rows(rows, scenes):
    if type(scenes) is not int or not 100 <= scenes <= 10000:
        raise ValueError('scene count outside 100..10000')
    snapshots=[r for r in rows if 'CapabilitySnapshot' in r]
    if len(snapshots)!=1 or not snapshots[0]['CapabilitySnapshot'].get('gl_renderer'):
        raise ValueError('missing real GL capability snapshot')
    results=[r for r in rows if 'scene' in r]
    if [r['scene'] for r in results]!=list(range(scenes)):
        raise ValueError('missing, duplicate, or unordered scene rows')
    for r in results:
        if r.get('live_owned_objects')!=0 or r.get('engine_estimated_texture_bytes')!=0:
            raise ValueError('scene retained owned resources')
        if r.get('context_generation')!=1+r['scene']//25:
            raise ValueError('context generation disagrees with controlled rebuild schedule')
    policies=[r for r in rows if r.get('case')=='synthetic-completion-policy']
    if len(policies)!=1 or policies[0].get('status')!='PASS' or policies[0].get('real_gpu_delayed_completion') is not False:
        raise ValueError('synthetic policy must not be attributed to GPU completion')
    if not rows or 'summary' not in rows[-1]:raise ValueError('missing final summary')
    s=rows[-1]['summary']
    expected={'status':'PASS','scenes':scenes,'surface_recreates':scenes//10,
              'controlled_context_recreates':scenes//25,'context_generation':1+scenes//25,
              'live_owned_objects':0,'engine_estimated_texture_peak_bytes':8192,
              'low_memory_signals_simulated':scenes,'budget_rejections':scenes,
              'upload_transfers':8*scenes,'readback_transfers':4*scenes,
              'canceled_transfers':4*scenes,'completed_transfers':12*scenes,
              'vram_residency_measurement':'NOT_AVAILABLE','driver_internal_leak_check':'NOT_MEASURED',
              'android_real_loss':'NOT_RUN_DEVICE','AHB_external_runtime':'NOT_RUN_DEVICE'}
    for key,value in expected.items():
        if s.get(key)!=value:raise ValueError(f'unexpected summary field {key}')
    counters=s.get('object_counters',[])
    if len(counters)!=4 or [r.get('kind') for r in counters]!=list(range(4)):
        raise ValueError('missing typed object counters')
    totals=[19*scenes+scenes//25,12*scenes,12*scenes,scenes+scenes//25]
    for row,total,peak in zip(counters,totals,[8,8,8,1]):
        if row.get('created')!=total or row.get('deleted')!=total or row.get('peak_live')!=peak:
            raise ValueError('unexplained GL object growth or missing deletes')
    for key in ['actual_zero_timeout_pending','actual_zero_timeout_complete']:
        if type(s.get(key)) is not int or s[key]<0:raise ValueError('missing actual fence polling observation')
    if s['actual_zero_timeout_pending']+s['actual_zero_timeout_complete']!=12*scenes:
        raise ValueError('actual first-poll observations inconsistent with transfers')
    return s
