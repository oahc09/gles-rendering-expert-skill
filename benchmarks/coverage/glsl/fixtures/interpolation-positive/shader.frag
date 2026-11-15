#version 300 es
precision highp float;
flat in highp int value;
out vec4 color;
void main(){color=vec4(float(value));}
