#!/usr/bin/env python3
"""docs-page-hashes.py — probe the /bx:evolve docs-lane allowlist for changed pages.

Read-only: fetches every allowlisted page's markdown rendering (`<url>.md`, which
code.claude.com serves as text/markdown), hashes the whitespace-normalized text, and
compares each hash with `watermark.docs_pages` in docs/upstream/state.json. It never
writes state — the orchestrator stores the hashes at Step 6 (SKILL.md), per
state-schema.md's Update mechanics.

Usage (from the repo root):
    python -I bx/skills/evolve/scripts/docs-page-hashes.py \
        --state docs/upstream/state.json \
        --allowlist bx/skills/evolve/references/scan-docs.md \
        [--inventory-file bx/skills/evolve/capabilities.json | <text, one per line> | -] [--full]

Prints one JSON object:
    inventory_hash        sha1 of the sorted, de-duplicated capability inventory ("" when no file given)
    inventory_changed     true when it differs from watermark.inventory_hash (null counts as changed)
    pages                 [{url, status: new|changed|unchanged|probe_failed, hash, size, error}]
    pages_to_scan         the URLs the docs lane must fetch this run
    counts                per-status totals

Decision rule (owned by SKILL.md Step 1.5, implemented here): with --full or a changed
inventory every page is scanned; otherwise only pages that are new (no stored hash),
changed, or whose probe failed. A page whose probe failed is scanned rather than skipped —
a guess is not a reason to skip.
"""
import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

USER_AGENT = "bx-evolve docs-page-hashes (+https://github.com/burak-maxitech/claude-config)"
ALLOWLIST_ROW = re.compile(r"^\| `(https://[^`]+)` \|", re.M)


def normalize(data: bytes) -> bytes:
    return re.sub(rb"\s+", b" ", data).strip()


def fetch_hash(url: str, timeout: float = 30.0):
    req = urllib.request.Request(url + ".md", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ctype = resp.headers.get("content-type", "")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return None, 0, f"{type(exc).__name__}: {exc}"
    if "markdown" not in ctype and "text/plain" not in ctype:
        return None, len(body), f"unexpected content-type {ctype!r} for {url}.md"
    return hashlib.sha1(normalize(body)).hexdigest(), len(body), None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--allowlist", required=True)
    ap.add_argument("--inventory-file")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    with open(args.allowlist, encoding="utf-8") as fh:
        urls = ALLOWLIST_ROW.findall(fh.read())
    if not urls:
        print(json.dumps({"error": f"no allowlist rows found in {args.allowlist}"}))
        return 2

    with open(args.state, encoding="utf-8") as fh:
        state = json.load(fh)
    wm = state.get("watermark", {})
    stored_pages = wm.get("docs_pages") or {}
    stored_inventory = wm.get("inventory_hash")

    inventory_hash = ""
    inventory_changed = False
    if args.inventory_file:
        if args.inventory_file.endswith(".json"):
            with open(args.inventory_file, encoding="utf-8") as fh:
                items = sorted(set(json.load(fh)["capabilities"]))
        else:
            fh = sys.stdin if args.inventory_file == "-" else open(args.inventory_file, encoding="utf-8")
            with fh:
                items = sorted({line.strip() for line in fh if line.strip()})
        inventory_hash = hashlib.sha1("\n".join(items).encode("utf-8")).hexdigest()
        inventory_changed = stored_inventory != inventory_hash

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(fetch_hash, urls))

    pages = []
    for url, (digest, size, error) in zip(urls, results):
        if digest is None:
            status = "probe_failed"
        elif url not in stored_pages:
            status = "new"
        elif stored_pages[url].get("hash") != digest:
            status = "changed"
        else:
            status = "unchanged"
        pages.append({"url": url, "status": status, "hash": digest, "size": size, "error": error})

    if args.full or inventory_changed:
        to_scan = [p["url"] for p in pages]
        reason = "--full" if args.full else "inventory changed"
    else:
        to_scan = [p["url"] for p in pages if p["status"] != "unchanged"]
        reason = "delta"

    counts = {}
    for p in pages:
        counts[p["status"]] = counts.get(p["status"], 0) + 1

    print(json.dumps({
        "inventory_hash": inventory_hash,
        "stored_inventory_hash": stored_inventory,
        "inventory_changed": inventory_changed,
        "scan_reason": reason,
        "pages": pages,
        "pages_to_scan": to_scan,
        "counts": counts,
        "total": len(pages),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
