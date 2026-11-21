# Legacy GLES 1.0 / 1.1 migration index

No legacy fixed-function core catalogue or runtime support is promised. Frozen Registry GLES1-only extensions remain visible for migration, not in the modern `gles2` extension denominator. The validator reports modern, legacy-only, EGL and union counts separately; 517 is their combined union, not a modern GLES semantic denominator.

| Legacy construct | Modern migration boundary |
|---|---|
| Fixed-function lighting / texture environment | Explicit vertex/fragment shader; preserve spaces, lighting model, alpha and color encoding with an image oracle |
| Matrix stacks | Application-owned matrices, shader uniforms or version-appropriate UBOs; preserve multiplication order and normal matrix |
| Client arrays | Explicit vertex buffer layout and attribute pointers; ES3 VAO state, ES2 separately negotiated VAO extension or application state |
| Fixed-function alpha test | Fragment shader discard where legal; preserve threshold/coverage, do not promise equivalent early-Z performance |
| Point sprites / fog | Explicit shader semantics and queried point-size limits, test clipped/edge cases |

Source: frozen `registry/gl.xml` feature `api="gles1"` and supported extension metadata; modern legal command boundaries are generated from `gles2` snapshots. Migration designs require semantic validation and are not blanket API aliases or certified equivalent implementations.
