#version 310 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
void main() {
vec2 pair = vec2((1.0 + 1.0)); color = vec4(pair, pair);
}
