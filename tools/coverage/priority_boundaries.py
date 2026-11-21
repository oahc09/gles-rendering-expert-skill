"""Six reviewed narrow capability policies; advertisement is never execution proof."""
def ver(s):
 if not isinstance(s,str) or len(s.split('.'))!=2 or not all(x.isdigit() for x in s.split('.')):raise ValueError('major.minor required')
 return tuple(map(int,s.split('.')))
def decide(family,*,gles='3.0',egl='1.4',gl_extensions=(),egl_extensions=(),entrypoints=(),facts=None,probe_pass=None):
 facts=facts or {};ge=set(gl_extensions);ee=set(egl_extensions);ep=set(entrypoints);why=[];route='extension';required=[]
 fallback={'sync':'CPU completion only through a verified glFinish route, no asynchronous promise','eglimage':'Keep verified owned 2D texture; no native/AHB zero-copy claim','robustness':'No reset-monitor guarantee; never intentionally access out of bounds','msrtt':'Verified single-sample attachment or separately validated explicit resolve','astc':'Verified RGBA8/ETC2 asset path; no inferred compression bandwidth gain','protected':'Reject protected playback/import; never downgrade protected data to an unprotected copy'}
 if family not in fallback:return dict(family=family,classification='implementation',usable=False,reasons=['NOT_REVIEWED'],fallback='do not enable')
 if family=='sync':
  if ver(egl)>=(1,5):route='core';required=['eglCreateSync','eglClientWaitSync','eglDestroySync']
  else:
   required=['eglCreateSyncKHR','eglClientWaitSyncKHR','eglDestroySyncKHR']
   if ver(egl)<(1,1) or 'EGL_KHR_fence_sync' not in ee or 'GL_OES_EGL_sync' not in ge:why.append('fence/client-API dependencies absent')
  if facts.get('current_context') is not True:why.append('current GLES context not established')
 elif family=='eglimage':
  if ver(egl)>=(1,5):route='core';required=['eglCreateImage','eglDestroyImage']
  else:
   required=['eglCreateImageKHR','eglDestroyImageKHR']
   if ver(egl)<(1,2) or not {'EGL_KHR_gl_texture_2D_image','EGL_KHR_image'}<=ee:why.append('KHR image dependencies absent')
  if facts.get('owned_complete_2d_texture') is not True:why.append('only owned complete 2D texture source reviewed')
 elif family=='robustness':
  if ver(gles)>=(3,2):route='core';required=['glGetGraphicsResetStatus']
  else:
   required=['glGetGraphicsResetStatusKHR']
   if ver(gles)<(2,0) or 'GL_KHR_robustness' not in ge:why.append('KHR reset-query route absent')
  if facts.get('operation')!='reset_query_only':why.append('robust access/context reset recovery is not proven by query support')
 elif family=='msrtt':
  required=['glFramebufferTexture2DMultisampleEXT','glRenderbufferStorageMultisampleEXT']
  if ver(gles)<(2,0) or 'GL_EXT_multisampled_render_to_texture' not in ge:why.append('MSRTT extension absent')
  samples=facts.get('samples');limit=facts.get('max_samples')
  if type(samples)is not int or type(limit)is not int or not 1<=samples<=limit:why.append('sample count outside queried limit')
  if facts.get('rgba8_2d_complete') is not True:why.append('format/attachment not verified')
 elif family=='astc':
  required=['glCompressedTexImage2D']
  if 'GL_KHR_texture_compression_astc_ldr' not in ge and 'GL_KHR_texture_compression_astc_hdr' not in ge:why.append('explicit ASTC profile extension absent; core inference not reviewed')
  if facts.get('format')!=0x93b0 or facts.get('block_bytes')!=16 or facts.get('size')!=[4,4] or facts.get('operation')!='upload_only':why.append('only 4x4 one-block LDR upload reviewed')
 elif family=='protected':
  required=['eglCreateContext']
  if ver(egl)<(1,4) or 'EGL_EXT_protected_content' not in ee:why.append('protected-content extension absent')
  if not all(facts.get(x) is True for x in ('protected_context','protected_resource','platform_secure_path')):why.append('secure context/resource/platform path not independently verified')
 if any(x not in ep for x in required):why.append('exact route entrypoints absent')
 if why:return dict(family=family,classification='unsupported',usable=False,reasons=why,fallback=fallback[family])
 if probe_pass is not True:return dict(family=family,classification='implementation',usable=False,reasons=['scoped runtime probe failed or absent'],fallback=fallback[family])
 return dict(family=family,classification=route,usable=True,reasons=['reviewed narrow parameters and caller-supplied runtime probe passed'],fallback=fallback[family],probe_trust='caller evidence, not authenticated device certification',performance='NOT_MEASURED')
