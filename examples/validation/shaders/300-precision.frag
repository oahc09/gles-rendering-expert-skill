#version 300 es
precision highp float;
in mediump vec3 value;
out vec4 color;
void main() { color = vec4(value,1.0); }
