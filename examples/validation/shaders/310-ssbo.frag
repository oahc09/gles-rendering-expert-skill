#version 310 es
precision highp float;
layout(std430, binding=0) buffer Data { vec4 value; };
layout(location=0) out vec4 color;
void main() { color = value; }
