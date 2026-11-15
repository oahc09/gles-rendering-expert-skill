"""Strict bounded KTX2 subset used by texture experiments, not a universal loader.
Khronos KTX2 spec: https://registry.khronos.org/KTX/specs/2.0/ktxspec.v2.html
Only unsupercompressed, one-level 2D RGBA8/ETC2 RGBA/ASTC4x4 accepted.
"""
import struct
MAGIC=b'\xabKTX 20\xbb\r\n\x1a\n'
FORMATS={37:('rgba',4),151:('etc2',16),157:('astc',16)}
def parse(data):
 if len(data)<104 or len(data)>16*1024*1024 or data[:12]!=MAGIC:raise ValueError('invalid identifier/size')
 vals=struct.unpack_from('<13I2Q',data,12)
 fmt,typ,w,h,d,layers,faces,levels,scheme,do,dl,ko,kl,so,sl=vals
 if fmt not in FORMATS or typ!=1 or not 0<w<=2048 or not 0<h<=2048 or d!=0 or layers!=0 or faces!=1 or levels!=1 or scheme!=0 or so or sl:raise ValueError('unsupported bounded topology/format/supercompression')
 off,length,uncompressed=struct.unpack_from('<3Q',data,80)
 mode,bpp=FORMATS[fmt];expected=w*h*4 if mode=='rgba' else ((w+3)//4)*((h+3)//4)*bpp
 if length!=expected or uncompressed!=length or off% (4 if mode=='rgba' else 16):raise ValueError('invalid payload length/alignment')
 spans=[(0,104,'header')]
 for offset,size,name in [(do,dl,'dfd'),(ko,kl,'kvd'),(off,length,'payload')]:
  if not size:
   if offset:raise ValueError('empty section with offset')
   continue
  if offset<104 or offset+size>len(data) or (name!='payload' and offset%4):raise ValueError('section range/alignment')
  spans.append((offset,offset+size,name))
 for a,b in zip(sorted(spans),sorted(spans)[1:]):
  if a[1]>b[0]:raise ValueError('overlapping sections')
 if dl<28 or struct.unpack_from('<I',data,do)[0]!=dl:raise ValueError('invalid DFD size')
 vendor_type,version,block=struct.unpack_from('<IHH',data,do+4)
 if vendor_type!=0 or version!=2 or block!=dl-4 or block<24 or (block-24)%16:raise ValueError('invalid basic DFD descriptor')
 model,primaries,transfer,flags=struct.unpack_from('<4B',data,do+12)
 expected_model={'rgba':1,'etc2':161,'astc':162}[mode]
 if model!=expected_model or primaries not in (0,1) or transfer!=1 or flags!=0:raise ValueError('DFD model/transfer/alpha mismatch')
 dims=tuple(data[do+16:do+20]);expected_dims=(0,0,0,0) if mode=='rgba' else (3,3,0,0)
 if dims!=expected_dims or data[do+20]!=bpp or any(data[do+21:do+28]):raise ValueError('DFD block dimensions/planes mismatch')
 samples=[struct.unpack_from('<HBB4BII',data,p) for p in range(do+28,do+dl,16)]
 expected_samples={'rgba':[(i*8,7,c,0,0,0,0,0,255) for i,c in enumerate((0,1,2,15))], 'etc2':[(0,63,15,0,0,0,0,0,4294967295),(64,63,2,0,0,0,0,0,4294967295)],'astc':[(0,127,0,0,0,0,0,0,4294967295)]}
 if samples!=expected_samples[mode]:raise ValueError('unsupported DFD sample layout')
 pos=ko;keys=set()
 while kl and pos<ko+kl:
  if pos+4>ko+kl:raise ValueError('truncated KVD')
  n=struct.unpack_from('<I',data,pos)[0];pos+=4
  if n==0 or pos+n>ko+kl or b'\0' not in data[pos:pos+n]:raise ValueError('invalid KVD key')
  key,value=data[pos:pos+n].split(b'\0',1)
  try:key=key.decode('utf-8')
  except UnicodeDecodeError:raise ValueError('invalid UTF8 metadata key')
  if not key or key in keys:raise ValueError('empty/duplicate metadata key')
  keys.add(key)
  if key=='KTXorientation' and value!=b'rd\0':raise ValueError('unsupported orientation')
  if key=='KTXswizzle' and value!=b'rgba\0':raise ValueError('unsupported swizzle')
  if key.startswith('KTX') and key not in ('KTXorientation','KTXswizzle','KTXwriter','KTXwriterScParams'):raise ValueError('unsupported semantic metadata')
  end=pos+n;pos=(end+3)&~3
  if pos>ko+kl or any(data[end:pos]):raise ValueError('invalid KVD padding')
 return dict(width=w,height=h,mode=mode,payload=data[off:off+length],vk_format=fmt)
