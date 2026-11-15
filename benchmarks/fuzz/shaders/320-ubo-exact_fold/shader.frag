#version 320 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
layout(std140) uniform Params { vec4 tint; };
void main() {
color = tint * 2.0;
}
