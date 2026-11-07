#version 310 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
layout(std140) uniform Params { vec4 tint; };
void main() {
color = tint * (1.0 + 1.0);
if (false) { color = vec4(0.0); }
}
