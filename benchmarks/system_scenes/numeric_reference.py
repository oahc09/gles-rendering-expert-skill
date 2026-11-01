"""Independent CPU expression oracles, tolerance-based not GPU bit-exact claims."""
import math
import struct

def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
def f16(v):return struct.unpack('e',struct.pack('e',v))[0]
def reference(group,w,h):
 value=0
 if group==1:value=(f32(.5002)-.5)*1000
 if group==2:value=(f32(.503)-.5)*100
 if group==3:value=((128/255+.055)/1.055)**2.4
 if group==4:
  v=16.
  for _ in range(1024):v=f32(v+f32(.001))
  value=(v-16)*.5
 if group==5:value=.5
 if 7<=group<=9:
  c=[0.,0.,0.]
  for i in range(8):
   source=(.8,.2,.05) if i%2 else (.05,.3,.7)
   c=[f16(source[k]*.12+c[k]*.88) for k in range(3)]
  color=[v**(1/2.2) for v in c]
 elif group in (11,12):
  v=0
  for _ in range(64):v=f16(v+1/1024)
  color=[v*8]*3
 else:color=[value]*3
 result=[]
 for y in range(h):
  for x in range(w):
   if group==6:
    a,b=(x+.5)/w-.5,1-(y+.5)/h-.5
    length=math.sqrt(a*a+b*b+1);d=(a*.1+b*.1+1)/(length*math.sqrt(1.02));color=[max(d,0)**64]*3
   if group==10:
    v=f16(((x+.5)/w)*5);color=[v/(1+v)]*3
   result.extend(max(0,min(255,round(c*255))) for c in color)
 return result

def evaluate(group,w,h,pixels):
 expected=reference(group,w,h);errors=[abs(a-b) for a,b in zip(expected,pixels)]
 # Documented lab tolerances include shader transcendental and half rounding variance.
 return {'mae_8bit':sum(errors)/len(errors),'max_error_8bit':max(errors),'mae_limit':1.5,'max_limit':4,'pass':sum(errors)/len(errors)<=1.5 and max(errors)<=4}
