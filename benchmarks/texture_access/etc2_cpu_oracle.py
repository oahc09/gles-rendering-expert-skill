"""Pinned KTX-Software 4.4.2 internal ETC2 oracle for one generated 4x4 block.
Source: https://github.com/KhronosGroup/KTX-Software/blob/v4.4.2/lib/etcunpack.cxx
The internal ABI is NOT a portable/public libktx API; absence fails explicitly.
External Apache-2.0 implementation is not copied or vendored.
"""
import ctypes as C
from pathlib import Path

def decode_block(payload, ktx_root):
 if len(payload)!=16:raise ValueError('only one ETC2_RGBA 4x4 block accepted')
 lib=C.CDLL(str(Path(ktx_root)/'lib/libktx.so'))
 try:fn=lib._ktxUnpackETC
 except AttributeError:raise RuntimeError('pinned internal ETC2 oracle unavailable')
 fn.argtypes=[C.c_void_p,C.c_uint,C.c_uint,C.c_uint,C.POINTER(C.c_void_p),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.c_int,C.c_ubyte];fn.restype=C.c_int
 src=(C.c_ubyte*16).from_buffer_copy(payload);out=C.c_void_p();fmt=C.c_uint();internal=C.c_uint();typ=C.c_uint()
 try:
  code=fn(src,0x9278,4,4,C.byref(out),C.byref(fmt),C.byref(internal),C.byref(typ),0,0)
  if code or not out or (fmt.value,internal.value,typ.value)!=(0x1908,0x8058,0x1401):raise RuntimeError('ETC2 CPU oracle failed')
  return list(C.string_at(out,64))
 finally:
  if out:
   free=C.CDLL(None).free;free.argtypes=[C.c_void_p];free.restype=None;free(out)
