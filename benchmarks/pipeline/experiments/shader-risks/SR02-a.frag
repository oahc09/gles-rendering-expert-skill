#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
void main(){if(uv.x>0.5) color=texture(image,uv);else color=vec4(0,0,0,1);}
