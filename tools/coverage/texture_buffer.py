"""Finite EXT route; OES/core aliases are not interchangeable evidence."""
def route(version,extensions,entrypoints):
 return 'EXT' if tuple(version)>=(3,1) and 'GL_EXT_texture_buffer' in extensions and {'glTexBufferEXT','glTexBufferRangeEXT'}<=set(entrypoints) else 'TEXTURE_2D'
def valid_fetch(index,texels):return type(index) is int and type(texels) is int and 0<=index<texels
def accepted_route(report):
 return 'EXT' if report.get('status')=='HOST_PASS' and report.get('facts',{}).get('route')=='EXT' else 'TEXTURE_2D'
