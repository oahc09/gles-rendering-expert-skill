#version 320 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
float identityValue(float x) { return x; }
void main() {
float localValue = (1.0 + 1.0);
color = vec4(identityValue(localValue));
}
