#!/usr/bin/env python3
"""Normalize existing radar metadata to the original plan contract, without promotion."""
import argparse,gzip,hashlib,json,re
from datetime import datetime
from pathlib import Path
FIELDS=('source_url','event_date','discovered_at','platform','gpu','driver','gles_version','evidence_class','affected_rules','repro','decision','test_id')

def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode()
def timestamp(value):
    if not isinstance(value,str):raise ValueError('timestamp must be actual recorded string')
    try:parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    except ValueError:raise ValueError('invalid timestamp')
    if parsed.tzinfo is None:raise ValueError('timestamp requires timezone')
    return value

def normalized(source,receipt):
    raw=Path(source).read_bytes();decoded=gzip.decompress(raw)
    if sha(raw)!=receipt.get('archive_sha256') or sha(decoded)!=receipt.get('decoded_sha256'):raise ValueError('stale or changed source archive')
    corpus=json.loads(decoded);discovered=timestamp(corpus.get('fetched_at'))
    items=corpus.get('items')
    if not isinstance(items,list) or len(items)!=receipt.get('candidate_count'):raise ValueError('source candidate count mismatch')
    rows=[];seen=set()
    for item in items:
        for key in ('url','event_at','source_hash','source','id','revision'):
            if not isinstance(item.get(key),str) or not item[key].strip():raise ValueError('missing source field '+key)
        if not item['url'].startswith('https://') or not re.fullmatch('[0-9a-f]{64}',item['source_hash']):raise ValueError('source URL/hash invalid')
        timestamp(item['event_at']);identity=(item['source'],item['id'])
        if identity in seen:raise ValueError('duplicate source identity')
        seen.add(identity)
        rows.append({'source_url':item['url'],'event_date':item['event_at'],'discovered_at':discovered,
            'platform':None,'gpu':None,'driver':None,'gles_version':None,
            'evidence_class':'UNVERIFIED','affected_rules':[],'repro':None,
            'decision':'PENDING_REVIEW_NO_RULE_PROMOTION','test_id':None,
            'source_binding':{'source':item['source'],'id':item['id'],'revision':item['revision'],
                'source_hash':item['source_hash'],'event_time_kind':item.get('event_time_kind')}})
    rows.sort(key=lambda r:(r['source_binding']['source'],r['source_binding']['id']))
    return {'schema_version':1,'scope':'metadata normalization only; selected reviews remain separate authoritative records',
        'discovered_at_semantics':'original corpus fetched_at, not claimed first discovery of each upstream item',
        'source_archive_sha256':sha(raw),'source_decoded_sha256':sha(decoded),
        'source_window':{'start':corpus.get('start'),'end':corpus.get('end')},'rows':rows}

def generate(source,source_receipt,out):
    receipt=json.loads(Path(source_receipt).read_text());index=normalized(source,receipt);data=canonical(index)
    packed=gzip.compress(data,mtime=0);out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(packed)
    note={'schema_version':1,'candidate_count':len(index['rows']),'required_fields':list(FIELDS),
        'archive':out.name,'archive_sha256':sha(packed),'decoded_sha256':sha(data),
        'source_archive_sha256':index['source_archive_sha256'],'source_decoded_sha256':index['source_decoded_sha256'],
        'source_window':index['source_window'],'discovered_at':index['rows'][0]['discovered_at'] if index['rows'] else None,
        'normalization':'PASS','independent_review':'NOT_RUN','rule_promotion':'NONE','performance_claim':None,
        'review_policy':'UNVERIFIED is this metadata-index evidence class, not a revocation of the ten selected separate AI reviews; no auto-promotion or new full-content review performed'}
    out.with_suffix('.receipt.json').write_bytes(canonical(note));return note

def validate(source,source_receipt,index,index_receipt):
    expected=normalized(source,json.loads(Path(source_receipt).read_text()))
    raw=Path(index).read_bytes();decoded=gzip.decompress(raw);actual=json.loads(decoded);receipt=json.loads(Path(index_receipt).read_text())
    if sha(raw)!=receipt.get('archive_sha256') or sha(decoded)!=receipt.get('decoded_sha256'):raise ValueError('index hash mismatch')
    if actual!=expected:raise ValueError('index missing fields, stale source mapping or unsupported promotion')
    if receipt.get('candidate_count')!=len(expected['rows']) or receipt.get('required_fields')!=list(FIELDS):raise ValueError('receipt contract mismatch')
    for key in ('source_archive_sha256','source_decoded_sha256','source_window'):
        if receipt.get(key)!=expected[key]:raise ValueError('receipt source binding mismatch')
    if receipt.get('discovered_at')!=(expected['rows'][0]['discovered_at'] if expected['rows'] else None):raise ValueError('receipt discovery time mismatch')
    if receipt.get('rule_promotion')!='NONE' or receipt.get('performance_claim') is not None or receipt.get('independent_review')!='NOT_RUN':raise ValueError('unsupported receipt claim')
    return {'status':'INDEX_CONTRACT_PASS','candidate_count':len(expected['rows']),'promoted_rules':0,'measured_claims':0,'independent_review':'NOT_RUN','scope':'integrity and metadata contract, not content acceptance'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['generate','validate']);p.add_argument('--source',type=Path,required=True);p.add_argument('--source-receipt',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--receipt',type=Path);p.add_argument('--report',type=Path);a=p.parse_args()
    try:
        result=generate(a.source,a.source_receipt,a.index) if a.mode=='generate' else validate(a.source,a.source_receipt,a.index,a.receipt or a.index.with_suffix('.receipt.json'))
        if a.report:a.report.write_bytes(canonical(result))
        print(json.dumps(result,indent=2))
    except (ValueError,KeyError,TypeError,OSError) as e:p.exit(2,str(e)+'\n')
