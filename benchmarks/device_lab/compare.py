#!/usr/bin/env python3
"""Compare recorded backend captures; never treats software as a native/ANGLE pair."""
import argparse
import json
from pathlib import Path
from lab import validate

def compare(left,right):
    for c in (left,right):validate(c,{'platform':c['snapshot']['platform'],'backend':c['snapshot']['backend']})
    a,b=left['snapshot'],right['snapshot']
    same_device=all(a[k]==b[k] for k in ('device','platform','os','os_build'))
    physical=a['hardware_kind']==b['hardware_kind']=='physical'
    target_pair={a['backend'],b['backend']}=={'native','angle_vulkan'}
    diffs={k:{'left':a.get(k),'right':b.get(k)} for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k)}
    return {'same_device':same_device,'physical_pair':physical,'native_angle_pair':target_pair,
        'status':'PAIRED_CAPTURE_REVIEW_REQUIRED' if same_device and physical and target_pair else 'NOT_TARGET_PAIR',
        'differences':diffs,'acceptance':False,'remaining':'Repeat each backend, review raw correctness/visual artifacts and backend creation provenance. Snapshot schema alone does not establish real-device conformance.'}
def main():
    p=argparse.ArgumentParser();p.add_argument('left',type=Path);p.add_argument('right',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:r=compare(json.loads(a.left.read_text()),json.loads(a.right.read_text()));a.output.write_text(json.dumps(r,indent=2)+'\n');return 0
    except (ValueError,KeyError,OSError) as e:print(str(e));return 2
if __name__=='__main__':raise SystemExit(main())
