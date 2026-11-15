#!/usr/bin/env python3
"""Logical uncompressed attachment traffic envelope, NEVER measured DRAM."""
import argparse
import json
from pathlib import Path
from workload_fingerprint import number
FORMATS={'RGBA8':4,'RGB8':3,'RG8':2,'R8':1,'RGBA16F':8,'RG16F':4,'R16F':2,'DEPTH24_STENCIL8':4,'DEPTH16':2,'RGBA32F':16}

def estimate(data):
    output=[]; total=0; unknown=False
    for a in data.get('attachments',[]):
        for key in ('width','height','samples','passes'):
            if type(a.get(key))!=int or not 1<=a[key]<=65536: raise ValueError('invalid '+key)
        if a['samples'] not in (1,2,4,8,16): raise ValueError('unsupported sample count')
        for key in ('clear','invalidate','resolve','external_consumer'):
            if type(a.get(key))!=bool: raise ValueError('explicit boolean required '+key)
        if a['invalidate'] and a['external_consumer']: raise ValueError('cannot invalidate externally consumed attachment')
        bpp=FORMATS.get(a.get('format')); lower=0; upper=None
        if bpp:
            single=a['width']*a['height']*bpp
            # Worst logical load/store of each declared pass; not bus compression/cache.
            upper=single*a['samples']*a['passes']*2
            if a['clear']: upper-=single*a['samples']
            if a['invalidate']: upper-=single*a['samples']
            if a['resolve'] and a['samples']>1: upper+=single*(a['samples']+1)
            total+=upper
        else: unknown=True
        output.append({'id':a.get('id'),'logical_lower_bytes':lower,'logical_upper_bytes':upper})
    samples=data.get('texture_samples',0); number(samples,'texture_samples')
    texel_bytes=data.get('bytes_per_sample'); texture_upper=None
    if texel_bytes is not None: number(texel_bytes,'bytes_per_sample');texture_upper=samples*texel_bytes
    elif samples: unknown=True
    if texture_upper is not None:total+=texture_upper
    return {'status':'ESTIMATE_ONLY','attachments':output,'logical_lower_bytes':0,'logical_upper_bytes':None if unknown else total,
            'texture_fetch_logical_upper_bytes':texture_upper,'dram_bytes':None,
            'assumptions':['Uncompressed logical transfers; no fixed tile size assumed.','No MSAA compression/cache/transaction amplification model.','passes declares all load/store cycles including FBO switches.','Overdraw texture samples must be supplied, not inferred from draw count.'],
            'unknowns':['Actual tile residency, DRAM, blending and sampling cache behavior require device counters.']}

def compare_calibration(result, measurement):
    for key in ('device','gpu','driver','backend','raw_trace'):
        if not measurement.get(key): raise ValueError('calibration scope missing '+key)
    actual=number(measurement.get('logical_bytes'),'logical_bytes')
    upper=result['logical_upper_bytes']
    return {'scope':measurement,'logical_upper_error_bytes':None if upper is None else upper-actual,
            'relative_error':None if upper is None or actual==0 else (upper-actual)/actual,
            'note':'Only comparable logical transfer counter; not a calibrated DRAM prediction.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    try: result=estimate(json.loads(a.input.read_text()));code=0
    except (ValueError,KeyError,TypeError) as e:result={'status':'INVALID','error':str(e)};code=2
    s=json.dumps(result,indent=2,allow_nan=False)+'\n'
    if a.output:a.output.write_text(s)
    else:print(s,end='')
    return code
if __name__=='__main__':raise SystemExit(main())
