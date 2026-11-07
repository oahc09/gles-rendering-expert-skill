#version 300 es
precision highp float;
precision highp int;
in highp vec2 uv;
uniform sampler2D image;
layout(location = 0) out vec4 color;
void main(){
vec4 v0=vec4(0.03125);
vec4 v1=vec4(0.0625);
vec4 v2=vec4(0.09375);
vec4 v3=vec4(0.125);
vec4 v4=vec4(0.15625);
vec4 v5=vec4(0.1875);
vec4 v6=vec4(0.21875);
vec4 v7=vec4(0.25);
vec4 v8=vec4(0.28125);
vec4 v9=vec4(0.3125);
vec4 v10=vec4(0.34375);
vec4 v11=vec4(0.375);
vec4 v12=vec4(0.40625);
vec4 v13=vec4(0.4375);
vec4 v14=vec4(0.46875);
vec4 v15=vec4(0.5);
vec4 v16=vec4(0.53125);
vec4 v17=vec4(0.5625);
vec4 v18=vec4(0.59375);
vec4 v19=vec4(0.625);
color=texture(image,uv);}
