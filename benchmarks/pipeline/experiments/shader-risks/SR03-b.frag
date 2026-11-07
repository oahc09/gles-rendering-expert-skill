#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
uniform bool enabled;
void main(){vec4 sampled=texture(image,uv);color=enabled?sampled:vec4(0,0,0,1);}
