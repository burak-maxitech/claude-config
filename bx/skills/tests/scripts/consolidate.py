#!/usr/bin/env python3
"""consolidate.py — find tests that differ only in their literals and can become one table test.

The mechanism behind the consolidate lane (spec D4, problem 31) in
docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md. Scanners read its JSON and judge
it; they do not compare test bodies by hand.

Two tests are candidates when their literal-stripped token shapes (from test_bodies.py) have a
multiset Jaccard >= --threshold, they share a file or call the same production symbol (from
references.py), and their setup matches (same fixtures, same mock-setup line count). A cluster is
`mechanical` when every member's shape is the identical token SEQUENCE: then the merge is a pure
table rewrite (one row per member, each member's literals as that row), which is the only kind
/bx:tests --fix may apply. Everything else is a judgment rewrite for --plan.

Read-only; writes only into --out.

Usage:
    python -I bx/skills/tests/scripts/consolidate.py --out <dir>
        --test-bodies <out>/test_bodies.jsonl [--references <out>/references.json] [--repo <path>]
        [--threshold 0.9] [--min-tokens 12] [--min-saved 4]

Writes <out>/consolidate.json:
    clusters[]  {id (positional, this run only), key (stable: hash of the member anchors),
                 same_file, files[], symbol,
                 rows[{anchor, file, describe[], name, line, end_line, body_lines}]
                   anchor = "file :: describe > ... > name" is how a row is found; line and
                   end_line are a hint that goes stale after any earlier edit in the file,
                 tests_before, tests_after: 1, cases_after (must equal tests_before),
                 lines_before, lines_after_est, saved_lines, jaccard_min, mechanical,
                 merge_table {name_slot, slots, rows[member][slot], comment_lines} | null,
                 not_mechanical_because,
                 matcher_variants[{matchers[], rows[]}] (non-mechanical only: members that assert
                   different relations, e.g. toBe vs toBeGreaterThanOrEqual; the table needs a
                   per-row matcher column),
                 worthwhile (saved_lines >= 20, or mechanical and >= 10)}
    totals      {clusters, tests_before, tests_after, saved_lines, mechanical_clusters,
                 worthwhile {clusters, tests_before, saved_lines, rule}}
    siblings[]  {clusters[2], keys[2], matched_members, differs_by[2][], saved_lines, suggestion}:
                 two clusters in one file that are one table on two fields (>= 75% of the smaller
                 one's members match a member of the other by shape; split only by setup)
    threshold, calibration{0.8, 0.85, 0.9, 0.95: cluster/test counts}
"""
import argparse
import hashlib
import io
import json
import os
import re
import textwrap
import tokenize
from collections import Counter


WORTH_MIN = 20
WORTH_MIN_MECHANICAL = 10  # a mechanical merge costs a y/n under --fix, so a smaller saving earns it


def jaccard(a, b):
    inter = sum((a & b).values())
    union = sum((a | b).values())
    return inter / union if union else 0.0


def anchor(r):
    """file :: describe > ... > test name — survives line shifts, unlike line numbers."""
    return "%s :: %s" % (r["file"], " > ".join(list(r.get("describe") or []) + [r["name"] or "?"]))


def cluster_key(members):
    """Stable across reruns, unlike the positional C### id: a hash of the member anchors."""
    return hashlib.sha1("\n".join(sorted(anchor(m) for m in members)).encode("utf-8")).hexdigest()[:8]


def setup_key(r):
    return (tuple(sorted(r.get("fixtures") or [])), r.get("mock_setup_lines", 0), r["lang"], tuple(r.get("describe") or [])[:1])


def cluster(rows, groups, threshold, min_tokens):
    """Greedy complete-linkage: a test joins a cluster only if it matches EVERY member."""
    shapes = {i: Counter(rows[i]["shape"].split()) for i in range(len(rows))}
    seqs = {i: rows[i]["shape"] for i in range(len(rows))}
    out, used = [], set()
    for key, members in groups.items():
        members = [i for i in members if i not in used and len(seqs[i].split()) >= min_tokens]
        by_setup = {}
        for i in members:
            by_setup.setdefault(setup_key(rows[i]), []).append(i)
        for same in by_setup.values():
            remaining = sorted(same, key=lambda i: (rows[i]["file"], rows[i]["line"]))
            while remaining:
                seed = remaining.pop(0)
                if seed in used:
                    continue
                cl, low = [seed], 1.0
                for j in list(remaining):
                    if j in used:
                        continue
                    sims = [jaccard(shapes[j], shapes[k]) for k in cl]
                    if min(sims) >= threshold:
                        cl.append(j)
                        low = min(low, min(sims))
                        remaining.remove(j)
                if len(cl) >= 2:
                    used.update(cl)
                    out.append((key, cl, low))
    return out


JS_TOKEN = re.compile(r"""`(?:\\.|[^`\\])*`|"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|/\*.*?\*/|//[^\n]*|\d[\w.]*|[A-Za-z_$][\w$]*|\S""", re.S)
LITERAL_WORDS = {"true", "false", "null", "undefined", "None", "True", "False"}


def raw_tokens(src, lang):
    """[(is_literal, text)] for a test's source, comments dropped."""
    out = []
    if lang == "py":
        after_def = False
        try:
            for t in tokenize.generate_tokens(io.StringIO(textwrap.dedent(src)).readline):
                if t.type in (tokenize.STRING, tokenize.NUMBER):
                    out.append((True, t.string))
                elif t.type == tokenize.NAME:
                    # `def test_x` — the name is the case label (slot 0), as a JS title string is
                    out.append((after_def or t.string in LITERAL_WORDS, t.string))
                elif t.type == tokenize.OP:
                    out.append((False, t.string))
                after_def = t.type == tokenize.NAME and t.string == "def"
        except (tokenize.TokenError, IndentationError, SyntaxError):
            return None
        return out
    for t in JS_TOKEN.findall(src):
        if t.startswith(("//", "/*")):
            continue
        out.append((t[0] in "\"'`" or t[0].isdigit() or t in LITERAL_WORDS, t))
    return out


def member_src(m, repo):
    with open(os.path.join(repo, m["file"]), encoding="utf-8", errors="replace") as fh:
        return "\n".join(fh.read().split("\n")[m.get("start_line", m["line"]) - 1:m["end_line"]])


JS_MATCHER = re.compile(r"\.\s*((?:not\s*\.\s*)?(?:resolves\s*\.\s*|rejects\s*\.\s*)?to[A-Z]\w*)\s*\(")
PY_ASSERT = re.compile(r"^\s*assert\b(.*)$", re.M)
PY_SELF_ASSERT = re.compile(r"\bself\.(assert\w+)\s*\(")
PY_OPS = re.compile(r"\s(==|!=|>=|<=|>|<|not\s+in|in|is\s+not|is)\s")


def matchers(src, lang):
    """The ordered assertion relations a test checks: `toBe`, `toBeGreaterThanOrEqual`, `==`, `>=`.
    Shape Jaccard strips literals, so two tests asserting `toBe(1)` and `>= 1` look alike (S257)."""
    if lang == "py":
        out = []
        for line in PY_ASSERT.findall(src):
            op = PY_OPS.search(line)
            out.append(re.sub(r"\s+", " ", op.group(1)) if op else "truthy")
        return out + PY_SELF_ASSERT.findall(src)
    return [re.sub(r"\s+", "", m) for m in JS_MATCHER.findall(src)]


def matcher_variants(members, repo):
    """[{matchers, rows}] when members check different relations, else []. A table built from such
    a cluster needs a per-row matcher column (S257 C174: three rows toBe(n), one deliberately >= 1)."""
    if not repo:
        return []
    groups = {}
    for k, m in enumerate(members):
        try:
            sig = tuple(matchers(member_src(m, repo), m["lang"]))
        except OSError:
            return []
        groups.setdefault(sig, []).append(k)
    if len(groups) < 2:
        return []
    return [{"matchers": list(sig), "rows": rows} for sig, rows in sorted(groups.items(), key=lambda g: g[1][0])]


def sibling_pairs(clusters, members_of, threshold, cover=0.75):
    """Pairs of clusters in one file that are the same table on two fields: at least `cover` of the
    smaller cluster's members match a distinct member of the other (shape Jaccard >= threshold).
    They were split only because their setup differs (the field is a describe block in one and a
    name prefix in the other). One shared runner can serve both tables (S257: dial_finishes and
    straps, two clusters with the same merge policy). `differs_by` is the identifiers only one side
    uses, which is usually the field."""
    out = []
    for i, a in enumerate(clusters):
        for b in clusters[i + 1:]:
            if set(a["files"]) != set(b["files"]):
                continue
            ma, mb = members_of(a), members_of(b)
            small, big = (ma, mb) if len(ma) <= len(mb) else (mb, ma)
            sb = [Counter(m["shape"].split()) for m in big]
            used, hits = set(), 0
            for m in small:
                sm = Counter(m["shape"].split())
                j = next((j for j, s in enumerate(sb) if j not in used and jaccard(sm, s) >= threshold), None)
                if j is not None:
                    used.add(j)
                    hits += 1
            if hits < 2 or hits < cover * len(small):
                continue
            ida = set().union(*(set(re.findall(r"[A-Za-z_$][\w$]*", m["shape"])) for m in ma))
            idb = set().union(*(set(re.findall(r"[A-Za-z_$][\w$]*", m["shape"])) for m in mb))
            out.append({"clusters": [a["id"], b["id"]], "keys": [a["key"], b["key"]],
                        "matched_members": hits,
                        "differs_by": [sorted(ida - idb)[:6], sorted(idb - ida)[:6]],
                        "saved_lines": a["saved_lines"] + b["saved_lines"],
                        "suggestion": "one shared runner serving both tables, parameterized by the field"})
    return out


def merge_table(members, repo):
    """The literal table a mechanical merge needs: one row per member, one column per literal slot
    whose value differs between members. A cluster is mechanical only if every member's NON-literal
    token sequence is identical, checked here on the raw source, not on the stripped shape."""
    if not repo:
        return None, "no --repo: table not computed"
    seqs, comments = [], 0
    for m in members:
        try:
            src = member_src(m, repo)
        except OSError:
            return None, "could not read %s" % m["file"]
        comments += len(re.findall(r"^\s*(//|#)", src, re.M))
        toks = raw_tokens(src, m["lang"])
        if toks is None:
            return None, "could not tokenize %s:%d" % (m["file"], m["line"])
        seqs.append(toks)
    skeleton = [t for lit, t in seqs[0] if not lit]
    if any([t for lit, t in s if not lit] != skeleton for s in seqs[1:]):
        return None, "members differ outside their literals"
    lits = [[t for lit, t in s if lit] for s in seqs]
    if len({len(l) for l in lits}) != 1:
        return None, "members have different literal counts"
    cols = [i for i in range(len(lits[0])) if len({l[i] for l in lits}) > 1]
    if cols == [0]:
        return None, "only the test name differs: duplicates, not cases (route to --plan)"
    return {"name_slot": 0, "slots": cols, "rows": [[l[i] for i in cols] for l in lits],
            "comment_lines": comments}, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-bodies", required=True)
    ap.add_argument("--references")
    ap.add_argument("--repo", help="read member sources to compute merge tables for mechanical clusters")
    ap.add_argument("--threshold", type=float, default=0.9)
    ap.add_argument("--min-tokens", type=int, default=12)
    ap.add_argument("--min-saved", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    with open(a.test_bodies, encoding="utf-8") as fh:
        allrows = [json.loads(l) for l in fh]
    refs = None
    if a.references:
        with open(a.references, encoding="utf-8") as fh:
            refs = json.load(fh)
    # tests of a life-support symbol are moved or deleted by that lane; merging them too would
    # count the same lines twice (S65 rerun: cluster C002 was two of build_reply_all_recipients' tests)
    life_rows = {(t["file"], t["line"]) for l in (refs or {}).get("life_support", []) for t in l["test_rows"]}
    # already-parameterized, skipped and assertion-free tests are not merge inputs
    rows = [r for r in allrows if r.get("shape") and not r.get("param_rows") and not r.get("skipped")
            and r["assertion_total"] and (r["file"], r["line"]) not in life_rows]
    index = {(r["file"], r["line"]): i for i, r in enumerate(rows)}

    groups = {}
    for i, r in enumerate(rows):
        groups.setdefault(("file", r["file"]), []).append(i)
    cross = {}
    if refs:
        for s in refs["symbols"]:
            files = {c["file"] for c in s["test_call_rows"]}
            if len(files) < 2:
                continue  # same-file pairs are already a file group
            ids = [index[(c["file"], c["line"])] for c in s["test_call_rows"] if (c["file"], c["line"]) in index]
            if len(ids) >= 2:
                cross[("symbol", s["id"])] = ids

    def build(threshold):
        found = cluster(rows, groups, threshold, a.min_tokens)
        taken = {i for _, cl, _ in found for i in cl}
        cross_left = {k: [i for i in v if i not in taken] for k, v in cross.items()}
        found += [(k, cl, low) for k, cl, low in cluster(rows, cross_left, threshold, a.min_tokens)
                  if len({rows[i]["file"] for i in cl}) > 1]
        return found

    calibration = {}
    for t in (0.8, 0.85, 0.9, 0.95):
        f = build(t)
        calibration[str(t)] = {"clusters": len(f), "tests": sum(len(cl) for _, cl, _ in f)}

    clusters, members_by_id = [], {}
    for n, (key, cl, low) in enumerate(build(a.threshold)):
        members = [rows[i] for i in cl]
        members_by_id["C%03d" % (n + 1)] = members
        table, why_not = merge_table(members, a.repo) if len({m["shape"] for m in members}) == 1 \
            else (None, "token shapes differ (Jaccard match, not identical)")
        lines_before = sum(m["body_lines"] for m in members)
        longest = max(m["body_lines"] for m in members)
        lines_after = longest + len(members) + 1  # one table row per case + the table brackets
        clusters.append({
            "id": "C%03d" % (n + 1),
            "same_file": key[0] == "file",
            "files": sorted({m["file"] for m in members}),
            "symbol": key[1] if key[0] == "symbol" else None,
            "key": cluster_key(members),
            # locate a row by its anchor; line/end_line are only a hint, stale after any earlier
            # edit in the file (S257: later clusters moved 50-300 lines after the first merge)
            "rows": [{"anchor": anchor(m), "file": m["file"], "describe": m.get("describe") or [],
                      "name": m["name"], "line": m["line"], "end_line": m["end_line"],
                      "body_lines": m["body_lines"]} for m in members],
            "tests_before": len(members), "tests_after": 1, "cases_after": len(members),
            "lines_before": lines_before, "lines_after_est": lines_after,
            "saved_lines": max(0, lines_before - lines_after),
            "jaccard_min": round(low, 3),
            # mechanical: a pure table rewrite the script has already computed (merge_table)
            "mechanical": table is not None,
            "merge_table": table,
            "not_mechanical_because": why_not,
            # rows that check a different relation need their own matcher column in the table
            "matcher_variants": [] if table else matcher_variants(members, a.repo),
        })
    # a merge that saves 1-3 lines costs a reviewer more than it returns (S65 calibration on horowell:
    # 207 of 458 clusters at 0.9 saved under 4 lines)
    clusters = [c for c in clusters if c["saved_lines"] >= a.min_saved]
    clusters.sort(key=lambda c: -c["saved_lines"])
    for c in clusters:
        c["worthwhile"] = c["saved_lines"] >= WORTH_MIN or c["mechanical"] and c["saved_lines"] >= WORTH_MIN_MECHANICAL
    worth = [c for c in clusters if c["worthwhile"]]
    totals = {
        "clusters": len(clusters),
        "tests_before": sum(c["tests_before"] for c in clusters),
        "tests_after": len(clusters),
        "saved_lines": sum(c["saved_lines"] for c in clusters),
        "mechanical_clusters": sum(1 for c in clusters if c["mechanical"]),
        # the headline leads with these: "774 -> 251" set an expectation the brief then cut by ~240
        # clusters (S257); all six merges it did by hand saved >= 20 lines
        "worthwhile": {"clusters": len(worth), "tests_before": sum(c["tests_before"] for c in worth),
                       "saved_lines": sum(c["saved_lines"] for c in worth),
                       "rule": "saved_lines >= %d, or mechanical and saved_lines >= %d" % (WORTH_MIN, WORTH_MIN_MECHANICAL)},
    }
    siblings = sibling_pairs(clusters, lambda c: members_by_id[c["id"]], a.threshold)
    result = {"threshold": a.threshold, "min_tokens": a.min_tokens, "min_saved": a.min_saved, "calibration": calibration,
              "totals": totals, "clusters": clusters, "siblings": siblings}
    path = os.path.join(a.out, "consolidate.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"totals": totals, "calibration": calibration}))
    print("consolidate=%s" % path)


if __name__ == "__main__":
    main()
