#!/usr/bin/env python3
"""Execute 8-bit BT.709 studio-range planar video readback on software GLES."""
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
W, H = 5, 3


def ints(*values):
    return (I * len(values))(*values)


def e(name, result, *args):
    fn = getattr(egl, 'egl' + name)
    fn.restype, fn.argtypes = result, args
    return fn


proc = e('GetProcAddress', P, S)


def g(name, result, *args):
    address = proc(('gl' + name).encode())
    assert address, name
    return c.CFUNCTYPE(result, *args)(address)


def display():
    if not angle:
        return e('GetDisplay', P, P)(None)
    address = proc(b'eglGetPlatformDisplayEXT')
    assert address
    return c.CFUNCTYPE(P, U, P, P)(address)(0x3202, None, ints(0x3203, 0x3450, 0x3209, 0x3487, 0x3038))


VERTEX = b"""#version 300 es
out vec2 uv;
void main(){
    vec2 p[3]=vec2[3](vec2(-1.,-1.),vec2(3.,-1.),vec2(-1.,3.));
    uv=(p[gl_VertexID]+1.)*.5;
    gl_Position=vec4(p[gl_VertexID],0.,1.);
}
"""
PLANES = (
    ((90, 99, 108, 117, 126), (105, 114, 123, 132, 141), (120, 129, 138, 147, 156)),
    ((112, 96, 160), (150, 135, 104)),
    ((105, 155, 120), (160, 100, 146)),
)
STRIDES = (8, 5, 7)


def oracle(x, y):
    iy, u, v = PLANES
    cx, cy = x // 2, y // 2
    luma = (iy[y][x] - 16) / 219
    cb, cr = (u[cy][cx] - 128) / 224, (v[cy][cx] - 128) / 224
    kr, kb = 0.2126, 0.0722
    r, b = luma + 2 * (1 - kr) * cr, luma + 2 * (1 - kb) * cb
    green = (luma - kr * r - kb * b) / (1 - kr - kb)
    return tuple(round(max(0, min(1, n)) * 255) for n in (r, green, b)) + (255,)


def mismatches(raw):
    rows = []
    for y in range(H):
        for x in range(W):
            begin = (y * W + x) * 4
            actual = tuple(raw[begin:begin + 4])
            want = oracle(x, y)
            if any(abs(a - b) > 1 for a, b in zip(actual, want)):
                rows.append({'pixel': [x, y], 'observed': actual, 'expected': want})
    return rows


def scenario(dpy, config, generation, fragment, output, repro_only):
    surface = e('CreatePbufferSurface', P, P, P, P)(dpy, config, ints(0x3057, W, 0x3056, H, 0x3038))
    ctx = e('CreateContext', P, P, P, P, P)(dpy, config, None, ints(0x3098, 3, 0x3038))
    current = e('MakeCurrent', U, P, P, P, P)
    assert ctx and surface and current(dpy, surface, surface, ctx)
    shaders = []
    textures = (U * 3)()
    prog = 0

    def clean():
        error = g('GetError', U)()
        assert error == 0, hex(error)

    def compile_shader(kind, code):
        name = g('CreateShader', U, U)(kind)
        shaders.append(name)
        source = S(code)
        g('ShaderSource', None, U, I, P, P)(name, 1, c.byref(source), None)
        g('CompileShader', None, U)(name)
        status = I()
        g('GetShaderiv', None, U, U, P)(name, 0x8B81, c.byref(status))
        if not status.value:
            log = c.create_string_buffer(2048)
            g('GetShaderInfoLog', None, U, I, P, P)(name, 2048, None, log)
            raise RuntimeError(log.value.decode())
        return name

    try:
        gl_string = g('GetString', S, U)
        renderer = gl_string(0x1F01).decode()
        lower = renderer.lower()
        assert ('angle' in lower and 'swiftshader' in lower) if angle else ('llvmpipe' in lower)
        prog = g('CreateProgram', U)()
        for kind, source in [(0x8B31, VERTEX), (0x8B30, fragment)]:
            g('AttachShader', None, U, U)(prog, compile_shader(kind, source))
        g('LinkProgram', None, U)(prog)
        status = I()
        g('GetProgramiv', None, U, U, P)(prog, 0x8B82, c.byref(status))
        assert status.value
        g('UseProgram', None, U)(prog)
        loc = g('GetUniformLocation', I, U, S)
        flag = loc(prog, b'blockAligned420')
        assert (flag == -1) if repro_only else (flag >= 0)
        g('Uniform2f', None, I, F, F)(loc(prog, b'krKb'), 0.2126, 0.0722)
        setint = g('Uniform1i', None, I, I)
        setint(loc(prog, b'limitedRange'), 1)
        g('GenTextures', None, I, P)(3, textures)
        for n, word in enumerate((b'yPlane', b'uPlane', b'vPlane')):
            setint(loc(prog, word), n)
            g('ActiveTexture', None, U)(0x84C0 + n)
            g('BindTexture', None, U, U)(0x0DE1, textures[n])
            for param in (0x2800, 0x2801):
                g('TexParameteri', None, U, U, I)(0x0DE1, param, 0x2600)
            for param in (0x2802, 0x2803):
                g('TexParameteri', None, U, U, I)(0x0DE1, param, 0x812F)
        clean()

        def upload(frame_generation, padded, planes=PLANES):
            if frame_generation != generation:
                return False  # no native upload for a stale frame
            store = g('PixelStorei', None, U, I)
            try:
                store(0x0CF5, 1)  # GL_UNPACK_ALIGNMENT
                for n, (rows, stride) in enumerate(zip(planes, STRIDES)):
                    width = len(rows[0])
                    pitch = stride if padded else width
                    # Valid bytes after each row, outside the image. Deliberately
                    # colored canaries detect accidental visible stride bytes.
                    body = bytes(v for row in rows for v in (*row, *([0xEE] * (pitch - width))))
                    payload = c.create_string_buffer(body)
                    store(0x0CF2, pitch if padded else 0)  # GL_UNPACK_ROW_LENGTH (texels)
                    g('ActiveTexture', None, U)(0x84C0 + n)
                    g('BindTexture', None, U, U)(0x0DE1, textures[n])
                    g('TexImage2D', None, U, I, I, I, I, I, U, U, P)(
                        0x0DE1, 0, 0x8229, width, len(rows), 0, 0x1903, 0x1401, payload)
                clean()
            finally:
                store(0x0CF2, 0)
                store(0x0CF5, 4)
            return True

        def render(blocks):
            if flag >= 0:
                setint(flag, int(blocks))
            g('Viewport', None, I, I, I, I)(0, 0, W, H)
            g('DrawArrays', None, U, I, I)(4, 0, 3)
            raw = (c.c_ubyte * (W * H * 4))()
            g('ReadPixels', None, I, I, I, I, U, U, P)(0, 0, W, H, 0x1908, 0x1401, raw)
            clean()
            return bytes(raw)

        assert upload(generation, padded=True)
        legacy = render(False)
        discrepancy = mismatches(legacy)
        assert discrepancy and any(r['pixel'][0] == 3 for r in discrepancy)
        (output / f'g{generation}-normalized.rgba').write_bytes(legacy)
        result = {'generation': generation, 'renderer': renderer, 'gles': gl_string(0x1F02).decode(),
                  'legacy_vs_block_mismatches': discrepancy, 'legacy_sha256': hashlib.sha256(legacy).hexdigest()}
        if repro_only:
            return result
        block = render(True)
        assert not mismatches(block), mismatches(block)
        assert upload(generation, padded=False)
        assert render(True) == block
        late_planes = tuple(tuple(tuple(255 - value for value in row) for row in plane) for plane in PLANES)
        stale_rejected = generation == 1 or not upload(generation - 1, padded=True, planes=late_planes)
        assert stale_rejected and render(True) == block
        assert render(False) == legacy, 'legacy normalized path changed after switching modes'
        (output / f'g{generation}-blocks.rgba').write_bytes(block)
        result.update(blocks_sha256=hashlib.sha256(block).hexdigest(), tight_fallback_matches=True,
                      stale_generation_rejected=generation > 1 and stale_rejected)
        return result
    finally:
        g('DeleteTextures', None, I, P)(3, textures)
        for name in shaders:
            g('DeleteShader', None, U)(name)
        if prog:
            g('DeleteProgram', None, U)(prog)
        assert current(dpy, None, None, None)
        assert e('DestroyContext', U, P, P)(dpy, ctx) and e('DestroySurface', U, P, P)(dpy, surface)


def main():
    assert len(sys.argv) in (3, 4)
    shader_file, output = map(Path, sys.argv[1:3])
    repro_only = len(sys.argv) == 4
    if repro_only:
        assert sys.argv[3] == '--repro-only'
    output.mkdir()
    fragment = shader_file.read_bytes()
    dpy = display()
    major, minor = I(), I()
    assert dpy and e('Initialize', U, P, P, P)(dpy, c.byref(major), c.byref(minor))
    assert e('BindAPI', U, U)(0x30A0)
    conf, count = P(), I()
    attrs = ints(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038)
    assert e('ChooseConfig', U, P, P, P, I, P)(dpy, attrs, c.byref(conf), 1, c.byref(count)) and count.value == 1
    try:
        generations = [scenario(dpy, conf, gen, fragment, output, repro_only) for gen in (1, 2)]
    finally:
        assert e('Terminate', U, P)(dpy)
    if not repro_only:
        assert generations[0]['blocks_sha256'] == generations[1]['blocks_sha256']
    print(json.dumps({'status': 'LEGACY_ODD_CHROMA_MISMATCH_REPRODUCED' if repro_only else 'PASS_SOFTWARE_VIDEO_CORRECTNESS',
                      'shader_sha256': hashlib.sha256(fragment).hexdigest(), 'dimensions': [W, H],
                      'source_row_strides': STRIDES, 'generations': generations,
                      'physical_hardware_verified': False, 'external_image_or_android_verified': False}, indent=2))


if __name__ == '__main__':
    main()
