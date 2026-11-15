"""Validate scene acceptance bookkeeping; file existence is not runtime proof."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DIMENSIONS=('correctness','quality','performance')
STATUSES={'PARTIAL','NOT_RUN','BLOCKED_BY_HARDWARE'}
def check(data, root=ROOT):
    if data.get('schema_version')!=1 or data.get('release_ready') is not False:
        raise ValueError('candidate-only schema required')
    scenes=data.get('scenes',[])
    if len(scenes)!=8 or {s.get('id') for s in scenes}!={f'S{i:02}' for i in range(1,9)}:
        raise ValueError('exactly eight unique original scenes required')
    for s in scenes:
        if not s.get('scope') or not s.get('remaining'):
            raise ValueError('explicit scope and remaining work required')
        for dim in DIMENSIONS:
            row=s.get(dim,{})
            if row.get('status') not in STATUSES or not row.get('reason'):
                raise ValueError('explicit conservative status/reason required')
            if dim=='performance' and row['status']!='BLOCKED_BY_HARDWARE':
                raise ValueError('no measured device evidence registered')
        refs=s.get('implementation',[])
        if not refs and any(s[d]['status']=='PARTIAL' for d in DIMENSIONS):
            raise ValueError('partial implementation needs references')
        for ref in refs:
            p=(root/ref).resolve()
            if not p.is_relative_to(root.resolve()) or not p.is_file():
                raise ValueError('invalid implementation reference')
    return {'bookkeeping':'PASS','acceptance':'INCOMPLETE','scenes':8,'release_ready':False}
if __name__=='__main__':
    print(json.dumps(check(json.loads((ROOT/'docs/v1.0.9/scene-coverage.json').read_text()))))
