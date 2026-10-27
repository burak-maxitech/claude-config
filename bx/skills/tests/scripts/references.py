#!/usr/bin/env python3
"""references.py — who references each production symbol, and how the tests touch it.

The mechanism behind symbol coverage (problems 5, 17, 27, 28) and the life_support lane
(problem 30) in docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md (D1, D4). Scanners
read its JSON and judge it; they do not grep for symbol names by hand.

Reference search follows /bx:clean's pinned local-use rule (scan-files-code.md): word-bounded,
code only (comments never keep a symbol alive), and the definition line itself excluded. It is
implemented as one identifier index over every tracked code file instead of one `git grep` per
name, so it also classifies each hit. String occurrences are counted separately: in production
they may be dynamic dispatch (`getattr(obj, "name")`), so they block life_support.

Read-only. Writes only into --out, which must be outside the repo.

Usage:
    python -I bx/skills/tests/scripts/references.py --repo <path> --out <dir>
        --test-bodies <out>/test_bodies.jsonl     from test_bodies.py
        --leverage <out>/leverage.json            from leverage.py (defines the source scope)
        [--time-budget <secs>]

Writes <out>/references.json:
    symbols[]       {id, name, kind, file, line, end_line, lines, owner,
                     prod_refs, prod_ref_files[<=10], prod_string_refs, prod_import_refs,
                     test_route_files (a decorated route a test client reaches by URL), leverage,
                     test_status: covered | mock_only | mention_only | name_only | untested,
                     test_call_rows[], test_mock_rows[], security_lines, priority, gap_lines}
                     A test reference is a CALL only from a test that can see the symbol (it
                     imports the defining module or a barrel re-exporting it; for methods, the
                     owner class) and has not mocked it. A call in a test file that vi.mock()s
                     the module, or inside a test that patch()es the name, is a mock.
    life_support[]  {symbol, prod_refs: 0, test_rows[], exclusive_rows[], deletable_lines,
                     successor, successor_evidence, successor_status}
                     deletable_lines = the symbol, plus its exclusive test rows only when there is
                     no successor (with one, the tests move and survive)
    modules         test:code ratio per module, test files attributed by the symbols they call
    coverage_partial[]
"""
import argparse
import ast
import io
import json
import math
import os
import re
import subprocess
import sys
import time
import tokenize

sys.dont_write_bytecode = True  # never leave __pycache__ in the skill (or the plugin cache)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_bodies import EXT_LANG, match_close, mask_clike  # noqa: E402
from leverage import (CONFIG_LIKE, DENSITY_FLOOR_LOC, Resolver, file_imports, git, is_code,  # noqa: E402
                      is_test_path, module_of, security_lines, subwords)

IDENT = re.compile(r"[A-Za-z_$][\w$]*")
JS_EXPORT_DEF = re.compile(
    r"^[ \t]*export\s+(default\s+)?(?:declare\s+)?(?:async\s+)?"
    r"(function\*?|const|let|var|class|abstract\s+class|enum|const\s+enum|interface|type)\s+([A-Za-z_$][\w$]*)", re.M)
JS_EXPORT_LIST = re.compile(r"^[ \t]*export\s+(?:type\s+)?\{([^}]*)\}\s*(from\b)?", re.M)
JS_EXPORT_DEFAULT_NAME = re.compile(r"^[ \t]*export\s+default\s+([A-Za-z_$][\w$]*)\s*;?\s*$", re.M)
JS_LOCAL_DEF = r"^[ \t]*(?:(?:async\s+)?function\*?|const|let|var|class|enum|interface|type)\s+%s\b"
JS_REEXPORT = re.compile(r"""^[ \t]*export\s+(?:type\s+)?(?:\*(?:\s+as\s+\w+)?|\{[^}]*\})\s*from\s*(["'])([^"']+)\1""", re.M)
JS_IMPORT_STMT = re.compile(r"""^[ \t]*(import|export)\b[^;]*?\bfrom\s*["'][^"'\n]+["']|^[ \t]*import\s*["'][^"'\n]+["']""", re.M | re.S)
NEXT_RESERVED = {"default", "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "metadata",
                 "generateMetadata", "generateStaticParams", "revalidate", "dynamic", "runtime",
                 "config", "viewport", "generateViewport", "middleware", "proxy", "fetchCache",
                 "preferredRegion", "maxDuration", "dynamicParams", "register", "onRequestError"}
TYPE_KINDS = {"interface", "type", "value", "enum"}  # declarative: never a coverage gap or life support
JS_FN_RHS = (r"(async\s+)?(function\b|\([^)]*\)\s*(:[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>|<[^>]*>\s*\(|"
             r"(React\s*\.\s*)?(memo|forwardRef|cache|unstable_cache|lazy|dynamic)\s*\()")


# --------------------------------------------------------------------------- masking

def py_masks(src):
    """(code-only, comment-blanked) versions of Python source, same length."""
    full, nocomment = list(src), list(src)
    starts = [0]
    for m in re.finditer("\n", src):
        starts.append(m.end())

    def span(t):
        return starts[t.start[0] - 1] + t.start[1], starts[t.end[0] - 1] + t.end[1]

    def blank(buf, a, b):
        for k in range(a, b):
            if buf[k] != "\n":
                buf[k] = " "

    try:
        for t in tokenize.generate_tokens(io.StringIO(src).readline):
            if t.type == tokenize.COMMENT:
                a, b = span(t)
                blank(full, a, b)
                blank(nocomment, a, b)
            elif t.type == tokenize.STRING or t.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
                a, b = span(t)
                blank(full, a, b)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    return "".join(full), "".join(nocomment)


def masks(rel, src):
    lang = EXT_LANG.get(os.path.splitext(rel)[1])
    if lang == "py":
        return py_masks(src)
    if lang in ("js", "go", "rs", "jvm"):
        return mask_clike(src, lang), mask_clike(src, lang, strings=False)
    return src, src


def line_starts(text):
    s = [0]
    for m in re.finditer("\n", text):
        s.append(m.end())
    return s


def lineno(starts, idx):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= idx:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


# --------------------------------------------------------------------------- symbols

def js_extent(masked, start):
    """End index of the top-level statement starting at `start`."""
    depth, i, n = 0, start, len(masked)
    while i < n:
        c = masked[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "\n" and depth <= 0:
            before = masked[start:i].rstrip()
            after = masked[i + 1:i + 200].lstrip()
            if before and before[-1] in "=,(+-*/?:|&" or before.endswith("=>") or (after and after[0] in "|&.?:+-*/=,)>"):
                i += 1
                continue
            return i
        i += 1
    return n


def js_symbols(rel, src, masked):
    starts = line_starts(src)
    out, seen = [], set()

    def add(name, kind, idx, default=False):
        if name in seen:
            return
        seen.add(name)
        end = js_extent(masked, idx)
        if kind in ("const", "let", "var"):
            rhs = re.search(r"\b%s\s*(?::[^=]+)?=\s*" % re.escape(name), masked[idx:idx + 600])
            tail = masked[idx + rhs.end():idx + rhs.end() + 200] if rhs else ""
            # a function value, or a wrapper returning one; anything else (tables, config, lookup
            # objects) is declarative data with no code path to cover
            kind = "function" if re.match(JS_FN_RHS, tail) else "value"
        out.append({"name": name, "kind": kind, "file": rel, "line": lineno(starts, idx),
                    "end_line": lineno(starts, max(idx, end - 1)), "owner": None, "decorated": False,
                    "default_export": default})

    for m in JS_EXPORT_DEF.finditer(masked):
        kind = re.sub(r"\s+", " ", m.group(2)).replace("abstract class", "class").replace("const enum", "enum").rstrip("*")
        add(m.group(3), kind, m.start(), default=bool(m.group(1)))
    local = []
    for m in JS_EXPORT_LIST.finditer(masked):
        if m.group(2):
            continue  # a re-export: defined elsewhere
        for part in m.group(1).split(","):
            nm = part.strip().split(" as ")[0].strip().replace("type ", "")
            if nm:
                local.append(nm)
    defaults = {m.group(1) for m in JS_EXPORT_DEFAULT_NAME.finditer(masked)}
    for nm in local + sorted(defaults):
        d = re.search(JS_LOCAL_DEF % re.escape(nm), masked, re.M)
        if d:
            kw = re.match(r"[ \t]*(?:async\s+)?(function|const|let|var|class|enum|interface|type)", masked[d.start():]).group(1)
            add(nm, kw, d.start(), default=nm in defaults)
    return out


def py_symbols(rel, src):
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return []
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
            first = min([d.lineno for d in node.decorator_list] + [node.lineno])
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            if kind == "class" and not any(isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and not
                                           (b.name.startswith("__") and b.name.endswith("__")) for b in node.body):
                kind = "value"  # an ORM model, dataclass, enum or settings shape: columns, no logic
            route = None
            for d in node.decorator_list:
                # @app.post("/slack/interactions"): tests reach it by URL through a test client
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.args and \
                        isinstance(d.args[0], ast.Constant) and isinstance(d.args[0].value, str) and \
                        d.func.attr in ("get", "post", "put", "patch", "delete", "route", "api_route", "websocket"):
                    route = d.args[0].value
            out.append({"name": node.name, "kind": kind,
                        "file": rel, "line": first, "end_line": node.end_lineno, "owner": None,
                        "decorated": bool(node.decorator_list), "route": route})
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and not sub.name.startswith("_"):
                        f2 = min([d.lineno for d in sub.decorator_list] + [sub.lineno])
                        deco = [d for d in sub.decorator_list if not (isinstance(d, ast.Name) and d.id in ("staticmethod", "classmethod", "property"))]
                        out.append({"name": sub.name, "kind": "method", "file": rel, "line": f2,
                                    "end_line": sub.end_lineno, "owner": node.name, "decorated": bool(deco)})
    return out


# --------------------------------------------------------------------------- per-file facts

def import_lines(rel, src):
    lang = EXT_LANG.get(os.path.splitext(rel)[1])
    lines, reexport = set(), set()
    if lang == "js":
        st = line_starts(src)
        for m in JS_IMPORT_STMT.finditer(src):
            a, b = lineno(st, m.start()), lineno(st, m.end())
            target = reexport if m.group(1) == "export" else lines
            target.update(range(a, b + 1))
    elif lang == "py":
        try:
            for node in ast.walk(ast.parse(src)):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    lines.update(range(node.lineno, node.end_lineno + 1))
        except (SyntaxError, ValueError):
            pass
    return lines, reexport


def js_mock_facts(src, masked, resolver, rel):
    """{module_path: None (whole module) | set(names in a partial factory)}, spied names, mocked() names."""
    modules = {}
    for m in re.finditer(r"""\b(?:vi|jest)\s*\.\s*(?:mock|doMock)\s*\(\s*(["'])([^"'\n]+)\1""", src):
        if masked[m.start()] != src[m.start()]:
            continue
        target = resolver.js(rel, m.group(2))
        if not target:
            continue
        paren = src.index("(", m.start())
        close = match_close(masked, paren)
        factory = masked[paren:close] if close > 0 else ""
        if re.search(r"importOriginal|importActual|requireActual|\borig\w*\s*\(", factory):
            modules[target] = set(IDENT.findall(factory))
        else:
            modules[target] = None
    spied = set(re.findall(r"""spyOn\s*\(\s*[\w$.]+\s*,\s*["']([\w$]+)["']""", src))
    mocked = set(re.findall(r"""\b(?:vi|jest)\s*\.\s*mocked\s*\(\s*([\w$]+)""", masked))
    return modules, spied | mocked


PY_PATCH_STR = re.compile(r"""\b(?:patch(?:\.object)?|mocker\.patch(?:\.object)?|monkeypatch\.setattr)\s*\(\s*(?:[\w.\[\]"']+\s*,\s*)?["']([\w.]+)["']""")


def py_patch_facts(src):
    """[(line, patched_name)] — the last component of every patch target string."""
    st = line_starts(src)
    return [(lineno(st, m.start()), m.group(1).rsplit(".", 1)[-1]) for m in PY_PATCH_STR.finditer(src)]


def py_fixture_patches(src):
    """{fixture_name: set(patched names)} for @pytest.fixture functions in a file."""
    out = {}
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return out
    lines = src.split("\n")
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                "fixture" in ast.unparse(d) for d in node.decorator_list):
            body = "\n".join(lines[node.lineno - 1:node.end_lineno])
            names = {n for _, n in py_patch_facts(body)}
            if names:
                out[node.name] = names
    return out


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--test-bodies", required=True)
    ap.add_argument("--leverage", required=True)
    ap.add_argument("--time-budget", type=float, default=600.0)
    a = ap.parse_args()
    repo = os.path.realpath(a.repo)
    out = os.path.realpath(a.out)
    if os.path.commonpath([repo, out]) == repo:
        sys.exit("refusing to write inside the scanned repo: %s" % out)
    os.makedirs(out, exist_ok=True)
    t0 = time.time()
    deadline = t0 + a.time_budget
    partial = []

    with open(a.leverage, encoding="utf-8") as fh:
        lev = json.load(fh)
    lev_files = {r["file"]: r for r in lev["files"]}
    rows_by_file = {}
    with open(a.test_bodies, encoding="utf-8") as fh:
        for l in fh:
            r = json.loads(l)
            rows_by_file.setdefault(r["file"], []).append(r)

    tracked = [p for p in git(repo, "ls-files", "-z").split("\0") if p]
    code = [p for p in tracked if is_code(p)]
    resolver = Resolver(repo, tracked)
    srcs = {}
    for rel in code:
        try:
            with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                srcs[rel] = fh.read()
        except OSError:
            pass

    # symbols in scope
    symbols = []
    mask_cache = {}
    for rel in lev_files:
        src = srcs.get(rel)
        if src is None:
            continue
        mask_cache[rel] = masks(rel, src)
        lang = EXT_LANG.get(os.path.splitext(rel)[1])
        if lang == "js":
            symbols += js_symbols(rel, src, mask_cache[rel][0])
        elif lang == "py":
            symbols += py_symbols(rel, src)
    names = {s["name"] for s in symbols}
    defs_at = {(s["file"], s["line"], s["name"]) for s in symbols}
    def_lines = {}
    for s in symbols:
        # the definition line itself (after decorators) is not a reference
        src_lines = srcs[s["file"]].split("\n")
        for ln in range(s["line"], min(s["end_line"], s["line"] + 6) + 1):
            if re.search(r"\b(def|class|function|const|let|var|enum|interface|type)\s+%s\b" % re.escape(s["name"]), src_lines[ln - 1]):
                def_lines.setdefault(s["file"], set()).add((ln, s["name"]))
                break

    # barrels: module -> files that re-export it (transitively)
    reexporters = {}
    for rel, src in srcs.items():
        if EXT_LANG.get(os.path.splitext(rel)[1]) != "js":
            continue
        for m in JS_REEXPORT.finditer(src):
            t = resolver.js(rel, m.group(2))
            if t:
                reexporters.setdefault(t, set()).add(rel)

    def aliases(path):
        seen, todo = {path}, [path]
        while todo:
            for r in reexporters.get(todo.pop(), ()):
                if r not in seen:
                    seen.add(r)
                    todo.append(r)
        return seen

    # identifier index: occ[name] -> [(file, line, kind, attr)]
    occ = {}
    strings = {}  # name -> {prod_file: n} occurrences inside strings in production files
    test_facts = {}
    scanned = 0
    for rel, src in srcs.items():
        if time.time() > deadline:
            partial.append({"category": "reference_index", "scanned": scanned, "total": len(srcs),
                            "reason": "time budget of %ss exhausted" % a.time_budget})
            break
        scanned += 1
        full, nocomment = mask_cache.get(rel) or masks(rel, src)
        st = line_starts(src)
        imp, reexp = import_lines(rel, src)
        test = is_test_path(rel)
        for m in IDENT.finditer(full):
            nm = m.group(0)
            if nm not in names:
                continue
            ln = lineno(st, m.start())
            if (ln, nm) in def_lines.get(rel, ()):
                continue
            j = m.end()
            while j < len(full) and full[j] in " \t":
                j += 1
            if j < len(full) and full[j] == "<" and not test or (j < len(full) and full[j] == "<" and re.match(r"<[\w$\s,.\[\]|&]*>\s*\(", full[j:j + 120])):
                g = re.match(r"<[^<>()]*>\s*", full[j:j + 120])
                if g:
                    j += g.end()
            before = full[max(0, m.start() - 5):m.start()]
            if ln in reexp:
                kind = "reexport"
            elif ln in imp:
                kind = "import"
            elif j < len(full) and full[j] == "(" or re.search(r"\bnew\s+$", before) or before.endswith("<") or before.endswith("@"):
                kind = "call"
            else:
                kind = "mention"
            occ.setdefault(nm, []).append((rel, ln, kind, before.rstrip().endswith(".")))
        if not test:
            if nocomment is not full:
                for m in IDENT.finditer(nocomment):
                    nm = m.group(0)
                    if nm in names and full[m.start():m.end()] != nm:
                        strings.setdefault(nm, {}).setdefault(rel, 0)
                        strings[nm][rel] += 1
        else:
            imps, _, _ = file_imports(rel, src, resolver)
            facts = {"imports": imps}
            if EXT_LANG.get(os.path.splitext(rel)[1]) == "js":
                facts["mocked_modules"], facts["mocked_names"] = js_mock_facts(src, full, resolver, rel)
            else:
                facts["patches"] = py_patch_facts(src)
                facts["fixture_patches"] = py_fixture_patches(src)
                facts["mentions_class"] = set(IDENT.findall(full))
            test_facts[rel] = facts

    conftest_patches = {}
    for rel, src in srcs.items():
        if rel.endswith("conftest.py"):
            conftest_patches[os.path.dirname(rel)] = py_fixture_patches(src)

    def fixture_patches_for(test_file):
        merged = dict(test_facts.get(test_file, {}).get("fixture_patches", {}))
        d = os.path.dirname(test_file)
        while True:
            for k, v in conftest_patches.get(d, {}).items():
                merged.setdefault(k, v)
            if not d:
                break
            d = os.path.dirname(d)
        return merged

    def row_of(test_file, ln):
        for r in rows_by_file.get(test_file, ()):
            if r.get("start_line", r["line"]) <= ln <= r["end_line"]:
                return r
        return None

    by_name_file = {}
    for s in symbols:
        by_name_file.setdefault(s["name"], []).append(s)
    entry_files = {f for f, r in lev_files.items() if r["entry_point"]}
    fan = sorted(r["fan_in"] for r in lev_files.values()) or [0]
    floor = lev.get("fan_in_floor_for_entry_points", 3)

    results = []
    row_symbols = {}  # (test_file, row_line) -> set(symbol ids called)
    for s in symbols:
        sid = "%s:%s%s" % (s["file"], (s["owner"] + ".") if s["owner"] else "", s["name"])
        s["id"] = sid
        s["lines"] = s["end_line"] - s["line"] + 1
        mod_aliases = aliases(s["file"])
        prod_files, prod_imports, test_hits = {}, 0, {}
        for (rel, ln, kind, attr) in occ.get(s["name"], ()):
            if is_test_path(rel):
                test_hits.setdefault(rel, []).append((ln, kind, attr))
                continue
            if kind == "reexport":
                continue
            if kind == "import":
                prod_imports += 1
                continue
            if s["kind"] == "method" and rel != s["file"] and not attr:
                continue  # a bare name elsewhere is not this method
            prod_files[rel] = prod_files.get(rel, 0) + 1
        string_refs = sum(strings.get(s["name"], {}).values())
        call_rows, mock_rows, mention_rows, name_only = [], [], [], 0
        for tf, hits in test_hits.items():
            facts = test_facts.get(tf, {})
            visible = bool(mod_aliases & facts.get("imports", set()))
            if s["kind"] == "method":
                visible = visible or s["owner"] in facts.get("mentions_class", set())
            mm = facts.get("mocked_modules", {})
            file_mocked = any(p in mm and (mm[p] is None or s["name"] in mm[p]) for p in mod_aliases) \
                or s["name"] in facts.get("mocked_names", set())
            fpatch = fixture_patches_for(tf) if tf.endswith(".py") else {}
            patch_lines = [ln for ln, nm in facts.get("patches", []) if nm == s["name"]]
            per_row = {}
            for ln, kind, attr in hits:
                if kind in ("import", "reexport"):
                    continue
                r = row_of(tf, ln)
                key = (r["line"] if r else None)
                per_row.setdefault(key, {"row": r, "kinds": set()})["kinds"].add(kind)
            for key, info in per_row.items():
                r = info["row"]
                mocked = file_mocked
                if r is not None and not mocked:
                    lo, hi = r.get("start_line", r["line"]), r["end_line"]
                    mocked = any(lo <= pl <= hi for pl in patch_lines) or any(
                        s["name"] in fpatch.get(fx, ()) for fx in r.get("fixtures", []))
                elif r is None and patch_lines:
                    mocked = True
                ref = {"file": tf, "line": r["line"] if r else None, "end_line": r["end_line"] if r else None,
                       "name": r["name"] if r else None}
                if mocked:
                    mock_rows.append(ref)
                elif "call" in info["kinds"] and visible:
                    call_rows.append(ref)
                    if r:
                        row_symbols.setdefault((tf, r["line"]), set()).add(sid)
                elif "call" in info["kinds"]:
                    name_only += 1
                else:
                    mention_rows.append(ref)
        route_tests = []
        if s.get("route"):
            stem = re.escape(s["route"].split("{")[0].rstrip("/"))
            # any path prefix: an APIRouter(prefix="/gmail") route "/webhook" is called as "/gmail/webhook"
            rx = re.compile(r"""\.(get|post|put|patch|delete|request|websocket_connect)\(\s*f?["'][^"'\s]*%s(["'?/{]|$)""" % stem)
            route_tests = sorted(tf for tf in test_facts if rx.search(srcs.get(tf, "")))
        if call_rows or route_tests:
            status = "covered"  # by a direct call, or by URL through a test client
        elif mock_rows:
            status = "mock_only"
        elif name_only:
            status = "name_only"
        elif mention_rows:
            status = "mention_only"
        else:
            status = "untested"
        src_lines = srcs[s["file"]].split("\n")
        sec = security_lines("\n".join(src_lines[s["line"] - 1:s["end_line"]]))
        lf = lev_files.get(s["file"], {})
        reached_from_entry = s["file"] in entry_files or any(f in entry_files for f in prod_files)
        fan_in = lf.get("fan_in", 0)
        eff = max(fan_in, floor) if reached_from_entry else fan_in
        density = min(1.0, sec / max(s["lines"], DENSITY_FLOOR_LOC))
        leverage = (1 + math.log10(lf.get("churn", 0) + 1)) * (1 + math.log10(eff + 1))
        prio = density * leverage
        results.append(dict(s, prod_refs=sum(prod_files.values()), prod_ref_files=sorted(prod_files)[:10],
                            test_route_files=route_tests[:10], leverage=round(leverage, 4),
                            prod_string_refs=string_refs, prod_import_refs=prod_imports,
                            test_status=status, test_call_rows=call_rows[:20], test_mock_rows=mock_rows[:20],
                            test_mention_rows=mention_rows[:10],
                            test_name_only_hits=name_only, reached_from_entry_point=reached_from_entry,
                            security_lines=sec, priority=round(prio, 4),
                            gap_lines=0 if status == "covered" or s["kind"] in TYPE_KINDS else s["lines"]))

    # a class with public methods is graded through them: covered if it or any method is, and
    # its own gap is 0 so the methods' gaps are not counted twice
    for r in results:
        if r["kind"] != "class":
            continue
        methods = [m for m in results if m["owner"] == r["name"] and m["file"] == r["file"]]
        if not methods:
            continue
        r["gap_lines"] = 0
        if r["test_status"] != "covered" and any(m["test_status"] == "covered" for m in methods):
            r["test_status"] = "covered"

    # ---------------------------------------------------------------- life support
    by_id = {r["id"]: r for r in results}
    live = [r for r in results if r["prod_refs"] > 0 and r["kind"] not in TYPE_KINDS]
    life = []
    for r in results:
        if r["kind"] in TYPE_KINDS or r["test_status"] != "covered" or r["prod_refs"] or r["prod_string_refs"]:
            continue
        if r["decorated"] or (r["file"] in entry_files and (r["name"] in NEXT_RESERVED or r.get("default_export"))):
            continue  # framework-invoked: the router calls it by file convention
        if r["name"].startswith("_"):
            continue  # a deliberate test seam (__setClient) or private by convention
        rows, exclusive = [], []
        for c in r["test_call_rows"]:
            if c["line"] is None:
                continue
            row = next((x for x in rows_by_file.get(c["file"], ()) if x["line"] == c["line"]), None)
            if not row:
                continue
            rows.append(c)
            others = {o for o in row_symbols.get((c["file"], c["line"]), set()) if o != r["id"]
                      and not (r["owner"] and by_id.get(o, {}).get("name") == r["owner"])}
            if not others:
                exclusive.append(dict(c, body_lines=row["body_lines"]))
        if not rows:
            continue
        succ, evidence, how = successor(repo, r, live, srcs)
        if succ and succ["file"] in entry_files and succ.get("default_export"):
            succ, evidence, how = None, None, None  # a page component is not a successor for a helper
        # a non-exclusive caller in ANOTHER module's test file uses it as a test helper (a guard test
        # importing scripts/lib/record.ts), which is test-support code, not dead code
        own_stem = os.path.splitext(os.path.basename(r["file"]))[0]
        excl = {(x["file"], x["line"]) for x in exclusive}
        helper_use = sorted({c["file"] for c in rows if (c["file"], c["line"]) not in excl and re.sub(
            r"\.(test|spec)$|^test_", "", os.path.splitext(os.path.basename(c["file"]))[0]) != own_stem})
        life.append({
            "symbol": r["id"], "file": r["file"], "line": r["line"], "end_line": r["end_line"],
            "symbol_lines": r["lines"], "prod_refs": 0, "prod_import_refs": r["prod_import_refs"],
            "test_rows": rows, "exclusive_rows": exclusive,
            "used_as_test_helper_in": helper_use,
            # with a successor the tests MOVE (they survive): only the symbol is deleted. Test-support
            # use means nothing is deletable until the helper moves to a test-support file
            "deletable_lines": 0 if helper_use else r["lines"] + (0 if succ else sum(x["body_lines"] for x in exclusive)),
            "successor": succ["id"] if succ else None,
            "successor_status": succ["test_status"] if succ else None,
            "successor_evidence": evidence,
            "successor_kind": how,
        })

    modules = module_ratios(results, lev_files, row_symbols, test_facts, srcs)
    # most symbols carry no security words and tie at priority 0 (S65: 128 of 147 on maxitech), so
    # leverage x log(gap size) breaks the tie instead of file order
    results.sort(key=lambda r: (-r["priority"], -r["leverage"] * math.log10(r["gap_lines"] + 1)))
    counts = {}
    for r in results:
        if r["kind"] not in TYPE_KINDS:
            counts[r["test_status"]] = counts.get(r["test_status"], 0) + 1
    result = {
        "repo": repo,
        "reference_rule": "word-bounded identifier index over every tracked code file; comments never "
                          "count; the definition line, import and re-export lines are not references; "
                          "string occurrences are counted separately (prod_string_refs)",
        "symbols": results, "status_counts": counts, "life_support": life, "modules": modules,
        "coverage_partial": partial, "elapsed_s": round(time.time() - t0, 2),
    }
    path = os.path.join(out, "references.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"symbols": len(results), "status_counts": counts, "life_support": len(life),
                      "partial": bool(partial), "elapsed_s": result["elapsed_s"]}))
    print("references=%s" % path)


def module_ratios(results, lev_files, row_symbols, test_facts, srcs):
    """test:code LOC per module (problem 7), attributing each test file by what it CALLS.

    Each test file counts toward the module whose symbols its tests call most (one vote per
    test row per symbol). Imports are only the fallback: a pipeline test imports models to build
    fixtures but calls the handler, and import votes sent it to models (S65 rerun). A test that
    neither calls nor imports anything local is unattributed, never guessed.
    """
    by_id = {r["id"]: r for r in results}
    code = {}
    for f, r in lev_files.items():
        if CONFIG_LIKE.search(f):
            continue
        m = module_of(f)
        code[m] = code.get(m, 0) + r["loc"]
    calls = {}
    for (tf, _line), sids in row_symbols.items():
        for sid in sids:
            m = module_of(by_id[sid]["file"])
            calls.setdefault(tf, {}).setdefault(m, 0)
            calls[tf][m] += 1
    tests, files, unattributed, by_import = {}, {}, 0, 0
    for tf, facts in test_facts.items():
        loc = srcs.get(tf, "").count("\n")
        votes = calls.get(tf)
        if not votes:
            votes = {}
            for p in facts.get("imports", ()):
                if p in lev_files and not CONFIG_LIKE.search(p):
                    votes[module_of(p)] = votes.get(module_of(p), 0) + 1
            if votes:
                by_import += 1
        if not votes:
            unattributed += loc
            continue
        m = max(sorted(votes), key=lambda k: votes[k])
        tests[m] = tests.get(m, 0) + loc
        files[m] = files.get(m, 0) + 1
    rows = [{"module": m, "code_loc": code.get(m, 0), "test_loc": tests.get(m, 0), "test_files": files.get(m, 0),
             "ratio": round(tests.get(m, 0) / max(code.get(m, 0), 1), 3)} for m in sorted(set(code) | set(tests))]
    return {"rows": rows, "unattributed_test_loc": unattributed, "attributed_by_import_only": by_import,
            "rule": "each test file counts toward the module whose symbols its tests call most, else the one it "
                    "imports most; config/schema/types/migration files are excluded from code_loc; compare "
                    "ratio as given (3 decimals), never rounded further"}


# git pathspecs that keep -S on code: doc and changelog edits mention a name without calling it
CODE_ONLY = [":(exclude)*.md", ":(exclude)*.txt", ":(exclude)*.json", ":(exclude)docs"]


def stem_similarity(a, b):
    mine, theirs = set(subwords(a)), set(subwords(b))
    return len(mine & theirs) / len(mine | theirs) if mine and theirs else 0.0


def successor(repo, r, live, srcs):
    """Most likely replacement for a life-support symbol, strongest evidence first.

    1. caller switched: a commit that removed a production reference to the symbol added, in the
       same file, a reference to a live symbol (the spec's "shared caller that moved");
    2. named in its own doc comment ("SQL twin of `needsAttentionSql`", "replaced by X");
    3. a thin wrapper (<= 15 lines) whose body calls a live symbol: its tests exercise that symbol;
    4. a shared name stem (Jaccard of sub-words >= 0.6, same first word).
    Stem alone at 0.5 named a sibling instead of the replacement on horowell (S65 rerun), so it is
    last and stricter. Returns (successor_row, evidence, kind).
    """
    by_name = {}
    for c in live:
        if c["id"] != r["id"] and c["kind"] in ("function", "method", "class"):
            by_name.setdefault(c["name"], c)
    if not by_name:
        return None, None, None
    pat = re.compile(r"\b%s\b" % re.escape(r["name"]))
    try:
        shas = subprocess.run(["git", "-C", repo, "log", "-S", r["name"], "--format=%H", "-n", "3", "--", "."] + CODE_ONLY,
                              capture_output=True, timeout=30).stdout.decode().split()
        for sha in shas[:3]:
            diff = subprocess.run(["git", "-C", repo, "show", "-U0", "--format=", sha],
                                  capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
            removed_call, added = None, {}
            for chunk in re.split(r"^diff --git ", diff, flags=re.M)[1:]:
                path = chunk.split("\n")[0].split(" b/")[-1]
                if is_test_path(path) or not is_code(path):
                    continue
                lines = chunk.split("\n")
                minus = "\n".join(l[1:] for l in lines if l.startswith("-") and not l.startswith("---"))
                plus = "\n".join(l[1:] for l in lines if l.startswith("+") and not l.startswith("+++"))
                if path != r["file"] and pat.search(minus):
                    removed_call = removed_call or path  # a production caller dropped the symbol here
                # candidates the commit newly CALLS anywhere in code (a local variable never qualifies)
                for m in re.finditer(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(", plus):
                    nm = m.group(1)
                    if nm in by_name and not re.search(r"\b%s\s*\(" % re.escape(nm), minus):
                        added[nm] = added.get(nm, 0) + 1
            # the replacement shares a name stem; an unrelated helper the commit also calls does not
            ranked = sorted((k for k in added if stem_similarity(k, r["name"]) >= 0.4),
                            key=lambda k: (-stem_similarity(k, r["name"]), -added[k], k))
            if removed_call and ranked:
                return by_name[ranked[0]], "caller switched in %s (%s)" % (sha[:8], removed_call), "caller_switched"
    except (subprocess.SubprocessError, OSError):
        pass
    src = srcs.get(r["file"], "").split("\n")
    doc = "\n".join(src[max(0, r["line"] - 13):r["end_line"]])
    for nm in re.findall(r"`([A-Za-z_$][\w$]*)`", doc):
        if nm in by_name and nm != r["name"]:
            return by_name[nm], "named in its doc comment", "doc_comment"
    # a twin named in a plain comment ("the SQL twin stuckLeadSql"), when it shares the name stem
    comments = "\n".join(l for l in src[max(0, r["line"] - 13):r["end_line"]]
                         if re.match(r"\s*(//|/?\*|#)", l))
    for nm in IDENT.findall(comments):
        if nm in by_name and nm != r["name"] and stem_similarity(nm, r["name"]) >= 0.4:
            return by_name[nm], "named in its doc comment", "doc_comment"
    if r["lines"] <= 15:
        body = "\n".join(src[r["line"]:r["end_line"]])
        for nm in IDENT.findall(body):
            # a ubiquitous utility (getDb, cn) is plumbing, not the logic the tests exercise
            if nm in by_name and nm != r["name"] and by_name[nm]["prod_refs"] < 15 \
                    and stem_similarity(nm, r["name"]) >= 0.3:  # composing a helper is not wrapping it
                return by_name[nm], "thin wrapper: its body calls live `%s`" % nm, "wrapper"
    best, score = None, 0.0
    first = next(iter(subwords(r["name"])), None)
    for nm, c in by_name.items():
        if next(iter(subwords(nm)), None) != first:
            continue
        j = stem_similarity(nm, r["name"])
        if j > score:
            best, score = c, j
    if best and score >= 0.6:
        return best, "shared name stem (%.2f)" % score, "stem"
    return None, None, None


if __name__ == "__main__":
    main()
