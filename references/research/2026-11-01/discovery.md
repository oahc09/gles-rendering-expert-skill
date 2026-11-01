# Discovery: inclusive UTC 2026-10-02–2026-11-01

Research executed 2026-11-01. The taskbook's previous search is a lead, not immutable truth. Official pages were opened and GitHub original `published_at` / commit committer dates fetched. [evidence.csv](evidence.csv) records reviewed claims; [radar.json](radar.json) is **unreviewed metadata candidates**, not 337 accepted changes.

## Verified material observations

* Khronos Oct 25 etnaviv certification supplies two concrete embedded-Linux target configurations. Oct 1 Windows-on-Arm NVIDIA entries remain **historical-context** outside the window. No local device was tested.
* October Vulkan CTS releases exist, but must not become GLES API changes. The inspected GLES CTS patch was July 21.
* Filament 1.77.3 / 1.78.0 / 1.78.1 / 1.79.0 fall in the window. Reviewed 1.78/1.79 notes motivate tracking material/compiler revision; they do not relax GLSL ES rules. Prior 1.77.2 is Sep 28 and historical.
* Perfetto v59.1 was published Oct 27. Trace tooling is a candidate diagnostic improvement, not proof that counters work on any particular GLES device.
* AGI latest inspected release v3.3.3 was **2025-01-20**, not this October. No verified material release update from AGI in the bounded release scan.
* Mesa Oct14/Oct28 bug-fix releases include driver-specific image/resource regressions (E16/E18). RenderDoc v1.47 Oct31 is in-window; glslang has no release candidate in the bounded scan. Neither fact replaces actual target-tool validation.
* ANGLE commit metadata includes lifecycle/EGL changes. Full diff/reproduction is pending; do not claim a new stable ANGLE release or promote metadata to MUST.

## Search record / limitations

Opened official Khronos conformance, Android Vulkan and WCG/frame-pacing docs, Khronos extension specs, Google ANGLE setup, CTS/Filament/AGI/Perfetto releases. GitHub API fetched all listed sources successfully with pagination; 337 in-window candidates (329 ANGLE commits, 2 CTS, 4 Filament, 1 Perfetto, 1 RenderDoc; zero AGI/glslang). The seven-source radar SHA256 is `5700a454300743b1aadd41fb958e3d93506dbd1df44c7cf9aefcc53bff30e0aa`. Metadata is not source-code review.

Web searches included `site:github.com/google/angle "2026-10" "Android"`, `site:x.com GLES October 2026 GPU`, vendor GMEM/HSR terms. No corroborated original X item was retained; X discovery is incomplete, **not** proof there were no useful posts. An advisory search result is not imported as a normative GLES rule. Arm documentation redirected to a page with no readable body; PowerVR initial legacy path failed, corrected official HSR pages were readable. No claims about current vendor tool versions were made from inaccessible pages. Mesa 26.2.5/26.2.6 release notes were inspected for etnaviv/Panfrost/Freedreno changes; individual commits and target reproduction remain deferred. RenderDoc/glslang release metadata is included; this does not substitute for full incremental commit review.

This is a bounded first-pass research archive. Follow [radar instructions](../../evolution/technology-radar.md) for further candidates. No background schedule is active. Manual device reproduction and broader ecosystem diff review are still required before declaring the entire research acceptance complete.
