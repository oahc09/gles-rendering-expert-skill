# Frozen Registry index versus semantic coverage

Sources are frozen by full upstream commit and SHA256 in `source-manifest.json`.
Regenerate without network:

```
python3 tools/coverage/build_gles_catalog.py
python3 tools/coverage/build_egl_catalog.py
python3 tools/coverage/check_coverage.py --root . --output /tmp/coverage-report.json
python3 -m unittest discover -s tools/coverage -p 'test_catalog.py' -v
```

`catalog.build(manifest, 'gles'|'egl')` is the shared deterministic library;
`build_gles_catalog.py` also regenerates the combined extension catalog by default.
`check_coverage.extensions(gles, egl)` builds the combined extension index using
`catalog.write(path, value)`. Regenerate all three when intentionally updating fixed
sources. The checker never fetches HEAD. Missing/hash-mismatched sources return
INCOMPLETE with indexed=null, not a perfect percentage.

GLES2.0/3.0/3.1/3.2 command counts are 142/246/314/358; enum counts
301/622/795/1001. EGL1.4 has34 commands/122 enums, EGL1.5 has44/165.
350 GL extensions support GLES1 and/or GLES2;167 EGL extensions are indexed.
GLES1-only extensions are recorded but not negotiated as GLES2 support.

Every applicable symbol has core_since, active core_versions, require/remove
history, extension conditions, alias metadata, rules/examples/tests arrays and
source_spec. XML alias relations are retained but never used to replace an exact
entrypoint. GLES KHR debug extension uses KHR-suffixed names even though GLES3.2
core uses unsuffixed names. Core availability derives from feature membership,
not extension suffix or an assumed promotion. EGL1.4 includes inherited1.0–1.3.
Desktop-only require blocks remain visible in extension metadata but do not
inject desktop-only symbols into the GLES symbol index.

**All entries are INDEXED_ONLY.** Empty rules/examples/tests are intentional gaps,
not fake semantic coverage. Categories are explicit name-based heuristics only.
Full semantic API errors, parameter contracts, per-function examples, shader
compilation, runtime, device and provider verification are separate and unclaimed.
The checker independently regenerates the structural graph and rejects missing
entries, ghost additions, wrong versions/extensions or unsupported coverage labels.
It also validates the explicit new semantic-links.json contract through
catalog_links.py: API/version/extension route, safe existing rule/example/test paths,
named positive/negative assertion cases and polarity, and API association on the
case declaration line. Twenty-four actual state-boundary pairs are linked to the
existing C++ executable assertions. This is not a parser of legacy prose or proof
that every spec rule is covered. Links count separately and do not imply compiled,
runtime, independent semantic or device acceptance.

## License/source preservation

The unmodified gl.xml/egl.xml headers carry Apache-2.0 and Khronos copyright;
the canonical Apache license text is archived and hashed. Extension-specification
prose is **not vendored**: its notices refer to separate specification copyright
terms, and redistribution permission could not be confirmed. The official
copyright endpoint returned HTTP403 during this check; the attempted fixed-revision
README.md URL returned404. This is an uncertainty boundary, not a finding that
redistribution is prohibited. XML Apache licensing is not extrapolated to prose.

`extension_specs` preserves pinned URL, revision, previously retrieved SHA256 and
short authored summaries. The checker validates only citation metadata consistency,
not absent text bytes or a renewed source retrieval. The three source texts remain
outside the repository for research; no repository-local path or offline-prose
validation claim remains. Existing adapters were informed by the earlier reading,
not newly verified full-text distribution rights.

## Explicit new semantic links

`semantic-links.json` has schema_version1 and rows with id, api_domain, api,
version, extension, rule, example, positive_test, negative_test, positive_case,
negative_case, level and source_url. Here the C++ executable assertion source is
the rule/example/test artifact, and case IDs bind each positive/error pair. All24
rows reference the GLES3.0 normative specification; immutable redefinition links
TexImage2D with the TexStorage2D setup on the same case line. Merely finding a
path does not prove the asserted rule matches every normative condition.

Ghost/missing APIs, unavailable core versions, wrong extension routes, escaping
paths, missing negative cases, wrong assertion polarity and unrelated API/case
links fail. Existing independent runtime evidence remains managed by its owner.
