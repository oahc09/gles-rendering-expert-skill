#version 300 es
precision highp float;

out vec4 color;
void main(){mat2 m=mat2(1);vec3 x=m*vec3(1);color=vec4(x,1);}
