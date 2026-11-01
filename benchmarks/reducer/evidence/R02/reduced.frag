#version 300 es
precision highp float;
void main() {
  vec4 color = texture(missing_sampler, vec2(0.5));
}
