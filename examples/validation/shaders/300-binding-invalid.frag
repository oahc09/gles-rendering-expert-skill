#version 300 es
precision highp float;
layout(std140, binding=0) uniform Params { vec4 tint; };
layout(location=0) out vec4 color;
void main() { color = tint; }
