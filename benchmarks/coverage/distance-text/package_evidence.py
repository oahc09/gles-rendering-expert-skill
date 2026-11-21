#!/usr/bin/env python3
"""Lossless deterministic packaging; collection and acceptance are unchanged."""
import gzip,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def package(directory):
 directory=Path(directory);entries=[]
 for driver in ('mesa','angle'):
  name=driver+'.json';raw=(directory/name).read_bytes();report=json.loads(raw)
  compressed=gzip.compress(raw,compresslevel=9,mtime=0)
  # Normalize the nonsemantic OS header byte across Python/zlib versions.
  compressed=compressed[:9]+b'\xff'+compressed[10:]
  if gzip.decompress(compressed)!=raw:raise ValueError('lossless verification failed')
  (directory/(name+'.gz')).write_bytes(compressed)
  entries.append(dict(file=name+'.gz',uncompressed_file=name,sha256=hashlib.sha256(raw).hexdigest(),compressed_sha256=hashlib.sha256(compressed).hexdigest(),bytes=len(raw),compressed_bytes=len(compressed),status=report['status'],draws=report['draws'],observations=len(report['rows']),pixel_values=sum(len(row['pixels']) for row in report['rows'])))
 result=dict(schema_version=1,encoding='gzip',lossless=True,entries=entries)
 (directory/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':package(HERE/'evidence')
