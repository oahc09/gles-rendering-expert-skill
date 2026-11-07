#version 320 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
void main() {
color = vec4((1.0 + 1.0));
if (false) { color = vec4(0.0); }
}
