#version 320 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
uniform highp sampler2D tex;
void main() {
float localValue = (1.0 + 1.0);
color = texture(tex, vec2(0.5)) * localValue;
}
