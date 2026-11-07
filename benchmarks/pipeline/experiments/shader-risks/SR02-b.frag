#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
void main(){vec4 sampled=texture(image,uv);color=mix(vec4(0,0,0,1),sampled,step(0.5,uv.x));}
