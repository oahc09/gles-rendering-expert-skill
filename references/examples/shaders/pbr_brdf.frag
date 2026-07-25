#version 300 es
/**
 * @file pbr_brdf.frag
 * @brief Cook-Torrance PBR fragment shader for OpenGL ES 3.0 (GLSL ES 3.00).
 *
 * Features:
 * - Metallic-Roughness workflow (glTF 2.0 compatible)
 * - Image-Based Lighting (IBL) with pre-filtered environment map
 * - Multiple punctual lights (directional + point)
 * - Mobile-optimized: mediump where safe, branchless math
 *
 * TBDR Note: This shader is designed for forward rendering.
 * For deferred on mobile, consider GL_EXT_shader_framebuffer_fetch
 * to avoid G-Buffer DRAM round-trips.
 */

// Fragment shader MUST declare precision
precision mediump float;
precision highp int;

// ============================================================================
// Inputs from vertex shader
// ============================================================================
in highp vec3 v_WorldPos;      // highp: avoid vertex jitter at large coordinates
in mediump vec3 v_WorldNormal; // mediump: sufficient for normalized vectors
in mediump vec2 v_TexCoord;    // mediump: OK for textures up to 4096x4096

// ============================================================================
// Output
// ============================================================================
layout(location = 0) out vec4 outColor;

// ============================================================================
// Material UBO (per-material, rarely changes)
// Binding assigned from host via glUniformBlockBinding (GLSL ES 3.00 does not
// support layout(binding=N); that requires GLSL ES 3.10+).
// ============================================================================
layout(std140) uniform MaterialBlock {
    mediump vec4  u_BaseColor;      // Linear RGBA base color
    mediump float u_Metallic;       // [0, 1]
    mediump float u_Roughness;      // [0, 1]
    mediump float u_AO;             // Ambient occlusion [0, 1]
    mediump float u_AlphaCutoff;    // For alpha testing
};

// ============================================================================
// Scene UBO (per-frame)
// ============================================================================
#define MAX_LIGHTS 4

struct Light {
    highp vec4 position;    // xyz = position, w = type (0=dir, 1=point)
    mediump vec4 color;     // rgb = color, a = intensity
    mediump vec4 direction; // xyz = direction (for directional lights)
    mediump vec4 params;    // x = range, y = spotInner, z = spotOuter, w = unused
};

layout(std140) uniform SceneBlock {
    highp mat4  u_ViewProjection;
    highp vec4  u_CameraPos;    // xyz = camera world position
    mediump vec4 u_AmbientColor;
    int         u_LightCount;
    Light       u_Lights[MAX_LIGHTS];
};

// ============================================================================
// Textures
// ============================================================================
uniform mediump sampler2D u_BaseColorMap;   // sRGB albedo texture
uniform mediump sampler2D u_NormalMap;      // Tangent-space normal map
uniform mediump sampler2D u_MetallicRoughnessMap; // G=roughness, B=metallic (glTF)
uniform mediump sampler2D u_AOMap;          // Ambient occlusion

// IBL textures
uniform mediump samplerCube u_EnvMap;           // Pre-filtered environment (mip = roughness)
uniform mediump sampler2D   u_BRDFLut;          // Split-sum BRDF integration LUT

// ============================================================================
// Constants
// ============================================================================
const mediump float PI = 3.14159265359;
const mediump float MIN_ROUGHNESS = 0.04; // Avoid division by zero at roughness=0

// ============================================================================
// PBR Functions (Cook-Torrance BRDF)
// ============================================================================

/// Normal Distribution Function — GGX/Trowbridge-Reitz
/// Uses mediump: N·H is in [0,1], no large-value precision issues
mediump float DistributionGGX(mediump vec3 N, mediump vec3 H, mediump float roughness) {
    mediump float a = roughness * roughness;
    mediump float a2 = a * a;
    mediump float NdotH = max(dot(N, H), 0.0);
    mediump float NdotH2 = NdotH * NdotH;

    mediump float denom = NdotH2 * (a2 - 1.0) + 1.0;
    return a2 / (PI * denom * denom);
}

/// Geometry Function — Smith's method with Schlick-GGX
mediump float GeometrySchlickGGX(mediump float NdotV, mediump float roughness) {
    mediump float r = roughness + 1.0;
    mediump float k = (r * r) / 8.0;
    return NdotV / (NdotV * (1.0 - k) + k);
}

mediump float GeometrySmith(mediump vec3 N, mediump vec3 V, mediump vec3 L, mediump float roughness) {
    mediump float NdotV = max(dot(N, V), 0.0);
    mediump float NdotL = max(dot(N, L), 0.0);
    return GeometrySchlickGGX(NdotV, roughness) * GeometrySchlickGGX(NdotL, roughness);
}

/// Fresnel — Schlick approximation
mediump vec3 FresnelSchlick(mediump float cosTheta, mediump vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

/// Fresnel with roughness (for IBL ambient)
mediump vec3 FresnelSchlickRoughness(mediump float cosTheta, mediump vec3 F0, mediump float roughness) {
    return F0 + (max(vec3(1.0 - roughness), F0) - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

// ============================================================================
// Normal Mapping (Tangent-space → World-space)
// ============================================================================
mediump vec3 GetNormalFromMap() {
    mediump vec3 tangentNormal = texture(u_NormalMap, v_TexCoord).xyz * 2.0 - 1.0;

    // Reconstruct TBN from screen-space derivatives (no tangent attribute needed)
    highp vec3 Q1 = dFdx(v_WorldPos);
    highp vec3 Q2 = dFdy(v_WorldPos);
    mediump vec2 st1 = dFdx(v_TexCoord);
    mediump vec2 st2 = dFdy(v_TexCoord);

    mediump vec3 N = normalize(v_WorldNormal);
    mediump vec3 T = normalize(Q1 * st2.t - Q2 * st1.t);
    mediump vec3 B = -normalize(cross(N, T));
    mat3 TBN = mat3(T, B, N);

    return normalize(TBN * tangentNormal);
}

// ============================================================================
// Main
// ============================================================================
void main() {
    // --- Sample material properties ---
    mediump vec4 baseColor = texture(u_BaseColorMap, v_TexCoord) * u_BaseColor;

    // Alpha test (branchless discard alternative: use alpha-to-coverage if available)
    if (baseColor.a < u_AlphaCutoff) {
        discard;
    }

    mediump vec2 mr = texture(u_MetallicRoughnessMap, v_TexCoord).gb; // glTF packing: .x=green(roughness), .y=blue(metallic)
    mediump float metallic  = mr.y * u_Metallic;
    mediump float roughness = max(mr.x * u_Roughness, MIN_ROUGHNESS);
    mediump float ao = texture(u_AOMap, v_TexCoord).r * u_AO;

    // --- Vectors ---
    mediump vec3 N = GetNormalFromMap();
    highp vec3 V = normalize(u_CameraPos.xyz - v_WorldPos);  // highp for camera distance
    mediump vec3 R = reflect(-V, N);

    // --- Dielectric F0 = 0.04, Metallic F0 = baseColor ---
    mediump vec3 F0 = mix(vec3(0.04), baseColor.rgb, metallic);

    // ==================================================================
    // Direct Lighting (Punctual Lights)
    // ==================================================================
    mediump vec3 Lo = vec3(0.0);

    for (int i = 0; i < MAX_LIGHTS; i++) {
        if (i >= u_LightCount) break;  // Uniform branch — OK on mobile

        // Determine light direction and attenuation
        mediump vec3 L;
        mediump float attenuation;

        if (u_Lights[i].position.w < 0.5) {
            // Directional light
            L = normalize(-u_Lights[i].direction.xyz);
            attenuation = 1.0;
        } else {
            // Point light with distance attenuation
            highp vec3 lightVec = u_Lights[i].position.xyz - v_WorldPos;
            highp float dist = length(lightVec);
            L = normalize(lightVec);
            // Physically-based inverse-square falloff with range limit
            mediump float range = u_Lights[i].params.x;
            attenuation = clamp(1.0 - pow(dist / range, 4.0), 0.0, 1.0);
            attenuation = (attenuation * attenuation) / (dist * dist + 1.0);
        }

        mediump vec3 H = normalize(V + L);
        mediump float NdotL = max(dot(N, L), 0.0);

        // Cook-Torrance BRDF
        mediump float NDF = DistributionGGX(N, H, roughness);
        mediump float G = GeometrySmith(N, V, L, roughness);
        mediump vec3 F = FresnelSchlick(max(dot(H, V), 0.0), F0);

        // Specular
        mediump vec3 numerator = NDF * G * F;
        mediump float denominator = 4.0 * max(dot(N, V), 0.0) * NdotL + 0.0001;
        mediump vec3 specular = numerator / denominator;

        // Diffuse (energy conservation: metals have no diffuse)
        mediump vec3 kD = (vec3(1.0) - F) * (1.0 - metallic);
        mediump vec3 diffuse = kD * baseColor.rgb / PI;

        // Accumulate
        mediump vec3 radiance = u_Lights[i].color.rgb * u_Lights[i].color.a;
        Lo += (diffuse + specular) * radiance * attenuation * NdotL;
    }

    // ==================================================================
    // Image-Based Lighting (Ambient / IBL)
    // ==================================================================
    mediump vec3 F_ibl = FresnelSchlickRoughness(max(dot(N, V), 0.0), F0, roughness);
    mediump vec3 kD_ibl = (vec3(1.0) - F_ibl) * (1.0 - metallic);

    // Pre-filtered environment map (mip level based on roughness)
    const mediump float MAX_MIP_LEVEL = 4.0;
    mediump vec3 prefilteredColor = textureLod(u_EnvMap, R, roughness * MAX_MIP_LEVEL).rgb;

    // BRDF LUT lookup
    mediump vec2 brdfLut = texture(u_BRDFLut, vec2(max(dot(N, V), 0.0), roughness)).rg;
    mediump vec3 specularIBL = prefilteredColor * (F_ibl * brdfLut.x + brdfLut.y);

    // Diffuse IBL (irradiance — could use a separate irradiance map)
    mediump vec3 diffuseIBL = u_AmbientColor.rgb * baseColor.rgb;

    mediump vec3 ambient = (kD_ibl * diffuseIBL + specularIBL) * ao;

    // ==================================================================
    // Final Composition (HDR output — tone map in post-process pass)
    // ==================================================================
    mediump vec3 color = ambient + Lo;

    // Output linear HDR color (tone mapping applied in post-process)
    outColor = vec4(color, baseColor.a);
}
