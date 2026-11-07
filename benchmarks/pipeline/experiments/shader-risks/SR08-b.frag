#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
// Build only the used macro combination.
void main(){color=texture(image,uv);}
