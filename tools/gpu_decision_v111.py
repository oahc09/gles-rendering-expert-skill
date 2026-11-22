#!/usr/bin/env python3
"""Offline v1.1.1 candidate. Never executes recommendations or attests device evidence."""

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

from attachment_lifecycle import lifecycle

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 128 * 1024
ACTIONS = ROOT / "references/decision/v111-strategies.json"
CASES = ROOT / "references/experience/v111-cases.json"
CAPS = ROOT / "references/coverage/gles-api-catalog.json.gz"
VERSIONS = ("2.0", "3.0", "3.1", "3.2")
GOALS = {"frame_time", "bandwidth", "memory", "quality", "power", "startup"}
STATES = {"CANDIDATE", "SPEC_VERIFIED", "SOURCE_VERIFIED", "REPRODUCED_SOFTWARE",
          "VERIFIED_DEVICE", "REJECTED", "RETRACTED"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_object(items):
    result = {}
    for key, val in items:
        require(key not in result, "duplicate JSON member")
        result[key] = val
    return result


def parse(data):
    require(len(data) <= LIMIT, "JSON size limit")
    return json.loads(data, object_pairs_hook=unique_object,
                      parse_constant=lambda _: require(False, "non-finite JSON number"))


def read(path):
    with path.open("rb") as stream:
        return parse(stream.read(LIMIT + 1))


def token(value):
    return (isinstance(value, str) and 1 <= len(value) <= 128
            and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.:-]*", value) is not None)


def tokens(value):
    return (isinstance(value, list) and len(value) <= 512 and all(map(token, value))
            and len(value) == len(set(value)))


def unit(value):
    return type(value) in (float, int) and 0 <= value <= 1 and math.isfinite(value)


def check_keys(value, required, optional=()):
    require(isinstance(value, dict) and set(required) <= value.keys()
            and value.keys() <= set(required) | set(optional), "invalid fields")


def request(value):
    check_keys(value, ("schema_version", "target", "workload", "objective", "as_of"),
               ("allowed_actions", "blocked_strategies"))
    require(type(value["schema_version"]) is int and value["schema_version"] == 1, "unsupported schema")
    d = value["target"]
    check_keys(d, ("gles", "extensions", "entrypoints", "probes"), ("profile",))
    require(d["gles"] in VERSIONS and tokens(d["extensions"]) and tokens(d["entrypoints"]),
            "invalid target capabilities")
    require(isinstance(d["probes"], dict) and len(d["probes"]) <= 128
            and all(token(k) and type(v) is bool for k, v in d["probes"].items()), "invalid probes")
    require("profile" not in d or token(d["profile"]), "invalid profile")
    check_keys(value["workload"], ("labels",), ("discard_scope",))
    require(tokens(value["workload"]["labels"]), "invalid workload labels")
    if "discard_scope" in value["workload"]:
        validate_discard_scope(value["workload"]["discard_scope"])
    w = value["objective"]
    require(isinstance(w, dict) and 0 < len(w) <= len(GOALS) and set(w) <= GOALS
            and all(unit(x) for x in w.values()) and any(w.values()), "invalid objective weights")
    require(tokens(value.get("blocked_strategies", [])), "invalid blocked strategies")
    scopes = value.get("allowed_actions", ["analyze", "propose"])
    require(tokens(scopes) and "analyze" in scopes
            and set(scopes) <= {"analyze", "propose"}, "only analyze/propose authorized")
    as_of = value["as_of"]
    require(isinstance(as_of, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of)), "invalid as_of")
    return date.fromisoformat(as_of)


def validate_discard_scope(scope):
    check_keys(scope, ("attachment", "end_event", "complete", "attachments", "lifecycle"))
    require(token(scope["attachment"]) and type(scope["end_event"]) is int
            and type(scope["complete"]) is bool
            and type(scope["attachments"]) is list and 1 <= len(scope["attachments"]) <= 32
            and type(scope["lifecycle"]) is list and 1 <= len(scope["lifecycle"]) <= 256
            and 0 <= scope["end_event"] < len(scope["lifecycle"]), "invalid discard scope")
    for spec in scope["attachments"]:
        check_keys(spec, ("id", "width", "height", "format", "samples"), ("initially_defined",))
        require(token(spec["id"]) and token(spec["format"]), "invalid attachment spec")
    keys = {
        "begin": ("op", "fbo", "loads"), "draw": ("op", "writes", "coverage"),
        "switch": ("op", "fbo"), "resolve": ("op", "attachment"),
        "end": ("op", "stores"), "consume": ("op", "attachment"),
    }
    for event in scope["lifecycle"]:
        require(type(event) is dict and isinstance(event.get("op"), str)
                and event["op"] in keys, "invalid attachment event")
        check_keys(event, keys[event["op"]])
    # It must describe a valid baseline, not an already-discarded or unrelated slot.
    lifecycle(scope)
    end = scope["lifecycle"][scope["end_event"]]
    require(end["op"] == "end" and end["stores"].get(scope["attachment"]) == "store",
            "discard must replace an existing store")


def discard_assessment(scope):
    if scope is None:
        return "MISSING_SCOPE"
    candidate = deepcopy(scope)
    candidate["lifecycle"][scope["end_event"]]["stores"][scope["attachment"]] = "discard"
    try:
        lifecycle(candidate)
    except ValueError:
        # The baseline was validated; its only changed event is one store action.
        return "LATER_CONSUMER"
    if not scope["complete"]:
        return "INCOMPLETE_SCOPE"
    # Declared complete by the caller; this is not an authenticated GPU trace.
    return "MODEL_NO_CONSUMER"

def find_cases(cases, action, target, labels, as_of):
    matches = []
    seen = set()
    for row in cases:
        check_keys(row, ("id","revision","strategy","labels","profile","evidence_class","effect",
                         "source_refs","valid_from","expires_at","approved"))
        require(token(row["id"]) and row["id"] not in seen and token(row["strategy"])
                and tokens(row["labels"]) and type(row["revision"]) is int and row["revision"] > 0
                and (row["profile"] is None or token(row["profile"]))
                and row["evidence_class"] in STATES
                and row["effect"] in ("supports", "counterexample")
                and isinstance(row["source_refs"], list) and bool(row["source_refs"])
                and all(isinstance(ref, str) and len(ref) <= 256 and not ref.startswith(("/", "."))
                        and ".." not in Path(ref).parts for ref in row["source_refs"])
                and type(row["approved"]) is bool, "invalid/duplicate case")
        seen.add(row["id"])
        start = date.fromisoformat(row["valid_from"])
        end = date.fromisoformat(row["expires_at"]) if row["expires_at"] else None
        require(end is None or end > start, "invalid case effective dates")
        if row["strategy"] != action or not labels.intersection(row["labels"]):
            continue
        scope = "RELATED_ONLY"
        if target.get("profile") is not None and row["profile"] == target["profile"]:
            scope = "EXACT_PROFILE"
        if row["evidence_class"] in ("REJECTED", "RETRACTED"):
            state = row["evidence_class"]
        elif as_of < start or (end is not None and as_of >= end):
            state = "OUTSIDE_VALID_WINDOW"
        else:
            state = "REFERENCE_ONLY"
        matches.append({"id":row["id"],"revision":row["revision"],"scope":scope,
                        "evidence_class":row["evidence_class"],"finding":row["effect"],
                        "state":state,"reviewed":row["approved"],"source_refs":row["source_refs"]})
    return sorted(matches, key=lambda row: (row["scope"] != "EXACT_PROFILE", row["id"]))


def decide(value, strategies=None, cases=None):
    as_of = request(value)
    target, weights = value["target"], value["objective"]
    labels = set(value["workload"]["labels"])
    discard = discard_assessment(value["workload"].get("discard_scope"))
    strategies = read(ACTIONS) if strategies is None else strategies
    cases = read(CASES) if cases is None else cases
    # The existing Khronos index is larger than the request cap and is trusted,
    # immutable package input. Callers cannot supply a catalog path.
    commands = {r["name"]: r["core_versions"] for r in json.loads(gzip.decompress(CAPS.read_bytes()))["commands"]}
    # Positive-weight schema goals are accepted even if this catalog does not
    # implement them. Catalog support and relevance to this workload differ.
    active_goals = sorted(k for k in weights if weights[k] > 0)
    supported_goals = sorted(k for k in active_goals if any(
        strat["relevance"].get(k, 0) > 0 for strat in strategies))
    unsupported_goals = sorted(set(active_goals) - set(supported_goals))
    total_weight = math.fsum(weights[k] for k in active_goals)
    result = []
    for strat in strategies:
        hits = sorted(labels.intersection(strat["labels"]))
        if not hits:
            continue
        relevance = strat["relevance"]
        relevant_goals = [k for k in supported_goals if relevance.get(k, 0) > 0]
        if not relevant_goals:
            continue
        # Keep a tiny positive policy score positive; rounding is not an
        # eligibility test. This is not a speed estimate or a measured result.
        raw_score = math.fsum((weights[k] / total_weight) * relevance[k] for k in relevant_goals)
        score = round(raw_score, 6) or raw_score or math.nextafter(0., 1.)
        reasons = []
        for name in strat["core_entrypoints"]:
            if target["gles"] not in commands.get(name, []):
                reasons.append("NOT_CORE:" + name)
        for name in sorted(set(strat["core_entrypoints"] + strat.get("extension_entrypoints", []))
                           - set(target["entrypoints"])):
            reasons.append("MISSING_ENTRYPOINT:" + name)
        for name in sorted(set(strat.get("extensions", [])) - set(target["extensions"])):
            reasons.append("MISSING_EXTENSION:" + name)
        probe = target["probes"].get(strat["id"])
        is_discard = strat["id"] == "discard-dead-attachment"
        if is_discard and discard == "LATER_CONSUMER":
            reasons.append("ATTACHMENT_HAS_LATER_CONSUMER")
        if probe is False:
            reasons.append("CORRECTNESS_PROBE_FAILED")
        if strat["id"] in value.get("blocked_strategies", []):
            reasons.append("BLOCKED_BY_CALLER")
        experience = find_cases(cases, strat["id"], target, labels, as_of)
        if any(row["scope"] == "EXACT_PROFILE" and row["state"] == "REFERENCE_ONLY"
               and row["finding"] == "counterexample" and row["reviewed"] for row in experience):
            reasons.append("SCOPED_COUNTEREXAMPLE_REVIEW_REQUIRED")
        if reasons:
            status = "BLOCKED"
        elif probe is None or (is_discard and discard != "MODEL_NO_CONSUMER"):
            status = "PROBE_REQUIRED"
        elif "propose" not in value.get("allowed_actions", ["analyze", "propose"]):
            status = "ANALYZE_ONLY"
        else:
            status = "EXPERIMENT_REQUIRED"
        liveness = {"attachment_liveness":discard} if is_discard else {}
        result.append({"strategy":strat["id"],"status":status,"blocked_reasons":reasons,
                       "hypothesis_labels":hits,"expected_mechanism":strat["mechanism"],
                       "preconditions":{"core_entrypoints":strat["core_entrypoints"],
                                        "extension_entrypoints":strat.get("extension_entrypoints", []),
                                        "extensions":strat.get("extensions", []),
                                        "correctness_probe":probe,**liveness},
                       "risk":strat["risk"],"required_experiment":strat["experiment"],
                       "fallback":strat["fallback"],"uncertainty":"PERFORMANCE_NOT_MEASURED",
                       "policy_relevance":None if reasons else score,"experience":experience})
    order = {"EXPERIMENT_REQUIRED":0,"ANALYZE_ONLY":1,"PROBE_REQUIRED":2,"BLOCKED":3}
    result.sort(key=lambda row: (order[row["status"]], -(row["policy_relevance"] or 0), row["strategy"]))
    recommend = any(r["status"] == "EXPERIMENT_REQUIRED" for r in result)
    evidence = hashlib.sha256(json.dumps(["objective-relevance-v1+discard-scope-v1", value, strategies, cases, sorted(commands.items())],
                                        sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"schema_version":1,"decision_id":evidence,
            "status": "EXPERIMENT_REQUIRED" if recommend
            else "NO_EXPERIMENT_RECOMMENDED",
            "candidates":result,"automatic_renderer_mutation":False,"performance_claim":False,
            "objective_evaluation":{
                "supported_goals":supported_goals,"unsupported_goals":unsupported_goals,
                "status":("UNSUPPORTED_GOALS" if not supported_goals else
                          "NO_RELEVANT_CANDIDATES" if not result else
                          "CORRECTNESS_PROBE_REQUIRED" if not recommend and any(
                              r["status"] == "PROBE_REQUIRED" for r in result) else
                          "RELEVANT_CANDIDATES")
            }}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", nargs="?", type=Path, help="JSON file; omit to read stdin")
    opts = parser.parse_args()
    try:
        data = read(opts.request) if opts.request else parse(sys.stdin.buffer.read(LIMIT + 1))
        print(json.dumps(decide(data), indent=2, allow_nan=False))
        return 0
    except (KeyError, TypeError, ValueError, OSError, RecursionError):
        print('{"status":"INVALID_INPUT","automatic_renderer_mutation":false}', file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
