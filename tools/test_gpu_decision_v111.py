import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

import gpu_decision_v111 as gd


def sample(label, gles="3.2", entries=(), extensions=(), probes=None, **kw):
    return {"schema_version":1, "target":{"gles":gles,"extensions":list(extensions),
            "entrypoints":list(entries),"probes":probes or {}}, "workload":{"labels":[label]},
            "objective":{"frame_time":1,"bandwidth":1}, "as_of":"2026-11-21", **kw}


def discard_scope(*later, complete=True):
    return {"attachment":"wallpaper-depth","end_event":1,"complete":complete,
            "attachments":[{"id":"wallpaper-depth","width":1080,"height":2400,
                            "format":"DEPTH24_STENCIL8","samples":1}],
            "lifecycle":[{"op":"begin","fbo":"wallpaper","loads":{"wallpaper-depth":"clear"}},
                         {"op":"end","stores":{"wallpaper-depth":"store"}}, *later]}


class DecisionTest(unittest.TestCase):
    def action(self, data, strategy, **kw):
        return next(a for a in gd.decide(data, **kw)["candidates"] if a["strategy"] == strategy)

    def test_capability_and_constraints(self):
        comp = "compute-to-fragment"
        disc = "discard-dead-attachment"
        fetch = "coherent-framebuffer-fetch"
        msaa = "resolve-msaa-once"
        fence = "fence-ring-reuse"
        mip = "texture-mip-selection"
        cc = ("glDispatchCompute", "glMemoryBarrier")
        dc = ("glInvalidateFramebuffer",)
        fc = ("GL_EXT_shader_framebuffer_fetch",)
        mc = ("glBlitFramebuffer", "glRenderbufferStorageMultisample")
        sc = ("glFenceSync", "glClientWaitSync", "glDeleteSync")
        tc = ("glTexParameteri",)
        rows = [
            (comp, sample("compute","3.0",cc,probes={comp:True}),"BLOCKED","NOT_CORE:glDispatchCompute"),
            (comp, sample("compute","3.1",cc,probes={comp:True}),"EXPERIMENT_REQUIRED",None),
            (comp, sample("compute","3.2",cc[:1],probes={comp:True}),"BLOCKED","MISSING_ENTRYPOINT:glMemoryBarrier"),
            (comp, sample("compute","3.2",cc),"PROBE_REQUIRED",None),
            (comp, sample("compute","3.2",cc,probes={comp:False}),"BLOCKED","CORRECTNESS_PROBE_FAILED"),
            (disc, sample("attachment-store","2.0",dc,probes={disc:True}),"BLOCKED","NOT_CORE:glInvalidateFramebuffer"),
            (disc, sample("attachment-store","3.0",dc,probes={disc:True}),"PROBE_REQUIRED",None),
            (disc, sample("attachment-store","3.2",dc,probes={disc:True},blocked_strategies=[disc]),"BLOCKED","BLOCKED_BY_CALLER"),
            (disc, sample("attachment-store","3.2",dc,probes={disc:True},allowed_actions=["analyze"],
                          workload={"labels":["attachment-store"],"discard_scope":discard_scope()}),"ANALYZE_ONLY",None),
            (disc, sample("attachment-store","3.2",(),probes={disc:True}),"BLOCKED","MISSING_ENTRYPOINT:glInvalidateFramebuffer"),
            (fetch, sample("framebuffer-fetch",probes={fetch:True}),"BLOCKED","MISSING_EXTENSION:"+fc[0]),
            (fetch, sample("framebuffer-fetch",extensions=fc),"PROBE_REQUIRED",None),
            (fetch, sample("framebuffer-fetch",extensions=fc,probes={fetch:True}),"EXPERIMENT_REQUIRED",None),
            (fetch, sample("framebuffer-fetch",extensions=fc,probes={fetch:False}),"BLOCKED","CORRECTNESS_PROBE_FAILED"),
            (msaa, sample("msaa","2.0",mc,probes={msaa:True}),"BLOCKED","NOT_CORE:glBlitFramebuffer"),
            (msaa, sample("msaa","3.0",mc,probes={msaa:True}),"EXPERIMENT_REQUIRED",None),
            (msaa, sample("msaa","3.2",mc[:1],probes={msaa:True}),"BLOCKED","MISSING_ENTRYPOINT:glRenderbufferStorageMultisample"),
            (fence, sample("synchronization","2.0",sc,probes={fence:True}),"BLOCKED","NOT_CORE:glFenceSync"),
            (fence, sample("synchronization","3.0",sc,probes={fence:True}),"EXPERIMENT_REQUIRED",None),
            (fence, sample("synchronization","3.2",sc,probes={fence:False}),"BLOCKED","CORRECTNESS_PROBE_FAILED"),
            (mip, sample("texture","2.0",tc,probes={mip:True}),"EXPERIMENT_REQUIRED",None),
            (mip, sample("texture","3.2",tc,probes={mip:False}),"BLOCKED","CORRECTNESS_PROBE_FAILED"),
        ]
        for index, (strategy, request, expected, reason) in enumerate(rows):
            with self.subTest(case=index, strategy=strategy):
                answer = self.action(request, strategy)
                self.assertEqual(answer["status"], expected)
                if reason:
                    self.assertIn(reason, answer["blocked_reasons"])
                    self.assertIsNone(answer["policy_relevance"])

    def test_deterministic_order_and_no_claim(self):
        data = sample("bandwidth", entries=["glInvalidateFramebuffer","glTexParameteri"],
                      probes={"discard-dead-attachment":True,"texture-mip-selection":True})
        data["objective"] = {"bandwidth": 1}
        data["workload"]["discard_scope"] = discard_scope()
        output = gd.decide(data)
        self.assertEqual(output,gd.decide(copy.deepcopy(data)))
        self.assertEqual(output["candidates"][0]["strategy"],"discard-dead-attachment")
        data["objective"] = {"quality":1}
        reranked = gd.decide(data)
        self.assertEqual(reranked["candidates"][0]["strategy"],"texture-mip-selection")
        self.assertFalse(reranked["performance_claim"])
        self.assertFalse(reranked["automatic_renderer_mutation"])
        self.assertNotEqual(output["decision_id"],reranked["decision_id"])

    def test_experience_is_exact_or_related_not_universal(self):
        action = "coherent-framebuffer-fetch"
        req = sample("framebuffer-fetch",extensions=["GL_EXT_shader_framebuffer_fetch"],probes={action:True})
        unknown = self.action(req,action)
        self.assertTrue(all(r["scope"] == "RELATED_ONLY" for r in unknown["experience"]))
        self.assertEqual(unknown["status"],"EXPERIMENT_REQUIRED")
        req["target"]["profile"] = "mesa-fetch-fixture"
        exact = self.action(req,action)
        self.assertEqual(exact["status"],"BLOCKED")
        self.assertIn("SCOPED_COUNTEREXAMPLE_REVIEW_REQUIRED",exact["blocked_reasons"])
        req["target"]["profile"] = "angle-fetch-fixture"
        other = self.action(req,action)
        self.assertEqual(other["status"],"EXPERIMENT_REQUIRED")
        self.assertEqual(other["experience"][0]["id"],"fetch-angle-software")
        req["target"]["extensions"] = []
        self.assertEqual(self.action(req,action)["status"],"BLOCKED")

    def test_ledger_review_expiry_retraction_and_duplicate(self):
        action = "coherent-framebuffer-fetch"
        req = sample("framebuffer-fetch",extensions=["GL_EXT_shader_framebuffer_fetch"],probes={action:True})
        req["target"]["profile"] = "mesa-fetch-fixture"
        row = gd.read(gd.CASES)[0]
        for update, state in [({"expires_at":"2026-11-22"},"OUTSIDE_VALID_WINDOW"),
                              ({"evidence_class":"RETRACTED"},"RETRACTED"),
                              ({"approved":False},"REFERENCE_ONLY")]:
            with self.subTest(update=update):
                req["as_of"] = "2026-11-22"
                result = self.action(req,action,cases=[dict(row,**update)])
                self.assertEqual(result["experience"][0]["state"],state)
                self.assertEqual(result["status"],"EXPERIMENT_REQUIRED")
        with self.assertRaises(ValueError):
            self.action(req,action,cases=[row,row])
        for case in gd.read(gd.CASES):
            for ref in case["source_refs"]:
                self.assertTrue((gd.ROOT/ref).is_file(),ref)

    def test_f02_startup_only_has_no_experiment_and_cli_is_compatible(self):
        data = sample("bandwidth", entries=["glInvalidateFramebuffer", "glTexParameteri"],
                      probes={"discard-dead-attachment": True, "texture-mip-selection": True})
        data["objective"] = {"startup": 1}
        data["as_of"] = "2026-11-22"
        expected = gd.decide(data)
        self.assertEqual(expected["schema_version"], 1)
        self.assertEqual(expected["status"], "NO_EXPERIMENT_RECOMMENDED")
        self.assertEqual(expected["candidates"], [])
        self.assertFalse(expected["performance_claim"])
        self.assertFalse(expected["automatic_renderer_mutation"])
        self.assertEqual(expected["objective_evaluation"],
                         {"supported_goals": [], "unsupported_goals": ["startup"], "status": "UNSUPPORTED_GOALS"})
        with tempfile.TemporaryDirectory() as temp:
            file = Path(temp) / "legacy-request.json"
            file.write_text(json.dumps(data), encoding="utf-8")
            cmd = [sys.executable, str(gd.ROOT / "tools/gpu_decision_v111.py")]
            stdin = subprocess.run(cmd, input=json.dumps(data), text=True, capture_output=True, timeout=5, check=True)
            from_file = subprocess.run(cmd + [str(file)], text=True, capture_output=True, timeout=5, check=True)
        self.assertEqual(stdin.stdout, from_file.stdout)
        self.assertEqual(json.loads(stdin.stdout), expected)

    def test_distinguishes_workload_and_probe_gaps_and_keeps_small_positive_weight(self):
        data = sample("synchronization", entries=["glFenceSync", "glClientWaitSync", "glDeleteSync"])
        data["objective"] = {"startup": 1, "quality": 0.5}
        out = gd.decide(data)
        self.assertEqual(out["objective_evaluation"],
                         {"supported_goals": ["quality"], "unsupported_goals": ["startup"], "status": "NO_RELEVANT_CANDIDATES"})
        self.assertEqual(out["candidates"], [])
        data["objective"] = {"startup": 1, "frame_time": 1e-12, "quality": 0}
        out = gd.decide(data)
        self.assertEqual(out["status"], "NO_EXPERIMENT_RECOMMENDED")
        self.assertEqual(out["objective_evaluation"]["status"], "CORRECTNESS_PROBE_REQUIRED")
        self.assertEqual([r["strategy"] for r in out["candidates"]], ["fence-ring-reuse"])
        self.assertEqual(out["candidates"][0]["status"], "PROBE_REQUIRED")
        self.assertGreater(out["candidates"][0]["policy_relevance"], 0)
        data["target"]["probes"]["fence-ring-reuse"] = False
        self.assertEqual(gd.decide(data)["candidates"][0]["status"], "BLOCKED")

    def test_wallpaper_depth_scope_controls_real_consumers_before_ranking(self):
        disc = "discard-dead-attachment"
        data = sample("attachment-store", entries=["glInvalidateFramebuffer"], probes={disc:True})
        read = {"op":"consume","attachment":"wallpaper-depth"}
        load = {"op":"begin","fbo":"subsequent-pass","loads":{"wallpaper-depth":"load"}}
        clear = {"op":"begin","fbo":"subsequent-pass","loads":{"wallpaper-depth":"clear"}}
        store = {"op":"end","stores":{"wallpaper-depth":"store"}}
        for scope, status, liveness in [
            (None, "PROBE_REQUIRED", "MISSING_SCOPE"),
            (discard_scope(complete=False), "PROBE_REQUIRED", "INCOMPLETE_SCOPE"),
            (discard_scope(read), "BLOCKED", "LATER_CONSUMER"),
            (discard_scope(load,store), "BLOCKED", "LATER_CONSUMER"),
            (discard_scope(clear,store,read), "EXPERIMENT_REQUIRED", "MODEL_NO_CONSUMER"),
        ]:
            with self.subTest(liveness=liveness):
                data["workload"] = {"labels":["attachment-store"]}
                if scope is not None:
                    data["workload"]["discard_scope"] = scope
                row = self.action(data, disc)
                self.assertEqual(row["status"],status)
                self.assertEqual(row["preconditions"]["attachment_liveness"],liveness)
                if liveness == "LATER_CONSUMER":
                    self.assertIn("ATTACHMENT_HAS_LATER_CONSUMER",row["blocked_reasons"])
        data["workload"]["discard_scope"]["end_event"] = 0
        with self.assertRaises(ValueError):
            gd.decide(data)

    def test_invalid_request_and_cli_bounds(self):
        for raw in (b'{"target":1,"target":2}', b'{"x":NaN}', b' '*(gd.LIMIT+1)):
            with self.assertRaises(ValueError):
                gd.parse(raw)
        req = sample("texture",allowed_actions=["analyze","execute"])
        bad = subprocess.run([sys.executable,str(gd.ROOT/"tools/gpu_decision_v111.py")],
                             input=json.dumps(req),text=True,capture_output=True,timeout=5)
        self.assertEqual(bad.returncode,2)
        self.assertEqual(json.loads(bad.stderr)["status"],"INVALID_INPUT")
        self.assertFalse(bad.stdout)
        good = subprocess.run([sys.executable,str(gd.ROOT/"tools/gpu_decision_v111.py")],
                              input=json.dumps(sample("unknown")),text=True,capture_output=True,timeout=5)
        self.assertEqual(good.returncode,0)
        self.assertEqual(json.loads(good.stdout)["candidates"],[])


if __name__ == "__main__":
    unittest.main()
