# Research decisions

| Source ID | Decision | Implemented mapping / remaining evidence |
|---|---|---|
| P59 | Use documented stable CSV protocol and inspect schema first | W5 adapter; 16 normalized + 3 native-parser fixtures; no device collection claim |
| F179 | Candidate only | Numeric/color/source-revision awareness; no automatic engine feature import |
| RD147 | Candidate only | Capture/replay support still target-specific |
| F1772 / CTS / KTX | Historical-context | Date-boundary tests reject current-window labeling |
| ADPF / PVR | Context only when source retrieved and readable | Long-run experiments still need true device thermal/power evidence |
| MESA / KHR | Named implementation/configuration observation | Individual diffs and affected-device tests remain deferred |
| ARM / QCOM | UNVERIFIED where dynamic/access/date checks incomplete | No change to normative GLES guidance |
| X | UNVERIFIED; no original post retained | No URL/author/date invented, no MUST |

No release was triggered and no rule was automatically promoted. Synthetic trace
classifier labels measure fixture behavior; they are not evidence of physical-device
causal accuracy, vendor support, or real model diagnostic improvement.
