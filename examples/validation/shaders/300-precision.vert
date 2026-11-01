#version 300 es
precision highp float;
out highp vec3 value;
void main() { gl_Position = vec4(0.0,0.0,0.0,1.0); value = vec3(1.0); }
