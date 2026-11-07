#version 310 es
precision highp float;
precision highp int;
in vec4 bridge; layout(location=0) out vec4 color; void main() { color=bridge; }
