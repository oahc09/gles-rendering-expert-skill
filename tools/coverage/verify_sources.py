"""Read-only pinned-source verification. Never fetch moving HEAD or rewrite snapshots."""
import argparse,hashlib,json,re,urllib.request
from pathlib import Path
from urllib.parse import urlsplit
MAX=8*1024*1024
def verify(manifest,online=False,fetch=None):
 manifest=Path(manifest);data=json.loads(manifest.read_text());rows=[]
 def download(url):
  with urllib.request.urlopen(url,timeout=45) as response:
   raw=response.read(MAX+1)
   if len(raw)>MAX:raise ValueError('source too large')
   return raw
 fetch=fetch or download
 for src in data['sources']:
  row={'repository':src['repository'],'commit':src['commit'],'mode':'ONLINE_PINNED' if online else 'OFFLINE','status':'INCOMPLETE'}
  try:
   url=urlsplit(src['url'])
   if url.scheme!='https' or url.netloc!='raw.githubusercontent.com' or not re.fullmatch('[0-9a-f]{40}',src['commit']) or '/'+src['commit']+'/' not in url.path:raise ValueError('source not pinned official raw GitHub URL')
   if online:raw=fetch(src['url'])
   else:
    p=(manifest.parent/src['file']).resolve()
    if not p.is_relative_to(manifest.parent.resolve()):raise ValueError('source escape')
    raw=p.read_bytes()
   if hashlib.sha256(raw).hexdigest()!=src['sha256'] or len(raw)!=src['bytes']:raise ValueError('source digest/size mismatch')
   row['status']='PASS'
  except Exception as ex:row['reason']=type(ex).__name__ # no host/network identifiers
  rows.append(row)
 return {'status':'PASS' if rows and all(r['status']=='PASS' for r in rows) else 'INCOMPLETE','rows':rows,'baseline_mutated':False}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,default=Path('references/coverage/source-manifest.json'));p.add_argument('--online',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=verify(a.manifest,a.online);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(r['status']);raise SystemExit(r['status']!='PASS')
