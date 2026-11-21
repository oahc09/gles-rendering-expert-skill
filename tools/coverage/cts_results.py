"""Index genuine supplied QPA logs without claiming Khronos certification."""
import argparse,hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
KNOWN={'Pass','Fail','QualityWarning','CompatibilityWarning','NotSupported','ResourceError','InternalError','Crash','Timeout'}
def parse_qpa(text):
 rows=[];current=None;lines=[]
 for line in text.splitlines():
  if line.startswith('#beginTestCaseResult '):
   if current is not None:raise ValueError('nested/truncated QPA case')
   current=line.split(' ',1)[1].strip();lines=[]
   if not current:raise ValueError('missing test identity')
  elif line=='#endTestCaseResult':
   if current is None:raise ValueError('orphan QPA terminator')
   try:
    xml='\n'.join(lines)
    if '<!DOCTYPE' in xml or '<!ENTITY' in xml:raise ValueError('QPA entities forbidden')
    root=ET.fromstring(xml)
   except ET.ParseError as e:raise ValueError('invalid QPA XML') from e
   if root.tag!='TestCaseResult' or root.get('CasePath') not in (None,current):raise ValueError('case identity mismatch')
   results=list(root.iter('Result'))
   if len(results)!=1 or results[0].get('StatusCode') not in KNOWN:raise ValueError('missing/unknown result')
   rows.append({'case':current,'status':results[0].get('StatusCode')});current=None
  elif current is not None:lines.append(line)
 if current is not None:raise ValueError('truncated QPA case')
 if not rows or len({x['case'] for x in rows})!=len(rows):raise ValueError('empty/duplicate QPA cases')
 return rows
def report(qpa,expected,exit_code):
 if type(exit_code) is not int:raise ValueError('integer process exit status required')
 if not isinstance(expected,list) or any(not isinstance(x,str) or not x.strip() for x in expected):raise ValueError('expected cases must be nonempty strings')
 rows=parse_qpa(qpa.decode('utf-8'));observed={r['case'] for r in rows}
 if not expected or len(expected)!=len(set(expected)):raise ValueError('enumerated unique expected cases required')
 missing=sorted(set(expected)-observed);extra=sorted(observed-set(expected))
 status='INCOMPLETE' if missing or extra else 'PASS' if exit_code==0 and all(r['status']=='Pass' for r in rows) else 'FAIL'
 return {'status':status,'raw_qpa_sha256':hashlib.sha256(qpa).hexdigest(),'rows':rows,'missing':missing,'unexpected':extra,'process_exit_code':exit_code,'certification_claim':False,'device_validation':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--qpa',type=Path,required=True);p.add_argument('--expected',type=Path,required=True);p.add_argument('--exit-code',type=int,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=report(a.qpa.read_bytes(),[x.strip() for x in a.expected.read_text().splitlines() if x.strip()],a.exit_code);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'certification_claim':False}));raise SystemExit(result['status']!='PASS')
