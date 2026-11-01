"""Explicit capability/metadata decisions, not a device-brand lookup."""
import math

def texture_target(es_major, extensions, denied=()):
    if type(es_major) is not int or es_major not in (2,3):raise ValueError('Only declared GLES 2/3 capability snapshots are supported')
    if not isinstance(extensions,list) or any(not isinstance(x,str) or not x or any(c.isspace() for c in x) for x in extensions):raise ValueError('Exact extension token strings required')
    if not isinstance(denied,(tuple,list,set)) or any(x not in ('astc','etc2','rgba') for x in denied):raise ValueError('Denied targets must be astc/etc2/rgba')
    candidates=[]
    if 'GL_KHR_texture_compression_astc_ldr' in extensions:candidates.append('astc')
    if es_major>=3:candidates.append('etc2')
    candidates.append('rgba')
    return next((x for x in candidates if x not in denied),None)

def video_path(metadata,gl_extensions,egl_extensions):
    if metadata.get('protected'):
        # This example has no protected context/surface producer integration: never
        # downgrade encrypted/protected content to CPU staging or public readback.
        required={'EGL_EXT_protected_content'}<=set(egl_extensions) and 'GL_EXT_protected_textures' in gl_extensions
        return {'path':'BLOCKED_PROTECTED_PIPELINE','extensions_present':required,'readback':False,'plaintext_export':False}
    if metadata.get('protected') is not False:raise ValueError('Protection must be explicit')
    if metadata.get('rotation') not in (0,90,180,270):raise ValueError('Unsupported rotation')
    if metadata.get('matrix') not in ('BT601','BT709','BT2020') or metadata.get('range') not in ('limited','full'):raise ValueError('Unknown YUV color metadata')
    if metadata.get('transfer')!='SDR':return {'path':'BLOCKED_HDR_TONEMAP_REQUIRED','readback':False}
    if metadata.get('source')=='SurfaceTexture':
        required={'GL_OES_EGL_image_external','GL_OES_EGL_image_external_essl3'}
        return {'path':'EXTERNAL_ESSL3' if required<=set(gl_extensions) else 'UNSUPPORTED_EXTERNAL',
                'color_conversion':'producer/implementation YUV to RGB; do NOT apply YUV matrix twice',
                'uv':'fresh SurfaceTexture transform after updateTexImage; rotation only if not already baked', 'readback':False}
    if metadata.get('source')=='CPU_YUV':return {'path':'EXPLICIT_YUV_PLANES','readback':False,'color_conversion':'matrix/range below; output nonlinear RGB, not linear-light'}
    raise ValueError('Unknown producer')

def yuv_rgb(y,u,v,matrix,limited=True):
    if any(not math.isfinite(x) or not 0<=x<=1 for x in (y,u,v)):raise ValueError('8bit normalized input range')
    kr,kb={'BT601':(.299,.114),'BT709':(.2126,.0722),'BT2020':(.2627,.0593)}[matrix]
    yy=(y*255-16)/219 if limited else y
    cb=(u*255-128)/(224 if limited else 255);cr=(v*255-128)/(224 if limited else 255)
    r=yy+2*(1-kr)*cr;b=yy+2*(1-kb)*cb;g=(yy-kr*r-kb*b)/(1-kr-kb)
    return tuple(max(0,min(1,x)) for x in (r,g,b))

def rotate_uv(u,v,degrees):
    return {0:(u,v),90:(v,1-u),180:(1-u,1-v),270:(1-v,u)}[degrees]
