#version 300 es
precision highp float;
in vec2 uv;out vec4 color;
layout(std140) uniform Film { vec4 parameters; };
void main(){
 float ior=parameters.y;float mu=.05+.95*uv.y;
 float ct=sqrt(max(0.,1.-(1.-mu*mu)/(ior*ior)));
 float a=(1.-ior)/(1.+ior),b=(ior-1.5)/(ior+1.5);
 vec3 c=cos(12.566370614359172*ior*(parameters.x*uv.x)*ct/vec3(650.,510.,475.));
 vec3 R=(a*a+b*b+2.*a*b*c)/(1.+a*a*b*b+2.*a*b*c);
 color=vec4(mix(vec3(.04),R,parameters.z),1.);
}
