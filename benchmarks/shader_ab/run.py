#!/usr/bin/env python3
"""Real software GLES compilation/draw/readback controls. Never GPU performance evidence."""
import argparse,ctypes as C,hashlib,importlib.util,json,math,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
from build_cases import corpus,VERTEX
from counterexamples import wrong,golden as cpu_golden
from variant_trace import variant,connect
spec=importlib.util.spec_from_file_location('v109_differential',ROOT/'benchmarks/differential/run.py')
diff=importlib.util.module_from_spec(spec);spec.loader.exec_module(diff)
U=diff.U;I=diff.I;P=diff.P;F=diff.F
class ExperimentHost(diff.Host):
    def draw(self,case,fragment,layers=None,texture=None):
        while self.error():pass
        fb=U();rb=U();vao=U();tex=U();program=0
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
            if texture is not None:
                self.fn('glGenTextures',None,[I,P])(1,C.byref(tex));self.fn('glActiveTexture',None,[U])(0x84c0)
                self.fn('glBindTexture',None,[U,U])(0x0de1,tex)
                for pname,value in ((0x2801,texture['filter']),(0x2800,texture['filter']),(0x2802,0x812f),(0x2803,0x812f)):
                    self.fn('glTexParameteri',None,[U,U,I])(0x0de1,pname,value)
                pixels=(C.c_ubyte*len(texture['pixels']))(*texture['pixels'])
                self.fn('glTexImage2D',None,[U,I,I,I,I,I,U,U,P])(0x0de1,0,0x8058,texture['size'],texture['size'],0,0x1908,0x1401,pixels)
                loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(program,b'tex')
                self.fn('glUniform1i',None,[I,I])(loc,0)
            if layers is not None:
                self.fn('glClearColor',None,[F]*4)(0,0,0,0); self.fn('glClear',None,[U])(0x4000)
                self.fn('glEnable',None,[U])(0x0be2)
                self.fn('glBlendFuncSeparate',None,[U]*4)(0x0302,0x0303,1,0x0303)
                loc=self.fn('glGetUniformLocation',I,[U,C.c_char_p])(program,b'layer')
                for layer in layers:
                    self.fn('glUniform4f',None,[I,F,F,F,F])(loc,*layer)
                    self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
            else:self.fn('glDrawArrays',None,[U,I,I])(4,0,3)
            pixels=(C.c_ubyte*64)();self.fn('glReadPixels',None,[I,I,I,I,U,U,P])(0,0,4,4,0x1908,0x1401,pixels)
            row.update(status='EXECUTED',pixels=list(pixels),harness_gl_error=self.error(),source_sha256=hashlib.sha256(fragment.encode()).hexdigest())
            return row
        finally:
            self.fn('glUseProgram',None,[U])(0);self.fn('glBindFramebuffer',None,[U,U])(0x8d40,0);self.fn('glBindVertexArray',None,[U])(0)
            if tex.value:self.fn('glDeleteTextures',None,[I,P])(1,C.byref(tex))
            if program:self.fn('glDeleteProgram',None,[U])(program)
            if vao.value:self.fn('glDeleteVertexArrays',None,[I,P])(1,C.byref(vao))
            if rb.value:self.fn('glDeleteRenderbuffers',None,[I,P])(1,C.byref(rb))
            if fb.value:self.fn('glDeleteFramebuffers',None,[I,P])(1,C.byref(fb))

def quality(a,b):
 if any(r.get('status')!='EXECUTED' or not r.get('compile') or not r.get('link') or r.get('harness_gl_error') for r in (a,b)):return 'UNKNOWN'
 if any(len(r.get('pixels',[]))!=64 or any(type(v) is not int or not 0<=v<=255 for v in r.get('pixels',[])) for r in (a,b)):return 'UNKNOWN'
 return 'PASS' if max(abs(x-y) for x,y in zip(a['pixels'],b['pixels']))<=1 else 'FAIL'

def scenes():
 return [dict(id=name,layers=[[((i*3)%7)/8,((i*5)%7)/8,((i*2)%7)/8,alpha] for i in range(count)],scope='4x4 full-screen overlapping sprite proxy, not production renderer') for name,count,alpha in [('gaussian-proxy',32,.125),('glass-layers',8,.25),('rain-particles',16,.125),('layered-ui',12,.5)]]

def blend_golden(layers):
 pixel=[0,0,0,0]
 for r,g,b,a in layers:
  vals=[r*a+pixel[0]/255*(1-a),g*a+pixel[1]/255*(1-a),b*a+pixel[2]/255*(1-a),a+pixel[3]/255*(1-a)]
  pixel=[math.floor(min(1,max(0,x))*255+.5) for x in vals]
 return pixel*16

def run(config,output,trace_bundle=None):
 h=ExperimentHost(config)
 report=dict(schema_version=1,status='FAIL',scope='finite host software correctness controls',performance_status='NOT_MEASURED',physical_gpu='BLOCKED_BY_HARDWARE',experiments=[],overlap_scenes=[])
 try:
  for c in corpus():
   negative,reason=wrong(c['id'])
   sources=dict(c['sources'],negative=negative)
   validated=[variant(src,arm) for arm,src in sources.items()]
   if any(v['errors'] for v in validated):raise ValueError('Invalid shader variant')
   draws=[h.draw(c['id'],sources[arm]) for arm in ('a','b','negative')]
   reference=dict(status='EXECUTED',compile=True,link=True,harness_gl_error=0,pixels=cpu_golden(c['id']))
   checks=[quality(d,reference) for d in draws]
   report['experiments'].append(dict(id=c['id'],observed=quality(*draws[:2]),expected=c['expected_quality'],draws=draws,variants=validated,cpu_golden=reference['pixels'],cpu_checks=checks,negative_reason=reason,negative_control=quality(draws[0],draws[2]),performance_status='NOT_MEASURED'))
  report['variant_trace']=connect(report['experiments'],trace_bundle)
  source='#version 300 es\nprecision highp float;\nuniform vec4 layer;\nlayout(location=0) out vec4 color;\nvoid main(){color=layer;}'
  for s in scenes():
   a=h.draw(s['id'],source,s['layers']);b=h.draw(s['id'],source,list(reversed(s['layers'])))
   golden=blend_golden(s['layers']);error=max(abs(x-y) for x,y in zip(a['pixels'],golden)) if len(a['pixels'])==64 else None
   report['overlap_scenes'].append(dict(id=s['id'],scope=s['scope'],draw_count=len(s['layers']),covered_fragments=16*len(s['layers']),coverage_estimate=True,cpu_rgba8_max_error=error,quality='PASS' if error is not None and error<=2 and not a['harness_gl_error'] else 'FAIL',sorting_negative_control=quality(a,b),draws=[a,b],performance_status='NOT_MEASURED',dynamic_camera='NOT_RUN',silhouette='NOT_RUN',parallax='NOT_RUN'))
  report['status']='HOST_PASS' if all(x['observed']==x['expected'] and x['cpu_checks']==['PASS',x['expected'],'FAIL'] and x['negative_control']=='FAIL' for x in report['experiments']) and all(x['quality']=='PASS' and x['sorting_negative_control']=='FAIL' for x in report['overlap_scenes']) else 'FAIL'
 finally:h.close()
 Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--config',required=True);p.add_argument('--output',required=True);p.add_argument('--trace-bundle');args=p.parse_args()
 try:r=run(json.loads(Path(args.config).read_text()),args.output,args.trace_bundle)
 except Exception as e:
  r=dict(status='BLOCKED_BY_DRIVER',reason=str(e),performance_status='NOT_MEASURED');Path(args.output).write_text(json.dumps(r))
 print(json.dumps({'status':r['status']}));raise SystemExit(r['status']!='HOST_PASS')
