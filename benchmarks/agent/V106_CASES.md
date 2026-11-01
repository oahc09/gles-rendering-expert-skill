# v1.0.6 Agent2 candidate

A113–A142 add30 authored difficult cases over the byte-frozen112-case predecessor. Four modes span ten topics: interop, multi-surface, compute, driver conditions, transparency, lighting, texture/video, precision, reducer and evidence. These prompts and expected findings are annotations requiring independent review, not model outputs or device observations.

Use existing `run.py --cases benchmarks/agent/cases-v1.0.6.json --output /path/run` with an explicitly authorized real adapter. With no adapter it records BLOCKED_BY_PROVIDER and no responses. Never substitute mock responses for live quality scores. Corpus/Skill/request/response hashes, model settings and budgets must be paired.

`score.py` reuses existing compile, evidence sufficiency, visual safety, precision/recall and mode-specific review metrics. v106 adds correct-fix rate only when a rationale and actual patch regression evidence exist; a FAIL cannot support correct_fix=true. Introduced-regression rate counts a paired baseline PASS versus patch FAIL with identical suite hash/environment. CLI verifies baseline/patch artifact and log bytes. These are human-adjudicated artifact-bound metrics, not automatic semantic truth; no model score is currently available. An absent denominator stays null. Performance wins remain separate and need device A/B.
