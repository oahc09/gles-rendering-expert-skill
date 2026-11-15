#!/usr/bin/env python3
"""Replay precision-policy selections against separately fixed CPU target contracts."""
import argparse,hashlib,json,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import blend_precision as b
import tiered as t
import projected as p
FORMATS=('RGBA8','RGBA16F','RGBA32F')
def draw_format(name,objects,camera,unorm,floating):
 if name=='RGBA8':return unorm.draw(objects,camera)
 if name=='RGBA16F':return floating.draw(objects,camera)
 if name=='RGBA32F':return floating.draw(objects,camera,full_float=True)
 raise ValueError('Unknown precision selection')
def replay(decision,draw,golden):
 selected=decision['selected']
 if selected is None:return dict(status='UNAVAILABLE',selected=None,executed=False),None
 if selected not in FORMATS:raise ValueError('Unknown precision selection')
 pixels=draw(selected);metrics=p.metrics(pixels,golden)
 return dict(status='PASS' if t.accepted(metrics) else 'FAIL',selected=selected,executed=True,metrics=metrics),pixels
def budget_scenarios(extensions,max_size):
 generous=dict(max_allocation_bytes=81920,max_logical_transfer_bytes=16_000_000,max_renderbuffer_size=max_size)
 return [
  ('full_budget',extensions,generous),
  ('rgba8_allocation_only',extensions,dict(generous,max_allocation_bytes=16384)),
  ('masked_float_capabilities',[x for x in extensions if x not in ('GL_EXT_color_buffer_float','GL_EXT_color_buffer_half_float','GL_EXT_float_blend')],generous),
  ('no_transfer',extensions,dict(generous,max_logical_transfer_bytes=0)),
  ('no_storage',extensions,dict(generous,max_allocation_bytes=0,max_logical_transfer_bytes=0)),
  ('undersized_limit',extensions,dict(generous,max_renderbuffer_size=32))]
def run(config,output):
 from precision_policy import choose
 path=Path(output);path.parent.mkdir(parents=True,exist_ok=True);unorm=t.TierHost(config);floating=b.FloatHost(config)
 count=0;probe_readbacks=0;replay_readbacks=0;probe_draws=0;replay_draws=0;rows=[];observations=[];artifacts={}
 # Runtime queried, not assumed from driver name. Exact limit is not public environment metadata.
 limit=p.I();floating.fn('glGetIntegerv',None,[p.U,p.P])(0x84e8,b.C.byref(limit))
 if floating.error() or limit.value<64:raise RuntimeError('Required renderbuffer limit query/size failed')
 extensions=floating.metadata['extensions']
 try:
  for n in (8,48):
   obs=t.scene(n)
   for cam in (0,.3):
    prefix=f'n{n}-cam{cam}';goldens={'original_unorm':b.reference(obs,cam,'ideal8'),'linear':b.reference(obs,cam,'linear')};actual={};unsupported=[]
    for name in FORMATS:
     try:actual[name]=draw_format(name,obs,cam,unorm,floating);count+=1;probe_readbacks+=1;probe_draws+=n
     except b.UnsupportedCapability:unsupported.append(name)
    quality={target:{name:name in actual and t.accepted(p.metrics(actual[name],gold)) for name in FORMATS} for target,gold in goldens.items()}
    observations.append(dict(count=n,camera=cam,quality_by_target=quality,unsupported=unsupported,metrics_by_target={target:{name:p.metrics(pix,gold) for name,pix in actual.items()} for target,gold in goldens.items()}))
    for name,pix in actual.items():artifacts[prefix+'-probe-'+name+'.rgba']=bytes(pix)
    for target,gold in goldens.items():
     artifacts[prefix+'-golden-'+target+'.rgba']=bytes(gold)
     for scenario,allowed,budget in budget_scenarios(extensions,limit.value):
      decision=choose(64,64,n,allowed,quality[target],target,budget)
      result,pixels=replay(decision,lambda name:draw_format(name,obs,cam,unorm,floating),gold)
      if pixels is not None:
       count+=1;replay_readbacks+=1;replay_draws+=n;artifacts[prefix+'-'+target+'-'+scenario+'.rgba']=bytes(pixels)
      # Do not publish actual extension inventories or hardware limits, only policy decisions/costs.
      safe_decision={k:v for k,v in decision.items() if k in ('selected','candidates','status','target_contract','performance_acceptance')}
      rows.append(dict(count=n,camera=cam,target_contract=target,scenario=scenario,quality=quality[target],decision=safe_decision,replay=result,artifact_prefix=prefix+'-'+target+'-'+scenario))
 finally:floating.close();unorm.close()
 archive=path.with_suffix('.zip')
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for name,value in sorted(artifacts.items()):
   info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,value)
 forced_unavailable=all(x['replay']['status']=='UNAVAILABLE' for x in rows if x['scenario'] in ('no_storage','no_transfer','undersized_limit'))
 result=dict(status='HOST_PASS' if forced_unavailable and all(x['replay']['status'] in ('PASS','UNAVAILABLE') for x in rows) else 'FAIL',scope='finite original_unorm vs linear target-specific capability/estimated logical-budget gate and actual selected-format redraw; unavailable is rejection, not quality success',performance_status='NOT_MEASURED',logical_cost_warning='allocation/logical transfer upper bounds are not actual DRAM bandwidth or GPU time',readbacks=count,probe_readbacks=probe_readbacks,replay_readbacks=replay_readbacks,probe_draw_calls=probe_draws,replay_draw_calls=replay_draws,probe_budget_scope='Independent bounded verification overhead: probes precede scenario admission and are not subject to simulated scenario budgets; not a production zero-overhead switcher',unavailable_extra_draws=0,policy_calls=len(rows),observations=observations,rows=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),artifact_archive=dict(file=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),instructions='Extract beside report; all .rgba are 64x64 bottom-up RGBA8'))
 result['dependency_source_sha256']={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ('precision_policy.py','tiered.py','blend_precision.py','projected.py')}
 path.write_text(json.dumps(result,indent=2)+'\n');return result
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);parser.add_argument('--output',required=True);a=parser.parse_args();r=run(json.loads(Path(a.config).read_text()),a.output);print(r['status']);raise SystemExit(r['status']!='HOST_PASS')
