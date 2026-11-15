#version 300 es
precision highp float;
layout(location=0) out vec4 color;
void main(){vec2 uv=gl_FragCoord.xy/4.0; color=vec4(uv.x<0.5?0.25:0.75,uv.y,0.0,1.0);}
