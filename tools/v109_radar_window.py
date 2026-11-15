"""Window selection for existing read-only radar; no scheduling/network side effects."""
import argparse,datetime as dt,json
def window(mode,end):
 if mode not in ('weekly','monthly'):raise ValueError('weekly or monthly required')
 if not isinstance(end,dt.date):raise ValueError('date required')
 days=7 if mode=='weekly' else 90
 return {'mode':mode,'start':str(end-dt.timedelta(days=days-1)),'end':str(end),'inclusive_days':days}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--mode',choices=['weekly','monthly'],required=True);p.add_argument('--end',type=dt.date.fromisoformat,default=dt.datetime.now(dt.timezone.utc).date());a=p.parse_args();print(json.dumps(window(a.mode,a.end)))
