#version 300 es
precision highp float;
layout(std140) uniform Block{vec4 c;}u;
out vec4 color;
void main(){color=u.c;}
