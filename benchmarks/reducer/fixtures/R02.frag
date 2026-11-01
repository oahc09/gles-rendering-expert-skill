#version 300 es
precision highp float;
precision highp int;
out vec4 outputColor;
// irrelevant setup retained in original fixture
float unused(float v) { return v * v; }
void main() {
  float unusedLocal = 0.25;
  vec4 color = texture(missing_sampler, vec2(0.5));
  outputColor=vec4(1);
}
