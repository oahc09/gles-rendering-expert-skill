#!/usr/bin/env python3
"""Execute the audited GLES documentation snippets on Mesa llvmpipe."""
import ctypes as c
import hashlib
import json
from pathlib import Path
import re
import sys

from odd_video import e, g, I, U, P, F, S, display, ints

ROOT = Path(__file__).resolve().parents[2]
FULLSCREEN = """#version 300 es
out highp vec2 v_Uv;
out mediump vec4 v_Color;
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
    v_Uv = p;
    v_Color = vec4(1.0);
}
"""
POINTS = """#version 300 es
void main() {
    gl_Position = vec4(-0.75 + 0.5 * float(gl_VertexID), 0.0, 0.0, 1.0);
    gl_PointSize = 1.0;
}
"""
RED = """#version 300 es
precision mediump float;
out vec4 color;
void main() { color = vec4(1, 0, 0, 1); }
"""
SDF = """#version 300 es
precision mediump float;
uniform sampler2D u_Atlas;
in highp vec2 v_Uv;
out vec4 color;
void main() { color = vec4(vec3(step(0.5, texture(u_Atlas, v_Uv).r)), 1); }
"""


def snippet(path, stage):
    matches = re.findall(r'```' + stage + r'\n(.*?)\n```', (ROOT / path).read_text(), re.S)
    assert len(matches) == 1, path
    return matches[0]


def checked():
    error = g('GetError', U)()
    assert error == 0, hex(error)


def program(**sources):
    result = g('CreateProgram', U)()
    for kind, source in sources.items():
        shader = g('CreateShader', U, U)({'vert': 0x8B31, 'frag': 0x8B30, 'comp': 0x91B9}[kind])
        raw = S(source.encode())
        g('ShaderSource', None, U, I, P, P)(shader, 1, c.byref(raw), None)
        g('CompileShader', None, U)(shader)
        status = I()
        g('GetShaderiv', None, U, U, P)(shader, 0x8B81, c.byref(status))
        if not status.value:
            log = c.create_string_buffer(8192)
            g('GetShaderInfoLog', None, U, I, P, P)(shader, len(log), None, log)
            raise RuntimeError(log.value.decode())
        g('AttachShader', None, U, U)(result, shader)
        g('DeleteShader', None, U)(shader)
    g('LinkProgram', None, U)(result)
    status = I()
    g('GetProgramiv', None, U, U, P)(result, 0x8B82, c.byref(status))
    if not status.value:
        log = c.create_string_buffer(8192)
        g('GetProgramInfoLog', None, U, I, P, P)(result, len(log), None, log)
        raise RuntimeError(log.value.decode())
    checked()
    return result


def clear():
    g('ClearColor', None, F, F, F, F)(0, 0, 0, 1)
    g('Clear', None, U)(0x4000)


def read():
    out = (c.c_ubyte * 16)()
    g('ReadPixels', None, I, I, I, I, U, U, P)(0, 0, 4, 1, 0x1908, 0x1401, out)
    checked()
    return list(out)


def culling():
    a = snippet('references/cards/28-gpu-culling.md', 'glsl')
    assert a == snippet('references/rules/gpu-culling.md', 'glsl')
    good = program(comp=a)
    old = program(comp=a.replace('>= -bt.sphere.w', '>= 0.0'))
    draw = program(vert=POINTS, frag=RED)

    class Batch(c.Structure):
        _fields_ = [('sphere', F * 4), ('range', U * 2), ('pad', U * 2)]

    # One normalized inward x-plane plus five permissive planes.
    spheres = [(-1.25, 1.0), (-1.0, 1.0), (-0.25, 1.0), (1.25, 1.0)]
    data = (Batch * 4)(*(Batch((x, 0, 0, radius), (slot, 1), (0, 0))
                        for slot, (x, radius) in enumerate(spheres)))
    planes = (F * 24)(1, 0, 0, 0, *([1, 0, 0, 100] * 5))
    commands = (U * 16)()
    buffers = (U * 3)()
    g('GenBuffers', None, I, P)(len(buffers), buffers)
    for buffer, target, binding, payload in ((buffers[0], 0x8A11, 0, planes),
                                             (buffers[1], 0x90D2, 1, data),
                                             (buffers[2], 0x90D2, 3, commands)):
        g('BindBuffer', None, U, U)(target, buffer)
        g('BufferData', None, U, c.c_ssize_t, P, U)(target, c.sizeof(payload), payload, 0x88E8)
        g('BindBufferBase', None, U, U, U)(target, binding, buffer)
    g('BindBuffer', None, U, U)(0x8F3F, buffers[2])

    def dispatch_and_draw(compute, multi=None):
        clear()
        g('UseProgram', None, U)(compute)
        loc = g('GetUniformLocation', I, U, S)(compute, b'u_BatchCount')
        assert loc >= 0
        g('Uniform1ui', None, I, U)(loc, 4)
        g('DispatchCompute', None, U, U, U)(1, 1, 1)
        g('MemoryBarrier', None, U)(0x40)  # GL_COMMAND_BARRIER_BIT
        g('UseProgram', None, U)(draw)
        if multi:
            multi(0, None, 4, 16)
        else:
            for slot in range(4):
                g('DrawArraysIndirect', None, U, P)(0, slot * 16)
        return read()

    try:
        core = dispatch_and_draw(good)
        center_only = dispatch_and_draw(old)
        assert core[::4] == [0, 255, 255, 255], core
        assert center_only[::4] == [0, 0, 0, 255], center_only
        count = I()
        g('GetIntegerv', None, U, P)(0x821D, c.byref(count))
        extensions = {g('GetStringi', S, U, U)(0x1F03, i) for i in range(count.value)}
        ext = {'status': 'NOT_ADVERTISED_CORE_FALLBACK_EXERCISED'}
        if b'GL_EXT_multi_draw_indirect' in extensions:
            ext_pixels = dispatch_and_draw(good, g('MultiDrawArraysIndirectEXT', None, U, P, I, I))
            assert ext_pixels == core
            ext = {'status': 'PASS', 'rgba': ext_pixels}
        return dict(core_rgba=core, center_only_rgba=center_only, multi_draw=ext,
                    shader_sha256=hashlib.sha256(a.encode()).hexdigest())
    finally:
        g('UseProgram', None, U)(0)
        for p in (good, old, draw):
            g('DeleteProgram', None, U)(p)
        g('DeleteBuffers', None, I, P)(len(buffers), buffers)


def formats():
    shader_paths = ('references/rules/text-rendering-sdf.md', 'references/cards/29-text-rendering-sdf.md')
    texture = U()
    g('GenTextures', None, I, P)(1, c.byref(texture))
    g('BindTexture', None, U, U)(0x0DE1, texture)
    g('PixelStorei', None, U, I)(0x0CF5, 1)  # RGB8 rows need not have 4-byte alignment.
    for param in (0x2800, 0x2801):
        g('TexParameteri', None, U, U, I)(0x0DE1, param, 0x2600)

    def sample(p, internal, upload, sample_bytes):
        clear()
        data = (c.c_ubyte * len(sample_bytes))(*sample_bytes)
        g('TexImage2D', None, U, I, I, I, I, I, U, U, P)(
            0x0DE1, 0, internal, 1, 1, 0, upload, 0x1401, data)
        g('UseProgram', None, U)(p)
        g('DrawArrays', None, U, I, I)(4, 0, 3)
        return read()

    def check(p, cases):
        result = {}
        for name, internal, upload, values, expected in cases:
            readback = sample(p, internal, upload, values)
            assert readback == [expected, expected, expected, 255] * 4, (name, readback)
            result[name] = readback
        return result

    rows = {}
    try:
        for path in shader_paths:
            source = snippet(path, 'glsl')
            p = program(vert=FULLSCREEN, frag=source)
            try:
                rows[path] = check(p, (
                    ('rgb_front', 0x8051, 0x1907, [20, 240, 250], 255),
                    ('rgba_front', 0x8058, 0x1908, [20, 240, 250, 255], 255),
                    ('rgb_back', 0x8051, 0x1907, [20, 40, 250], 0),
                    ('r8_front_broken', 0x8229, 0x1903, [20], 0),
                ))
            finally:
                g('UseProgram', None, U)(0)
                g('DeleteProgram', None, U)(p)
        p = program(vert=FULLSCREEN, frag=SDF)
        try:
            rows['single_channel_sdf'] = check(p, (
                ('r8_front', 0x8229, 0x1903, [240], 255),
                ('r8_back', 0x8229, 0x1903, [20], 0),
            ))
        finally:
            g('UseProgram', None, U)(0)
            g('DeleteProgram', None, U)(p)
    finally:
        g('DeleteTextures', None, I, P)(1, c.byref(texture))
    return rows


def depth_only():
    framebuffer, depth = U(), U()
    g('GenFramebuffers', None, I, P)(1, c.byref(framebuffer))
    g('GenTextures', None, I, P)(1, c.byref(depth))
    try:
        g('BindFramebuffer', None, U, U)(0x8D40, framebuffer)
        g('BindTexture', None, U, U)(0x0DE1, depth)
        g('TexStorage2D', None, U, I, U, I, I)(0x0DE1, 1, 0x81A5, 4, 1)
        g('FramebufferTexture2D', None, U, U, U, U, I)(0x8D40, 0x8D00, 0x0DE1, depth, 0)
        g('DrawBuffers', None, I, P)(1, (U * 1)(0))
        g('ReadBuffer', None, U)(0)
        status = g('CheckFramebufferStatus', U, U)(0x8D40)
        assert status == 0x8CD5
        checked()
        return {'status': 'FRAMEBUFFER_COMPLETE'}
    finally:
        g('BindFramebuffer', None, U, U)(0x8D40, 0)
        g('DeleteFramebuffers', None, I, P)(1, c.byref(framebuffer))
        g('DeleteTextures', None, I, P)(1, c.byref(depth))


def main(output):
    dpy = display()
    major, minor, count, config = I(), I(), I(), P()
    assert dpy and e('Initialize', U, P, P, P)(dpy, c.byref(major), c.byref(minor))
    assert e('BindAPI', U, U)(0x30A0)
    attrs = ints(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038)
    assert e('ChooseConfig', U, P, P, P, I, P)(dpy, attrs, c.byref(config), 1, c.byref(count)) and count.value
    surface = e('CreatePbufferSurface', P, P, P, P)(dpy, config, ints(0x3057, 4, 0x3056, 1, 0x3038))
    context = e('CreateContext', P, P, P, P, P)(dpy, config, None, ints(0x3098, 3, 0x3038))
    current = e('MakeCurrent', U, P, P, P, P)
    assert surface and context and current(dpy, surface, surface, context)
    vao = U()
    try:
        renderer = g('GetString', S, U)(0x1F01).decode()
        api = g('GetString', S, U)(0x1F02).decode()
        assert 'llvmpipe' in renderer.lower() and re.search(r'OpenGL ES 3\.[12]', api), (renderer, api)
        g('Viewport', None, I, I, I, I)(0, 0, 4, 1)
        g('GenVertexArrays', None, I, P)(1, c.byref(vao))
        g('BindVertexArray', None, U)(vao)
        data = dict(status='PASS_SOFTWARE_GLES_CORRECTNESS', renderer=renderer, api=api,
                    culling=culling(), depth_only=depth_only(), atlas=formats(), physical_hardware_verified=False,
                    performance_measured=False, font_layout_verified=False)
        checked()
    finally:
        g('DeleteVertexArrays', None, I, P)(1, c.byref(vao))
        assert current(dpy, None, None, None)
        assert e('DestroyContext', U, P, P)(dpy, context)
        assert e('DestroySurface', U, P, P)(dpy, surface)
        assert e('Terminate', U, P)(dpy)
    with Path(output).open('x') as f:
        json.dump(data, f, indent=2)
        f.write('\n')
    print(data['status'])


if __name__ == '__main__':
    main(sys.argv[1])
