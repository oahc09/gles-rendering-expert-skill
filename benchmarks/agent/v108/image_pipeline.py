#!/usr/bin/env python3
"""Fixed 4x4 GLES3 image repair controls; only finite reviewed expressions allowed."""
import argparse, ctypes as C, hashlib, json, math, sys, tempfile
from pathlib import Path
import shader_pipeline as numeric
fuzz=numeric.fuzz;diff=numeric.diff
U=diff.U;I=diff.I;P=diff.P;F=diff.F
VERTEX='''#version 300 es
void main(){
 vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
 gl_Position=vec4(p*2.0-1.0,0.0,1.0);
}
'''
PREFIX='''#version 300 es
precision highp float;
layout(location=0) out vec4 outColor;
void main(){
 vec2 uv=gl_FragCoord.xy/vec2(4.0);
 vec4 base=vec4(0.8,0.2,0.6,0.5);
 outColor='''
SUFFIX=';\n}\n'
EXPRESSIONS={
 'uv-swizzle':('vec4(uv.xy,0.25,1.0)','vec4(uv.yx,0.25,1.0)','vec4(vec2(1.0)-uv,0.25,1.0)'),
 'color-swizzle':('base.rgba','base.bgra','base.argb'),
 'premultiplied-alpha':('vec4(base.rgb*base.a,base.a)','base','base*base.a'),
 'alpha-output':('vec4(uv.x,0.25,uv.y,0.5)','vec4(uv.x,0.25,uv.y,1.0)','vec4(uv.x*0.5,0.125,uv.y*0.5,0.5)')}

def source(case,variant):return PREFIX+EXPRESSIONS[case][variant]+SUFFIX

def validate_source(case,text):
    if case not in EXPRESSIONS:raise ValueError('unknown image case')
    if not isinstance(text,str) or len(text.encode())>2048:raise ValueError('shader quota/type')
    if text not in [source(case,i) for i in range(3)]:raise ValueError('outside reviewed finite shader repair domain')
    return text

def cpu_golden(case):
    """Independent scalar pixel-center formulas, bottom-left GL row order."""
    out=[]
    for y in range(4):
        for x in range(4):
            u=(x+.5)/4;v=(y+.5)/4
            if case=='uv-swizzle':pixel=[u,v,.25,1]
            elif case=='color-swizzle':pixel=[.8,.2,.6,.5]
            elif case=='premultiplied-alpha':pixel=[.4,.1,.3,.5]
            elif case=='alpha-output':pixel=[u,.25,v,.5]
            else:raise ValueError('unknown CPU golden')
            out.extend(math.floor(max(0,min(1,n))*255+.5) for n in pixel)
    return out

def pixel_match(actual,expected):
    return isinstance(actual,list) and len(actual)==64 and all(type(x) is int and 0<=x<=255 for x in actual) and all(abs(x-y)<=1 for x,y in zip(actual,expected))

class ImageHost(diff.Host):
    def draw(self,case,fragment):
        validate_source(case,fragment)
        while self.error():pass
        fb=U();rb=U();vao=U();program=0
        try:
            program,observed=self.program({'shader.vert':VERTEX,'shader.frag':fragment})
            row=dict(case=case,compile=observed['compile'],link=observed['link'],compile_logs=observed['compile_logs'],link_log=observed['link_log'],status='COMPILE_FAILED',pixels=[])
            if not observed['compile'] or not observed['link']:return row
            self.fn('glGenFramebuffers',None,[I,P])(1,C.byref(fb));self.fn('glBindFramebuffer',None,[U,U])(0x8d40,fb)
            self.fn('glGenRenderbuffers',None,[I,P])(1,C.byref(rb));self.fn('glBindRenderbuffer',None,[U,U])(0x8d41,rb)
            self.fn('glRenderbufferStorage',None,[U,U,I,I])(0x8d41,0x8058,4,4)
            self.fn('glFramebufferRenderbuffer',None,[U,U,U,U])(0x8d40,0x8ce0,0x8d41,rb)
            if self.fn('glCheckFramebufferStatus',U,[U])(0x8d40)!=0x8cd5:raise RuntimeError('RGBA8 framebuffer incomplete')
            for cap in (0x0bd0,0x0be2,0x0b71,0x0b90,0x0c11,0x0b44):self.fn('glDisable',None,[U])(cap)
            self.fn('glColorMask',None,[U,U,U,U])(1,1,1,1)
            self.fn('glViewport',None,[I,I,I,I])(0,0,4,4)
            self.fn('glGenVertexArrays',None,[I,P])(1,C.byref(vao));self.fn('glBindVertexArray',None,[U])(vao)
            self.fn('glUseProgram',None,[U])(program)
            self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
            pixels=(C.c_ubyte*64)();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels)
            row.update(status='EXECUTED',pixels=list(pixels),harness_gl_error=self.error(),source_sha256=hashlib.sha256(fragment.encode()).hexdigest())
            return row
        finally:
            self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
            if program:self.fn('glDeleteProgram',None,[U])(program)
            if vao.value:self.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
            if rb.value:self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(rb))
            if fb.value:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))

def child(config,requests):
    if len(requests)>12:raise ValueError('draw-count quota')
    for req in requests:validate_source(req['case'],req['source'])
    h=ImageHost(config)
    try:
        return dict(status='EXECUTED',metadata=h.metadata,draws=[dict(h.draw(r['case'],r['source']),variant=r['variant']) for r in requests])
    finally:h.close()

def isolated(config,requests):
    with tempfile.TemporaryDirectory(prefix='gles-image-repair-') as td:
        path=Path(td);request=path/'request.json';output=path/'result.json'
        request.write_text(json.dumps({'config':config,'requests':requests}))
        process=fuzz.isolated([sys.executable,str(Path(__file__).resolve()),'--child',str(request),'--output',str(output)],45,4096,2**20)
        if process['status']!='EXITED' or process['exit_code']!=0 or not output.exists():return dict(status='UNKNOWN',process=process,draws=[])
        return json.loads(output.read_text())

def compare(case,variants):
    # Independent CPU validation first, then peer agreement. Two identical wrong
    # outputs cannot pass. Compile/link success is necessary but insufficient.
    if len(variants)!=2 or any(r.get('status')!='EXECUTED' or not r.get('compile') or not r.get('link') or r.get('harness_gl_error')!=0 for r in variants):return 'UNKNOWN'
    golden=cpu_golden(case)
    ok=all(pixel_match(r.get('pixels'),golden) for r in variants) and pixel_match(variants[0]['pixels'],variants[1]['pixels'])
    return 'PASS' if ok else 'FAIL'

def run(configs,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    requests=[dict(case=c,variant=v,source=source(c,i)) for c in EXPRESSIONS for i,v in enumerate(('repair','original','wrong_repair'))]
    report=dict(schema_version=1,scope='authored finite-domain real GLES fragment image repairs; not model evaluation',status='BLOCKED_BY_DRIVER',
        provider_status='BLOCKED_BY_PROVIDER',model_quality='NOT_EVALUATED',physical_gpu='BLOCKED_BY_HARDWARE',
        target=dict(width=4,height=4,format='RGBA8',row_order='bottom-to-top',tolerance=1,blend=False,dither=False),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),requests=requests,cpu_goldens={c:cpu_golden(c) for c in EXPRESSIONS})
    try:
        numeric.validate_configs(configs)
        runs=[isolated(c,requests) for c in configs];report['runs']=runs
        if all(r.get('status')=='EXECUTED' and len(r.get('draws',[]))==len(requests) for r in runs):
            if {r.get('metadata',{}).get('implementation') for r in runs}!={'mesa','angle'}:raise ValueError('independent driver identities absent')
            rows=[]
            for i,req in enumerate(requests):
                observation=[r['draws'][i] for r in runs]
                identity_ok=all(r.get('case')==req['case'] and r.get('variant')==req['variant'] and r.get('source_sha256')==hashlib.sha256(req['source'].encode()).hexdigest() for r in observation)
                status=compare(req['case'],observation) if identity_ok else 'UNKNOWN'
                rows.append(dict(case=req['case'],variant=req['variant'],status=status,expected='PASS' if req['variant']=='repair' else 'FAIL'))
            report['comparisons']=rows;report['status']='HOST_PASS' if all(r['status']==r['expected'] for r in rows) else 'FAIL'
    except (ValueError,FileNotFoundError) as e:report['reason']=str(e)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    (out/'report.md').write_text('# Fragment image repair pipeline\n\nStatus: '+report['status']+'\n\n4x4 RGBA8, one-code-value CPU+peer tolerance.\nProvider BLOCKED_BY_PROVIDER; no model quality score.\n'+ '\n'.join('- '+r['case']+' / '+r['variant']+': '+r['status'] for r in report.get('comparisons',[]))+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path);p.add_argument('--child',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.child:
        if a.child.stat().st_size>65536:raise ValueError('request quota')
        try:
            data=json.loads(a.child.read_text());r=child(data['config'],data['requests'])
        except Exception as e:r=dict(status='UNKNOWN',reason=str(e),draws=[])
        a.output.write_text(json.dumps(r));raise SystemExit(0)
    if a.config.stat().st_size>16384:raise ValueError('config quota')
    r=run(json.loads(a.config.read_text()),a.output);print(json.dumps({'status':r['status']}));raise SystemExit(0 if r['status']=='HOST_PASS' else 2)
