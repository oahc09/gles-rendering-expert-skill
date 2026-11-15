"""Verify declared source-review -> bounded experiment -> test file bindings.
Does not re-fetch upstream, authenticate reviewers, or promote performance rules.
"""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def file_hash(root,path):
 p=(root/path).resolve()
 if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('missing/escaped file')
 return hashlib.sha256(p.read_bytes()).hexdigest()
def check(chain,root=ROOT):
 review_path='docs/v1.0.9/research/implementation-review.json'
 if chain['review_sha256']!=file_hash(root,review_path):raise ValueError('stale source review')
 reviews={r['review_id']:r for r in json.loads((root/review_path).read_text())['records']}
 if len(chain['rows'])!=len(reviews) or {r['review_id'] for r in chain['rows']}!=set(reviews):raise ValueError('review coverage')
 for row in chain['rows']:
  source=reviews[row['review_id']]
  if row['source_revision']!=source['revision'] or row['rule_promotion']!='NONE' or row['performance_claim'] is not None:raise ValueError('unauthorized promotion')
  if row['independent_review']!='NOT_RUN':raise ValueError('independent review not established')
  if row['experiment_status']=='NO_LOCAL_EXACT_EXPERIMENT':
   if row['files']:raise ValueError('absent experiment cannot bind code')
  elif row['experiment_status']=='BOUNDED_CONTROL_NOT_EXACT_UPSTREAM':
   if len(row['files'])<2:raise ValueError('code and test required')
   for f in row['files']:
    if file_hash(root,f['path'])!=f['sha256']:raise ValueError('stale experiment/test')
  else:raise ValueError('unknown evidence state')
 return {'status':'PASS','links':len(chain['rows']),'scope':'file integrity and declared mapping only','independent_review':'NOT_RUN','new_rules':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);a=p.parse_args()
 r=check(json.loads((ROOT/'docs/v1.0.9/research/experiment-chain.json').read_text()))
 s=json.dumps(r,indent=2)+'\n'
 if a.output:a.output.write_text(s)
 else:print(s,end='')
