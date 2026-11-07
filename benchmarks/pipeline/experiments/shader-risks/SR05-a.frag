#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
void main(){vec4 c=vec4(0);for(int i=0;i<4;i++){c+=texture(image,uv);}color=c*0.25;}
