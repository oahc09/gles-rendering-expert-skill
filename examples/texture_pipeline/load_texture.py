#!/usr/bin/env python3
"""Select one Basis payload's runtime target from an explicit DeviceLab snapshot.
Transcode only; upload is caller-owned on the current GL context. Never select by brand.
"""
import argparse,json,subprocess
from pathlib import Path
from policy import texture_target

def load(binary,source,prefix,snapshot,denied=()):
    major=snapshot.get('gles_major')
    target=texture_target(major,snapshot.get('gl_extensions'),denied)
    if target is None:raise ValueError('No allowed texture path')
    process=subprocess.run([str(binary),str(source),target,str(prefix)],capture_output=True,text=True,timeout=120)
    if process.returncode:raise ValueError('Transcode failed; reject resource rather than upload incomplete bytes: '+process.stderr)
    record=json.loads(process.stdout)
    if record.get('status')!='TRANSCODED' or record.get('target')!=target:raise ValueError('Runtime result mismatch')
    record.update(selection='exact extension/core version predicates',capability_source={'gl_vendor':snapshot.get('gl_vendor'),'gl_renderer':snapshot.get('gl_renderer'),'gl_version':snapshot.get('gl_version')})
    return record
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--output-prefix',type=Path,required=True);p.add_argument('--probe',type=Path,required=True);p.add_argument('--deny',action='append',default=[]);a=p.parse_args()
    capture=json.loads(a.probe.read_text());snapshot=capture.get('snapshot',capture)
    print(json.dumps(load(a.binary,a.source,a.output_prefix,snapshot,a.deny)))
