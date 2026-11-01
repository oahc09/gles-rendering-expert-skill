#!/usr/bin/env python3
"""RGB8 encoded-domain regression metrics, not perceptual HDR certification.
Reuse the existing strict P6 decoder. SSIM is local 8x8, population covariance,
constants (0.01*255)^2/(0.03*255)^2, computed on encoded luma (Rec.709 weights).
"""
import importlib.util
import math
from pathlib import Path
MODULE = Path(__file__).resolve().parents[1] / 'scenes/run.py'
spec = importlib.util.spec_from_file_location('scene_image_io', MODULE)
scene_io = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scene_io)
read_ppm = scene_io.read_ppm


def write_ppm(path, w, h, data):
    Path(path).write_bytes(f'P6\n{w} {h}\n255\n'.encode() + bytes(data))


def downsample(w, h, pixels, factor):
    if w % factor or h % factor:
        raise ValueError('Multiscale dimensions must be divisible by factor')
    out = []
    for y in range(0, h, factor):
        for x in range(0, w, factor):
            for c in range(3):
                out.append(sum(pixels[((y+j)*w+x+i)*3+c]
                               for j in range(factor) for i in range(factor)) / factor**2)
    return w//factor, h//factor, out


def local_ssim(w, h, a, b):
    la = [sum(a[i+c]*v for c,v in enumerate((.2126,.7152,.0722))) for i in range(0,len(a),3)]
    lb = [sum(b[i+c]*v for c,v in enumerate((.2126,.7152,.0722))) for i in range(0,len(b),3)]
    scores = []
    for y in range(0,h,8):
        for x in range(0,w,8):
            ids = [j*w+i for j in range(y,min(y+8,h)) for i in range(x,min(x+8,w))]
            aa,bb = [la[i] for i in ids],[lb[i] for i in ids]
            ma,mb = sum(aa)/len(aa),sum(bb)/len(bb)
            va,vb = sum((v-ma)**2 for v in aa)/len(aa),sum((v-mb)**2 for v in bb)/len(bb)
            cov = sum((u-ma)*(v-mb) for u,v in zip(aa,bb))/len(aa)
            scores.append(((2*ma*mb+6.5025)*(2*cov+58.5225))/((ma*ma+mb*mb+6.5025)*(va+vb+58.5225)))
    return sum(scores)/len(scores)


def masks(w,h,reference,scene):
    luma = [sum(reference[i+c]*v for c,v in enumerate((.2126,.7152,.0722))) for i in range(0,len(reference),3)]
    edge=[]
    for y in range(h):
        for x in range(w):
            i=y*w+x
            edge.append(abs(luma[i]-luma[y*w+min(w-1,x+1)])+abs(luma[i]-luma[min(h-1,y+1)*w+x])>8)
    return {'global':[True]*(w*h),'edge':edge,
            'shadow':[v<80 for v in luma], 'glow':[v>190 for v in luma],
            'transparent':[((x/w-.5)**2+(y/h-.5)**2<.16 and scene=='P06') for y in range(h) for x in range(w)]}


def compare(reference, actual, config, scene, heatmap=None):
    w,h,a=read_ppm(reference);x,y,b=read_ppm(actual)
    if (w,h)!=(x,y): raise ValueError('Image size mismatch')
    result={'scales':{},'regions':{},'pass':True}
    for factor in (1,2,4):
        ww,hh,aa=downsample(w,h,a,factor);_,_,bb=downsample(w,h,b,factor)
        mae=sum(abs(u-v) for u,v in zip(aa,bb))/len(aa)
        ssim=local_ssim(ww,hh,aa,bb)
        ok=mae<=config['multiscale'][str(factor)]['mae_max'] and ssim>=config['multiscale'][str(factor)]['ssim_min']
        result['scales'][str(factor)]={'mae':mae,'local_luma_ssim':ssim,'pass':ok}
        result['pass'] &= ok
    for name,mask in masks(w,h,a,scene).items():
        differences=[abs(a[i*3+c]-b[i*3+c]) for i,on in enumerate(mask) if on for c in range(3)]
        if not differences:
            result['regions'][name]={'status':'NOT_APPLICABLE','pixels':0};continue
        mae=sum(differences)/len(differences);maximum=max(differences)
        bad=sum(v>config['regions'][name]['channel_tolerance'] for v in differences)/len(differences)
        ok=mae<=config['regions'][name]['mae_max'] and bad<=config['regions'][name]['fraction_max'] and maximum<=config['regions'][name]['max_error']
        result['regions'][name]={'pixels':len(differences)//3,'mae':mae,'max_error':maximum,'bad_fraction':bad,'pass':ok}
        result['pass'] &= ok
    if heatmap:
        heat=[]
        for i in range(0,len(a),3):
            value=min(255,4*max(abs(a[i+c]-b[i+c]) for c in range(3)))
            heat.extend((value,0,255-value))
        write_ppm(heatmap,w,h,heat)
    return result


def temporal(reference_frames, actual_frames, maximum_mae=1.5):
    if len(reference_frames)!=len(actual_frames) or len(reference_frames)<2:
        raise ValueError('Temporal comparison needs matching sequences >=2')
    refs=[read_ppm(p) for p in reference_frames]; acts=[read_ppm(p) for p in actual_frames]
    if len({(w,h) for w,h,_ in refs+acts})!=1: raise ValueError('Temporal dimensions differ')
    errors=[]
    for i in range(1,len(refs)):
        a,b=refs[i-1][2],refs[i][2];c,d=acts[i-1][2],acts[i][2]
        errors.append(sum(abs((v-u)-(y-x)) for u,v,x,y in zip(a,b,c,d))/len(a))
    return {'delta_mae_8bit':errors,'allowed_delta_mae':maximum_mae,'pass':all(v<=maximum_mae for v in errors)}
