#!/usr/bin/env python3
"""leverage.py — per-file leverage and git-history signals for /bx:tests coverage + economics.

The mechanism behind priority ranking (spec D1, problems 5, 6, 7, 9, 16, 19, 20, 21, 32 in
docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md). Scanners read its JSON and judge
it; they do not recompute churn, fan-in or keyword density by hand.

Read-only. Runs git (log, ls-files, ls-tree, cat-file, rev-list) and reads files; writes only
into --out, which must be outside the repo.

Usage:
    python -I bx/skills/tests/scripts/leverage.py --repo <path> --out <dir>
        [--source-files <list.txt>]  production files in scope, repo-relative (default: every
                                     tracked code file that is not a test or test support)
        [--bugfix-window 200]        commits scanned for fix subjects (then filtered)
        [--growth-points 6]          monthly points for the test/source trend (0 disables)
        [--time-budget <secs>]       stop early and report the rest as partial (default 600)

Writes <out>/leverage.json:
    files[]     {file, loc, churn, fan_in, importers[<=10], test_importers[], test_mockers[],
                 entry_point, entry_reason, security_lines, security_density, priority}
                fan_in counts production files whose imports RESOLVE to this path (relative,
                tsconfig/vite aliases, Python dotted and relative modules), never basenames.
                test_importers are the test files that import it — the neighbour lookup.
                test_mockers are the test files that mock it (vi.mock / jest.mock / patch).
    priority_formula, fan_in_floor_for_entry_points
    bugfix_commits[]  {sha, subject, files[], touched_tests}  window: the last N commits
    flake_commits[]   {sha, subject, files[]}
    growth[]          {date, commit, test_loc, source_loc, ratio, test_case_lines}
    unresolved_local_imports, coverage_partial[]
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import date, timedelta

sys.dont_write_bytecode = True  # never leave __pycache__ in the skill (or the plugin cache)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_bodies import EXT_LANG, PRUNE, mask_clike  # noqa: E402

JS_EXTS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")
TEST_PATH = re.compile(
    r"(\.(test|spec)\.[cm]?[jt]sx?$)|(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py)$|_test\.go$"
    r"|(Test|Tests|IT)\.(java|kt)$|\.bats$|(^|/)test-[^/]*\.(sh|bash)$|\.Tests\.ps1$"
    r"|(^|/)(tests?|__tests__|__mocks__|e2e|testing|test-utils|fixtures|__fixtures__|spec)/"
    r"|\.(fixture|mock|mocks|stories)\.[cm]?[jt]sx?$|(^|/)(vitest|jest|playwright)\.[^/]*config\.[^/]+$"
)
ENTRY_POINTS = [
    (re.compile(r"(^|/)app/(.*/)?(page|layout|route|loading|error|global-error|not-found|template|default)\.[jt]sx?$"), "next app router file"),
    (re.compile(r"(^|/)pages/(?!_).*\.[jt]sx?$|(^|/)pages/api/"), "next pages router file"),
    (re.compile(r"(^|/)(src/)?(middleware|proxy|instrumentation)\.[jt]s$"), "next middleware/proxy"),
    (re.compile(r"(^|/)(main|manage|wsgi|asgi|app|server|cli|__main__)\.py$"), "python entry module"),
    (re.compile(r"(^|/)(cmd/[^/]+/)?main\.go$|(^|/)src/(main|bin/[^/]+)\.rs$"), "binary entry"),
]
PY_ENTRY_DECORATOR = re.compile(r"^\s*@\s*\w+\.(get|post|put|patch|delete|options|head|route|api_route|websocket|on_event|middleware|exception_handler|task|command)\s*\(", re.M)
PY_MAIN_GUARD = re.compile(r"""^if\s+__name__\s*==\s*['"]__main__['"]""", re.M)

# Security vocabulary (problem 20). Matched on identifier SUB-WORDS, so verifySignature and
# verify_signature both hit `verify` and `signature`; `Snowflake`-style substrings never do.
SECURITY_STRONG = {
    "auth", "authenticate", "authentication", "authorize", "authorization", "authz", "authn",
    "password", "passwd", "token", "tokens", "crypto", "permission",
    "permissions", "payment", "payments", "charge", "refund", "secret", "secrets", "signature",
    "signed", "hmac", "webhook", "jwt", "oauth", "nonce", "replay", "csrf", "xss", "sanitize",
    "escape", "encrypt", "decrypt", "verify", "validate", "sql", "injection", "credential",
    "credentials", "cookie", "cookies", "bearer", "login", "logout", "otp", "totp", "rbac", "acl",
}
# generic words count only on a line that also carries a strong word ("key" alone is an enum key)
# ("session" is a DB session as often as a login session)
SECURITY_GENERIC = {"key", "keys", "role", "roles", "hash", "sign", "admin", "scope", "scopes", "session", "sessions"}
DENSITY_FLOOR_LOC = 20


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    if check and r.returncode:
        raise RuntimeError("git %s failed: %s" % (" ".join(args[:3]), r.stderr.decode("utf-8", "replace")[:300]))
    return r.stdout.decode("utf-8", "replace")


def is_test_path(rel):
    return bool(TEST_PATH.search(rel))


def is_code(rel):
    lang = EXT_LANG.get(os.path.splitext(rel)[1])
    return lang in ("js", "py", "go", "rs", "jvm") and not rel.endswith(".d.ts") and not PRUNE.search(rel)


def subwords(text):
    for ident in re.findall(r"[A-Za-z][A-Za-z0-9]*", text):
        for w in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+", ident):
            yield w.lower()


def security_lines(src):
    hits = 0
    for line in src.split("\n"):
        words = set(subwords(line))
        if words & SECURITY_STRONG:
            hits += 1  # a generic word on the same line adds nothing: the line already counts
    return hits


# --------------------------------------------------------------------------- import resolution

def strip_json_comments(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r'(^|[^:"\\])//[^\n]*', r"\1", text)
    return re.sub(r",(\s*[}\]])", r"\1", text)


class Resolver:
    """Resolve import specifiers to tracked repo paths."""

    def __init__(self, repo, tracked):
        self.repo = repo
        self.tracked = set(tracked)
        self.aliases = []  # (prefix, [target_dirs]) longest first
        self._load_aliases()
        roots = [""]
        for d in ("src", "lib", "app"):
            if any(p.startswith(d + "/") and p.endswith(".py") for p in self.tracked):
                roots.append(d + "/")
        self.py_roots = roots

    def _load_aliases(self):
        for cfg in sorted(p for p in self.tracked if re.search(r"(^|/)(ts|js)config(\.[\w-]+)?\.json$", p)):
            try:
                with open(os.path.join(self.repo, cfg), encoding="utf-8") as fh:
                    data = json.loads(strip_json_comments(fh.read()))
            except (OSError, ValueError):
                continue
            opts = data.get("compilerOptions", {}) if isinstance(data, dict) else {}
            base = os.path.normpath(os.path.join(os.path.dirname(cfg), opts.get("baseUrl", "."))).replace("\\", "/")
            for pat, targets in (opts.get("paths") or {}).items():
                prefix = pat.rstrip("*")
                dirs = []
                for t in targets:
                    dirs.append(os.path.normpath(os.path.join(base, t.rstrip("*"))).replace("\\", "/").lstrip("./") if t.rstrip("*") not in (".", "./") else "")
                self.aliases.append((prefix, dirs))
        for cfg in (p for p in self.tracked if re.search(r"(^|/)(vite|vitest)\.config\.[cm]?[jt]s$", p)):
            try:
                with open(os.path.join(self.repo, cfg), encoding="utf-8") as fh:
                    src = fh.read()
            except OSError:
                continue
            for m in re.finditer(r"""["']?([@~#$][\w/-]*)["']?\s*:\s*(?:path\.)?(?:resolve|join)\(\s*__dirname\s*,\s*["']([^"']+)["']""", src):
                self.aliases.append((m.group(1).rstrip("/") + "/", [os.path.normpath(os.path.join(os.path.dirname(cfg), m.group(2))).replace("\\", "/")]))
        self.aliases.sort(key=lambda a: -len(a[0]))

    def _js_candidates(self, base):
        base = base.replace("\\", "/")
        if base.startswith("./"):
            base = base[2:]
        stem = re.sub(r"\.(js|jsx|mjs|cjs)$", "", base)
        yield base
        for b in (base, stem):
            for e in JS_EXTS:
                yield b + e
            for e in JS_EXTS:
                yield b + "/index" + e

    def js(self, importer, spec):
        if spec.startswith("."):
            bases = [os.path.normpath(os.path.join(os.path.dirname(importer), spec)).replace("\\", "/")]
        else:
            bases = []
            for prefix, dirs in self.aliases:
                if spec.startswith(prefix) or spec + "/" == prefix:
                    rest = spec[len(prefix):]
                    bases = [(d + "/" + rest).strip("/") if d else rest for d in dirs]
                    break
            if not bases:
                return None  # a package
        for b in bases:
            for c in self._js_candidates(b):
                if c in self.tracked:
                    return c
        return False  # local-looking but unresolved

    def py_module(self, module):
        """Dotted module -> path, or None."""
        parts = module.split(".")
        for root in self.py_roots:
            p = root + "/".join(parts)
            for c in (p + ".py", p + "/__init__.py"):
                if c in self.tracked:
                    return c
        return None

    def py(self, importer, module, names, level):
        """Paths imported by `from <module> import names` (level = leading dots) or `import module`."""
        if level:
            pkg = os.path.dirname(importer).replace("\\", "/").split("/") if os.path.dirname(importer) else []
            pkg = pkg[:len(pkg) - (level - 1)] if level > 1 else pkg
            module = ".".join([p for p in pkg if p] + ([module] if module else []))
        out = []
        if module:
            m = self.py_module(module)
            if m:
                out.append(m)
        for n in names or []:
            sub = self.py_module((module + "." if module else "") + n)
            if sub:
                out.append(sub)
        return out


JS_IMPORT = re.compile(r"""(?:\bimport\s+(?:type\s+)?(?:[\w*{}\s,$]+?\s+from\s+)?|\bexport\s+(?:type\s+)?(?:\*|\{[^}]*\})\s*(?:as\s+\w+\s+)?from\s+|\brequire\s*\(\s*|\bimport\s*\(\s*)(["'])([^"'\n]+)\1""")
JS_MOCK = re.compile(r"""\b(?:vi|jest)\s*\.\s*(?:mock|doMock|unmock)\s*\(\s*(["'])([^"'\n]+)\1""")
PY_PATCH = re.compile(r"""\b(?:patch|mocker\.patch|monkeypatch\.setattr)\s*\(\s*(["'])([\w.]+)\1""")


def js_imports(rel, src, resolver):
    masked = mask_clike(src, "js")
    imports, mocks, unresolved = set(), set(), 0
    for rx, bucket in ((JS_IMPORT, imports), (JS_MOCK, mocks)):
        for m in rx.finditer(src):
            if masked[m.start()] != src[m.start()]:
                continue  # inside a comment or string
            r = resolver.js(rel, m.group(2))
            if r:
                bucket.add(r)
            elif r is False:
                unresolved += 1
    return imports, mocks, unresolved


def py_imports(rel, src, resolver):
    import ast
    imports, mocks = set(), set()
    try:
        tree = ast.parse(src)
    except (SyntaxError, ValueError):
        return imports, mocks, 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imports.update(resolver.py(rel, a.name, None, 0))
        elif isinstance(node, ast.ImportFrom):
            imports.update(resolver.py(rel, node.module or "", [a.name for a in node.names], node.level))
    for m in PY_PATCH.finditer(src):
        target = m.group(2).rsplit(".", 1)[0]
        p = resolver.py_module(target)
        if p:
            mocks.add(p)
    return imports, mocks, 0


def file_imports(rel, src, resolver):
    lang = EXT_LANG.get(os.path.splitext(rel)[1])
    if lang == "js":
        return js_imports(rel, src, resolver)
    if lang == "py":
        return py_imports(rel, src, resolver)
    return set(), set(), 0


# --------------------------------------------------------------------------- git history

BUGFIX = re.compile(r"^(fix|bugfix|hotfix)\b|\b(fix(es|ed)?|close[sd]?|resolve[sd]?)\s+#\d+", re.I)
FLAKE = re.compile(r"\b(flak(e|es|y|iness)|deflake|intermittent(ly)?|non-?deterministic|race\s+in\s+test)\b", re.I)
TESTISH = re.compile(r"\b(tests?|specs?|e2e|ci|vitest|jest|pytest|playwright)\b", re.I)


def churn_and_history(repo, window):
    log = git(repo, "log", "--since=1 year ago", "--name-only", "--format=%x1e%H")
    churn = {}
    for block in log.split("\x1e")[1:]:
        for f in set(l for l in block.split("\n")[1:] if l.strip()):
            churn[f] = churn.get(f, 0) + 1
    recent = git(repo, "log", "-%d" % window, "--name-only", "--format=%x1e%H%x1f%s%x1f%b%x1f")
    bugfix, flake = [], []
    for block in recent.split("\x1e")[1:]:
        head, _, files = block.rpartition("\x1f")
        sha, subject, body = (head.split("\x1f") + ["", ""])[:3]
        files = [f for f in files.split("\n") if f.strip()]
        if BUGFIX.search(subject):
            bugfix.append({"sha": sha[:8], "subject": subject, "files": files[:20],
                           "touched_tests": any(is_test_path(f) for f in files)})
        text = subject + "\n" + body
        if FLAKE.search(text) and (TESTISH.search(text) or any(is_test_path(f) for f in files)):
            flake.append({"sha": sha[:8], "subject": subject, "files": files[:20]})
    return churn, bugfix, flake


CASE_LINE = re.compile(rb"^\s*(?:it|test)(?:\.\w+)*\s*[(`]|^\s*(?:async\s+)?def\s+test_|^\s*func\s+Test\w+\(|^\s*#\[(?:\w+::)?test\]", re.M)


def growth(repo, points, deadline):
    out = []
    head = git(repo, "rev-parse", "HEAD").strip()
    # anchor on the last commit, not today: an idle repo would repeat one commit at every point
    today = date.fromisoformat(git(repo, "log", "-1", "--format=%cs", head).strip())
    cache = {}
    for k in range(points - 1, -1, -1):
        if time.time() > deadline:
            break
        when = (today.replace(day=1) - timedelta(days=30 * k)) if k else today
        sha = git(repo, "rev-list", "-1", "--before=%s" % when.isoformat(), head).strip() if k else head
        if not sha:
            continue
        tree = git(repo, "ls-tree", "-r", sha)
        blobs = []
        for line in tree.split("\n"):
            m = re.match(r"\d+ blob ([0-9a-f]+)\t(.+)$", line)
            if m and is_code(m.group(2)):
                blobs.append((m.group(1), m.group(2)))
        need = [b for b, _ in blobs if b not in cache]
        if need:
            r = subprocess.run(["git", "-C", repo, "cat-file", "--batch"], input=("\n".join(need) + "\n").encode(), capture_output=True)
            data, i = r.stdout, 0
            for b in need:
                nl = data.index(b"\n", i)
                size = int(data[i:nl].split()[2])
                content = data[nl + 1:nl + 1 + size]
                cache[b] = (content.count(b"\n"), len(CASE_LINE.findall(content)))
                i = nl + 1 + size + 1
        t = sum(cache[b][0] for b, p in blobs if is_test_path(p))
        s = sum(cache[b][0] for b, p in blobs if not is_test_path(p))
        cases = sum(cache[b][1] for b, p in blobs if is_test_path(p))
        out.append({"date": when.isoformat(), "commit": sha[:8], "test_loc": t, "source_loc": s,
                    "ratio": round(t / s, 2) if s else None, "test_case_lines": cases})
    return out


def module_of(rel):
    """Top-level directory under src/ (or the repo root); root-level files form module '.'."""
    parts = rel.split("/")
    if parts[0] in ("src", "lib", "app") and len(parts) > 2:
        return parts[0] + "/" + parts[1]
    return parts[0] if len(parts) > 1 else "."


# config, schema, type and migration files are not code a test ratio should be measured against
CONFIG_LIKE = re.compile(r"\.config\.|schema\.|(^|/)types(\.ts$|/)|\.d\.ts$|(^|/)(migrations|alembic/versions|drizzle)/")


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--source-files")
    ap.add_argument("--bugfix-window", type=int, default=200)
    ap.add_argument("--growth-points", type=int, default=6)
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

    tracked = [p for p in git(repo, "ls-files", "-z").split("\0") if p]
    code = [p for p in tracked if is_code(p)]
    if a.source_files:
        with open(a.source_files, encoding="utf-8") as fh:
            sources = [l.strip().replace("\\", "/") for l in fh if l.strip()]
    else:
        sources = [p for p in code if not is_test_path(p)]
    resolver = Resolver(repo, tracked)

    importers, test_importers, test_mockers = {}, {}, {}
    srcs, unresolved, read = {}, 0, 0
    for rel in code:
        if time.time() > deadline:
            partial.append({"category": "import_graph", "scanned": read, "total": len(code),
                            "reason": "time budget of %ss exhausted" % a.time_budget})
            break
        try:
            with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        read += 1
        srcs[rel] = src
        imps, mocks, u = file_imports(rel, src, resolver)
        unresolved += u
        test = is_test_path(rel)
        for target in imps:
            if target == rel:
                continue
            (test_importers if test else importers).setdefault(target, set()).add(rel)
        if test:
            for target in mocks:
                test_mockers.setdefault(target, set()).add(rel)

    churn, bugfix, flake = churn_and_history(repo, a.bugfix_window)

    rows = []
    for rel in sources:
        src = srcs.get(rel)
        if src is None:
            try:
                with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
            except OSError:
                continue
        loc = src.count("\n") + (0 if src.endswith("\n") or not src else 1)
        reason = next((why for rx, why in ENTRY_POINTS if rx.search(rel)), None)
        if not reason and rel.endswith(".py"):
            if PY_ENTRY_DECORATOR.search(src):
                reason = "route/handler decorator"
            elif PY_MAIN_GUARD.search(src):
                reason = "__main__ guard"
        sec = security_lines(src)
        rows.append({
            "file": rel, "loc": loc, "churn": churn.get(rel, 0),
            "fan_in": len(importers.get(rel, ())), "importers": sorted(importers.get(rel, ()))[:10],
            "test_importers": sorted(test_importers.get(rel, ())),
            "test_mockers": sorted(test_mockers.get(rel, ())),
            "entry_point": bool(reason), "entry_reason": reason,
            "security_lines": sec,
            "security_density": round(min(1.0, sec / max(loc, DENSITY_FLOOR_LOC)), 4),
        })

    fan = sorted(r["fan_in"] for r in rows) or [0]
    floor = max(3, fan[int(0.9 * (len(fan) - 1))])
    for r in rows:
        eff = max(r["fan_in"], floor) if r["entry_point"] else r["fan_in"]
        r["fan_in_effective"] = eff
        r["priority"] = round(r["security_density"] * (1 + math.log10(r["churn"] + 1)) * (1 + math.log10(eff + 1)), 4)
    rows.sort(key=lambda r: -r["priority"])

    grow = growth(repo, a.growth_points, deadline) if a.growth_points else []
    if a.growth_points and len(grow) < a.growth_points:
        partial.append({"category": "growth_trend", "scanned": len(grow), "total": a.growth_points,
                        "reason": "time budget exhausted or history shorter than the window"})

    result = {
        "repo": repo,
        "priority_formula": "security_density x (1 + log10(churn + 1)) x (1 + log10(fan_in_effective + 1)); "
                            "density = lines with a strong security sub-word / max(loc, %d)" % DENSITY_FLOOR_LOC,
        "fan_in_floor_for_entry_points": floor,
        "files": rows,
        "bugfix_window": "last %d commits, then subjects matching %s" % (a.bugfix_window, BUGFIX.pattern),
        "bugfix_commits": bugfix,
        "flake_commits": flake,
        "growth": grow,
        "unresolved_local_imports": unresolved,
        "coverage_partial": partial,
        "elapsed_s": round(time.time() - t0, 2),
    }
    path = os.path.join(out, "leverage.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False)
    print(json.dumps({"files": len(rows), "fan_in_floor": floor, "bugfix_commits": len(bugfix),
                      "flake_commits": len(flake), "growth_points": len(grow),
                      "unresolved_local_imports": unresolved, "partial": bool(partial),
                      "elapsed_s": result["elapsed_s"]}))
    print("leverage=%s" % path)


if __name__ == "__main__":
    main()
