#!/usr/bin/env python3
"""Read-only public GitHub radar; archive metadata, never promote a rule or schedule a job."""
import argparse
import datetime as dt
import hashlib
import json
import re
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

SOURCES = {
    "cts": ("KhronosGroup/VK-GL-CTS", "releases"),
    "filament": ("google/filament", "releases"),
    "filament-commits": ("google/filament", "commits"),
    "spirv-tools": ("KhronosGroup/SPIRV-Tools", "releases"),
    "agi": ("google/agi", "releases"),
    "perfetto": ("google/perfetto", "releases"),
    "renderdoc": ("baldurk/renderdoc", "releases"),
    "glslang": ("KhronosGroup/glslang", "releases"),
    "angle": ("google/angle", "commits"),
    "ktx": ("KhronosGroup/KTX-Software", "releases"),
    "cocos-engine": ("cocos/cocos-engine", "releases"),
    "unity-graphics": ("Unity-Technologies/Graphics", "releases"),
    "godot": ("godotengine/godot", "releases"),
}
MAX_PAGES = 10

def day(value):
    return dt.date.fromisoformat(value)

def normalize(source, kind, record):
    # Hash the canonical full API record, not a crawl timestamp or an invented source.
    provenance = {"source_hash": hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(),
                  "source_hash_kind": "sha256-canonical-github-api-record",
                  "published_at": record.get("published_at") if kind == "releases" else None,
                  "event_time_kind": "release_published_at" if kind == "releases" else "commit_committer_date"}

    if kind == "releases":
        return {**provenance, "source": source, "id": str(record["id"]), "url": record["html_url"],
                "event_at": record["published_at"], "revision": record["tag_name"],
                "title": record.get("name") or record["tag_name"],
                "draft": record.get("draft", False), "prerelease": record.get("prerelease", False)}
    return {**provenance, "source": source, "id": record["sha"], "url": record["html_url"],
            "event_at": record["commit"]["committer"]["date"], "revision": record["sha"],
            "title": record["commit"]["message"].splitlines()[0], "draft": False, "prerelease": False}

def event_utc_day(value):
    if not isinstance(value,str):
        return None
    try:
        stamp=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
        if stamp.tzinfo is None:
            return None
        return stamp.astimezone(dt.timezone.utc).date()
    except ValueError:
        return None

def validate_decision(row):
    stages={'candidate','source_verified','reproduced','accepted','rejected','deferred'}
    if row.get('stage') not in stages:
        raise ValueError('Unknown research stage')
    if row['stage'] in ('source_verified','reproduced','accepted'):
        if not row.get('original_url') or event_utc_day(row.get('event_at')) is None or not row.get('source_evidence'):
            raise ValueError('Verified signal needs original source, UTC date and evidence')
        if row.get('retrieval_complete') is not True:
            raise ValueError('Incomplete retrieval cannot yield verified signal')
    if row['stage'] in ('reproduced','accepted') and not row.get('reproduction_evidence'):
        raise ValueError('Reproduced/accepted requires actual reproduction evidence')
    if row['stage']=='accepted':
        for field in ('rule_ids','device_conditions','minimal_sample','test_ids','affected_sections','reviewer'):
            if not row.get(field):
                raise ValueError('Accepted signal missing '+field)
    return row

def validate_v105_evidence(row):
    """Validate explicit v1.0.5 ledger rows; no promotion or rule mutation."""
    required={'source_url','author_org','published_at','event_at','collected_at','source_hash',
              'hardware','driver','api_version','extension','actual_change','engineering_impact',
              'repro_steps','evidence_level','decision','target_rule','test_id'}
    if not isinstance(row,dict) or required-set(row):raise ValueError('Incomplete v1.0.5 evidence row')
    if row['evidence_level'] not in ('OFFICIAL_SPEC','OFFICIAL_IMPLEMENTATION','REPRODUCED','SECONDARY','UNVERIFIED'):
        raise ValueError('Unknown evidence level')
    digest=row['source_hash']
    if digest is not None and (not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest)):
        raise ValueError('Invalid source hash')
    if row['evidence_level']!='UNVERIFIED' and (digest is None or not row['source_url']):
        raise ValueError('Verified source requires URL and captured source hash')
    if row.get('normative_action')=='MUST' and row['evidence_level']!='OFFICIAL_SPEC':
        raise ValueError('Only reviewed normative specification can support MUST; no automatic promotion')
    for field in ('published_at','event_at','collected_at'):
        if row[field] is not None and event_utc_day(row[field]) is None:raise ValueError('Invalid UTC-aware '+field)
    if row.get('window_class')=='in-window' and (event_utc_day(row['event_at']) is None or not dt.date(2026,10,2)<=event_utc_day(row['event_at'])<=dt.date(2026,11,1)):
        raise ValueError('Historical/unknown event cannot be called current-window')
    return row

def validate_v107_evidence(row, start=dt.date(2026, 8, 5), end=dt.date(2026, 11, 2)):
    """Extend the same radar decision contract with explicit 90-day provenance."""
    validate_decision(row)
    states = {'VERIFIED_SOURCE', 'SPEC_CONFIRMED', 'REPRODUCED', 'UNVERIFIED', 'REJECTED'}
    if row.get('evidence_state') not in states:
        raise ValueError('Unknown v1.0.7 evidence state')
    if row.get('window_class') not in {'in-window', 'historical-context', 'date-unknown'}:
        raise ValueError('Missing window classification')
    event = event_utc_day(row.get('event_at'))
    if row['window_class'] == 'in-window' and (event is None or not start <= event <= end):
        raise ValueError('Event is outside the declared 90-day window')
    if row['window_class'] == 'historical-context' and (event is None or event >= start):
        raise ValueError('Historical context requires an older known event date')
    if row['window_class'] == 'date-unknown' and event is not None:
        raise ValueError('Known event date must be classified explicitly')
    if event_utc_day(row.get('discovered_at')) is None:
        raise ValueError('UTC discovery timestamp required')
    if row['evidence_state'] not in {'UNVERIFIED', 'REJECTED'}:
        value = row.get('source_sha256')
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('Verified source requires captured SHA256')
    if row['stage'] == 'accepted' and row['evidence_state'] not in {'REPRODUCED', 'SPEC_CONFIRMED'}:
        raise ValueError('Source verification alone cannot promote a technical rule')
    if row.get('performance_status') not in {'NOT_RUN', 'NOT_APPLICABLE'}:
        raise ValueError('This candidate has no independently measured device performance')
    return row

def select(records, start, end, known):
    result = {}
    for row in records:
        if not row.get("event_at") or row.get("draft"):
            continue
        event_day=event_utc_day(row["event_at"])
        if event_day is None or not start <= event_day <= end:
            continue
        key = row["source"] + ":" + row["id"]
        if key not in known:
            result[key] = row
    return [result[key] for key in sorted(result)]

def collect(source, start, end):
    repo, kind = SOURCES[source]
    records, complete = [], False
    for page in range(1, MAX_PAGES + 1):
        query = {"per_page": 100, "page": page}
        if kind == "commits":
            query.update(since=start.isoformat()+"T00:00:00Z", until=end.isoformat()+"T23:59:59Z")
        url = f"https://api.github.com/repos/{repo}/{kind}?" + urllib.parse.urlencode(query)
        req = urllib.request.Request(url, headers={"User-Agent": "gles-skill-evidence-radar", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            batch = json.load(response)
        if not isinstance(batch, list):
            raise ValueError("unexpected GitHub response")
        rows = [normalize(source, kind, r) for r in batch]
        records.extend(rows)
        # Releases can be republished out of order; do not stop at first older date.
        if len(batch) < 100:
            complete = True
            break
    return records, complete

# Bounded, versioned metadata state, distinct from review/promotion.
HISTORY_DAYS = 90
MAX_HISTORY_BYTES = 4 * 1024 * 1024
MAX_HISTORY_ROWS = 24_000


def horizon(end):
    return end - dt.timedelta(days=HISTORY_DAYS - 1)


def item_key(source, item_id):
    if not isinstance(source, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", source):
        raise ValueError("invalid history source")
    if not isinstance(item_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", item_id):
        raise ValueError("invalid history item id")
    return source + ":" + item_id


def read_history(path, end):
    with path.open("rb") as fh:
        data = fh.read(MAX_HISTORY_BYTES + 1)
    if len(data) > MAX_HISTORY_BYTES:
        raise ValueError("history exceeds byte bound")
    report = json.loads(data)
    if not isinstance(report, dict) or set(report) != {"schema_version", "through", "items"}:
        raise ValueError("invalid history envelope")
    if type(report["schema_version"]) is not int or report["schema_version"] != 1:
        raise ValueError("unsupported history schema")
    through = day(report["through"])
    if through > end:
        raise ValueError("history is newer than the current run")
    rows = report["items"]
    if not isinstance(rows, list) or len(rows) > MAX_HISTORY_ROWS:
        raise ValueError("invalid history size")
    seen = set()
    carried = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"source", "id", "event_day"}:
            raise ValueError("invalid history item")
        key = item_key(row["source"], row["id"])
        event = day(row["event_day"])
        if key in seen or not horizon(through) <= event <= through:
            raise ValueError("duplicate or out-of-range history item")
        seen.add(key)
        if event >= horizon(end):
            carried[key] = row
    return through, carried


def write_history(path, end, carried, selected):
    for row in selected:
        event = event_utc_day(row["event_at"])
        if not horizon(end) <= event <= end:
            continue
        key = item_key(row["source"], row["id"])
        carried[key] = {"source": row["source"], "id": row["id"], "event_day": str(event)}
    items = [carried[key] for key in sorted(carried)]
    data = (json.dumps({"schema_version": 1, "through": str(end), "items": items},
                       ensure_ascii=True, separators=(",", ":")) + "\n").encode()
    if len(items) > MAX_HISTORY_ROWS or len(data) > MAX_HISTORY_BYTES:
        raise ValueError("history exceeds bound; refusing to truncate potentially active identities")
    with path.open("xb") as fh:
        fh.write(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=day)
    parser.add_argument("--end", required=True, type=day)
    parser.add_argument("--source", choices=sorted(SOURCES), action="append")
    parser.add_argument("--archive", type=Path, default=Path(__file__).parent)
    parser.add_argument("--input", type=Path, help="offline normalized metadata fixture; no network")
    parser.add_argument("--decisions", type=Path, help="Human-reviewed lifecycle rows; validated, never applied to Skill automatically")
    parser.add_argument("--history-in", type=Path, help="validated metadata identities from a prior complete run")
    parser.add_argument("--history-out", type=Path, help="new metadata history; written only on complete retrieval")
    args = parser.parse_args()
    decisions = [validate_decision(row) for row in json.loads(args.decisions.read_text())] if args.decisions else []
    if args.start > args.end:
        parser.error("start must not exceed end")
    archive = args.archive / args.end.isoformat()
    archive.mkdir(parents=True, exist_ok=True)
    if args.history_in and not args.history_out:
        parser.error("--history-in requires --history-out")
    if args.history_out and (args.end - args.start).days >= HISTORY_DAYS:
        parser.error("cross-run history supports at most 90 inclusive days")
    through, carried = read_history(args.history_in, args.end) if args.history_in else (None, {})
    known = set(carried)
    # Exclude this date so reruns refresh rather than incorrectly erase its discoveries.
    for path in args.archive.glob("*/radar.json"):
        if path.parent != archive:
            for row in json.loads(path.read_text())["items"]:
                known.add(row["source"] + ":" + row["id"])
    records, statuses = [], []
    if args.input:
        records = json.loads(args.input.read_text())
        statuses.append({"source": "fixture", "status": "OFFLINE_FIXTURE", "complete": True})
    else:
        for source in args.source or sorted(SOURCES):
            try:
                rows, complete = collect(source, args.start, args.end)
                records.extend(rows)
                statuses.append({"source": source, "status": "FETCHED", "complete": complete})
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
                statuses.append({"source": source, "status": "FETCH_FAILED", "complete": False,
                                 "error": type(exc).__name__ + ": " + str(exc)})
    selected = select(records, args.start, args.end, known)
    complete = all(s["complete"] for s in statuses)
    report = {"schema_version": 1, "start": str(args.start), "end": str(args.end),
              "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(), "sources": statuses,
              "status": "INCOMPLETE" if not complete else ("REVIEW_REQUIRED" if selected else "NO_NEW_CANDIDATES"),
              "retrieval_complete": complete,
              "date_unknown_candidates": [r for r in records if event_utc_day(r.get("event_at")) is None],
              "manual_sources": [{"source": s, "status": "MANUAL_REVIEW_REQUIRED"} for s in ("X", "Khronos", "Android", "Arm", "Qualcomm", "Imagination", "Mesa")],
              "note": "Metadata candidates only; no verified material updates is a human review conclusion, not a fetch result.",
              "review_decisions": decisions, "items": selected}
    if args.history_out:
        report["history"] = {
            "mode": "RESTORED" if through else "NO_PRIOR_COMPLETE_HISTORY",
            "prior_through": str(through) if through else None,
            "retained_identities": len(carried),
            "retained_days": HISTORY_DAYS,
            "write_admitted": complete,
        }
    output = archive / "radar.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), "items": len(selected), "complete": complete,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
    if complete and args.history_out:
        write_history(args.history_out, args.end, carried, selected)
    return 0 if complete else 2

if __name__ == "__main__":
    raise SystemExit(main())
