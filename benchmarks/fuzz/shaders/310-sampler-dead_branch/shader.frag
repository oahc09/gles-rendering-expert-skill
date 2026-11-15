#version 310 es
precision highp float;
precision highp int;
layout(location=0) out vec4 color;
uniform highp sampler2D tex;
void main() {
color = texture(tex, vec2(0.5)) * (1.0 + 1.0);
if (false) { color = vec4(0.0); }
}
