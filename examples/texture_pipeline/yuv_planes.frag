#version 300 es
precision highp float;
uniform sampler2D yPlane;
uniform sampler2D uPlane;
uniform sampler2D vPlane;
uniform vec2 krKb; // BT.601 .299,.114; BT.709 .2126,.0722; BT.2020 .2627,.0593
uniform bool limitedRange;
in vec2 uv;
out vec4 color;
void main() {
    vec3 code=vec3(texture(yPlane,uv).r,texture(uPlane,uv).r,texture(vPlane,uv).r)*255.0;
    float y=limitedRange?(code.x-16.0)/219.0:code.x/255.0;
    vec2 chroma=(code.yz-128.0)/(limitedRange?224.0:255.0);
    float r=y+2.0*(1.0-krKb.x)*chroma.y;
    float b=y+2.0*(1.0-krKb.y)*chroma.x;
    float g=(y-krKb.x*r-krKb.y*b)/(1.0-krKb.x-krKb.y);
    color=vec4(clamp(vec3(r,g,b),0.0,1.0),1.0);
    // Nonlinear SDR RGB, not linear-light output. Only explicit 8-bit YUV planes;
    // NOT samplerExternalOES, P010, HDR/PQ/HLG, or protected buffers.
}
