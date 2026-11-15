#version 300 es
precision highp float;

out vec4 color;
void main(){float x=0.;for(int i=0;i<3;i++){if(i==1)continue;x+=.1;}color=vec4(x);}
