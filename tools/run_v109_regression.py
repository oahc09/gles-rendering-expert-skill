#!/usr/bin/env python3
"""Reproducible host unit-regression summary; never hardware/provider acceptance.
Raw child stdout/stderr stays local (printed on failures). Published JSON contains
only manifest-relative paths, counts and exit status, not machine inventories.
"""
import argparse,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def summarize(directory,returncode,output):
    match=re.search(r'^Ran (\d+) tests? in ',output,re.M)
    count=int(match[1]) if match else 0
    skips=re.search(r'skipped=(\d+)',output)
    skipped=int(skips[1]) if skips else 0
    ok=bool(re.search(r'^OK(?: \([^\n]*\))?$',output,re.M))
    return {'directory':directory,'tests':count,'skipped':skipped,'returncode':returncode,
            'status':'PASS' if returncode==0 and count>0 and ok and skipped==0 else 'FAIL'}
def validate_manifest(data,root=ROOT):
    dirs=data.get('directories')
    if data.get('schema_version')!=1 or not isinstance(dirs,list) or not dirs or any(not isinstance(d,str) for d in dirs) or len(dirs)!=len(set(dirs)):
        raise ValueError('unique nonempty directory manifest required')
    for d in dirs:
        if not isinstance(d,str) or Path(d).is_absolute() or '..' in Path(d).parts:
            raise ValueError('relative directory required')
        p=(root/d).resolve()
        if not p.is_relative_to(root.resolve()) or not p.is_dir() or not any(p.glob('test_*.py')):
            raise ValueError('missing or escaped test directory')
    return dirs
def run(manifest):
    rows=[]
    for directory in validate_manifest(manifest):
        result=subprocess.run([sys.executable,'-m','unittest','discover','-s',directory,'-p','test_*.py'],cwd=ROOT,capture_output=True,text=True)
        output=result.stdout+result.stderr;row=summarize(directory,result.returncode,output);rows.append(row)
        if row['status']!='PASS':print(output,file=sys.stderr)
    return {'schema_version':1,'status':'PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',
            'total_tests':sum(x['tests'] for x in rows),'total_skipped':sum(x['skipped'] for x in rows),
            'scope':'host unit regression, not GPU runtime or physical/provider acceptance','rows':rows}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=run(json.loads((ROOT/'docs/v1.0.9/test-manifest.json').read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}));raise SystemExit(result['status']!='PASS')
