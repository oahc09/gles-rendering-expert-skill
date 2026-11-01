#!/usr/bin/env python3
"""Replay annotated synthetic fixtures; distinguish SQLite contract tests from native processor."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import adapter

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
builder=load('builder',adapter.HERE/'fixtures/build.py');native=load('native',adapter.HERE/'fixtures/build_native.py')
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--processor');a=p.parse_args()
    report={'sqlite_version':adapter.sqlite3.sqlite_version,'label_source':'Manually authored expected synthetic outcomes; not independent human review of device root causes.',
            'physical_device':'NOT_RUN','normalized_sqlite':[],'native_perfetto':[],
            'confusion_on_nonunknown_fixture_labels':{'true_positive':0,'false_positive':0,'true_negative':0,'false_negative':0},'abstentions':0}
    with tempfile.TemporaryDirectory(prefix='gles-trace-sql-') as tmp:
        for case in builder.CASES['cases']:
            root=Path(tmp)/case['id'];raw,meta=builder.materialize(case,root);r=adapter.run(raw,meta,root/'result')
            expected=set(case['expected_hypotheses']);actual={h['category'] for h in r.get('inferred',[])}
            match=r['status']==case['expected_status'] and actual==expected
            report['normalized_sqlite'].append({'id':case['id'],'expected_status':case['expected_status'],'actual_status':r['status'],'expected_hypotheses':sorted(expected),'actual_hypotheses':sorted(actual),'pass':match,'raw_sha256':adapter.sha(raw)})
            if case['expected_status']=='UNKNOWN':report['abstentions']+=1
            else:
                for category in adapter.legacy.RULES:
                    label=('true_positive' if category in expected else 'false_positive') if category in actual else ('false_negative' if category in expected else 'true_negative')
                    report['confusion_on_nonunknown_fixture_labels'][label]+=1
        if a.processor:
            report['processor_version']=subprocess.check_output([a.processor,'--version'],text=True).strip()
            report['processor_sha256']=hashlib.sha256(Path(a.processor).read_bytes()).hexdigest()
            root=Path(tmp)/'native';raw,meta=native.generate(root)
            for kind in ('complete','empty','truncated'):
                candidate=root/(kind+'.pftrace');candidate.write_bytes(raw.read_bytes() if kind=='complete' else (b'' if kind=='empty' else raw.read_bytes()[:-3]))
                md=dict(meta,raw_sha256=adapter.sha(candidate));result=adapter.run(candidate,md,root/(kind+'-result'),a.processor)
                actual={h['category'] for h in result.get('inferred',[])}
                expected={'shader_compile_hitch'} if kind=='complete' else set()
                match=(result['status']!='UNKNOWN' if kind=='complete' else result['status']=='UNKNOWN') and actual==expected
                report['native_perfetto'].append({'id':kind,'actual_status':result['status'],'actual_hypotheses':sorted(actual),'pass':match,'raw_sha256':adapter.sha(candidate),'provenance':'synthetic native TrackEvent protobuf'})
        else:report['native_perfetto_status']='NOT_RUN_TOOLCHAIN'
    report['status']='PASS' if all(x['pass'] for x in report['normalized_sqlite']+report['native_perfetto']) else 'FAIL'
    report['fixtures_sha256']=adapter.sha(adapter.HERE/'fixtures/cases.json')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'sqlite_fixtures':len(report['normalized_sqlite']),'native_processor_fixtures':len(report['native_perfetto'])}));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
