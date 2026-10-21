#!/usr/bin/env python3
"""check-state.py - validate docs/upstream/state.json (and docs/upstream/pain-points.json)
against bx/skills/evolve/references/state-schema.md.

Usage: python -I check-state.py [repo-root]      (default: cwd)
Exit 0 = valid. Exit 1 = at least one FAIL. Warnings never change the exit code.

Stdlib only. Mirrors the validation step of state-schema.md's "Update mechanics"; the schema
file owns the rules, this script makes them mechanical. Keep the two in sync.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HEX40 = re.compile(r"^[0-9a-f]{40}$")
SENTINEL = "0" * 40
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CAPABILITY = re.compile(r"^bx:[a-z0-9-]+/[a-z0-9/-]+$")
DECISIONS = {"open", "applied", "rejected", "deferred"}
CLASSES = {"breakage", "best_practice", "opportunity"}

WATERMARK_KEYS = ["last_changelog_version", "docs_checked_at", "community_checked_at", "changelog_gap", "docs_pages", "inventory_hash"]
LEGACY_KEYS = ["finding_id", "decision", "date", "source_url", "affected_capability",
               "source_content_hash", "class", "title", "note"]
NEW_KEYS = ["proposed_edit", "affected_files", "source_excerpt", "citation"]
ENTRY_KEYS = LEGACY_KEYS + NEW_KEYS
REGISTRY_KEYS = ["id", "text", "source", "status", "aliases", "first_seen", "last_seen"]
PAIN_ID = re.compile(r"^[a-z0-9-]+$")

failures = []
warnings = []


def fail(msg):
    failures.append(msg)


def warn(msg):
    warnings.append(msg)


def canonical_url(url):
    """state-schema.md 'source_url canonicalization (normative)'."""
    m = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*://)([^/?#]+)(.*)$", url)
    if not m:
        return url
    scheme, host, rest = m.group(1).lower(), m.group(2).lower(), m.group(3)
    rest = rest.split("#", 1)[0]
    path, _, query = rest.partition("?")
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    if query:
        kept = [p for p in query.split("&") if not p.lower().startswith("utm_")]
        query = "&".join(kept)
    return scheme + host + path + ("?" + query if query else "")


def check_state(root):
    path = root / "docs" / "upstream" / "state.json"
    if not path.exists():
        fail(f"{path} missing")
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"state.json is not valid JSON: {e}")
        return None

    if list(state.keys()) != ["watermark", "decisions"]:
        fail(f"root keys must be exactly ['watermark', 'decisions'], got {list(state.keys())}")
    wm = state.get("watermark", {})
    wm_keys = list(wm.keys())
    if wm_keys == WATERMARK_KEYS[:3]:
        warn("watermark lacks `changelog_gap` (pre-2.11.0 shape; migration owed)")
    elif wm_keys == WATERMARK_KEYS[:4]:
        warn("watermark lacks `docs_pages`/`inventory_hash` (pre-2.12.0 shape; the next run adds them)")
    elif wm_keys != WATERMARK_KEYS:
        fail(f"watermark keys out of order or wrong: {wm_keys}")
    v = wm.get("last_changelog_version")
    if v is not None and not re.match(r"^\d+\.\d+\.\d+$", str(v)):
        fail(f"last_changelog_version must be unprefixed semver or null, got {v!r}")
    for k in ("docs_checked_at", "community_checked_at"):
        d = wm.get(k)
        if d is not None and not DATE.match(str(d)):
            fail(f"watermark.{k} must be YYYY-MM-DD or null, got {d!r}")
    gap = wm.get("changelog_gap")
    if gap is not None:
        if list(gap.keys()) != ["after", "before", "recorded"]:
            fail(f"changelog_gap keys must be [after, before, recorded], got {list(gap.keys())}")
        elif not DATE.match(str(gap["recorded"])):
            fail(f"changelog_gap.recorded must be YYYY-MM-DD, got {gap['recorded']!r}")

    pages = wm.get("docs_pages", {})
    if not isinstance(pages, dict):
        fail("watermark.docs_pages must be an object keyed by URL")
    else:
        for url, entry in pages.items():
            if not str(url).startswith("https://"):
                fail(f"docs_pages key {url!r} is not an https URL")
            if not isinstance(entry, dict) or list(entry.keys()) != ["hash", "scanned"]:
                fail(f"docs_pages[{url!r}] must be {{hash, scanned}} in that order")
                continue
            if not HEX40.match(str(entry["hash"])):
                fail(f"docs_pages[{url!r}].hash is not 40 lowercase hex chars")
            if not DATE.match(str(entry["scanned"])):
                fail(f"docs_pages[{url!r}].scanned must be YYYY-MM-DD")
    ih = wm.get("inventory_hash")
    if ih is not None and not HEX40.match(str(ih)):
        fail("watermark.inventory_hash must be 40 lowercase hex chars or null")

    decisions = state.get("decisions")
    if not isinstance(decisions, list):
        fail("decisions must be an array")
        return state
    seen = {}
    legacy = 0
    for i, e in enumerate(decisions):
        tag = f"decisions[{i}] ({str(e.get('finding_id', '?'))[:8]})"
        keys = list(e.keys())
        if keys == LEGACY_KEYS:
            legacy += 1
        elif keys != ENTRY_KEYS:
            fail(f"{tag}: keys must be in schema order {ENTRY_KEYS} (or the 9-key legacy prefix), got {keys}")
        fid = e.get("finding_id")
        if not isinstance(fid, str) or not HEX40.match(fid):
            fail(f"{tag}: finding_id is not 40 lowercase hex chars")
        elif fid in seen:
            fail(f"{tag}: duplicate finding_id (also at decisions[{seen[fid]}])")
        else:
            seen[fid] = i
        if e.get("decision") not in DECISIONS:
            fail(f"{tag}: decision {e.get('decision')!r} not in {sorted(DECISIONS)}")
        if not DATE.match(str(e.get("date"))):
            fail(f"{tag}: date must be YYYY-MM-DD")
        url = e.get("source_url")
        if not isinstance(url, str) or not url:
            fail(f"{tag}: source_url missing")
        elif canonical_url(url) != url:
            fail(f"{tag}: source_url is not canonical ({url!r} -> {canonical_url(url)!r})")
        cap = e.get("affected_capability")
        if not isinstance(cap, str) or not CAPABILITY.match(cap):
            fail(f"{tag}: affected_capability {cap!r} does not match {CAPABILITY.pattern}")
        elif isinstance(url, str) and isinstance(fid, str):
            expect = hashlib.sha1((url + "|" + cap).encode("utf-8")).hexdigest()
            if expect != fid:
                fail(f"{tag}: finding_id does not equal sha1(source_url|affected_capability) = {expect[:8]}…")
        h = e.get("source_content_hash")
        if not isinstance(h, str) or not HEX40.match(h):
            fail(f"{tag}: source_content_hash is not 40 lowercase hex chars (empty string is not allowed; use the sentinel)")
        if e.get("class") not in CLASSES:
            fail(f"{tag}: class {e.get('class')!r} not in {sorted(CLASSES)}")
        if not isinstance(e.get("title"), str) or not e.get("title"):
            fail(f"{tag}: title missing")
        if "note" not in e or not (e["note"] is None or isinstance(e["note"], str)):
            fail(f"{tag}: note must be present (string or null)")
        if keys == ENTRY_KEYS:
            for k in ("proposed_edit", "source_excerpt", "citation"):
                if not (e[k] is None or isinstance(e[k], str)):
                    fail(f"{tag}: {k} must be string or null")
            af = e["affected_files"]
            if not isinstance(af, list) or not all(isinstance(p, str) for p in af):
                fail(f"{tag}: affected_files must be an array of strings")
            elif e.get("decision") == "open" and (e["proposed_edit"] is None or not af):
                warn(f"{tag}: open entry without a stored edit (legacy — display-only until triaged)")
            if any(str(p).startswith(("/", "C:", "c:")) or ".." in str(p) for p in (af or [])):
                fail(f"{tag}: affected_files must be repo-relative paths")
    if legacy:
        warn(f"{legacy} legacy 9-key entries (pre-2.11.0); migration owed")
    return state


def check_registry(root, state):
    path = root / "docs" / "upstream" / "pain-points.json"
    if not path.exists():
        warn("docs/upstream/pain-points.json missing (pre-2.11.0; created by the first Step 0.3 run)")
        return
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"pain-points.json is not valid JSON: {e}")
        return
    if list(reg.keys()) != ["pain_points"] or not isinstance(reg["pain_points"], list):
        fail("pain-points.json root must be {\"pain_points\": [...]}")
        return
    ids, aliases = {}, {}
    for i, p in enumerate(reg["pain_points"]):
        tag = f"pain_points[{i}] ({p.get('id', '?')})"
        if list(p.keys()) != REGISTRY_KEYS:
            fail(f"{tag}: keys must be {REGISTRY_KEYS}, got {list(p.keys())}")
            continue
        if not PAIN_ID.match(str(p["id"])):
            fail(f"{tag}: id must be kebab-case [a-z0-9-]")
        if p["id"] in ids:
            fail(f"{tag}: duplicate id")
        ids[p["id"]] = i
        if p["source"] not in ("claude-md", "status-md"):
            fail(f"{tag}: source must be claude-md or status-md")
        if p["status"] not in ("active", "retired"):
            fail(f"{tag}: status must be active or retired")
        for k in ("first_seen", "last_seen"):
            if not DATE.match(str(p[k])):
                fail(f"{tag}: {k} must be YYYY-MM-DD")
        if not isinstance(p["aliases"], list):
            fail(f"{tag}: aliases must be an array")
            continue
        for a in p["aliases"]:
            if a in aliases or a in ids and ids[a] != i:
                fail(f"{tag}: alias {a!r} is not unique across the registry")
            aliases[a] = i
    if state:
        for i, e in enumerate(state.get("decisions", [])):
            cap = str(e.get("affected_capability", ""))
            if cap.startswith("bx:pain/"):
                pid = cap[len("bx:pain/"):]
                if pid not in ids:
                    if pid in aliases:
                        fail(f"decisions[{i}]: bx:pain/{pid} is an alias — rewrite to its registry id and recompute finding_id")
                    else:
                        fail(f"decisions[{i}]: bx:pain/{pid} has no registry entry")


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    state = check_state(root)
    check_registry(root, state)
    for w in warnings:
        print(f"  WARN  {w}")
    for f in failures:
        print(f"  FAIL  {f}")
    if failures:
        print(f"{len(failures)} state check(s) failed.")
        return 1
    print(f"state.json valid ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
