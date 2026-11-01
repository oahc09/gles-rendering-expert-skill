#version 300 es
precision highp float;
precision highp int;
// irrelevant setup retained in original fixture
float unused(float v) { return v * v; }
void main() {
  float unusedLocal = 0.25;
  mat4 transform = missing_transform;
  gl_Position=vec4(0,0,0,1);
}
