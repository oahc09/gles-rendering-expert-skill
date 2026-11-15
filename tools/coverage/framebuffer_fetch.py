"""Capability plus ordered runtime evidence, never advertisement alone."""
def decide(extensions,noncoherent=False,barrier_entrypoint=False,barrier_before_each_pass=False,probe_pass=False):
 if noncoherent:
  if 'GL_EXT_shader_framebuffer_fetch_non_coherent' not in extensions:return 'PING_PONG'
  if not barrier_entrypoint or not barrier_before_each_pass:return 'REJECT_MISSING_ORDERING'
  return 'FETCH_NONCOHERENT' if probe_pass is True else 'PING_PONG'
 return 'FETCH_COHERENT' if 'GL_EXT_shader_framebuffer_fetch' in extensions and probe_pass is True else 'PING_PONG'
