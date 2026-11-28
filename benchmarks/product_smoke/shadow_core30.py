#!/usr/bin/env python3
"""Compile the exact guide snippets and exercise PCF border semantics on software GLES."""
import argparse
import ctypes as c
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from audit_formats_culling import ROOT, checked, program, snippet
from odd_video import e, g, I, U, P, F, S, display, ints

RULE = 'references/rules/shadow-mapping-mobile.md'
VERTEX = """#version 300 es
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
"""
FIXTURE = """
out vec4 outputColor;
void main() {
    float visibility = ShadowFactor();
    outputColor = vec4(vec3(visibility), 1.0);
}
"""
# Light clip-space positions: interior, left edge, two-axis corner,
# right edge, XY outside, far, near, and behind the light.
POSITIONS = """uniform highp vec4 u_TestPoints[8];
#define v_LightSpacePos u_TestPoints[int(gl_FragCoord.x)]"""
EXPECTED = [0, 85, 142, 85, 255, 255, 255, 255]


def compile_snippets(headers, directory):
    document = (ROOT / RULE).read_text()
    setup, optional = re.findall(r'```cpp\n(.*?)\n```', document, re.S)
    assert 'GL_CLAMP_TO_BORDER' not in setup
    source = directory / 'shadow.cpp'
    commands = []
    for name in ['gl3.h', 'gl31.h', 'gl32.h']:
        source.write_text(f'#include <GLES3/{name}>\n{optional}\n'
                          'extern "C" void Setup(GLuint& shadowDepthTex, GLuint shadowFbo) {\n'
                          f'{setup}\n}}\n')
        argv = ['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-fsyntax-only',
                '-I', str(headers), str(source)]
        subprocess.run(argv, check=True)
        commands.append({'header': name, 'sha256': hashlib.sha256((headers / 'GLES3' / name).read_bytes()).hexdigest()})
    source.write_text(source.read_text().replace('GLES3/gl32.h', 'GLES3/gl3.h'))
    native = directory / 'shadow.so'
    subprocess.run(['c++', '-std=c++17', '-shared', '-fPIC', '-I', str(headers),
                    str(source), '-Wl,-l:libGLESv2.so.2', '-o', str(native)], check=True)
    return c.CDLL(str(native)), commands


def render(lib):
    dpy = display()
    major, minor, count, config = I(), I(), I(), P()
    assert dpy and e('Initialize', U, P, P, P)(dpy, c.byref(major), c.byref(minor))
    assert e('BindAPI', U, U)(0x30A0)
    attrs = ints(0x3033, 1, 0x3040, 0x40, 0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3038)
    assert e('ChooseConfig', U, P, P, P, I, P)(dpy, attrs, c.byref(config), 1, c.byref(count)) and count.value
    surface = e('CreatePbufferSurface', P, P, P, P)(dpy, config, ints(0x3057, 8, 0x3056, 1, 0x3038))
    context = e('CreateContext', P, P, P, P, P)(dpy, config, None, ints(0x3098, 3, 0x3038))
    current = e('MakeCurrent', U, P, P, P, P)
    assert surface and context and current(dpy, surface, surface, context)
    fbo, depth = U(), U()
    programs = []
    try:
        api = g('GetString', S, U)(0x1F02).decode()
        renderer = g('GetString', S, U)(0x1F01).decode()
        assert 'OpenGL ES 3.0' in api and 'llvmpipe' in renderer.lower(), (api, renderer)
        g('GenFramebuffers', None, I, P)(1, c.byref(fbo))
        lib.Setup.argtypes = [P, U]
        lib.Setup.restype = None
        lib.Setup(c.byref(depth), fbo)
        checked()
        assert g('CheckFramebufferStatus', U, U)(0x8D40) == 0x8CD5
        g('ClearDepthf', None, F)(0.25)
        g('Clear', None, U)(0x0100)
        g('BindFramebuffer', None, U, U)(0x8D40, 0)
        g('Viewport', None, I, I, I, I)(0, 0, 8, 1)
        shader = snippet(RULE, 'glsl').replace('in highp vec4 v_LightSpacePos;', POSITIONS)
        points = (F * 32)(
            0, 0, 0, 1, -0.999, 0, 0, 1, -0.999, -0.999, 0, 1,
            0.999, 0, 0, 1, -1.25, 0, 0, 1, 0, 0, 1.25, 1,
            0, 0, -1.25, 1, 0, 0, 0, -1,
        )

        def sample(source):
            p = program(vert=VERTEX, frag=source + FIXTURE)
            programs.append(p)
            g('UseProgram', None, U)(p)
            location = g('GetUniformLocation', I, U, S)(p, b'u_TestPoints[0]')
            assert location >= 0
            g('Uniform4fv', None, I, I, P)(location, 8, points)
            g('DrawArrays', None, U, I, I)(0x0004, 0, 3)
            pixels = (c.c_ubyte * 32)()
            g('ReadPixels', None, I, I, I, I, U, U, P)(0, 0, 8, 1, 0x1908, 0x1401, pixels)
            checked()
            return list(pixels)[::4]

        actual = sample(shader)
        assert all(abs(a - b) <= 1 for a, b in zip(actual, EXPECTED)), (actual, EXPECTED)
        dark_border = sample(shader.replace('visibility += 1.0;', 'visibility += 0.0;'))
        assert dark_border == [0, 0, 0, 0, 255, 255, 255, 255], dark_border
        return {'api': api, 'renderer': renderer, 'expected': EXPECTED, 'actual': actual,
                'dark_border_negative': dark_border}
    finally:
        g('UseProgram', None, U)(0)
        for p in programs:
            g('DeleteProgram', None, U)(p)
        g('DeleteTextures', None, I, P)(1, c.byref(depth))
        g('DeleteFramebuffers', None, I, P)(1, c.byref(fbo))
        assert current(dpy, None, None, None)
        assert e('DestroyContext', U, P, P)(dpy, context)
        assert e('DestroySurface', U, P, P)(dpy, surface)
        assert e('Terminate', U, P)(dpy)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headers', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as name:
        lib, compiled = compile_snippets(args.headers.resolve(), Path(name))
        result = render(lib)
    report = {'status': 'PASS_SOFTWARE_SHADOW_BOUNDARY', 'compiled': compiled, **result,
              'physical_hardware_verified': False, 'performance_measured': False}
    with args.out.open('x') as handle:
        json.dump(report, handle, indent=2)
        handle.write('\n')
    print(report['status'])
