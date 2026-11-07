#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
uniform sampler2D images[2];
uniform int index;
void main(){color=texture(images[index],uv);}
