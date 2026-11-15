#version 300 es
precision highp float;
precision highp int;
uniform sampler2D tex; layout(location=0) out vec4 color; void main() { color=texture(tex, vec3(0.0)); }
