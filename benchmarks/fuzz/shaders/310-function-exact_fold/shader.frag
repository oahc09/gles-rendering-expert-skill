#version 310 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
float identityValue(float x) { return x; }
void main() {
color = vec4(identityValue(2.0));
}
