#version 300 es
// multiview_stereo.vert
// -----------------------------------------------------------------------------
// Single-pass stereo rendering with ARM/Khronos multiview.
//
// Distilled from ARM's "Using multiview rendering" (OpenGL ES SDK for Android).
// One draw call renders to BOTH eyes at once, writing into the two layers of a
// GL_TEXTURE_2D_ARRAY color/depth attachment. This halves CPU draw-call overhead
// and vertex-processing cost versus rendering each eye separately -- a major win
// for VR on mobile TBDR GPUs.
//
// Requires: OpenGL ES 3.0 + GL_OVR_multiview2.
//   * GL_OVR_multiview (base) only allows gl_Position to depend on the view.
//   * GL_OVR_multiview2 (used here) lets lighting/varyings depend on the view too.
//   * num_views MUST equal the FBO's array-texture layer count.
//   * Multiview CANNOT be combined with geometry or tessellation shaders.
//
// Host-side setup (reference):
//   glGenTextures(1, &colorTex);
//   glBindTexture(GL_TEXTURE_2D_ARRAY, colorTex);
//   glTexStorage3D(GL_TEXTURE_2D_ARRAY, 1, GL_RGBA8, w, h, 2);   // 2 layers
//   glFramebufferTextureMultiviewOVR(GL_DRAW_FRAMEBUFFER, GL_COLOR_ATTACHMENT0,
//                                    colorTex, 0, /*baseViewIndex*/0, /*numViews*/2);
//   // (resolve glFramebufferTextureMultiviewOVR via eglGetProcAddress if missing)
// -----------------------------------------------------------------------------
#extension GL_OVR_multiview2 : require

layout(num_views = 2) in;   // must match FBO layer count

precision highp float;

layout(location = 0) in vec3 a_Position;
layout(location = 1) in vec3 a_Normal;

// One matrix per view (per eye). gl_ViewID_OVR selects the correct one.
uniform mat4 u_ViewProjection[2];
uniform mat4 u_Model;
uniform mat3 u_NormalMatrix;

// With multiview2 we may output view-dependent data (e.g. world/view vectors).
out mediump vec3 v_WorldNormal;
out highp   vec3 v_WorldPos;

void main() {
    highp vec4 worldPos = u_Model * vec4(a_Position, 1.0);
    v_WorldPos    = worldPos.xyz;
    v_WorldNormal = normalize(u_NormalMatrix * a_Normal);

    // gl_ViewID_OVR is 0 for the left eye, 1 for the right eye.
    gl_Position = u_ViewProjection[gl_ViewID_OVR] * worldPos;
}
