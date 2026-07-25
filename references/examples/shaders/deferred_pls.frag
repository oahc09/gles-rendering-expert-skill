#version 300 es
// deferred_pls.frag
// -----------------------------------------------------------------------------
// Deferred shading using EXT Pixel Local Storage (PLS).
//
// Distilled from ARM's "Advanced Shading Techniques with Pixel Local Storage"
// (OpenGL ES SDK for Android). PLS keeps the ENTIRE G-Buffer inside on-chip tile
// memory across draw calls within one render pass, so it is NEVER written back to
// DRAM. On a TBDR mobile GPU (Mali/Adreno/PowerVR) this eliminates the dominant
// bandwidth/power cost of a traditional MRT G-Buffer.
//
// Requires: OpenGL ES 3.0 + GL_EXT_shader_pixel_local_storage.
//
// IMPORTANT (EXT_shader_pixel_local_storage spec constraint):
//   A shader that statically writes to PLS outputs MUST NOT also statically write
//   to fragment color outputs (o_Color). Violating this causes a COMPILE ERROR.
//   Therefore we split the logic into 3 separate compilation units selected by
//   preprocessor defines at glCompileShader time:
//     -DPASS_GEOMETRY  → geometry pass: writes PLS only
//     -DPASS_LIGHTING  → lighting pass: reads/writes PLS only
//     -DPASS_RESOLVE   → resolve pass: reads PLS, writes fragment color output
//
// Host-side lifecycle (REQUIRED around the PLS render pass):
//   glEnable(GL_SHADER_PIXEL_LOCAL_STORAGE_EXT);
//   // Draw calls for geometry, lighting, resolve sub-passes (no FBO switch!)
//   glDisable(GL_SHADER_PIXEL_LOCAL_STORAGE_EXT);
//
// See references/rules/egl-and-context.md and references/rules/powervr/pixel-local-storage-and-deferred.md
// for full host-side integration.
// -----------------------------------------------------------------------------
#extension GL_EXT_shader_pixel_local_storage : require

// Compile-time validation: exactly one pass must be defined.
#if (!defined(PASS_GEOMETRY) && !defined(PASS_LIGHTING) && !defined(PASS_RESOLVE))
  #error "One of PASS_GEOMETRY, PASS_LIGHTING, or PASS_RESOLVE must be defined."
#endif
#if (defined(PASS_GEOMETRY) && defined(PASS_LIGHTING)) \
 || (defined(PASS_GEOMETRY) && defined(PASS_RESOLVE))  \
 || (defined(PASS_LIGHTING) && defined(PASS_RESOLVE))
  #error "Only ONE of PASS_GEOMETRY, PASS_LIGHTING, PASS_RESOLVE may be defined."
#endif

precision highp float;

// PLS layout. Pack aggressively to fit the per-pixel tile budget (~128 bits).
// Store normal.xy and reconstruct z; pack the normal.z sign into albedo.a.
__pixel_localEXT FragDataLocal {
    layout(rgb10_a2) vec4 lighting;   // accumulated light (RGB) + unused A
    layout(rgb10_a2) vec4 albedo;     // material albedo (RGB) + sign(normal.z)
    layout(rg16f)    vec2 normalXY;   // view-space normal xy
    layout(r11f_g11f_b10f) vec3 posVS;// view-space position for lighting
} gbuf;

// ============================================================================
// GEOMETRY PASS — writes material into PLS (no fragment color output)
// ============================================================================
#ifdef PASS_GEOMETRY

uniform vec3 u_Albedo;
in vec3 v_NormalVS;
in vec3 v_PositionVS;

void main() {
    vec3 n = normalize(v_NormalVS);
    gbuf.lighting = vec4(0.0);          // clear accumulator at pass start
    gbuf.albedo.rgb = u_Albedo;
    gbuf.albedo.a   = (n.z >= 0.0) ? 1.0 : 0.0;
    gbuf.normalXY   = n.xy;
    gbuf.posVS      = v_PositionVS;
}

#endif // PASS_GEOMETRY

// ============================================================================
// LIGHTING PASS — reads material, accumulates light contribution (PLS only)
// ============================================================================
#ifdef PASS_LIGHTING

uniform vec3  u_LightPosVS;
uniform vec3  u_LightColor;
uniform float u_LightRadius;

vec3 decodeNormal() {
    vec2 nxy = gbuf.normalXY;
    float nz = sqrt(max(0.0, 1.0 - dot(nxy, nxy)));
    nz *= (gbuf.albedo.a > 0.5) ? 1.0 : -1.0;
    return normalize(vec3(nxy, nz));
}

void main() {
    vec3 N = decodeNormal();
    vec3 P = gbuf.posVS;
    vec3 L = u_LightPosVS - P;
    float dist = length(L);
    L /= max(dist, 1e-4);

    float ndotl = max(dot(N, L), 0.0);
    float atten = clamp(1.0 - (dist / u_LightRadius), 0.0, 1.0);
    atten *= atten;

    vec3 contribution = gbuf.albedo.rgb * u_LightColor * (ndotl * atten);
    gbuf.lighting.rgb += contribution;  // accumulate in tile memory (no DRAM)
}

#endif // PASS_LIGHTING

// ============================================================================
// RESOLVE PASS — reads accumulated light from PLS, outputs final fragment color
// ============================================================================
#ifdef PASS_RESOLVE

layout(location = 0) out vec4 o_Color;

void main() {
    o_Color = vec4(gbuf.lighting.rgb, 1.0);
}

#endif // PASS_RESOLVE
