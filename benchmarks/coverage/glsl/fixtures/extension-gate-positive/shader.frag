#version 100
#extension GL_OES_standard_derivatives : require
precision highp float;
void main(){gl_FragColor=vec4(dFdx(gl_FragCoord.x));}
