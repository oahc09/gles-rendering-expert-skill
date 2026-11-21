#version 300 es
precision highp float;
uniform sampler2D tex;
out vec4 color;
void main(){color=texture(tex,vec3(.5));}
