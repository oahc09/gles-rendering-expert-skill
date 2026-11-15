"""Review-only lifecycle checks over existing radar records; never activates schedules."""
import argparse,datetime,hashlib,json
from pathlib import Path
STATES={'new','verified','adopted','deprecated','superseded','disputed','blocked'}
TRANSITIONS={'new':{'verified','blocked','disputed'},'verified':{'adopted','blocked','disputed','deprecated'},'adopted':{'deprecated','superseded','disputed','blocked'},'deprecated':{'superseded','verified'},'superseded':set(),'disputed':{'verified','blocked'},'blocked':{'new','verified'}}
LEVELS={'MUST','SHOULD','CONDITIONAL','EXPERIMENTAL'}
def date(value):
 try:return datetime.date.fromisoformat(value)
 except (ValueError,TypeError):raise ValueError('ISO date required')
def validate(rows,root,today):
 root=Path(root).resolve();today=date(today);ids=set();out=[]
 for row in rows:
  ident=row.get('id')
  if not isinstance(ident,str) or not ident or ident in ids:raise ValueError('unique rule ID required')
  ids.add(ident)
  if row.get('state') not in STATES or row.get('level') not in LEVELS:raise ValueError('invalid state/level')
  if not row.get('source_url','').startswith('https://') or not row.get('claim') or not row.get('conditions'):raise ValueError('source/claim/conditions required')
  if row['level']=='MUST' and row.get('source_class')!='normative_spec':raise ValueError('MUST requires normative source, not vendor advice')
  if row.get('measured_gain') is not None:raise ValueError('lifecycle review does not certify gains; use existing physical evidence gate')
  reviewed=date(row['reviewed_at']) if row.get('reviewed_at') else None
  expires=date(row['expires_at']) if row.get('expires_at') else None
  if reviewed and reviewed>today:raise ValueError('future review')
  if row.get('workaround') and (not expires or not row.get('driver_range') or not row.get('fallback')):raise ValueError('workaround requires exact driver range, expiry and fallback')
  if row['state'] in ('verified','adopted'):
   if not reviewed or not row.get('reviewer') or not row.get('evidence'):raise ValueError('review/evidence required')
  for record in row.get('evidence',[]):
   p=(root/record.get('path','')).resolve()
   if not p.is_relative_to(root) or not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=record.get('sha256'):raise ValueError('missing or stale evidence')
  if row['state']=='adopted' and (not row.get('rule') or not row.get('example') or not row.get('test')):raise ValueError('adoption needs rule/example/test chain')
  for key in ('rule','example','test'):
   if row.get(key):
    p=(root/row[key]).resolve()
    if not p.is_relative_to(root) or not p.is_file():raise ValueError('missing chain target')
  out.append({'id':ident,'state':row['state'],'effective_state':'blocked' if expires and today>expires else row['state'],'expiry':'EXPIRED' if expires and today>expires else 'CURRENT' if expires else 'NOT_APPLICABLE','required_action':'RECONFIRM_OR_FALLBACK' if expires and today>expires else 'REVIEW' if row['state'] in ('new','disputed','blocked') else 'NONE'})
 for row in rows:
  if row['state']=='superseded' and row.get('superseded_by') not in ids:raise ValueError('missing superseding record')
 successors={r['id']:r.get('superseded_by') for r in rows if r['state']=='superseded'}
 for start in successors:
  seen=set();current=start
  while current in successors:
   if current in seen:raise ValueError('supersession cycle')
   seen.add(current);current=successors[current]
 conflicts=[]
 for i,a in enumerate(rows):
  for b in rows[i+1:]:
   if a.get('topic') and a.get('topic')==b.get('topic') and a.get('conditions')==b.get('conditions') and a.get('recommendation')!=b.get('recommendation') and a['state'] in ('verified','adopted') and b['state'] in ('verified','adopted'):
    conflicts.append({'ids':[a['id'],b['id']],'action':'HUMAN_REVIEW_NO_AUTOMATIC_WINNER'})
 return {'status':'REVIEW_REQUIRED' if conflicts or any(x['required_action']!='NONE' for x in out) else 'CONSISTENT','records':out,'conflicts':conflicts,'schedule_activated':False,'release_acceptance':False}
def transition(row,target,review):
 if target not in TRANSITIONS.get(row.get('state'),set()):raise ValueError('illegal lifecycle transition')
 if not review.get('reviewer') or not review.get('reason') or not review.get('reviewed_at'):raise ValueError('explicit review record required')
 return {**row,'state':target,'reviewer':review['reviewer'],'reviewed_at':review['reviewed_at'],'transition_reason':review['reason']}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ledger',type=Path,required=True);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--date',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=validate(json.loads(a.ledger.read_text())['rules'],a.root,a.date);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'schedule_activated':False}))
