#version 300 es
precision highp float;

out vec4 color;
void main(){mat2 m=mat2(1);float a[2]=float[2](.2,.3);color=vec4(m*vec2(a[0]),0,1);}
