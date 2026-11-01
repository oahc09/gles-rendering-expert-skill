#!/usr/bin/env python3
import argparse,json,hashlib
from pathlib import Path
from policy import QualityPolicy

def replay(data):
    policy=QualityPolicy(**data.get('policy',{}))
    return [policy.step(s,enabled=s.get('enabled',True),capabilities=data.get('capabilities'),approved_levels=data.get('approved_levels',[])) for s in data['samples']]

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    data=json.loads(a.input.read_text());result={'source_sha256':hashlib.sha256(a.input.read_bytes()).hexdigest(),'scope':'deterministic recommendation replay, not GPU or device performance','decisions':replay(data)}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
