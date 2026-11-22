# Round 1: Decision-to-Advisor eligibility

Advisor JSON may carry a top-level `decision_request` in the existing
`gpu_decision_v111.py` request shape. Advisor computes the Decision locally; supplied
status fields are not accepted as a Decision. Goal, core API, entry point, known
strategy and caller scope checks apply before the mapped experiment is proposed.
Unsupported objectives or known objectives with no relevant strategy keep the
baseline instead of beginning an unrelated experiment.

The bounded mapping is only the `COMPUTE` candidate of `shader-advanced-v1`
to the `compute-to-fragment` prerequisites. This enforces the existing core
compute and barrier requirements; the registered experiment is a finite initial
correctness control, not proof that an application's fragment alternative is
equivalent. Requests for this arm without Decision context are insufficient.
Other legacy requests keep non-executing hypothesis behavior unless context is
present, in which case unbound strategy/experiment combinations are insufficient.

A usable fallback is always a non-blank string. Explicit failed quality remains
a veto. The additive `decision_alignment` output explains the eligibility
status; caller declarations are not validated W2 device receipts. The bridge
authorizes no execution, produces no physical-performance verdict, and does not
bound a result to real target draw/dispatch behavior. Full W2/W3/W4 integration,
per-attachment liveness and physical/model validation remain separate.

Test the authored kiosk, wallpaper and post-processing cases with
`python3 -m unittest discover -s benchmarks/workloads -p 'test_*.py'`.
