"""Fail-closed structural dispatch negotiation; semantic probes are always explicit."""
import math

def version(v):
 if not isinstance(v,str) or len(v.split('.'))!=2 or not all(x.isdigit() for x in v.split('.')):raise ValueError('major.minor version required')
 return tuple(map(int,v.split('.')))

class CapabilityNegotiator:
 def __init__(self,catalog,api_version,extensions=(),entrypoints=(),limits=None):
  self.catalog=catalog;self.version=api_version
  if api_version not in catalog['core_snapshots']:raise ValueError('version outside frozen API snapshots')
  if isinstance(extensions,str) or isinstance(entrypoints,str):raise ValueError('lists required, not extension strings')
  if not all(isinstance(x,str) for x in extensions) or not all(isinstance(x,str) for x in entrypoints):raise ValueError('explicit extension and pointer-name lists required')
  self.extensions=set(extensions);self.entrypoints=set(entrypoints);self.limits=limits or {}
 def negotiate(self,name,*,extension=None,required_extensions=(),minimum_limits=None,probe_pass=None,dependency_reviewed=False):
  rows=[r for kind in ('commands','enums') for r in self.catalog[kind] if r['name']==name]
  result={'name':name,'classification':'unsupported','usable':False,'reasons':[],'fallback':'do not call; retain verified baseline','performance':'NOT_MEASURED'}
  if not rows:result['reasons']=['unknown Registry name'];return result
  row=rows[0];route=None
  if extension is None and self.version in row['core_versions']:route='core'
  elif extension:
   ext=next((e for e in self.catalog['extensions'] if e['name']==extension),None)
   if not ext or self.catalog['api'] not in ext['supported'] or extension not in self.extensions:
    result['reasons']=['extension absent, not advertised or wrong API'];return result
   members=[b for b in ext['blocks'] if name in b['commands']+b['enums'] and b['operation']=='require' and b['conditions'].get('api',self.catalog['api'])==self.catalog['api']]
   if not members:result['reasons']=['name not required by requested extension for this API'];return result
   # Conditional require/removes are not guessed from extension advertisement alone.
   if any(set(b['conditions'])-{'api','comment'} for b in members) or any(b['operation']=='remove' and name in b['commands']+b['enums'] for b in ext['blocks']):
    result.update(classification='implementation',reasons=['conditional require/remove needs explicit specialized semantic adapter']);return result
   route='extension'
  if route is None:result['reasons']=['not core at this version; explicit extension route required'];return result
  if row['kind']=='command' and name not in self.entrypoints:result['reasons']=['exact entrypoint unavailable; aliases are not interchangeable'];return result
  if any(e not in self.extensions for e in required_extensions):result['reasons']=['declared extension dependency missing'];return result
  for limit,required in (minimum_limits or {}).items():
   if type(required) not in (int,float) or not math.isfinite(required) or required<0:raise ValueError('invalid minimum limit')
   actual=self.limits.get(limit)
   if type(actual) not in (int,float) or not math.isfinite(actual) or actual<required:
    result.update(classification='implementation',reasons=['runtime limit unavailable or insufficient: '+limit]);return result
  if probe_pass is False:result['reasons']=['runtime capability/parameter probe failed'];return result
  if probe_pass is not True or (route=='extension' and dependency_reviewed is not True):
   result.update(classification='implementation',route=route,reasons=['structural route found; semantic dependencies and runtime parameter probe not verified']);return result
  result.update(classification=route,usable=True,reasons=['exact structural route, entrypoint and supplied scoped probe passed'],probe_trust='caller-supplied scoped evidence, not independent driver certification')
  return result

 def priority(self,family,*,probe_pass=None,egl_version=None,egl_extensions=(),essl_version=None,disjoint=None):
  """Three explicitly reviewed narrow routes; not generic extension semantic acceptance."""
  if family=='debug_callback':
   if version(self.version)>=(3,2):return self.negotiate('glDebugMessageCallback',probe_pass=probe_pass)
   return self.negotiate('glDebugMessageCallbackKHR',extension='GL_KHR_debug',dependency_reviewed=True,probe_pass=probe_pass)
  if family=='external_texture':
   # OES text requires EGL1.2 + EGL_KHR_image_base or EGL_KHR_image.
   if egl_version is None or version(egl_version)<(1,2) or not set(egl_extensions)&{'EGL_KHR_image_base','EGL_KHR_image'}:
    return {'classification':'unsupported','usable':False,'reasons':['OES external requires EGL1.2 and image_base/image dependency'],'fallback':'ordinary verified 2D texture'}
   if essl_version not in ('1.00','3.00','3.10','3.20'):return {'classification':'implementation','usable':False,'reasons':['ESSL version not supplied'],'fallback':'ordinary verified 2D texture'}
   if essl_version!='1.00' and 'GL_OES_EGL_image_external_essl3' not in self.extensions:
    return {'classification':'unsupported','usable':False,'reasons':['ESSL3 external sampler requires external_essl3'],'fallback':'ordinary verified 2D texture'}
   return self.negotiate('glEGLImageTargetTexture2DOES',extension='GL_OES_EGL_image_external',dependency_reviewed=True,probe_pass=probe_pass)
  if family=='timer_query':
   r=self.negotiate('glQueryCounterEXT',extension='GL_EXT_disjoint_timer_query',dependency_reviewed=True,probe_pass=probe_pass)
   if disjoint is not False:
    r.update(classification='implementation',usable=False,reasons=['disjoint state true/unknown; elapsed result cannot be accepted'])
   return r
  return {'classification':'implementation','usable':False,'reasons':['priority family has no reviewed semantic adapter'],'fallback':'do not enable'}
