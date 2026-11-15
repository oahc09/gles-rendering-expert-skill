"""Pinned official KTX preparation and content-keyed bounded CPU payload cache."""
import hashlib,json,os,subprocess,sys,tarfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'texture_access'))
from ktx2_container import parse
from etc2_cpu_oracle import decode_block
LOCK='a8781bad05f9624edbf910b7f258cd0a4ba7d3e63b49ecc0a0ab440bf6a0a245'
def verify_tools(root,archive):
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=LOCK:raise ValueError('official archive digest mismatch')
 # Verify extracted regular files as well, without publishing local file hashes.
 with tarfile.open(archive) as t:
  for member in t.getmembers():
   if member.issym():
    local=root.joinpath(*Path(member.name).parts[1:])
    if not local.is_symlink() or os.readlink(local)!=member.linkname:raise ValueError("tool symlink mismatch")
   if member.isfile():
    parts=Path(member.name).parts
    if not parts or '..' in parts or Path(member.name).is_absolute():raise ValueError('archive path')
    local=root.joinpath(*parts[1:])
    if local.read_bytes()!=t.extractfile(member).read():raise ValueError('extracted tool mismatch')
 return True

def quality(decoded,golden):
 if len(decoded)!=64 or len(golden)!=64 or any(type(v)!=int or not 0<=v<=255 for v in decoded+golden):raise ValueError('invalid pixels')
 return max(abs(a-b) for a,b in zip(decoded,golden))

class Cache:
 def __init__(self,root,tmp,astc):
  self.root=root;self.tmp=tmp;self.astc=astc;self.entries={};self.hits=0;self.reports=[]
  self.binary=tmp/'transcode'
  source=Path(__file__).resolve().parents[2]/'examples/texture_pipeline/transcode.cpp'
  subprocess.run(['c++','-std=c++17','-I'+str(root/'include'),str(source),'-L'+str(root/'lib'),'-Wl,-rpath,'+str(root/'lib'),'-lktx','-o',str(self.binary)],check=True,capture_output=True)
 def get(self,asset):
  if asset not in ('A','B','C'):raise ValueError('unknown asset')
  step=64 if asset=='C' else 8
  rgb=bytes(v for y in range(4) for x in range(4) for v in (x*step,y*step,(x+y)*(step//2)))
  golden=[v for i in range(16) for v in list(rgb[i*3:i*3+3])+[255]]
  mode='astc' if asset=='B' and self.astc else 'etc2'
  key=(hashlib.sha256(rgb).hexdigest(),mode,LOCK)
  if key in self.entries:self.hits+=1;return self.entries[key]
  ppm=self.tmp/(asset+'.ppm');ppm.write_bytes(b'P6\n4 4\n255\n'+rgb);source=self.tmp/(asset+'.source.ktx2');prefix=self.tmp/asset
  start=time.perf_counter_ns();subprocess.run([str(self.root/'bin/toktx'),'--t2','--encode','uastc','--threads','1','--assign_oetf','linear',str(source),str(ppm)],check=True,capture_output=True);encode=(time.perf_counter_ns()-start)/1e6
  raw=subprocess.run([str(self.binary),str(source),mode,str(prefix)],check=True,capture_output=True,text=True);stages=json.loads(raw.stdout)
  start=time.perf_counter_ns();payload=parse(prefix.with_suffix('.ktx2').read_bytes());validate=(time.perf_counter_ns()-start)/1e6
  start=time.perf_counter_ns();cpu=decode_block(payload['payload'],self.root) if mode=='etc2' else list(prefix.with_suffix('.rgba').read_bytes());decode=(time.perf_counter_ns()-start)/1e6
  error=quality(cpu,golden);fallback=error>32
  report=dict(asset=asset,requested_codec=mode,source_sha256=key[0],cpu_encode_process_ms=encode,cpu_libktx_load_ms=stages['load_ms'],cpu_libktx_transcode_ms=stages['transcode_ms'],cpu_container_validate_ms=validate,cpu_decode_or_read_ms=decode,candidate_error=error,quality_budget=32,fallback=fallback,route='ORIGINAL_RGBA8' if fallback else mode,optimization_status='REJECTED_BY_QUALITY' if fallback else 'INSUFFICIENT_EVIDENCE')
  if fallback:payload=dict(mode='rgba',width=4,height=4,payload=bytes(golden));cpu=golden
  value=dict(payload=payload,cpu=cpu,golden=golden,report=report);self.entries[key]=value;self.reports.append(report);return value
