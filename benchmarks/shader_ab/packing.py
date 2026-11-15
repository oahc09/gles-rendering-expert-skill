#!/usr/bin/env python3
"""Source-informed packing boundary controls, not reproduction of a 16-bit driver bug."""
import argparse
import ctypes as C
import importlib.util
import json
import math
from pathlib import Path
SPEC=importlib.util.spec_from_file_location('packing_shader_ab',Path(__file__).with_name('run.py'))
ab=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(ab)

UNSIGNED=[(0,0,0,0),(1,1,1,1),(0,1,0,1),(1,0,1,0),(.25,.5,.75,1),(-1,2,0,1),(1/255,127/255,128/255,254/255),(254/255,128/255,127/255,1/255)]
SIGNED=[(-1,-1,-1,-1),(1,1,1,1),(-1,0,1,0),(0,0,0,0),(-.75,-.25,.25,.75),(-2,2,0,1),(-126/127,-1/127,1/127,126/127),(126/127,1/127,-1/127,-126/127)]
WORDS=[0,0xffffffff,0x010080ff,0x7f80fe01,0x80808080,0x7f7f7f7f,0x00ff007f,0x817e01ff]

def nearest(x):return math.floor(x+.5) if x>=0 else math.ceil(x-.5)
def pack(values,signed):
    multiplier=127 if signed else 255
    return sum((nearest(max(-1 if signed else 0,min(1,x))*multiplier)&255)<<(8*i) for i,x in enumerate(values))
def bytes_rgba(word):return [(word>>(8*i))&255 for i in range(4)]
def unpack(word,signed):
    b=bytes_rgba(word)
    if signed:return [max(-1,(x-256 if x>=128 else x)/127) for x in b]
    return [x/255 for x in b]
def output_pixel(values,signed):return [nearest(max(0,min(1,(x*.5+.5) if signed else x))*255) for x in values]
def cases():
    rows=[]
    for signed in (False,True):
        for operation in ('pack','unpack'):
            values=(SIGNED if signed else UNSIGNED) if operation=='pack' else WORDS
            for offset in (0,4):
                selected=values[offset:offset+4]
                pixels=[bytes_rgba(pack(v,signed)) if operation=='pack' else output_pixel(unpack(v,signed),signed) for v in selected]
                rows.append({'id':('snorm' if signed else 'unorm')+'-'+operation+'-'+str(offset//4),'signed':signed,'operation':operation,'values':selected,'golden':sum(pixels,[])*4})
    return rows

def source(case,variant):
    signed=case['signed'];operation=case['operation'];legacy=variant=='legacy'
    if operation=='pack':
        array=','.join('vec4('+','.join(format(x,'.12g')+('.0' if float(x).is_integer() else '') for x in v)+')' for v in case['values'])
        convert='uint(int(v.COMP)&0xff)' if signed else 'uint(v.COMP)'
        declarations=[]
        for name,comp,shift in zip('abcd','xyzw',(0,8,16,24)):
            expression=convert.replace('COMP',comp)
            if legacy and shift:expression+=' << '+str(shift)
            declarations.append('highp uint '+name+'='+expression+';')
        result='a|b|c|d' if legacy else 'a|(b<<8u)|(c<<16u)|(d<<24u)'
        body=f'mediump vec4 inputValues[4]=vec4[4]({array});mediump vec4 v=inputValues[int(gl_FragCoord.x)];v=round(clamp(v,{"-1.0" if signed else "0.0"},1.0)*{127 if signed else 255}.0);'+''.join(declarations)+'highp uint word='+result+';'
        if variant=='negative':body+='word=word & 0x00ffffffu;'
        body+='color=vec4(float(word&255u),float((word>>8u)&255u),float((word>>16u)&255u),float((word>>24u)&255u))/255.0;'
    else:
        array=','.join(str(v)+'u' for v in case['values'])
        body='highp uint words[4]=uint[4]('+array+');highp uint word=words[int(gl_FragCoord.x)];'
        if signed:
            for name,shift in zip('abcd',(0,8,16,24)):
                body+=('' if legacy else 'highp ')+'int '+name+'=int(((word>>'+str(shift)+'u)&255u)<<24u)>>24;'
            body+='vec4 v=clamp(vec4(float(a),float(b),float(c),float(d))/127.0,-1.0,1.0);color=v*0.5+0.5;'
        else:body+='color=vec4(float(word&255u),float((word>>8u)&255u),float((word>>16u)&255u),float((word>>24u)&255u))/255.0;'
        if variant=='negative':body+='color.a=0.0;'
    return '#version 300 es\nprecision highp float;precision mediump int;layout(location=0) out vec4 color;void main(){'+body+'}'

def compare(row,golden):
    if (row.get('status')!='EXECUTED' or row.get('compile') is not True or row.get('link') is not True or row.get('harness_gl_error')!=0 or len(row.get('pixels',[]))!=64 or len(golden)!=64 or any(type(v) is not int or not 0<=v<=255 for v in row.get('pixels',[])+golden)):return {'status':'UNKNOWN','max_error':None}
    error=max(abs(x-y) for x,y in zip(row['pixels'],golden));return {'status':'PASS' if error<=1 else 'FAIL','max_error':error}

def run(config):
    h=ab.ExperimentHost(config);rows=[];precision={}
    try:
        for name,enum in [('mediump_int',0x8df4),('highp_int',0x8df5),('mediump_float',0x8df1)]:
            ranges=(ab.I*2)();bits=ab.I();h.fn('glGetShaderPrecisionFormat',None,[ab.U,ab.U,ab.P,ab.P])(0x8b30,enum,ranges,C.byref(bits))
            precision[name]={'range':list(ranges),'precision':bits.value}
        for c in cases():
            draws={v:h.draw(c['id'],source(c,v)) for v in ('fixed','negative','legacy')}
            evaluations={v:compare(draw,c['golden']) for v,draw in draws.items()}
            rows.append({'id':c['id'],'cpu_golden':c['golden'],'evaluations':evaluations,'draws':draws})
    finally:h.close()
    ok=all(c['evaluations']['fixed']['status']=='PASS' and c['evaluations']['negative']['status']=='FAIL' for c in rows)
    return {'status':'HOST_PASS' if ok else 'FAIL','cases':rows,'precision_query':precision,'scope':'finite source-informed signed/unsigned pack/unpack pixel oracle','legacy_status':'Diagnostic only; no expectation that legal mediump behaves as 16-bit on this implementation','specific_upstream_bug_reproduced':False,'physical_precision_distribution':'NOT_RUN','performance':'NOT_MEASURED'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=run(json.loads(a.config.read_text()));a.output.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);raise SystemExit(result['status']!='HOST_PASS')
