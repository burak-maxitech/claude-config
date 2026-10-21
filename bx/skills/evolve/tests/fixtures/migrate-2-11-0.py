#!/usr/bin/env python3
"""One-time migration of docs/upstream/state.json to the bx 2.11.0 schema, plus the
S61 hand-triage verdicts and the bootstrap of docs/upstream/pain-points.json.

Run from the repo root:  python -X utf8 -I bx/skills/evolve/tests/fixtures/migrate-2-11-0.py [--apply]
Without --apply it prints what it would write and changes nothing. Kept in the repo as the
record of how the 2.11.0 state came to be; it is not part of any skill's runtime."""
import hashlib, io, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
STATE = ROOT / "docs" / "upstream" / "state.json"
REG = ROOT / "docs" / "upstream" / "pain-points.json"
TODAY = "2026-10-20"
SENTINEL = "0" * 40
ORDER = ["finding_id", "decision", "date", "source_url", "affected_capability", "source_content_hash",
         "class", "title", "note", "proposed_edit", "affected_files", "source_excerpt", "citation"]

# ---------------------------------------------------------------- S61 triage verdicts
REJECT = {
    "19758d30": "superseded by 15742589 (same concern, docs-sourced); the activation gap was addressed by explicit semver versioning + the version-bump guard (S54/S60)",
    "1c627424": "a plugin-wide dependency on a project-scoped, cross-marketplace plugin would burden every bx user for one skill; /bx:webdesign's setup step owns the stitch-skills install",
    "83031ba5": "a Stop hook fires at the end of every turn, so the reminder would be noise; since v2.9.0 /bx:resume's wrap-up step invokes /bx:save itself",
    "79708ccf": "moot: S59 found no Skill(bx-*) anywhere in the repo and renamed the one stale local entry; the migration this unblocked no longer exists",
    "b866308e": "informational; the S37 symlink-retirement plan is unchanged",
    "eda8e370": "informational; the S37 symlink-retirement plan is unchanged",
    "0b6ef289": "S53 ruling stands: ReportFindings is exclusive-of-text and would drop the Convention Violations, What's Good and verification sections; /bx:review keeps its markdown report",
    "df34007f": "README's install block already carries no manual marketplace refresh (marketplace add + install); the update path is outside this finding's scope",
    "03c9a575": "command / mode:link marketplace sources do not apply to a git-hosted marketplace like burak-tools",
    "3dd5decb": "already covered by the generalized 'runs as a background subagent since v2.1.218' wording in README and workflow.md (same ruling as finding 282556d0)",
}
APPLIED = {
    "59d3bdac": "explicit await statements already present in arch/clean/evolve/seo/tests SKILL.md; verified by every fan-out run since S58 (S61 triage)",
}
DEFER = {
    "cc7d1af6": "blocked until Claude Design exposes an API/MCP; the stored hash tracks the announcement's integrations line",
    "15742589": "distribution-model decision (marketplace vs skills-dir); brainstorm when the activation gap next bites",
    "093df977": "smoke-check the eight `2>/dev/null` sites during the next /bx:health and /bx:resume deep runs; d29f48d (S60) may already be the fix",
    "55ba40ea": "remaining half = doc-tiering Phase 2 (.claude/rules tier, spec D4-D6), gated on re-verifying `paths:` against the memory docs",
    "161ae182": "needs its own design pass (eval suite in the plugin-evals format); pairs with the /bx:health dogfood",
}
OPEN_EDITS = {
    "0e4083ea": {
        "proposed_edit": "Name `/reload-skills` as the lighter refresh when only SKILL.md files changed (hooks, agents and .mcp.json still need `/reload-plugins`): in fix-mode-evolve.md's post-pass 'Next steps' block (`/reload-plugins` → `/reload-plugins` (or `/reload-skills` for SKILL.md-only edits)) and in README's 'Updating to the latest version' paragraph.",
        "affected_files": ["bx/skills/evolve/references/fix-mode-evolve.md", "README.md"],
        "citation": "https://github.com/anthropics/claude-code/releases/tag/v2.1.152",
    },
    "dadac845": {
        "proposed_edit": "Before Phase 3's first per-page rollback (`git restore .` + `git clean -fd`, phase3-inject.md), add an explicit user-confirmation step and phrase the cleanup as a user-requested discard of the failed injection, so auto mode's destructive-git classifier reads it as requested; keep the Phase 1 invariant text in step. Verify live on the kaanarik Phase-3 run before treating as confirmed breakage.",
        "affected_files": ["bx/skills/webdesign/references/phase3-inject.md", "bx/skills/webdesign/references/phase1-extract.md"],
        "citation": "https://github.com/anthropics/claude-code/releases/tag/v2.1.183 · https://code.claude.com/docs/en/auto-mode-config",
    },
}

# ---------------------------------------------------------------- pain registry bootstrap
STOP = set("this that with from into when then than they have been will skill skills still after before".split())


def significant(text):
    """state-schema.md 'Significant words': lowercase tokens of letters/digits joined by -, . or :
    (so `start-claude.ps1` and `/bx:arch` survive as one word), at least four alphanumerics,
    possessive 's dropped, stoplist removed."""
    t = re.sub(r"[’']s\b", "", text.lower())
    words = []
    for tok in re.findall(r"[a-z0-9]+(?:[-.:][a-z0-9]+)*", t):
        if len(re.sub(r"[^a-z0-9]", "", tok)) >= 4 and tok not in STOP:
            words.append(tok)
    return words


def make_id(text):
    """First four significant words, kebab-joined, truncated at a word boundary to <= 40 chars."""
    parts = []
    for w in significant(text)[:4]:
        k = re.sub(r"[^a-z0-9]+", "-", w).strip("-")
        if parts and len("-".join(parts + [k])) > 40:
            break
        parts.append(k)
    return re.sub(r"-+", "-", "-".join(parts)).strip("-")[:40].rstrip("-")


def lead_of(line):
    m = re.match(r"^\s*(?:\d+\.\s+|[-*]\s+)?(?:\[[ x]\]\s*)?\*\*(.+?)\*\*", line)
    if m:
        return m.group(1).strip().rstrip(":.")
    body = re.sub(r"^\s*(?:\d+\.\s+|[-*]\s+)", "", line)
    return re.split(r" — |\. ", body, 1)[0].strip()


def live_leads():
    leads = []
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    i = claude.index("## Known Issues / Blockers")
    for line in claude[i + 1:]:
        if line.startswith("## "):
            break
        if line.startswith("**") or re.match(r"^(- |\* |\d+\. )", line):
            leads.append(("claude-md", lead_of(line)))
    status = (ROOT / "docs" / "STATUS.md").read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    i = status.index("## Next Steps")
    for line in status[i + 1:]:
        if line.startswith("## "):
            break
        if re.match(r"^\d+\. ", line):
            leads.append(("status-md", lead_of(line)))
    return leads


# old slug -> (registry id text to match, or None for retired) — the 8 pre-2.11.0 slugs
ALIAS_TARGET = {
    "plugin-cache-staleness-after-every-push-activation-gap": "Plugin-versioning sharp edge (S54)",
    "plugin-cache-staleness-skills-run-from-cache-a-bx-push-without-a-version-bump-reaches-no-user": "Plugin-versioning sharp edge (S54)",
    "s37-leftovers-install-smoke-test-symlink-retirement-settings-skillbx-to-skillbx": "S37 plugin-packaging leftovers",
    "s37-plugin-packaging-leftovers-install-smoke-test-symlink-retirement": "S37 plugin-packaging leftovers",
    "bx-health-never-run-end-to-end": "Dogfood `/bx:health`",
    "stitch-mcp-stitch-skills-plugin-not-yet-installed": None,
    "permission-prompts-when-allowed-tools-misses-a-command": None,
    "claude-md-over-its-size-target-with-no-path-scoped-rules-tier": None,
}
RETIRED_TEXT = {
    "stitch-mcp-stitch-skills-plugin-not-yet-installed": "Stitch MCP + stitch-skills plugin not yet installed",
    "permission-prompts-when-allowed-tools-misses-a-command": "permission prompts when allowed-tools misses a command",
    "claude-md-over-its-size-target-with-no-path-scoped-rules-tier": "CLAUDE.md over its size target with no path-scoped rules tier",
}


def main():
    apply = "--apply" in sys.argv
    state = json.loads(STATE.read_text(encoding="utf-8"))
    decisions = state["decisions"]
    by_prefix = {e["finding_id"][:8]: e for e in decisions}

    # 1. verdicts
    for p, note in REJECT.items():
        e = by_prefix[p]; e.update(decision="rejected", date=TODAY, note=note)
    for p, note in APPLIED.items():
        e = by_prefix[p]; e.update(decision="applied", date=TODAY, note=note)
    for p, note in DEFER.items():
        e = by_prefix[p]; e.update(decision="deferred", date=TODAY, note=note)

    # 2. 2.11.0 fields on every entry
    for e in decisions:
        e.setdefault("proposed_edit", None)
        e.setdefault("affected_files", [])
        e.setdefault("source_excerpt", None)
        e.setdefault("citation", None)
    for p, edit in OPEN_EDITS.items():
        e = by_prefix[p]
        assert e["decision"] == "open", p
        e.update(edit)

    # 3. registry
    earliest = {}
    for e in decisions:
        cap = e["affected_capability"]
        if cap.startswith("bx:pain/"):
            slug = cap[len("bx:pain/"):]
            earliest[slug] = min(earliest.get(slug, e["date"]), e["date"])
    registry, by_text = [], {}
    for source, text in live_leads():
        pid = make_id(text)
        assert pid and pid not in {r["id"] for r in registry}, (pid, text)
        r = {"id": pid, "text": text[:160], "source": source, "status": "active", "aliases": [],
             "first_seen": TODAY, "last_seen": TODAY}
        registry.append(r); by_text[text] = r
    slug_to_id = {}
    for slug, target in ALIAS_TARGET.items():
        if target is None:
            r = {"id": make_id(RETIRED_TEXT[slug]), "text": RETIRED_TEXT[slug], "source": "claude-md",
                 "status": "retired", "aliases": [slug], "first_seen": earliest.get(slug, TODAY), "last_seen": earliest.get(slug, TODAY)}
            registry.append(r)
        else:
            r = by_text[target]
            r["aliases"].append(slug)
            r["first_seen"] = min(r["first_seen"], earliest.get(slug, TODAY))
        slug_to_id[slug] = r["id"]

    # 4. rewrite pain capabilities + recompute ids
    renamed = []
    for e in decisions:
        cap = e["affected_capability"]
        if cap.startswith("bx:pain/"):
            slug = cap[len("bx:pain/"):]
            new_cap = "bx:pain/" + slug_to_id[slug]
            old_id = e["finding_id"]
            e["affected_capability"] = new_cap
            e["finding_id"] = hashlib.sha1((e["source_url"] + "|" + new_cap).encode("utf-8")).hexdigest()
            renamed.append((old_id[:8], e["finding_id"][:8], new_cap))

    # 5. watermark + ordering
    wm = state["watermark"]
    wm = {"last_changelog_version": wm["last_changelog_version"], "docs_checked_at": wm["docs_checked_at"],
          "community_checked_at": wm["community_checked_at"], "changelog_gap": None}
    decisions = [{k: e[k] for k in ORDER} for e in decisions]
    out = {"watermark": wm, "decisions": decisions}

    from collections import Counter
    print("verdicts:", Counter(e["decision"] for e in decisions))
    print("renamed finding_ids:"); [print("  ", a, "->", b, c) for a, b, c in renamed]
    print("registry:"); [print("  ", r["status"][:3], r["id"], "|", r["text"][:60], "| aliases:", r["aliases"]) for r in registry]
    if apply:
        io.open(STATE, "w", encoding="utf-8", newline="").write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
        io.open(REG, "w", encoding="utf-8", newline="").write(json.dumps({"pain_points": registry}, indent=2, ensure_ascii=False) + "\n")
        print("written:", STATE, REG)
    else:
        print("dry run — nothing written (pass --apply)")


if __name__ == "__main__":
    main()
