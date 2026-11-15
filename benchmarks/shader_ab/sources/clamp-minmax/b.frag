#version 300 es
precision highp float;
layout(location=0) out vec4 color;
void main(){vec2 uv=gl_FragCoord.xy/4.0; color=vec4(min(max(uv,vec2(0.25)),vec2(0.75)),0.0,1.0);}
