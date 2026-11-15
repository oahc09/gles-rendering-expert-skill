"""Restore losslessly packed coverage data with two hashes; no network or overwrite."""
import argparse,gzip,hashlib,json,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def materialize(root=ROOT,fetch_public=False):
 root=Path(root).resolve();manifest=json.loads((root/'references/coverage/packed-artifacts.json').read_text());count=0
 for row in manifest['artifacts']:
  target=(root/row['path']).resolve()
  if not target.is_relative_to(root):raise ValueError('target path escape')
  if row.get('distribution')=='EXTERNAL_PUBLIC_DEPENDENCY_NOT_VENDORED':
   if target.is_file():data=target.read_bytes()
   elif not fetch_public:raise ValueError('INCOMPLETE: exact public gl.xml is not vendored; explicit --fetch-public required')
   else:
    url=row['source_url'];commit=row['source_commit']
    if not url.startswith('https://raw.githubusercontent.com/KhronosGroup/OpenGL-Registry/'+commit+'/') or len(commit)!=40:raise ValueError('unfixed public dependency')
    with urllib.request.urlopen(url,timeout=30) as response:data=response.read(row['bytes']+1)
   if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('public dependency digest mismatch')
   if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
   count+=1;continue
  packed=(root/row['packed_path']).resolve()
  if not target.is_relative_to(root) or not packed.is_relative_to(root):raise ValueError('archive path escape')
  raw=packed.read_bytes()
  if len(raw)!=row['packed_bytes'] or hashlib.sha256(raw).hexdigest()!=row['packed_sha256']:raise ValueError('packed digest mismatch')
  data=gzip.decompress(raw)
  if len(data)!=row['bytes'] or hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('restored digest mismatch')
  if target.exists():
   if target.read_bytes()!=data:raise ValueError('refuse to overwrite modified data')
  else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  count+=1
 return {'status':'EXACT_BYTES_VERIFIED','artifacts':count,'network_allowed':fetch_public}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--fetch-public',action='store_true');a=p.parse_args();print(json.dumps(materialize(fetch_public=a.fetch_public)))
