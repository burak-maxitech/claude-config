#!/usr/bin/env python3
"""run.py — run the four /bx:tests mechanisms in order and write one manifest.

SKILL.md Step 1.5 runs this once per workspace; the scanners read the manifest's files and
never run the scripts or write parsers of their own (spec D1).

Usage:
    python -I bx/skills/tests/scripts/run.py --repo <path> --out <dir>
        [--test-files <list.txt>] [--source-files <list.txt>] [--time-budget <secs per script>]

Writes <out>/manifest.json:
    {test_bodies, test_bodies_summary, leverage, references, consolidate: <paths>,
     coverage_partial: [every script's partial entries, plus a failed script as a partial],
     steps: [{script, ok, seconds, stdout_tail}]}
Exits 0 even when a step fails: a failed step becomes a coverage_partial entry, so the report
discloses it instead of silently reading zero.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-files")
    ap.add_argument("--source-files")
    ap.add_argument("--time-budget", default="600")
    a = ap.parse_args()
    out = os.path.realpath(a.out)
    os.makedirs(out, exist_ok=True)
    paths = {
        "test_bodies": os.path.join(out, "test_bodies.jsonl"),
        "test_bodies_summary": os.path.join(out, "test_bodies.summary.json"),
        "leverage": os.path.join(out, "leverage.json"),
        "references": os.path.join(out, "references.json"),
        "consolidate": os.path.join(out, "consolidate.json"),
    }
    base = ["--repo", a.repo, "--out", out]
    steps = [
        ("test_bodies.py", base + (["--files", a.test_files] if a.test_files else []) + ["--time-budget", a.time_budget],
         "test_bodies_summary", "test_bodies"),
        ("leverage.py", base + (["--source-files", a.source_files] if a.source_files else []) + ["--time-budget", a.time_budget],
         "leverage", "import_graph"),
        ("references.py", base + ["--test-bodies", paths["test_bodies"], "--leverage", paths["leverage"], "--time-budget", a.time_budget],
         "references", "reference_index"),
        ("consolidate.py", ["--out", out, "--repo", a.repo, "--test-bodies", paths["test_bodies"], "--references", paths["references"]],
         "consolidate", "consolidate"),
    ]
    partial, log = [], []
    for script, args, key, category in steps:
        t = time.time()
        r = subprocess.run([sys.executable, "-I", "-B", os.path.join(HERE, script)] + args, capture_output=True)
        ok = r.returncode == 0 and os.path.exists(paths[key])
        log.append({"script": script, "ok": ok, "seconds": round(time.time() - t, 2),
                    "stdout_tail": r.stdout.decode("utf-8", "replace")[-400:],
                    "stderr_tail": r.stderr.decode("utf-8", "replace")[-400:] if not ok else ""})
        if not ok:
            partial.append({"category": category, "scanned": 0, "total": None,
                            "reason": "%s failed (exit %d): %s" % (script, r.returncode, r.stderr.decode("utf-8", "replace")[-200:].strip())})
            continue
        try:
            with open(paths[key], encoding="utf-8") as fh:
                partial += json.load(fh).get("coverage_partial", [])
        except ValueError:
            pass
    manifest = dict(paths, coverage_partial=partial, steps=log)
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"steps": [(s["script"], s["ok"], s["seconds"]) for s in log], "partial": len(partial)}))
    print("manifest=%s" % os.path.join(out, "manifest.json"))


if __name__ == "__main__":
    main()
