#!/usr/bin/env python3
"""Bounded source/license hygiene audit; not a complete vulnerability scanner."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'dbef940fd261d269ad950770a9105636bab4f915'
PATTERNS = [r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
            r'gh[pousr]_[A-Za-z0-9]{30,}', r'AKIA[0-9A-Z]{16}',
            r'sk-proj-[A-Za-z0-9_-]{40,}']

def audit(base=BASE):
    changed = subprocess.check_output(['git','diff','--name-only',base],cwd=ROOT,text=True).splitlines()
    untracked = subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines()
    files = sorted(set(changed+untracked))
    errors, scanned = [], []
    for name in files:
        path = ROOT/name
        if name.startswith('docs/v1.0.7/evidence/'):
            continue  # Avoid recursively hashing generated audit reports and logs.
        if not path.is_file() or path.suffix not in ('.py','.cpp','.hpp','.sh','.json','.yml','.yaml','.md','.txt'):
            continue
        text = path.read_text()
        for pattern in PATTERNS:
            if re.search(pattern,text): errors.append({'path':name,'kind':'credential-pattern'})
        if path.suffix=='.py':
            tree=ast.parse(text,filename=name)
            for node in ast.walk(tree):
                if isinstance(node,ast.Call):
                    if isinstance(node.func,ast.Name) and node.func.id in {'eval','exec'}:
                        errors.append({'path':name,'line':node.lineno,'kind':'dynamic-code-evaluation'})
                    if any(k.arg=='shell' and isinstance(k.value,ast.Constant) and k.value.value is True for k in node.keywords):
                        errors.append({'path':name,'line':node.lineno,'kind':'shell-true'})
        scanned.append({'path':name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    license_path=ROOT/'LICENSE'
    if 'MIT License' not in license_path.read_text(): errors.append({'kind':'root-license-changed'})
    upstream=ROOT/'references/research/2026-11-02-v107/sources/LICENSE-APACHE-2.0.txt'
    if not upstream.exists() or 'Apache License' not in upstream.read_text(): errors.append({'kind':'upstream-license-missing'})
    if not (upstream.parent/'NOTICE.md').exists(): errors.append({'kind':'upstream-attribution-missing'})
    return {'status':'PASS' if not errors else 'FAIL','baseline':base,'files':scanned,'findings':errors,
            'license_scope':'Original additions under root MIT; archived Filament excerpts retain Apache2 license and attribution.',
            'limitations':'High-confidence secret-pattern and dynamic-shell/code scan only; not a security certification, full SAST, dependency audit or legal opinion.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=Path('reports/v107-hygiene.json'))
    args=p.parse_args();report=audit();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'files':len(report['files']),'findings':report['findings']}))
    raise SystemExit(report['status']!='PASS')
