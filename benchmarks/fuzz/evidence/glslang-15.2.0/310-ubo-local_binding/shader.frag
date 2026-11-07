#version 310 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
layout(std140) uniform Params { vec4 tint; };
void main() {
float localValue = (1.0 + 1.0);
color = tint * localValue;
}
