"""Conditional workaround review; reuse DeviceLab identity, never infer GPU from brand."""
import datetime as dt
import re
import importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('device_lab',Path(__file__).resolve().parents[1]/'device_lab/lab.py')
lab=importlib.util.module_from_spec(s);s.loader.exec_module(lab)
FIELDS={'id','vendor','renderer','driver','os','backend','extensions_all','extensions_absent','symptom','minimal_reproducer','source','confidence','regression_tests','expiry','withdraw_when','action','evidence'}

def validate_issue(issue):
    if FIELDS-set(issue):raise ValueError('Incomplete conditional issue')
    for name in ('vendor','renderer','driver','os','backend'):
        if not isinstance(issue[name],list) or not issue[name] or any(not isinstance(x,str) or not x or x=='*' for x in issue[name]):raise ValueError('Exact bounded identity lists required')
    for name in ('extensions_all','extensions_absent','regression_tests'):
        if not isinstance(issue[name],list):raise ValueError('Lists required')
    if set(issue['extensions_all'])&set(issue['extensions_absent']):raise ValueError('Contradictory predicates')
    if not issue['source'].startswith('https://') or not issue['minimal_reproducer'] or not issue['regression_tests'] or not issue['withdraw_when']:raise ValueError('Source, repro and revocation required')
    if issue['confidence'] not in ('synthetic','candidate','confirmed'):raise ValueError('Unknown confidence')
    dt.date.fromisoformat(issue['expiry'])
    if issue['confidence']=='confirmed' and not all(issue['evidence'].get(k) for k in ('raw_sha256','reproducer_sha256','before','after','device_fingerprint')):raise ValueError('Confirmed requires before/after capture evidence')
    if issue['confidence']=='confirmed':
        for key in ('raw_sha256','reproducer_sha256','device_fingerprint'):
            if not isinstance(issue['evidence'][key],str) or not re.fullmatch('[0-9a-f]{64}',issue['evidence'][key]):raise ValueError('Invalid evidence digest')
    return issue

def evaluate(record,issue,today):
    validate_issue(issue)
    if record.get('status')!='CAPTURED':return {'status':'UNKNOWN','apply':False}
    snapshot=record['snapshot'];lab.validate(record,{'backend':snapshot['backend'],'platform':snapshot['platform']})
    if dt.date.fromisoformat(today)>dt.date.fromisoformat(issue['expiry']):return {'status':'EXPIRED','apply':False}
    mapping={'vendor':'gl_vendor','renderer':'gl_renderer','driver':'gl_version','os':'os_build','backend':'backend'}
    identity=all(snapshot[field] in issue[name] for name,field in mapping.items())
    ext=set(snapshot['gl_extensions']);predicates=set(issue['extensions_all'])<=ext and not set(issue['extensions_absent'])&ext
    matched=identity and predicates
    return {'status':'MATCHED_REVIEW_REQUIRED' if matched else 'NOT_MATCHED','apply':False,
            'eligible_after_operator_review':matched and issue['confidence']=='confirmed','fingerprint':record['fingerprint'],
            'note':'This library never auto-enables a workaround; expiry/repro/withdraw conditions require review.'}
