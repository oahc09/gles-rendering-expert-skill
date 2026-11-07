#!/usr/bin/env python3
"""Validate an operator-provisioned locked software driver bundle, never fetch it."""
import argparse
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

def main():
    p=argparse.ArgumentParser();p.add_argument('--angle-root',default=os.environ.get('GLES_ANGLE_ROOT'))
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    root=Path(a.angle_root) if a.angle_root else None
    lock=json.loads(Path(__file__).with_name('driver-lock.json').read_text())
    missing=[name for name,want in lock['files'].items() if root is None or not(root/name).is_file() or hashlib.sha256((root/name).read_bytes()).hexdigest()!=want]
    if missing:
        report=dict(status='BLOCKED_BY_TOOLCHAIN',reason='Provision the tested trusted ANGLE/SwiftShader bundle; no automatic external download or execution',missing_or_mismatching=missing)
        (a.output/'summary.json').write_text(json.dumps(report,indent=2)+'\n');(a.output/'summary.md').write_text('# Host differential\n\nBLOCKED_BY_TOOLCHAIN: verified ANGLE bundle is required.\n');print(json.dumps(report));return 2
    config=[dict(kind='mesa',egl=ctypes.util.find_library('EGL') or 'libEGL.so.1',gles=os.environ.get('GLES_LIBRARY') or ctypes.util.find_library('GLESv2') or 'libGLESv2.so.2'),
            dict(kind='angle',egl=str(root/'libEGL.so'),gles=str(root/'libGLESv2.so'),icd=str(root/'vk_swiftshader_icd.json'))]
    path=a.output/'config.json';path.write_text(json.dumps(config,indent=2)+'\n')
    return subprocess.run([sys.executable,str(Path(__file__).with_name('run.py')),'--config',str(path),'--output',str(a.output/'comparison')],timeout=600).returncode
if __name__=='__main__':raise SystemExit(main())
