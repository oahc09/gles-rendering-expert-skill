"""Bounded three-wavelength thin-film teaching approximation, not spectral PBR."""
import math, hashlib, json, importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('prior_material',ROOT/'benchmarks/pipeline/material.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
ABI={'gles':'3.0','blocks':[{'name':'Film','kind':'ubo','layout':'std140','binding':0,'size':16,'members':[{'name':'parameters','type':'vec4','offset':0}]}],'samplers':[]}
def validate(d):
    if not isinstance(d,dict) or type(d.get('version')) is not int or d['version'] not in (1,2): raise ValueError('VERSION')
    allowed={'version','thickness_nm','ior','strength'} if d['version']==2 else {'version','thickness_nm'}
    if set(d)-allowed: raise ValueError('UNKNOWN_FIELD')
    for key,default,low,high in [('thickness_nm',400,0,1200),('ior',1.4,1.01,2.5),('strength',1,0,1)]:
        v=d.get(key,default)
        if type(v) not in (int,float) or not math.isfinite(v) or not low<=v<=high: raise ValueError(key)
    if prior.validate(ABI): raise ValueError('ABI')
    return dict(version=2,thickness_nm=d.get('thickness_nm',400),ior=d.get('ior',1.4),strength=d.get('strength',1))
def migrate(d,target):
    n=validate(d)
    if target==2:return n
    if target!=1:raise ValueError('TARGET_VERSION')
    if n['ior']!=1.4 or n['strength']!=1:raise ValueError('LOSSY_ROLLBACK')
    return {'version':1,'thickness_nm':n['thickness_nm']}
def cache_key(d,shader,driver,precision='highp'):
    if precision not in ('highp','mediump'):raise ValueError('PRECISION')
    return hashlib.sha256(json.dumps([validate(d),ABI,shader,driver,precision],sort_keys=True,allow_nan=False).encode()).hexdigest()
def rgb(thickness,mu,ior=1.4,strength=1):
    # Snell optical path; normal-incidence interface amplitudes approximation.
    ct=math.sqrt(max(0,1-(1-mu*mu)/(ior*ior)))
    r01=(1-ior)/(1+ior);r12=(ior-1.5)/(ior+1.5)
    result=[]
    for wave in (650,510,475):
        c=math.cos(4*math.pi*ior*thickness*ct/wave)
        refl=(r01*r01+r12*r12+2*r01*r12*c)/(1+(r01*r12)**2+2*r01*r12*c)
        result.append((1-strength)*.04+strength*refl)
    return result
