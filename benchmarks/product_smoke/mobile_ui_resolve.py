#!/usr/bin/env python3
"""Software EGL / GLES business fixture: composited translucent mobile UI panel."""
import ctypes as c
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('EGL_PLATFORM', 'surfaceless')
os.environ.setdefault('LIBGL_ALWAYS_SOFTWARE', '1')
os.environ.setdefault('MESA_SHADER_CACHE_DISABLE', 'true')
angle = Path(os.environ['GLES_ANGLE_ROOT']).resolve() if os.environ.get('GLES_ANGLE_ROOT') else None
if angle:
    os.environ['VK_ICD_FILENAMES'] = str(angle / 'vk_swiftshader_icd.json')
egl = c.CDLL(str(angle / 'libEGL.so') if angle else 'libEGL.so.1')
I, U, P, F, S = c.c_int32, c.c_uint32, c.c_void_p, c.c_float, c.c_char_p

def e(name, result, *args):
    fn = getattr(egl, name)
    fn.restype, fn.argtypes = result, args
    return fn

get_display = e('eglGetDisplay', P, P)
initialize = e('eglInitialize', U, P, P, P)
bind_api = e('eglBindAPI', U, U)
choose = e('eglChooseConfig', U, P, P, P, I, P)
create_surface = e('eglCreatePbufferSurface', P, P, P, P)
create_context = e('eglCreateContext', P, P, P, P, P)
make_current = e('eglMakeCurrent', U, P, P, P, P)
destroy_context = e('eglDestroyContext', U, P, P)
destroy_surface = e('eglDestroySurface', U, P, P)
terminate = e('eglTerminate', U, P)
proc = e('eglGetProcAddress', P, S)


def software_display():
    if angle is None:
        return get_display(None)
    p = proc(b'eglGetPlatformDisplayEXT')
    assert p
    # EGL_PLATFORM_ANGLE_ANGLE / TYPE_VULKAN / DEVICE_TYPE_SWIFTSHADER.
    attrs = ints(0x3203,0x3450,0x3209,0x3487,0x3038)
    return c.CFUNCTYPE(P,U,P,c.POINTER(I))(p)(0x3202,None,attrs)


def g(name, result, *args):
    p = proc(('gl' + name).encode())
    assert p, name
    return c.CFUNCTYPE(result, *args)(p)

def ints(*values):
    return (I * len(values))(*values)

D = 16
GL_FRAMEBUFFER, GL_RENDERBUFFER, COLOR = 0x8D40, 0x8D41, 0x8CE0
GL_READ_FRAMEBUFFER, GL_DRAW_FRAMEBUFFER, GL_COLOR_BIT = 0x8CA8, 0x8CA9, 0x4000

def scenario(display, config, generation, samples, output):
    allocated_samples = samples
    surface = create_surface(display, config, ints(0x3057,D,0x3056,D,0x3038))
    context = create_context(display, config, None, ints(0x3098,3,0x3038))
    assert surface and context and make_current(display, surface, surface, context)
    rows = []
    glerr = g('GetError', U)
    native = g('GetString', S, U)
    ident = {name:native(token).decode() for name,token in
             [('vendor',0x1F00),('renderer',0x1F01),('gles_version',0x1F02),('glsl',0x8B8C)]}
    renderer_name=ident['renderer'].lower()
    if angle:
        assert 'angle' in renderer_name and 'swiftshader' in renderer_name, ident
    else:
        assert 'llvmpipe' in renderer_name or 'softpipe' in renderer_name, ident
    count = I()
    internal = g('GetInternalformativ',None,U,U,U,I,P)
    internal(GL_RENDERBUFFER,0x8058,0x9380,1,c.byref(count)) # GL_NUM_SAMPLE_COUNTS
    assert 0 <= count.value <= 64
    supported = (I * count.value)()
    if count.value:
        internal(GL_RENDERBUFFER,0x8058,0x80A9,count.value,supported) # GL_SAMPLES
    assert glerr() == 0
    if samples and samples not in supported:
        samples = 0
    funcs = {'textures':(g('GenTextures',None,I,P),g('DeleteTextures',None,I,P)),
             'fbos':(g('GenFramebuffers',None,I,P),g('DeleteFramebuffers',None,I,P)),
             'rbs':(g('GenRenderbuffers',None,I,P),g('DeleteRenderbuffers',None,I,P))}
    created = {key:[] for key in funcs}
    shaders = []
    programs = []

    def new(kind):
        handle=U()
        funcs[kind][0](1,c.byref(handle))
        assert handle.value
        created[kind].append(handle)
        return handle.value

    def require_clean():
        error=glerr()
        assert error == 0, hex(error)

    def shader(kind, source):
        sh = g('CreateShader',U,U)(kind)
        shaders.append(sh)
        ptr = S(source)
        g('ShaderSource',None,U,I,P,P)(sh,1,c.byref(ptr),None)
        g('CompileShader',None,U)(sh)
        ok=I()
        g('GetShaderiv',None,U,U,P)(sh,0x8B81,c.byref(ok))
        if not ok.value:
            log=c.create_string_buffer(2048)
            g('GetShaderInfoLog',None,U,I,P,P)(sh,2048,None,log)
            raise RuntimeError(log.value.decode())
        return sh

    def read(fbo):
        g('BindFramebuffer',None,U,U)(GL_FRAMEBUFFER,fbo)
        raw=(c.c_ubyte*(D*D*4))()
        g('ReadPixels',None,I,I,I,I,U,U,P)(0,0,D,D,0x1908,0x1401,raw)
        require_clean()
        return bytes(raw)

    def texture(internal, rgba=(192,96,48,128)):
        name=new('textures')
        g('BindTexture',None,U,U)(0x0DE1,name)
        for key in [0x2800,0x2801]: g('TexParameteri',None,U,U,I)(0x0DE1,key,0x2600)
        pixel=(c.c_ubyte*4)(*rgba)
        g('TexImage2D',None,U,I,I,I,I,I,U,U,P)(0x0DE1,0,internal,1,1,0,0x1908,0x1401,pixel)
        return name

    def attached(samples, depth=False):
        fbo,rb = new('fbos'),new('rbs')
        g('BindFramebuffer',None,U,U)(GL_FRAMEBUFFER,fbo)
        g('BindRenderbuffer',None,U,U)(GL_RENDERBUFFER,rb)
        if samples:
            g('RenderbufferStorageMultisample',None,U,I,U,I,I)(GL_RENDERBUFFER,samples,0x8058,D,D)
        else:
            g('RenderbufferStorage',None,U,U,I,I)(GL_RENDERBUFFER,0x8058,D,D)
        sample_count=I()
        g('GetRenderbufferParameteriv',None,U,U,P)(GL_RENDERBUFFER,0x8CAB,c.byref(sample_count))
        assert sample_count.value == samples, sample_count.value
        g('FramebufferRenderbuffer',None,U,U,U,U)(GL_FRAMEBUFFER,COLOR,GL_RENDERBUFFER,rb)
        if depth:
            depth_rb = new('rbs')
            g('BindRenderbuffer',None,U,U)(GL_RENDERBUFFER,depth_rb)
            if samples:
                g('RenderbufferStorageMultisample',None,U,I,U,I,I)(GL_RENDERBUFFER,samples,0x81A5,D,D)
            else:
                g('RenderbufferStorage',None,U,U,I,I)(GL_RENDERBUFFER,0x81A5,D,D)
            g('FramebufferRenderbuffer',None,U,U,U,U)(GL_FRAMEBUFFER,0x8D00,GL_RENDERBUFFER,depth_rb)
        assert g('CheckFramebufferStatus',U,U)(GL_FRAMEBUFFER) == 0x8CD5
        require_clean()
        return fbo

    def clear(word):
        g('Disable',None,U)(0x0C11)
        g('ClearColor',None,F,F,F,F)(*word)
        g('Clear',None,U)(GL_COLOR_BIT)

    def blit(source,dest,filter_, dest_size=D):
        bind=g('BindFramebuffer',None,U,U)
        bind(GL_READ_FRAMEBUFFER,source); bind(GL_DRAW_FRAMEBUFFER,dest)
        g('BlitFramebuffer',None,*([I]*8),U,U)(0,0,D,D,0,0,dest_size,dest_size,GL_COLOR_BIT,filter_)

    vert=b'''#version 300 es
    uniform float panelScale;
    uniform float clipDepth;
    void main(){vec2 p[3]=vec2[3](vec2(-1.,-1.),vec2(3.,-1.),vec2(-1.,3.));
    gl_Position=vec4(p[gl_VertexID]*panelScale,clipDepth,1.);}'''
    frag=b'''#version 300 es
    precision highp float;
    uniform sampler2D icon;
    layout(location=0) out vec4 color;
    void main(){vec4 s=texture(icon,vec2(0.5));color=vec4(s.rgb*s.a,s.a);}'''
    program=g('CreateProgram',U)()
    programs.append(program)
    for source,kind in [(vert,0x8B31),(frag,0x8B30)]:
        g('AttachShader',None,U,U)(program,shader(kind,source))
    g('LinkProgram',None,U)(program)
    linked=I()
    g('GetProgramiv',None,U,U,P)(program,0x8B82,c.byref(linked))
    assert linked.value
    g('UseProgram',None,U)(program)
    g('Uniform1i',None,I,I)(g('GetUniformLocation',I,U,S)(program,b'icon'),0)

    uniform = g('GetUniformLocation',I,U,S)
    scalar = g('Uniform1f',None,I,F)
    scale = uniform(program,b'panelScale')
    dep = uniform(program,b'clipDepth')
    assert scale >= 0 and dep >= 0
    scalar(scale,1.0)
    scalar(dep,0.0)
    bg=(26,51,77,255)
    def unit(value):
        return value/255
    def linear(value):
        value=unit(value)
        return value/12.92 if value<=0.04045 else ((value+0.055)/1.055)**2.4
    def predicted(srgb,wrong=False,base_rgba=bg):
        fn=linear if srgb else unit
        alpha=unit(128)
        return tuple(round((fn(ch)*alpha*(alpha if wrong else 1)+unit(base)*(1-alpha))*255)
                     for ch,base in zip((192,96,48),base_rgba))+ (255,)

    def check(raw, inside, outside):
        changed_edge = []
        for y in range(D):
            for x in range(D):
                p=(y*D+x)*4
                pixel = list(raw[p:p+4])
                if samples and ((x == 2 and 3 <= y < 12) or (y == 3 and 3 <= x < 13)):
                    if pixel != list(outside):
                        changed_edge.append([x,y,pixel])
                    # Record observed edge behavior explicitly. Do not count these
                    # pixels under the strict guard/center expected-value model.
                    assert all(min(a,b)-1<=v<=max(a,b)+1 for v,a,b in zip(pixel,inside,outside))
                    continue
                want=inside if 3<=x<13 and 4<=y<12 else outside
                assert max(abs(a-b) for a,b in zip(pixel,want))<=1, (x,y,pixel,want)
        return changed_edge

    def resolved_scene_ui(result_fbo):
        # Opaque depth-tested 3D card preview, followed by a distinct, single-sample
        # premultiplied icon pass. Test depth by drawing the farther overlapping
        # primitive last: it must not replace the closer center.
        scene=attached(samples,depth=True)
        g('BindFramebuffer',None,U,U)(GL_FRAMEBUFFER,scene)
        g('Viewport',None,I,I,I,I)(0,0,D,D)
        clear([unit(x) for x in bg])
        g('Enable',None,U)(0x0B71) # GL_DEPTH_TEST
        g('DepthFunc',None,U)(0x0201) # GL_LESS
        g('ClearDepthf',None,F)(1.0)
        g('Clear',None,U)(0x0100) # GL_DEPTH_BUFFER_BIT
        g('Disable',None,U)(0x0BE2)
        scalar(scale,0.55)
        def draw(rgba,z):
            g('BindTexture',None,U,U)(0x0DE1,texture(0x8058,rgba))
            scalar(dep,z)
            g('DrawArrays',None,U,I,I)(4,0,3)
        near=(40,110,180,255)
        draw(near,-0.35)
        draw((190,40,25,255),0.3)
        g('Disable',None,U)(0x0B71)
        require_clean()
        blit(scene,result_fbo,0x2600)
        require_clean()
        resolved=read(result_fbo)
        offset=(8*D+8)*4
        assert resolved[offset:offset+4]==bytes(near),list(resolved[offset:offset+4])
        assert resolved[:4]==bytes(bg)

        scalar(scale,1.0)
        scalar(dep,0.0)
        g('BindTexture',None,U,U)(0x0DE1,texture(0x8C43))
        g('Enable',None,U)(0x0C11)
        g('Scissor',None,I,I,I,I)(3,4,10,8)
        g('Enable',None,U)(0x0BE2)
        g('BlendFuncSeparate',None,U,U,U,U)(1,0x0303,1,0x0303)
        g('DrawArrays',None,U,I,I)(4,0,3)
        g('Disable',None,U)(0x0C11)
        require_clean()
        composited=read(result_fbo)
        inside_changed=0
        for y in range(D):
            for x in range(D):
                i=(y*D+x)*4
                original=resolved[i:i+4]
                final=composited[i:i+4]
                if 3<=x<13 and 4<=y<12:
                    assert max(abs(a-b) for a,b in zip(final,predicted(True,base_rgba=original)))<=1,(x,y)
                    inside_changed+=final!=original
                else:
                    assert final==original,(x,y,list(final),list(original))
        assert inside_changed==80
        out_hash={}
        for label,raw in [('scene-resolved',resolved),('scene-ui-strict',composited)]:
            (output/f'g{generation}-s{samples}-{label}.rgba').write_bytes(raw)
            out_hash[label]=hashlib.sha256(raw).hexdigest()
        return {'case':'opaque-depth-preview-then-single-sample-ui','requested_scene_samples':allocated_samples,
                'actual_scene_samples':samples,'ui_samples':0,'sample_fallback':samples!=allocated_samples,
                'scene_center':list(resolved[offset:offset+4]),'ui_center':list(composited[offset:offset+4]),
                'inside_changed':inside_changed,'exact_outside_unchanged':D*D-inside_changed,'readbacks':out_hash}

    try:
        msaa=attached(samples)
        resolve=attached(0)
        for label,internal,wrong in [('correct-srgb-premult',0x8C43,False),
                                    ('adversarial-double-alpha',0x8C43,True),
                                    ('adversarial-missing-srgb-decode',0x8058,False)]:
            g('BindFramebuffer',None,U,U)(GL_FRAMEBUFFER,msaa)
            clear([unit(x) for x in bg])
            g('BindTexture',None,U,U)(0x0DE1,texture(internal))
            g('Viewport',None,I,I,I,I)(0,0,D,D)
            g('Enable',None,U)(0x0C11)
            g('Scissor',None,I,I,I,I)(3,4,10,8)
            g('Enable',None,U)(0x0BE2)
            g('BlendFuncSeparate',None,U,U,U,U)(0x0302 if wrong else 1,0x0303,1,0x0303)
            g('DrawArrays',None,U,I,I)(4,0,3)
            g('Disable',None,U)(0x0C11)
            require_clean()
            blit(msaa, resolve, 0x2600)
            require_clean()
            raw=read(resolve)
            (output/f'g{generation}-s{samples}-{label}.rgba').write_bytes(raw)
            changed_edge=check(raw,predicted(internal==0x8C43,wrong),bg)
            center=list(raw[(8*D+8)*4:(8*D+8)*4+4])
            assert max(abs(a-b) for a,b in zip(center,predicted(True))) >= 10 if label.startswith('adversarial') else True
            rows.append({'case':label,'readback_sha256':hashlib.sha256(raw).hexdigest(),'center':center,
                         'analytical_oracle':predicted(internal==0x8C43,wrong),'guard_rgba':list(raw[:4]),
                         'correct_policy': not label.startswith('adversarial'),'scope':'software correctness only',
                         'changed_adjacent_edge_pixels':changed_edge})
        if samples:
            g('BindFramebuffer',None,U,U)(GL_FRAMEBUFFER,resolve)
            clear((0,1,0,1))
            guard=read(resolve)
            blit(msaa,resolve,0x2600,D-1)
            error=glerr()
            assert error==0x0502,hex(error)
            assert read(resolve)==guard
            rows.append({'case':'adversarial-scaled-msaa-resolve','gl_error':hex(error),'destination_unchanged':True})
        rows.append(resolved_scene_ui(resolve))
    finally:
        for kind, handles in created.items():
            for handle in handles: funcs[kind][1](1,c.byref(handle))
        for sh in shaders: g('DeleteShader',None,U)(sh)
        for prog in programs: g('DeleteProgram',None,U)(prog)
        require_clean()
        assert make_current(display,None,None,None)
        assert destroy_context(display,context) and destroy_surface(display,surface)
    return {'context_generation':generation,'surface_generation':generation,'requested_fbo_samples':allocated_samples,'fbo_samples':samples,'rgba8_supported_msaa':list(supported),
            'device':ident,'cases':rows}

def main():
    output=Path(sys.argv[1])
    output.mkdir()
    display=software_display()
    major,minor=I(),I()
    assert display and initialize(display,c.byref(major),c.byref(minor)), 'cannot initialize software EGL'
    assert bind_api(0x30A0)
    cfg,count=P(),I()
    attrs=ints(0x3033,1,0x3040,0x40,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038)
    assert choose(display,attrs,c.byref(cfg),1,c.byref(count)) and count.value==1
    try:
        generations=[scenario(display,cfg,n,s,output) for n,s in [(1,0),(2,4),(3,4)]]
    finally:
        assert terminate(display)
    first,second=(row['cases'] for row in generations[1:])
    assert first==second
    print(json.dumps({'status':'PASS_SOFTWARE_GLES_CORRECTNESS','egl':f'{major.value}.{minor.value}',
                      'backend':'angle-swiftshader-vulkan' if angle else 'mesa-gallium-software',
                      'generations':generations,'controlled_create_destroy_recreate_match':True,
                      'requested_4x_supported':generations[1]['fbo_samples']==4,
                      'strict_ui_compositing_validated':True,
                      'exact_context_loss_observed':False,'physical_hardware_verified':False,
                      'performance_measured':False},indent=2))
if __name__=='__main__':
    main()
