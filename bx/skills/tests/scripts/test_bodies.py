#!/usr/bin/env python3
"""test_bodies.py — extract every test body in a repo and count its assertions.

The mechanism behind /bx:tests' quality findings (T01a/T01b/T02/T03) and the input to the
consolidate lane. Scanners read its JSON and judge it; they do not write their own parsers
(spec: docs/superpowers/specs/2026-10-26-bx-tests-upkeep-design.md, D1). The assertion
definition it implements is canonical in references/test-smell-catalog.md, "What counts as an
assertion" — change the two together.

Read-only. Runs `git ls-files` in the repo and reads files; writes only into --out, which must
be outside the repo.

Usage:
    python -I bx/skills/tests/scripts/test_bodies.py --repo <path> --out <dir>
        [--files <list.txt>]      test files to scan, repo-relative, one per line
                                  (default: every tracked file matching a test pattern)
        [--time-budget <secs>]    stop early and report the rest as partial (default 600)
        [--no-shapes]             omit the token shapes the consolidate lane needs

Writes:
    <out>/test_bodies.jsonl       one row per test (fields: see ROW FIELDS below)
    <out>/test_bodies.summary.json
        counts, t01a/t01b, helper allowlist evidence, per-file flags, parse errors, partial
Prints the summary path and the headline counts.

ROW FIELDS
    file, line, end_line, lang, framework, name, describe[], body_lines
    assertions{kind: n}       kinds: value, weak, presence, mock_verify, mock_absent, snapshot, raises,
                              query, playwright, helper, assert
    assertion_total           sum of the above
    weak_only                 every assertion is a weak matcher (T02 candidate)
    mock_setup_lines          lines that build mocks/patches (not a smell by themselves)
    t03_candidate             T03_RULE holds (verification assertions dominate)
    t06_candidate             the name promises an outcome (shows/renders/returns/sends/...) and the
                              only assertions are weak or never-called checks
    mock_verify_lines         lines that verify interactions (T03 counts these)
    calls[]                   callees in the body, setup/mock/logging names removed
    t01                       null, or {kind: "a"|"b", signals[]} when assertion_total == 0
    todo_assert, skipped, param_rows, shape
"""
import argparse
import ast
import io
import json
import os
import re
import subprocess
import sys
import textwrap
import time
import tokenize

HELPER_VERBS = "assert|should|expect|check|verify|ensure|require|must"
ALLOWLIST_PATTERNS = {
    "js": r"^\s*(export\s+)?(default\s+)?(async\s+)?(function\s+|const\s+|let\s+)((?:%s)\w*)" % HELPER_VERBS,
    "py": r"^\s*(async\s+)?def\s+((?:%s)\w*)\s*\(" % HELPER_VERBS,
    "rs": r"^\s*(pub(\([a-z]+\))?\s+)?fn\s+((?:%s)\w*)" % HELPER_VERBS,
    "go": r"^func\s+(\([^)]*\)\s*)?((?:%s)\w*)\(" % HELPER_VERBS,
}
EXT_LANG = {
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js", ".ts": "js", ".tsx": "js", ".mts": "js",
    ".cts": "js", ".py": "py", ".go": "go", ".rs": "rs", ".java": "jvm", ".kt": "jvm",
    ".sh": "sh", ".bash": "sh", ".bats": "sh", ".ps1": "ps",
}
TEST_FILE = re.compile(
    r"(\.(test|spec)\.[cm]?[jt]sx?$)|(^|/)(test_[^/]*\.py|[^/]*_test\.py)$|(^|/)tests?/.*\.py$"
    r"|_test\.go$|\.rs$|(Test|Tests|IT)\.(java|kt)$|\.bats$|(^|/)test-[^/]*\.(sh|bash)$|\.Tests\.ps1$"
)
PRUNE = re.compile(r"(^|/)(node_modules|dist|build|\.next|coverage|vendor|target|\.venv|venv)/")


# --------------------------------------------------------------------------- C-like masking

def mask_clike(src, lang, strings=True):
    """Return src with string/comment contents blanked (same length, newlines kept).

    Template-literal `${...}` expressions stay visible; JS regex literals are blanked. The
    result is what brace matching and token regexes run on, so a `}` or `expect(` inside a
    string never counts. strings=False blanks comments only and keeps string contents.
    """
    out = list(src)
    n = len(src)
    i = 0
    stack = []  # template-literal brace depths (JS)
    prev_sig = ""

    def blank(a, b):
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    def sblank(a, b):
        if strings:
            blank(a, b)

    while i < n:
        c = src[i]
        nxt = src[i + 1] if i + 1 < n else ""
        if c == "/" and nxt == "/" and lang != "sh":
            j = src.find("\n", i)
            j = n if j < 0 else j
            blank(i, j)
            i = j
            continue
        if c == "/" and nxt == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            blank(i, j)
            i = j
            continue
        if lang == "rs" and c == "r" and re.match(r'r#*"', src[i:i + 8]) and not (i and (src[i - 1].isalnum() or src[i - 1] == "_")):
            hashes = re.match(r'r(#*)"', src[i:]).group(1)
            end = src.find('"' + hashes, i + 2 + len(hashes))
            end = n if end < 0 else end + 1 + len(hashes)
            sblank(i + 1, end)
            i = end
            continue
        if lang == "jvm" and src.startswith('"""', i):
            end = src.find('"""', i + 3)
            end = n if end < 0 else end + 3
            sblank(i + 3, end - 3)
            i = end
            continue
        if c in "\"'" or (c == "`" and lang in ("js", "go")):
            if c == "'" and lang == "rs" and not re.match(r"'(\\.|[^\\'\n])'", src[i:i + 12]):
                i += 1  # a lifetime, not a char literal
                continue
            q = c
            j = i + 1
            while j < n:
                d = src[j]
                if d == "\\" and q != "`" or (d == "\\" and lang == "js"):
                    j += 2
                    continue
                if q == "`" and lang == "js" and d == "$" and j + 1 < n and src[j + 1] == "{":
                    sblank(i + 1, j)
                    stack.append(0)
                    i = j + 2
                    break
                if d == q:
                    sblank(i + 1, j)
                    i = j + 1
                    break
                if d == "\n" and q != "`":
                    sblank(i + 1, j)
                    i = j
                    break
                j += 1
            else:
                sblank(i + 1, n)
                i = n
            prev_sig = q
            continue
        if lang == "js" and stack:
            if c == "{":
                stack[-1] += 1
            elif c == "}":
                if stack[-1] == 0:
                    stack.pop()
                    # resume the template literal after `}`
                    j = i + 1
                    while j < n:
                        d = src[j]
                        if d == "\\":
                            j += 2
                            continue
                        if d == "$" and j + 1 < n and src[j + 1] == "{":
                            sblank(i + 1, j)
                            stack.append(0)
                            j += 2
                            break
                        if d == "`":
                            sblank(i + 1, j)
                            j += 1
                            break
                        j += 1
                    i = j
                    prev_sig = "`"
                    continue
                stack[-1] -= 1
        if lang == "js" and c == "/" and (prev_sig in ("", "(", ",", "=", ":", "[", "!", "&", "|", "?", "{", "}", ";", "+", "-", "*", "%", "<", ">", "~", "^") or re.search(r"\b(return|typeof|case|in|of|void|delete|throw)\s*$", src[max(0, i - 12):i])):
            m = re.match(r"/(\\.|\[(\\.|[^\]\\\n])*\]|[^/\\\n\[])+/[a-z]*", src[i:])
            if m:
                blank(i + 1, i + m.end() - 1)
                i += m.end()
                prev_sig = "r"
                continue
        if not c.isspace():
            prev_sig = c if not (c.isalnum() or c in "_$") else "a"
        i += 1
    return "".join(out)


def match_close(masked, open_idx):
    """Index of the bracket closing masked[open_idx], or -1."""
    pairs = {"(": ")", "{": "}", "[": "]"}
    o = masked[open_idx]
    cl = pairs[o]
    depth = 0
    for k in range(open_idx, len(masked)):
        ch = masked[k]
        if ch == o:
            depth += 1
        elif ch == cl:
            depth -= 1
            if depth == 0:
                return k
    return -1


def line_of(text, idx, starts):
    lo, hi = 0, len(starts) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if starts[mid] <= idx:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def line_starts(text):
    s = [0]
    for m in re.finditer("\n", text):
        s.append(m.end())
    return s


def shape_of(masked_body, original_body):
    """Token sequence with literals replaced by L — what consolidate compares."""
    toks = re.findall(r"[A-Za-z_$][\w$]*|\d[\w.]*|\S", masked_body)
    out = []
    for t in toks:
        out.append("L" if t[0].isdigit() or t in ("true", "false", "null", "undefined", "None", "True", "False") else t)
    # string literals were blanked to spaces between quotes; collapse each quote pair into L
    s = " ".join(out)
    s = re.sub(r"([\"'`])\s*\1", "L", s)
    return s


# --------------------------------------------------------------------------- JS / TS

JS_TEST_START = re.compile(r"(?<![\w$.])(it|test)((?:\s*\.\s*(?:only|skip|concurrent|sequential|todo|fails|each|failing|skipIf|runIf|fixme|slow)\b)*)\s*(?=[(`<])")
JS_DESCRIBE_START = re.compile(r"(?<![\w$.])(describe|suite|context)((?:\s*\.\s*\w+)*)\s*(?=[(`])|(?<![\w$])test\s*\.\s*describe((?:\s*\.\s*\w+)*)\s*(?=\()")
JS_HOOK = re.compile(r"(?<![\w$.])(?:test\s*\.\s*)?(afterEach|afterAll|beforeEach|beforeAll)\s*\(")
# toBeNull()/toBeUndefined() pin a value; only their negations merely assert existence
JS_WEAK = {"toBeTruthy", "toBeFalsy", "toBeDefined", "toBeInstanceOf"}
JS_WEAK_NEGATED = {"toBeNull", "toBeUndefined", "toBeNaN"}
JS_PRESENCE = {"toBeInTheDocument", "toBeVisible", "toBeAttached", "toHaveLength", "toBeEnabled", "toBeDisabled", "toBeChecked"}
JS_MOCK_VERIFY = re.compile(r"^(toHaveBeenCalled\w*|toHaveBeenNthCalledWith|toHaveBeenLastCalledWith|toBeCalled\w*|lastCalledWith|toHaveReturned\w*|nthCalledWith)$")
JS_SNAPSHOT = re.compile(r"^(toMatchSnapshot|toMatchInlineSnapshot|toMatchFileSnapshot|toThrowErrorMatchingSnapshot|toThrowErrorMatchingInlineSnapshot|toHaveScreenshot)$")
JS_RAISES = re.compile(r"^(toThrow\w*|rejects|resolves)$")
JS_QUERY = re.compile(r"(?<![\w$])(?:screen\s*\.\s*|\w+\s*\.\s*)?(getBy|getAllBy|findBy|findAllBy)\w+\s*\(")
JS_PLAYWRIGHT = re.compile(r"\.\s*(click|dblclick|fill|check|uncheck|selectOption|press|pressSequentially|type|hover|tap|setInputFiles|waitForSelector|waitForURL|waitForResponse|waitForRequest|dragTo)\s*\(")
JS_MOCK_SETUP = re.compile(r"\b(vi|jest)\s*\.\s*(fn|mock|spyOn|doMock|hoisted|stubGlobal|stubEnv|mocked)\b|\.\s*mock(ReturnValue|ResolvedValue|RejectedValue|Implementation)\w*\s*\(|\bsinon\s*\.\s*(stub|spy|mock)\b")
JS_VERIFY_LINE = re.compile(r"\.\s*(toHaveBeenCalled\w*|toHaveBeenNthCalledWith|toHaveBeenLastCalledWith|toBeCalled\w*)\b|\.\s*mock\s*\.\s*(calls|results|lastCall)\b|\bverify\s*\(")
JS_CALL = re.compile(r"(?<![\w$])((?:[A-Za-z_$][\w$]*\s*\.\s*)*[A-Za-z_$][\w$]*)\s*(?:<[^<>()]*>)?\s*\(")
JS_NOT_UNDER_TEST = re.compile(
    r"^(if|for|while|switch|catch|function|return|typeof|await|async|new|super|import|require|"
    r"expect\b.*|vi\..*|jest\..*|sinon\..*|console\..*|describe.*|it|test|beforeEach|afterEach|"
    r"Symbol|String|Number|Boolean|Array|Object|JSON|Math|Date|Promise|Error|Map|Set|"
    r"mock\w*|.*\.mock\w*|spy\w*|setTimeout|setImmediate|clearTimeout|structuredClone)$"
)
JS_ASSERT_TOKENS = re.compile(r"(?<![\w$])(expect|assert)(\s*\.\s*\w+)*\s*\(|(?<![\w$])(getBy|getAllBy|findBy|findAllBy)\w+\s*\(|\bthrow\b|\.should\b")


def js_find_calls(masked, start_re):
    """Yield (start, ident_end, open_paren, close_paren, chain) for each call matching start_re."""
    for m in start_re.finditer(masked):
        k = m.end()
        chain = m.group(0)
        if k < len(masked) and masked[k] == "<":  # it.each<[string, number]>(...)
            depth, limit = 0, min(len(masked), k + 400)  # `test < x` is a comparison: stay bounded
            while k < limit:
                depth += {"<": 1, ">": -1}.get(masked[k], 0)
                k += 1
                if depth == 0:
                    break
            while k < len(masked) and masked[k].isspace():
                k += 1
        # `.each(table)` / `.each`\`table\`` must be skipped before the real argument list
        if ".each" in re.sub(r"\s", "", chain):
            if k < len(masked) and masked[k] == "(":
                c = match_close(masked, k)
                if c < 0:
                    continue
                each_args = (k, c)
                k = c + 1
            elif k < len(masked) and masked[k] == "`":
                c = masked.find("`", k + 1)
                if c < 0:
                    continue
                each_args = (k, c)
                k = c + 1
            else:
                continue
            while k < len(masked) and masked[k].isspace():
                k += 1
            if k >= len(masked) or masked[k] != "(":
                continue
        else:
            each_args = None
        if k >= len(masked) or masked[k] != "(":
            continue
        close = match_close(masked, k)
        if close < 0:
            continue
        yield m.start(), k, close, chain, each_args


def js_split_args(masked, open_, close):
    """Top-level comma positions inside (open_, close)."""
    parts, depth, last = [], 0, open_ + 1
    for k in range(open_ + 1, close):
        ch = masked[k]
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append((last, k))
            last = k + 1
    parts.append((last, close))
    return [(a, b) for a, b in parts if masked[a:b].strip()]


def js_callback(masked, arg):
    """(body_start, body_end, is_block) of a function-valued argument, or None."""
    a, b = arg
    seg = masked[a:b]
    m = re.match(r"\s*(async\s+)?function\b[^(]*\(", seg)
    if m:
        p = a + m.end() - 1
        pc = match_close(masked, p)
        br = masked.find("{", pc)
        if br < 0 or br >= b:
            return None
        return br, match_close(masked, br), True
    m = re.match(r"\s*(async\s+)?(\([^)]*\)|[A-Za-z_$][\w$]*)\s*(:\s*[^=]+)?=>", seg, re.S)
    if not m:
        # parameter list containing nested parens/destructuring: find `=>` at depth 0
        m2 = re.match(r"\s*(async\s+)?\(", seg)
        if not m2:
            return None
        pc = match_close(masked, a + m2.end() - 1)
        arrow = masked.find("=>", pc)
        if pc < 0 or arrow < 0 or arrow >= b or masked[pc + 1:arrow].strip() and not masked[pc + 1:arrow].strip().startswith(":"):
            return None
        k = arrow + 2
    else:
        k = a + m.end()
    while k < b and masked[k].isspace():
        k += 1
    if k < b and masked[k] == "{":
        return k, match_close(masked, k), True
    return k, b, False


def js_string_value(src, masked, arg):
    a, b = arg
    seg = src[a:b].strip()
    m = re.match(r"""^(['"`])(.*)\1$""", seg, re.S)
    if m:
        return m.group(2)
    return seg[:120]


def js_each_rows(masked, each_args):
    if not each_args:
        return None
    a, b = each_args
    if masked[a] == "`":
        rows = [l for l in masked[a + 1:b].split("\n") if l.strip()]
        return max(0, len(rows) - 1)  # first row is the header
    inner = masked[a + 1:b].strip()
    if inner.startswith("["):
        lb = a + 1 + masked[a + 1:b].index("[")
        rb = match_close(masked, lb)
        return len(js_split_args(masked, lb, rb)) if rb > 0 else None
    return None


def js_matchers_after_expect(masked, body_s, body_e):
    """For every expect(...) in the body, return the terminal matcher name chain."""
    out = []
    for m in re.finditer(r"(?<![\w$])expect(\s*\.\s*(soft|poll))?\s*\(", masked[body_s:body_e]):
        p = body_s + m.end() - 1
        c = match_close(masked, p)
        if c < 0:
            continue
        tail = masked[c + 1:c + 200]
        chain = re.match(r"(\s*\.\s*[A-Za-z_$][\w$]*)+", tail)
        names = re.findall(r"[A-Za-z_$][\w$]*", chain.group(0)) if chain else []
        negated = "not" in names
        names = [x for x in names if x != "not"]
        mt = names[-1] if names else ""
        if mt == "toBeInstanceOf":
            arg = re.match(r"\s*\(\s*([\w$.]+)", tail[chain.end():] if chain else "")
            # instanceOf(AbortSignal) pins a concrete type; only Object/Function is existence-only
            if not (arg and arg.group(1) in ("Object", "Function")):
                mt = "toBeInstanceOf:concrete"
        out.append((mt, masked[p + 1:c], negated))
    return out


def js_local_asserting_functions(masked):
    """Names of functions defined in this file whose body asserts or throws (fixpoint)."""
    defs = {}
    for m in re.finditer(r"(?<![\w$.])(?:function\s+([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\s*\(|(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:async\s+)?(?:function\b[^(]*\(|\(|[A-Za-z_$][\w$]*\s*=>))", masked):
        name = m.group(1) or m.group(2)
        k = m.end()
        # locate the body: the first `{` after the param list, or an arrow expression
        p = masked.rfind("(", m.start(), k)
        if p >= 0:
            pc = match_close(masked, p)
        else:
            pc = k
        if pc < 0:
            continue
        rest = masked[pc + 1:pc + 400]
        am = re.match(r"\s*(:[^={]+)?(=>)?\s*\{", rest)
        if am:
            bs = pc + 1 + am.end() - 1
            be = match_close(masked, bs)
            if be > 0:
                defs[name] = masked[bs:be]
        else:
            em = re.match(r"\s*(:[^=]+)?=>\s*", rest)
            if em:
                e = pc + 1 + em.end()
                defs[name] = masked[e:masked.find("\n", e)]
    asserting = set()
    for _ in range(4):
        changed = False
        for name, body in defs.items():
            if name in asserting:
                continue
            if JS_ASSERT_TOKENS.search(body) or any(re.search(r"(?<![\w$.])%s\s*\(" % re.escape(h), body) for h in asserting):
                asserting.add(name)
                changed = True
        if not changed:
            break
    return asserting


def js_classify_body(src, masked, bs, be, helpers, is_playwright, local_helpers):
    body_m = masked[bs:be]
    kinds = {}

    def add(k, n=1):
        kinds[k] = kinds.get(k, 0) + n

    matchers = js_matchers_after_expect(masked, bs, be)
    in_expect_query = 0
    for m in re.finditer(r"(?<![\w$])expect(\s*\.\s*(soft|poll))?\s*\(", body_m):
        p = bs + m.end() - 1
        c = match_close(masked, p)
        inner = masked[p + 1:c] if c > 0 else ""
        if JS_QUERY.search(inner):
            in_expect_query += 1
    for idx, (mt, inner, negated) in enumerate(matchers):
        if negated and JS_MOCK_VERIFY.match(mt):
            add("mock_absent")  # "never called": an observable absence, not coupling
        elif JS_MOCK_VERIFY.match(mt) or re.search(r"\.\s*mock\s*\.\s*(calls|results|lastCall|instances)\b", inner):
            add("mock_verify")
        elif JS_SNAPSHOT.match(mt):
            add("snapshot")
        elif JS_RAISES.match(mt):
            add("raises")
        elif mt in JS_PRESENCE:
            add("presence")
        elif mt in JS_WEAK or (negated and mt in JS_WEAK_NEGATED):
            add("weak")
        else:
            add("value")
    # a getBy* inside expect() already throws on a miss: the matcher is a presence check, not T02
    if in_expect_query and kinds.get("weak"):
        moved = min(in_expect_query, kinds["weak"])
        kinds["weak"] -= moved
        add("presence", moved)
        if not kinds["weak"]:
            del kinds["weak"]
    q_total = len(JS_QUERY.findall(body_m))
    if q_total - in_expect_query > 0:
        add("query", q_total - in_expect_query)
    a = len(re.findall(r"(?<![\w$])assert(\s*\.\s*\w+)?\s*\(", body_m)) + len(re.findall(r"\.should\b", body_m))
    if a:
        add("assert", a)
    if is_playwright:
        n = len(JS_PLAYWRIGHT.findall(body_m))
        if n:
            add("playwright", n)
    h = 0
    for name in helpers | local_helpers:
        if name in ("expect", "assert"):
            continue
        h += len(re.findall(r"(?<![\w$.])%s\s*\(" % re.escape(name), body_m))
    if h:
        add("helper", h)
    if re.search(r"\bthrow\s+new\b", body_m) and not kinds:
        add("assert")  # a hand-rolled `if (...) throw` check
    lines = body_m.split("\n")
    setup = sum(1 for l in lines if JS_MOCK_SETUP.search(l))
    verify = sum(1 for l in lines if JS_VERIFY_LINE.search(l))
    calls = []
    local_mocks = set(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*(?::[^=]+)?=\s*(?:vi|jest)\s*\.\s*fn\b", body_m))
    for m in JS_CALL.finditer(body_m):
        name = re.sub(r"\s", "", m.group(1))
        if JS_NOT_UNDER_TEST.match(name) or name in calls or name.split(".")[0] in local_mocks:
            continue
        calls.append(name)
    return kinds, setup, verify, calls


def js_scan(path, src, helpers):
    masked = mask_clike(src, "js")
    starts = line_starts(src)
    is_pw = bool(re.search(r"""from\s+['"]@playwright/test['"]|require\(\s*['"]@playwright/test""", src))
    local_helpers = js_local_asserting_functions(masked)
    describes = []
    for s, o, c, chain, ea in js_find_calls(masked, JS_DESCRIBE_START):
        args = js_split_args(masked, o, c)
        if args:
            describes.append((o, c, js_string_value(src, masked, args[0])))
    hook_asserts = False
    for m in JS_HOOK.finditer(masked):
        o = m.end() - 1
        c = match_close(masked, o)
        if c > 0 and re.search(r"(?<![\w$])(expect|assert)\s*[.(]", masked[o:c]):
            hook_asserts = True
    property_based = bool(re.search(r"""['"](fast-check|@fast-check/\w+)['"]""", src))
    rows = []
    for s, o, c, chain, ea in js_find_calls(masked, JS_TEST_START):
        chain_n = re.sub(r"\s", "", chain)
        if ".describe" in chain_n:
            continue
        args = js_split_args(masked, o, c)
        if not args:
            continue
        name = js_string_value(src, masked, args[0])
        todo = ".todo" in chain_n
        cb = None
        for arg in args[1:]:
            cb = js_callback(masked, arg)
            if cb:
                break
        if cb is None:
            if todo or len(args) == 1:
                continue  # it.todo('x') / a name-only placeholder: not a test body
            continue
        bs, be, is_block = cb
        if be < 0:
            continue
        kinds, setup, verify, calls = js_classify_body(src, masked, bs, be, helpers, is_pw, local_helpers)
        line = line_of(src, s, starts)
        end_line = line_of(src, c, starts)
        body_src = src[bs:be]
        rows.append({
            "file": path, "line": line, "end_line": end_line, "lang": "js",
            "framework": "playwright" if is_pw else "js",
            "name": name,
            "describe": [d[2] for d in describes if d[0] < s < d[1]],
            "body_lines": end_line - line + 1,
            "assertions": kinds,
            "mock_setup_lines": setup, "mock_verify_lines": verify,
            "calls": calls[:25],
            "todo_assert": bool(re.search(r"(//|/\*).*\b(TODO|FIXME)\b.*\b(assert|expect|check|verify)", body_src, re.I)),
            "skipped": ".skip" in chain_n or ".fixme" in chain_n or todo,
            "param_rows": js_each_rows(masked, ea),
            "_shape_src": (masked[bs:be], body_src),
        })
    return rows, {"hook_asserts": hook_asserts, "property_based": property_based,
                  "file_mocks": len(re.findall(r"\b(vi|jest)\s*\.\s*mock\s*\(", masked))}


# --------------------------------------------------------------------------- Python

PY_MOCK_VERIFY = re.compile(r"^assert_(called\w*|awaited\w*|not_called|not_awaited|has_calls|any_call|has_awaits|any_await)$")
PY_NOT_UNDER_TEST = re.compile(
    r"^(print|len|str|int|float|bool|list|dict|set|tuple|range|isinstance|getattr|setattr|hasattr|"
    r"sorted|enumerate|zip|type|super|open|"
    r"patch(\..*)?|mock\..*|.*\.patch(\..*)?|.*\.patch\.object|MagicMock|AsyncMock|Mock|PropertyMock|"
    r"create_autospec|call|ANY|logging\..*|logger\..*|.*\.log(ger)?\.\w+|pytest\..*|mocker\..*|"
    r"monkeypatch\..*|caplog\..*|capsys\..*|self\.assert\w*|freeze_time|.*\.assert_\w+)$"
)
PY_CALL_RECORD = {"call_args", "call_args_list", "call_count", "await_count", "mock_calls", "await_args", "await_args_list", "called", "await_args"}
PY_SETUP_LINE = re.compile(r"\b(patch(\.object|\.dict)?\s*\(|MagicMock\(|AsyncMock\(|Mock\(|PropertyMock\(|create_autospec\(|mocker\.\w+|monkeypatch\.\w+)|\.(return_value|side_effect)\s*=")
PY_VERIFY_LINE = re.compile(r"\.assert_(called|awaited|not_called|not_awaited|has_calls|any_call|has_awaits|any_await)\w*\s*\(|\.(call_args(_list)?|call_count|await_count|mock_calls|await_args(_list)?)\b")


def dotted(node):
    parts = []
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        # mocks["slack"].send_dm.assert_called_once() — a subscript is still a mock path
        parts.append(node.attr if isinstance(node, ast.Attribute) else "[]")
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    elif isinstance(node, ast.Call):
        parts.append(dotted(node.func) + "()")
    else:
        return ""
    return ".".join(reversed(parts))


def py_weak_assert(test):
    if isinstance(test, ast.Constant):
        return True
    if isinstance(test, (ast.Name, ast.Attribute)):
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.IsNot) \
            and isinstance(test.comparators[0], ast.Constant) and test.comparators[0].value is None:
        return True
    if isinstance(test, ast.Call) and dotted(test.func) in ("isinstance", "callable", "hasattr"):
        return True
    return False


def py_classify(fn, helpers, src_lines):
    kinds = {}

    def add(k, n=1):
        kinds[k] = kinds.get(k, 0) + n

    calls = []
    local_mocks = {t.id for n in ast.walk(fn) if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                   and dotted(n.value.func).split(".")[-1] in ("Mock", "MagicMock", "AsyncMock", "create_autospec")
                   for t in n.targets if isinstance(t, ast.Name)}
    for node in ast.walk(fn):
        if node is fn:
            continue
        if isinstance(node, ast.Assert):
            if any(isinstance(n, ast.Attribute) and n.attr in PY_CALL_RECORD for n in ast.walk(node.test)):
                add("mock_verify")  # assert m.call_args == ...: interaction, not behaviour
            else:
                add("weak" if py_weak_assert(node.test) else "assert")
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                ce = item.context_expr
                if isinstance(ce, ast.Call) and dotted(ce.func).split(".")[-1] in ("raises", "warns", "assertRaises", "assertRaisesRegex", "assertWarns", "assertLogs"):
                    add("raises")
        elif isinstance(node, ast.Raise):
            pass
        elif isinstance(node, ast.Call):
            name = dotted(node.func)
            last = name.split(".")[-1] if name else ""
            if last in ("assert_not_called", "assert_not_awaited"):
                add("mock_absent")
            elif PY_MOCK_VERIFY.match(last):
                add("mock_verify")
            elif last.startswith("assert") and name.startswith("self."):
                add("assert")
            elif name in ("pytest.fail", "self.fail", "fail"):
                add("assert")
            elif name.endswith(".raises") or name.endswith(".warns"):
                add("raises")
            elif last.startswith("assert") and ("testing" in name or name.startswith(("np.", "numpy.", "pd.", "pandas."))):
                add("assert")
            elif last in helpers or name in helpers:
                add("helper")
            elif name and not PY_NOT_UNDER_TEST.match(name) and name not in calls and name.split(".")[0] not in local_mocks:
                calls.append(name)
    # decorator-level raises (unittest expectedFailure is not an assertion)
    for d in fn.decorator_list:
        dn = dotted(d.func if isinstance(d, ast.Call) else d)
        if dn.endswith("mark.xfail") and isinstance(d, ast.Call) and any(k.arg == "raises" for k in d.keywords):
            add("raises")
    body_lines = src_lines[fn.lineno - 1:fn.end_lineno]
    setup = sum(1 for l in body_lines if PY_SETUP_LINE.search(l))
    setup += sum(1 for d in fn.decorator_list if "patch" in dotted(d.func if isinstance(d, ast.Call) else d))
    verify = sum(1 for l in body_lines if PY_VERIFY_LINE.search(l))
    return kinds, setup, verify, calls


def py_param_rows(fn):
    rows = None
    for d in fn.decorator_list:
        if isinstance(d, ast.Call) and dotted(d.func).endswith("mark.parametrize") and len(d.args) >= 2:
            v = d.args[1]
            if isinstance(v, (ast.List, ast.Tuple)):
                rows = (rows or 1) * len(v.elts)
    return rows


def py_is_skipped(fn, cls=None):
    for d in list(fn.decorator_list) + (list(cls.decorator_list) if cls else []):
        dn = dotted(d.func if isinstance(d, ast.Call) else d)
        if dn.endswith(("mark.skip", "mark.skipif", "unittest.skip", "skip", "skipIf", "skipUnless")):
            return True
    return False


def py_local_asserting(tree):
    """Module/class-level functions (non-test) whose body asserts or raises."""
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("test"):
            for sub in ast.walk(node):
                if isinstance(sub, (ast.Assert, ast.Raise)) or (isinstance(sub, ast.Call) and (
                        PY_MOCK_VERIFY.match(dotted(sub.func).split(".")[-1] or "") or dotted(sub.func) in ("pytest.fail",))):
                    out.add(node.name)
                    break
    return out


def py_scan(path, src, helpers):
    tree = ast.parse(src)
    lines = src.split("\n")
    local = py_local_asserting(tree)
    helpers = helpers | local
    rows = []
    hook_asserts = False
    property_based = bool(re.search(r"^\s*(from|import)\s+hypothesis\b", src, re.M))

    def is_unittest_class(c):
        return any(dotted(b).split(".")[-1] in ("TestCase", "IsolatedAsyncioTestCase", "AsyncTestCase", "TransactionTestCase", "SimpleTestCase") for b in c.bases)

    def visit(body, cls_stack):
        nonlocal hook_asserts
        for node in body:
            if isinstance(node, ast.ClassDef):
                if node.name.startswith("Test") or is_unittest_class(node):
                    visit(node.body, cls_stack + [node])
                continue
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.name in ("setUp", "tearDown", "setup_method", "teardown_method", "asyncSetUp", "asyncTearDown") or \
                    any("fixture" in dotted(d.func if isinstance(d, ast.Call) else d) for d in node.decorator_list):
                k, _, _, _ = py_classify(node, helpers, lines)
                if k:
                    hook_asserts = True
                continue
            if not node.name.startswith("test"):
                continue
            kinds, setup, verify, calls = py_classify(node, helpers, lines)
            first = min([d.lineno for d in node.decorator_list] + [node.lineno])
            body_src = "\n".join(lines[node.lineno - 1:node.end_lineno])
            rows.append({
                "file": path, "line": node.lineno, "start_line": first, "end_line": node.end_lineno, "lang": "py",
                "framework": "unittest" if cls_stack and is_unittest_class(cls_stack[-1]) else "pytest",
                "name": node.name,
                "describe": [c.name for c in cls_stack],
                "body_lines": node.end_lineno - first + 1,
                "assertions": kinds,
                "mock_setup_lines": setup, "mock_verify_lines": verify,
                "calls": calls[:25],
                "fixtures": [a.arg for a in node.args.args if a.arg not in ("self", "cls")],
                "todo_assert": bool(re.search(r"#.*\b(TODO|FIXME)\b.*\b(assert|check|verify)", body_src, re.I)),
                "skipped": py_is_skipped(node, cls_stack[-1] if cls_stack else None),
                "param_rows": py_param_rows(node),
                "_shape_py": body_src,
            })

    visit(tree.body, [])
    return rows, {"hook_asserts": hook_asserts, "property_based": property_based,
                  "file_mocks": len(re.findall(r"\bpatch(\.object)?\s*\(", src))}


def py_shape(body_src):
    toks, after_def = [], False
    try:
        # dedent: a class method's body is indented and would not tokenize as-is
        for t in tokenize.generate_tokens(io.StringIO(textwrap.dedent(body_src)).readline):
            if t.type in (tokenize.STRING, tokenize.NUMBER):
                toks.append("L")
            elif t.type in (tokenize.NAME, tokenize.OP):
                # the test's own name is its label, like a JS test's title string: a literal slot
                toks.append("L" if after_def or t.string in ("True", "False", "None") else t.string)
            after_def = t.type == tokenize.NAME and t.string == "def"
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return " ".join(re.findall(r"\w+|\S", body_src))
    return " ".join(toks)


# --------------------------------------------------------------------------- Go / Rust / JVM / shell

GENERIC = {
    "go": {
        "start": re.compile(r"^func\s+(Test\w+|Example\w*|Fuzz\w+)\s*\(\s*\w+\s+\*testing\.(T|F)\s*\)\s*\{", re.M),
        "assert": [("assert", re.compile(r"\b\w+\.(Error|Errorf|Fatal|Fatalf|Fail|FailNow)\s*\(")),
                   ("assert", re.compile(r"\b(assert|require)\.\w+\s*\("))],
        "setup": re.compile(r"\bgomock\.|\.EXPECT\(\)|mock\.\w+"),
        "verify": re.compile(r"\.AssertExpectations\(|\.AssertCalled\(|\.AssertNumberOfCalls\("),
    },
    "rs": {
        "start": re.compile(r"#\[(?:tokio::|async_std::|actix_rt::)?test(?:\([^)]*\))?\]\s*(?:#\[[^\]]*\]\s*)*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*(?:<[^>]*>)?\s*\([^)]*\)\s*(?:->\s*[^{]+)?\{"),
        "assert": [("assert", re.compile(r"\b(assert|assert_eq|assert_ne|debug_assert\w*|panic|unreachable)!\s*[(\[{]")),
                   ("raises", re.compile(r"#\[should_panic"))],
        "setup": re.compile(r"\bmock!|Mock\w+::new|\.expect_\w+\("),
        "verify": re.compile(r"\.checkpoint\(\)|\.times\("),
    },
    "jvm": {
        "start": re.compile(r"@(?:Test|ParameterizedTest|RepeatedTest|TestFactory)\b[^\n]*\n(?:\s*@[^\n]*\n)*\s*(?:(?:public|private|protected|internal|open|override|suspend)\s+)*(?:void\s+|fun\s+)`?([\w ]+?)`?\s*\([^)]*\)[^{=]*[{=]"),
        "assert": [("assert", re.compile(r"\b(assert\w*|fail)\s*\(|\bAssertions\.\w+|\bAssert\.\w+|\bassertThat\b|\bshould\w*\b")),
                   ("mock_verify", re.compile(r"\bverify\s*\(|\bcoVerify\b|\bconfirmVerified\b"))],
        "setup": re.compile(r"\bmock\(|@Mock\b|\bwhen\(|\bevery\s*\{|\bmockk\("),
        "verify": re.compile(r"\bverify\s*\(|\bcoVerify\b"),
    },
}
SH_START = re.compile(r"^\s*@test\s+(['\"])(.*?)\1\s*\{|^\s*(?:function\s+)?(test_\w+)\s*(?:\(\s*\))?\s*\{", re.M)
PS_START = re.compile(r"^\s*It\s+(['\"])(.*?)\1[^{]*\{", re.M | re.I)


def generic_scan(path, src, lang, helpers):
    if lang in ("sh", "ps"):
        return shell_scan(path, src, lang, helpers)
    spec = GENERIC[lang]
    masked = mask_clike(src, lang)
    starts = line_starts(src)
    rows = []
    for m in spec["start"].finditer(masked if lang != "jvm" else src):
        open_ = masked.find("{", m.end() - 1) if masked[m.end() - 1] == "{" else -1
        if open_ < 0:
            # Kotlin expression body `= ...` — take the rest of the line
            open_ = m.end() - 1
            close = masked.find("\n", open_)
        else:
            close = match_close(masked, open_)
        if close < 0:
            continue
        body = masked[open_:close]
        kinds = {}
        header = masked[m.start():open_]
        for kind, rx in spec["assert"]:
            n = len(rx.findall(body)) + (len(rx.findall(header)) if kind == "raises" else 0)
            if n:
                kinds[kind] = kinds.get(kind, 0) + n
        h = sum(len(re.findall(r"(?<![\w.])%s\s*[(!]" % re.escape(x), body)) for x in helpers)
        if h:
            kinds["helper"] = h
        line = line_of(src, m.start(), starts)
        end_line = line_of(src, close, starts)
        calls = []
        for cm in re.finditer(r"(?<![\w$])((?:[A-Za-z_]\w*\s*(?:\.|::)\s*)*[A-Za-z_]\w*)\s*\(", body):
            nm = re.sub(r"\s", "", cm.group(1))
            if nm in calls or re.match(r"^(if|for|while|switch|return|func|fn|make|len|append|new|t\.\w+|assert\w*|require\.\w+|fmt\.\w+|println|print|format|vec|Some|Ok|Err)$", nm):
                continue
            calls.append(nm)
        rows.append({
            "file": path, "line": line, "end_line": end_line, "lang": lang, "framework": lang,
            "name": (m.group(1) or "").strip(), "describe": [],
            "body_lines": end_line - line + 1, "assertions": kinds,
            "mock_setup_lines": sum(1 for l in body.split("\n") if spec["setup"].search(l)),
            "mock_verify_lines": sum(1 for l in body.split("\n") if spec["verify"].search(l)),
            "calls": calls[:25],
            "todo_assert": bool(re.search(r"(//|#).*\b(TODO|FIXME)\b.*\b(assert|check|verify)", src[open_:close], re.I)),
            "skipped": bool(re.search(r"t\.Skip\(|#\[ignore\]|@Disabled|@Ignore", header + body[:200])),
            "param_rows": len(re.findall(r"^\s*\{", body, re.M)) if lang == "go" and "t.Run(" in body else None,
            "_shape_src": (body, src[open_:close]),
        })
    return rows, {"hook_asserts": False, "property_based": bool(re.search(r"\bproptest!|quickcheck|jqwik|testing/quick", src)), "file_mocks": 0}


def shell_scan(path, src, lang, helpers):
    lines = src.split("\n")
    rows = []
    rx = SH_START if lang == "sh" else PS_START
    for m in rx.finditer(src):
        start_line = src.count("\n", 0, m.start()) + 1
        depth, end_line = 0, None
        for i in range(start_line - 1, len(lines)):
            stripped = re.sub(r"(['\"]).*?\1", "", lines[i])
            stripped = re.sub(r"(^|\s)#.*$", "", stripped)
            depth += stripped.count("{") - stripped.count("}")
            if depth <= 0 and i >= start_line - 1 and "{" in "".join(lines[start_line - 1:i + 1]):
                end_line = i + 1
                break
        if end_line is None:
            continue
        body = "\n".join(lines[start_line:end_line - 1])
        kinds = {}
        if lang == "sh":
            pats = [("assert", r"(?<![\w-])(fail|pass|assert\w*|assert_\w+)\b"), ("assert", r"\bexit\s+1\b")]
            if m.group(2) is not None:  # bats: any failing command fails the test
                pats.append(("assert", r"^\s*\[\[?\s|\brun\b|\bassert_\w+"))
        else:
            pats = [("assert", r"\|\s*Should\b|\bShould\s+-"), ("raises", r"\{[^}]*\}\s*\|\s*Should\s+-Throw")]
        for kind, p in pats:
            n = len(re.findall(p, body, re.M))
            if n:
                kinds[kind] = kinds.get(kind, 0) + n
        h = sum(len(re.findall(r"(?<![\w-])%s\b" % re.escape(x), body)) for x in helpers)
        if h:
            kinds["helper"] = h
        calls = [c for c in dict.fromkeys(re.findall(r"^\s*([A-Za-z_][\w./-]*)", body, re.M))
                 if c not in ("local", "echo", "printf", "if", "then", "fi", "else", "for", "do", "done", "return", "export", "cd", "run", "Mock", "Should", "set")]
        rows.append({
            "file": path, "line": start_line, "end_line": end_line, "lang": lang, "framework": "bats" if m.group(2) is not None and lang == "sh" else lang,
            "name": m.group(2) if m.group(2) is not None else (m.group(3) if lang == "sh" else m.group(2)),
            "describe": [], "body_lines": end_line - start_line + 1, "assertions": kinds,
            "mock_setup_lines": len(re.findall(r"^\s*Mock\b", body, re.M)), "mock_verify_lines": len(re.findall(r"Should\s+-Invoke", body)),
            "calls": calls[:25], "todo_assert": bool(re.search(r"#.*\b(TODO|FIXME)\b.*\b(assert|check)", body, re.I)),
            "skipped": bool(re.search(r"^\s*skip\b|-Skip\b", body + lines[start_line - 1], re.M)), "param_rows": None,
            "_shape_src": (body, body),
        })
    return rows, {"hook_asserts": False, "property_based": False, "file_mocks": 0}


# --------------------------------------------------------------------------- helper allowlist

def helper_allowlist(repo, tracked):
    """Run the catalog's allowlist patterns over every tracked code file.

    Keeps a name only if its definition body asserts or raises. Returns (names, evidence).
    """
    pats = {k: re.compile(v, re.M) for k, v in ALLOWLIST_PATTERNS.items()}
    kept, rejected, searched = set(), [], 0
    for rel in tracked:
        lang = EXT_LANG.get(os.path.splitext(rel)[1])
        key = {"js": "js", "py": "py", "rs": "rs", "go": "go"}.get(lang)
        if not key or PRUNE.search(rel):
            continue
        try:
            with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        searched += 1
        for m in pats[key].finditer(src):
            name = [g for g in m.groups() if g and re.match(r"^(%s)\w*$" % HELPER_VERBS, g)]
            if not name:
                continue
            name = name[-1]
            if key == "js" and re.match(r"\s*(const|let)\b", m.group(0)) and not re.match(
                    r"\s*(:[^=]+)?=\s*(async\s+)?(function\b|\([^)]*\)\s*(:[^=]+)?=>|[A-Za-z_$][\w$]*\s*=>)",
                    src[m.end():m.end() + 300]):
                rejected.append({"name": name, "file": rel, "reason": "a variable, not a function"})
                continue
            if key == "py":
                # the body ends at the first non-blank line indented no deeper than the def
                indent = len(m.group(0)) - len(m.group(0).lstrip())
                body = src[m.start():]
                end = re.search(r"\n(?=[ \t]{0,%d}\S)" % indent, body[1:])
                body = body[:end.start() + 1] if end else body
                ok = re.search(r"^\s+(assert\b|raise\b)|\.assert_\w+\(|pytest\.fail\(", body, re.M)
            else:
                masked = mask_clike(src[m.start():m.start() + 20000], key)
                br = masked.find("{")
                if br < 0:
                    rejected.append({"name": name, "file": rel, "reason": "no body found"})
                    continue
                close = match_close(masked, br)
                body = masked[br:close] if close > 0 else masked[br:br + 2000]
                ok = JS_ASSERT_TOKENS.search(body) if key == "js" else re.search(r"\b(assert\w*!|panic!|t\.(Error|Fatal)\w*|require\.|assert\.)", body)
            if ok:
                kept.add(name)
            else:
                rejected.append({"name": name, "file": rel, "reason": "body neither asserts nor raises"})
    return kept, {
        "helper_allowlist_size": len(kept),
        "helper_allowlist": sorted(kept),
        "helper_allowlist_patterns": ALLOWLIST_PATTERNS,
        "helper_allowlist_files_searched": searched,
        "helper_allowlist_rejected": rejected[:50],
        "helper_allowlist_rejected_total": len(rejected),
    }


# --------------------------------------------------------------------------- T01 / T03 classification

# T03 counts verification assertions only (problem 24: setup lines are not coupling)
T03_MIN, T03_RATIO = 4, 2.0
T06_OUTCOME = re.compile(r"(?i)(^|[\s_])(shows?|renders?|displays?|returns?|sends?|redirects?|notif\w*|emits?|records?|writes?|saves?)([\s_]|$)")
# "emits nothing", "does NOT record", "never writes": a negative promise that a never-called check keeps
T06_NEGATED = re.compile(r"(?i)(^|[\s_])(no|not|nothing|never|none|without|neither|nor|doesn'?t|don'?t|won'?t|skips?)([\s_,.;:]|$)")
T03_RULE = ("mock_verify assertions >= %d and mock_verify / max(other assertions, 1) > %.1f; "
            "weak and mock_absent (never-called) assertions count on neither side" % (T03_MIN, T03_RATIO))

T01B_NAME = re.compile(r"does[ _]?not[ _]?(raise|throw|crash|fail)|doesn'?t[ _](raise|throw|crash)|handles?|gracefully|no[ _]error|is[ _]safe|survives|tolerat|ignores", re.I)
T01B_COMMENT = re.compile(r"(#|//).*\b(should\s+not|does\s+not|doesn'?t|must\s+not|no)\s+(raise|throw|crash|error|fail)", re.I)


def classify_t01(row, body_src, file_flags):
    if sum(row["assertions"].values()):
        return None
    signals = []
    if row["calls"]:
        signals.append("calls code: " + ", ".join(row["calls"][:5]))
    if T01B_NAME.search(row["name"] or ""):
        signals.append("name states a no-raise contract")
    if T01B_COMMENT.search(body_src or ""):
        signals.append("comment states a no-raise contract")
    if file_flags.get("hook_asserts"):
        signals.append("file hook asserts")
    if file_flags.get("property_based"):
        signals.append("property-based imports")
    if row.get("param_rows"):
        signals.append("parameterized")
    # Only something that can run code under test makes it T01b: with no calls, a name that
    # promises "does not throw" has nothing left to throw. Guards stay conservative.
    can_fail = bool(row["calls"]) or file_flags.get("hook_asserts") or file_flags.get("property_based") \
        or bool(row.get("param_rows"))
    return {"kind": "b" if can_fail else "a", "signals": signals or ["no calls, no assertions"]}


# --------------------------------------------------------------------------- main

def git_ls_files(repo):
    out = subprocess.run(["git", "-C", repo, "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--files")
    ap.add_argument("--time-budget", type=float, default=600.0)
    ap.add_argument("--no-shapes", action="store_true")
    a = ap.parse_args()

    repo = os.path.realpath(a.repo)
    out = os.path.realpath(a.out)
    if os.path.commonpath([repo, out]) == repo:
        sys.exit("refusing to write inside the scanned repo: %s" % out)
    os.makedirs(out, exist_ok=True)

    t0 = time.time()
    tracked = git_ls_files(repo)
    if a.files:
        with open(a.files, encoding="utf-8") as fh:
            files = [l.strip().replace("\\", "/") for l in fh if l.strip()]
    else:
        files = [p for p in tracked if TEST_FILE.search(p) and not PRUNE.search(p)]
    helpers, evidence = helper_allowlist(repo, tracked)

    rows, file_info, errors = [], {}, []
    scanned = 0
    partial = None
    for rel in files:
        if time.time() - t0 > a.time_budget:
            partial = {"category": "test_bodies", "scanned": scanned, "total": len(files),
                       "reason": "time budget of %ss exhausted" % a.time_budget}
            break
        lang = EXT_LANG.get(os.path.splitext(rel)[1])
        scanned += 1
        if not lang:
            continue
        try:
            with open(os.path.join(repo, rel), encoding="utf-8", errors="replace") as fh:
                src = fh.read()
        except OSError as e:
            errors.append({"file": rel, "error": str(e)})
            continue
        if lang == "rs" and "#[test]" not in src and "::test]" not in src:
            continue
        try:
            if lang == "js":
                frows, flags = js_scan(rel, src, helpers)
            elif lang == "py":
                frows, flags = py_scan(rel, src, helpers)
            else:
                frows, flags = generic_scan(rel, src, lang, helpers)
        except (SyntaxError, ValueError, RecursionError) as e:
            errors.append({"file": rel, "error": "%s: %s" % (type(e).__name__, e)})
            continue
        file_info[rel] = dict(flags, tests=len(frows))
        for r in frows:
            if "_shape_py" in r:
                body_src = r.pop("_shape_py")
                shape = py_shape(body_src)
            else:
                masked_body, body_src = r.pop("_shape_src")
                shape = shape_of(masked_body, body_src)
            r["assertion_total"] = sum(r["assertions"].values())
            r["weak_only"] = r["assertion_total"] > 0 and set(r["assertions"]) == {"weak"}
            r["t01"] = classify_t01(r, body_src, flags)
            impl = r["assertions"].get("mock_verify", 0)
            behaviour = sum(v for k, v in r["assertions"].items() if k not in ("mock_verify", "mock_absent", "weak"))
            r["t03_candidate"] = impl >= T03_MIN and impl / max(behaviour, 1) > T03_RATIO
            # T06 hint: the name promises a visible outcome, but nothing asserts a value or presence
            r["t06_candidate"] = bool(T06_OUTCOME.search(r["name"] or "")) and not T06_NEGATED.search(r["name"] or "") \
                and r["assertion_total"] > 0 \
                and set(r["assertions"]) <= {"mock_absent", "weak"}
            if not a.no_shapes:
                r["shape"] = shape
            rows.append(r)

    with open(os.path.join(out, "test_bodies.jsonl"), "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds_total = {}
    for r in rows:
        for k, v in r["assertions"].items():
            kinds_total[k] = kinds_total.get(k, 0) + v
    summary = {
        "repo": repo,
        "files_listed": len(files), "files_scanned": scanned, "files_with_tests": sum(1 for f in file_info.values() if f["tests"]),
        "tests": len(rows),
        "tests_skipped": sum(1 for r in rows if r["skipped"]),
        "param_cases": sum((r["param_rows"] or 1) for r in rows),
        "assertion_kinds": kinds_total,
        "t01a": sum(1 for r in rows if r["t01"] and r["t01"]["kind"] == "a"),
        "t01b": sum(1 for r in rows if r["t01"] and r["t01"]["kind"] == "b"),
        "weak_only": sum(1 for r in rows if r["weak_only"]),
        "t03_candidates": sum(1 for r in rows if r["t03_candidate"]),
        "t06_candidates": sum(1 for r in rows if r["t06_candidate"]),
        "t03_rule": T03_RULE,
        **evidence,
        "files": file_info,
        "parse_errors": errors,
        "coverage_partial": [partial] if partial else [],
        "elapsed_s": round(time.time() - t0, 2),
    }
    spath = os.path.join(out, "test_bodies.summary.json")
    with open(spath, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False)
    print(json.dumps({k: summary[k] for k in ("tests", "param_cases", "t01a", "t01b", "weak_only", "t03_candidates",
                                               "helper_allowlist_size", "helper_allowlist_files_searched", "elapsed_s")}))
    print("parse_errors=%d partial=%s summary=%s" % (len(errors), bool(partial), spath))


if __name__ == "__main__":
    main()
