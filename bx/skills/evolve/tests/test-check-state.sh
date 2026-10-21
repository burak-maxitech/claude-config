#!/usr/bin/env bash
# test-check-state.sh - exercise check-state.py against the live state and four planted defects.
# bash 3.2 compatible; needs python3 (or python) on PATH.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
CHECK="$SCRIPT_DIR/check-state.py"
PY=""
for c in python3 python; do   # on Windows `python3` may be a Store stub that only prints an install hint
    if "$c" -I -c "pass" >/dev/null 2>&1; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "no working python found"; exit 2; }
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

FAILURES=0
pass() { echo "  PASS  $1"; }
fail() { echo "  FAIL  $1"; FAILURES=$((FAILURES + 1)); }

run_check() {  # <root> -> exit status; output captured in $OUT
    OUT="$(PYTHONUTF8=1 "$PY" -I "$CHECK" "$1" 2>&1)"; return $?
}

# live state must validate
if run_check "$REPO"; then pass "live state.json validates"; else fail "live state.json validates -- $OUT"; fi

# planted defects: copy the live state into a throwaway root and mutate with python
plant() {  # <name> <python-expression mutating `d`> <expected-substring>
    local root="$TMP/$1"
    mkdir -p "$root/docs/upstream"
    cp "$REPO/docs/upstream/state.json" "$root/docs/upstream/state.json"
    [ -f "$REPO/docs/upstream/pain-points.json" ] && cp "$REPO/docs/upstream/pain-points.json" "$root/docs/upstream/"
    PYTHONUTF8=1 "$PY" -I - "$root/docs/upstream/state.json" "$2" <<'PY'
import json, sys
p, expr = sys.argv[1], sys.argv[2]
d = json.load(open(p, encoding="utf-8"))
exec(expr)
json.dump(d, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PY
    if run_check "$root"; then fail "$1 is rejected -- validator passed"
    elif printf '%s' "$OUT" | grep -qF -- "$3"; then pass "$1 is rejected"
    else fail "$1 is rejected -- wrong reason: $OUT"; fi
}

plant duplicate-id   "d['decisions'].append(dict(d['decisions'][0]))"                         "duplicate finding_id"
plant short-hash     "d['decisions'][0]['source_content_hash']='abc'"                            "source_content_hash is not 40"
plant missing-field  "del d['decisions'][0]['title']"                                            "keys must be in schema order"
plant bad-key-order  "e=d['decisions'][0]; n=e.pop('note'); d['decisions'][0]=dict([('note',n)]+list(e.items()))" "keys must be in schema order"
plant bad-decision   "d['decisions'][0]['decision']='maybe'"                                     "not in"
plant id-mismatch    "d['decisions'][0]['affected_capability']='bx:other/thing'"                 "does not equal sha1"

# pain registry: a state whose bx:pain/<x> points at an alias or an unknown id must fail
plant_reg() {  # <name> <python-expression mutating `d` (state) and `r` (registry)> <expected-substring>
    local root="$TMP/$1"
    mkdir -p "$root/docs/upstream"
    cp "$REPO/docs/upstream/state.json" "$root/docs/upstream/state.json"
    PYTHONUTF8=1 "$PY" -I - "$root/docs/upstream" "$2" <<'PY'
import hashlib, json, sys
d_dir, expr = sys.argv[1], sys.argv[2]
d = json.load(open(d_dir + "/state.json", encoding="utf-8"))
r = {"pain_points": [{"id": "sample-pain", "text": "Sample pain point", "source": "claude-md", "status": "active",
                      "aliases": ["sample-pain-old-slug"], "first_seen": "2026-10-20", "last_seen": "2026-10-20"}]}
url = d["decisions"][0]["source_url"]
def point(cap):
    e = d["decisions"][0]; e["affected_capability"] = cap
    e["finding_id"] = hashlib.sha1((url + "|" + cap).encode()).hexdigest()
exec(expr)
json.dump(d, open(d_dir + "/state.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
json.dump(r, open(d_dir + "/pain-points.json", "w", encoding="utf-8"), indent=2)
PY
    if run_check "$root"; then fail "$1 is rejected -- validator passed"
    elif printf '%s' "$OUT" | grep -qF -- "$3"; then pass "$1 is rejected"
    else fail "$1 is rejected -- wrong reason: $OUT"; fi
}
plant_reg pain-alias-used   "point('bx:pain/sample-pain-old-slug')"                                  "is an alias"
plant_reg pain-unknown-id   "point('bx:pain/nobody-knows')"                                          "no registry entry"
plant_reg registry-dup-id   "point('bx:pain/sample-pain'); r['pain_points'].append(dict(r['pain_points'][0]))" "duplicate id"
plant_reg registry-bad-keys "point('bx:pain/sample-pain'); r['pain_points'][0].pop('last_seen')"    "keys must be"

echo ""
if [ "$FAILURES" -gt 0 ]; then echo "$FAILURES check-state test(s) failed."; exit 1; fi
echo "All check-state tests passed."
