#!/usr/bin/env python3
"""Read-only public GitHub radar; archive metadata, never promote a rule or schedule a job."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request

SOURCES = {
    "cts": ("KhronosGroup/VK-GL-CTS", "releases"),
    "filament": ("google/filament", "releases"),
    "agi": ("google/agi", "releases"),
    "perfetto": ("google/perfetto", "releases"),
    "renderdoc": ("baldurk/renderdoc", "releases"),
    "glslang": ("KhronosGroup/glslang", "releases"),
    "angle": ("google/angle", "commits"),
}
MAX_PAGES = 10

def day(value):
    return dt.date.fromisoformat(value)

def normalize(source, kind, record):
    if kind == "releases":
        return {"source": source, "id": str(record["id"]), "url": record["html_url"],
                "event_at": record["published_at"], "revision": record["tag_name"],
                "title": record.get("name") or record["tag_name"],
                "draft": record.get("draft", False), "prerelease": record.get("prerelease", False)}
    return {"source": source, "id": record["sha"], "url": record["html_url"],
            "event_at": record["commit"]["committer"]["date"], "revision": record["sha"],
            "title": record["commit"]["message"].splitlines()[0], "draft": False, "prerelease": False}

def select(records, start, end, known):
    result = {}
    for row in records:
        if not row.get("event_at") or row.get("draft"):
            continue
        if not start <= day(row["event_at"][:10]) <= end:
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

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, type=day)
    parser.add_argument("--end", required=True, type=day)
    parser.add_argument("--source", choices=sorted(SOURCES), action="append")
    parser.add_argument("--archive", type=Path, default=Path(__file__).parent)
    parser.add_argument("--input", type=Path, help="offline normalized metadata fixture; no network")
    args = parser.parse_args()
    if args.start > args.end:
        parser.error("start must not exceed end")
    archive = args.archive / args.end.isoformat()
    archive.mkdir(parents=True, exist_ok=True)
    known = set()
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
              "status": "REVIEW_REQUIRED" if selected else ("NO_NEW_CANDIDATES" if complete else "INCOMPLETE"),
              "note": "Metadata candidates only; no verified material updates is a human review conclusion, not a fetch result.",
              "items": selected}
    output = archive / "radar.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), "items": len(selected), "complete": complete,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
    return 0 if complete else 2

if __name__ == "__main__":
    raise SystemExit(main())
