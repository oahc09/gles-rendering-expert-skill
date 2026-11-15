#version 300 es
precision mediump float;
layout(location=0) out vec4 color;
void main(){vec2 uv=gl_FragCoord.xy/4.0; color=vec4(uv,0.25,1.0);}
