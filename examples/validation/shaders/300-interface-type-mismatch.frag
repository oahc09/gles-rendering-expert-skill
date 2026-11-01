#version 300 es
precision highp float;
in highp vec2 value;
out vec4 color;
void main() { color = vec4(value,0.0,1.0); }
