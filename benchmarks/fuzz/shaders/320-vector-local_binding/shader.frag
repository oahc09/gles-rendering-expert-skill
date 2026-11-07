#version 320 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
void main() {
float localValue = (1.0 + 1.0);
vec2 pair = vec2(localValue); color = vec4(pair, pair);
}
