#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
uniform sampler2D images[2];
uniform int index;
void main(){color=index==0?texture(images[0],uv):texture(images[1],uv);}
