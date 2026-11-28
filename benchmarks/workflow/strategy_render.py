"""Fixed GLES render controls for resolve scheduling and dynamic buffer retirement."""

import ctypes as c
from time import perf_counter_ns


class Unsupported(RuntimeError):
    pass


class Target:
    def __init__(self, host):
        self.host = host
        self.objects = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.call('glBindFramebuffer', [c.c_uint] * 2, 0x8D40, 0)
        self.call('glBindVertexArray', [c.c_uint], 0)
        self.call('glUseProgram', [c.c_uint], 0)
        for kind, name in reversed(self.objects):
            self.call('glDelete' + kind, [c.c_int, c.c_void_p], 1, c.byref(name))

    def call(self, name, signature, *args, returns=None):
        return self.host.fn(name, returns, signature)(*args)

    def make(self, kind):
        name = c.c_uint()
        self.call('glGen' + kind, [c.c_int, c.c_void_p], 1, c.byref(name))
        self.objects.append((kind, name))
        return name

    def framebuffer(self, samples):
        u, i = c.c_uint, c.c_int
        fb, color = self.make('Framebuffers'), self.make('Renderbuffers')
        self.call('glBindFramebuffer', [u, u], 0x8D40, fb)
        self.call('glBindRenderbuffer', [u, u], 0x8D41, color)
        if samples:
            self.call('glRenderbufferStorageMultisample', [u, i, u, i, i], 0x8D41, samples, 0x8058, 4, 4)
        else:
            self.call('glRenderbufferStorage', [u, u, i, i], 0x8D41, 0x8058, 4, 4)
        self.call('glFramebufferRenderbuffer', [u] * 4, 0x8D40, 0x8CE0, 0x8D41, color)
        if self.call('glCheckFramebufferStatus', [u], 0x8D40, returns=u) != 0x8CD5:
            raise RuntimeError('RGBA8 framebuffer incomplete')
        return fb

    def read(self, fb):
        u, i, p = c.c_uint, c.c_int, c.c_void_p
        self.call('glBindFramebuffer', [u, u], 0x8D40, fb)
        pixels = (c.c_ubyte * 64)()
        self.call('glReadPixels', [i] * 4 + [u, u, p], 0, 0, 4, 4, 0x1908, 0x1401, pixels)
        error = self.host.error()
        if error:
            raise RuntimeError(f'GLES experiment error {error:#x}')
        return list(pixels)


def resolve_scope(samples, *, intermediate_consumer=False, same_format=True, generation_matches=True):
    return samples >= 2 and not intermediate_consumer and same_format and generation_matches


def resolve_once(host, variant, *, use_depth=False, discard_depth=False):
    u, i, f = c.c_uint, c.c_int, c.c_float
    with Target(host) as gl:
        max_samples = i()
        gl.call('glGetIntegerv', [u, c.c_void_p], 0x8D57, c.byref(max_samples))
        samples = min(4, max_samples.value)
        if not resolve_scope(samples):
            raise Unsupported('multisample RGBA8 unavailable')
        source = gl.framebuffer(samples)
        if use_depth:
            depth = gl.make('Renderbuffers')
            gl.call('glBindRenderbuffer', [u, u], 0x8D41, depth)
            gl.call('glRenderbufferStorageMultisample', [u, i, u, i, i], 0x8D41, samples, 0x81A5, 4, 4)
            gl.call('glFramebufferRenderbuffer', [u] * 4, 0x8D40, 0x8D00, 0x8D41, depth)
            if gl.call('glCheckFramebufferStatus', [u], 0x8D40, returns=u) != 0x8CD5:
                raise Unsupported('multisample depth/color framebuffer incomplete')
        output = gl.framebuffer(0)

        def clear(red, green, blue):
            gl.call('glBindFramebuffer', [u, u], 0x8D40, source)
            gl.call('glClearColor', [f] * 4, red, green, blue, 1)
            gl.call('glClear', [u], 0x4100 if use_depth else 0x4000)

        def resolve():
            gl.call('glBindFramebuffer', [u, u], 0x8CA8, source)
            gl.call('glBindFramebuffer', [u, u], 0x8CA9, output)
            gl.call('glBlitFramebuffer', [i] * 8 + [u, u], 0, 0, 4, 4, 0, 0, 4, 4, 0x4000, 0x2600)

        gl.call('glDisable', [u], 0x0BD0)
        clear(1, 0, 0)
        if variant != 'candidate':
            resolve()
        clear(0, 1, 0)
        if variant != 'negative':
            resolve()
        if discard_depth:
            gl.call('glBindFramebuffer', [u, u], 0x8D40, source)
            gl.call('glInvalidateFramebuffer', [u, i, c.c_void_p], 0x8D40, 1, (u * 1)(0x8D00))
        return {'pixels': gl.read(output), 'samples_requested': samples,
                'resolve_count': 2 if variant == 'baseline' else 1, 'depth_invalidated': discard_depth}


SYNC_COMPLETE = {0x911A, 0x911C}


def may_reuse(sync_result, slot_generation, context_generation):
    return slot_generation == context_generation and (sync_result is None or sync_result in SYNC_COMPLETE)


FENCE_VERTEX = """#version 300 es
layout(location=0) in vec4 inputColor;
flat out vec4 vertexColor;
void main(){
    vec2 position=vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position=vec4(position*2.0-1.0,0.0,1.0);
    vertexColor=inputColor;
}"""
FENCE_FRAGMENT = """#version 300 es
precision highp float;
flat in vec4 vertexColor;
out vec4 color;
void main(){color=vertexColor;}"""
COLORS = ((1., 0., 0., 1.), (0., 1., 0., 1.), (0., 0., 1., 1.), (1., 1., 1., 1.))


def render_ring(host, variant):
    u, i, p, f = c.c_uint, c.c_int, c.c_void_p, c.c_float
    use_ring = variant == 'candidate'
    fences = {}
    program, status = host.program({'shader.vert': FENCE_VERTEX, 'shader.frag': FENCE_FRAGMENT})
    try:
        if not status['compile'] or not status['link']:
            raise RuntimeError('ring shader failed: ' + str(status))
        with Target(host) as gl:
            fb = gl.framebuffer(0)
            vao = gl.make('VertexArrays')
            slots = [gl.make('Buffers') for _ in range(2 if use_ring else 1)]
            gl.call('glUseProgram', [u], program)
            gl.call('glBindVertexArray', [u], vao)
            gl.call('glDisable', [u], 0x0BD0)
            gl.call('glViewport', [i] * 4, 0, 0, 4, 4)
            gl.call('glEnable', [u], 0x0C11)
            gl.call('glEnableVertexAttribArray', [u], 0)
            wait_ns = submit_ns = 0
            waits = []
            for frame in range(8):
                slot = frame % len(slots)
                if slot in fences:
                    t0 = perf_counter_ns()
                    wait = gl.call('glClientWaitSync', [p, u, c.c_uint64], fences[slot], 1, 5_000_000, returns=u)
                    wait_ns += perf_counter_ns() - t0
                    waits.append(wait)
                    if not may_reuse(wait, 1, 1):
                        raise RuntimeError(f'fence slot stopped before overwrite: {wait:#x}')
                    gl.call('glDeleteSync', [p], fences.pop(slot))
                color = COLORS[frame % 4] if variant != 'negative' else COLORS[0]
                raw = (f * 12)(*(color * 3))
                t0 = perf_counter_ns()
                gl.call('glBindBuffer', [u, u], 0x8892, slots[slot])
                if not use_ring or frame < len(slots):
                    gl.call('glBufferData', [u, c.c_ssize_t, p, u], 0x8892, 48, raw, 0x88E0)
                else:
                    gl.call('glBufferSubData', [u, c.c_ssize_t, c.c_ssize_t, p], 0x8892, 0, 48, raw)
                gl.call('glVertexAttribPointer', [u, i, u, c.c_ubyte, i, p], 0, 4, 0x1406, 0, 0, None)
                gl.call('glScissor', [i] * 4, frame % 4, (frame // 4) * 2, 1, 2)
                gl.call('glDrawArrays', [u, i, i], 4, 0, 3)
                if use_ring:
                    fence = gl.call('glFenceSync', [u, u], 0x9117, 0, returns=p)
                    if not fence:
                        raise RuntimeError('glFenceSync failed')
                    fences[slot] = fence
                else:
                    gl.call('glFinish', [])
                submit_ns += perf_counter_ns() - t0
            return {'pixels': gl.read(fb), 'wait_ns': wait_ns, 'wait_results': waits,
                    'cpu_submit_and_baseline_sync_ns': submit_ns, 'logical_buffer_bytes': len(slots) * 48}
    finally:
        host.fn('glDisable', None, [u])(0x0C11)
        for fence in fences.values():
            host.fn('glDeleteSync', None, [p])(fence)
        host.fn('glDeleteProgram', None, [u])(program)
