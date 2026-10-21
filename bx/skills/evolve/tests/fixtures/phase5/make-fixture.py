#!/usr/bin/env python3
"""Regenerates the phase-5 rehearsal fixture: --fix pre-pass over carried-forward (Section 4)
entries — staleness re-grep, auto-close, legacy and no-token display-only cases. Run from
the repo root: python -I <this file>. Writes state.json and expected.md beside this script.
The fixture's affected_files point at REAL files in this repo so the re-grep is real."""
import hashlib, io, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
S = "0" * 40
R = lambda v: f"https://github.com/anthropics/claude-code/releases/tag/v{v}"
D = lambda p: f"https://code.claude.com/docs/en/{p}"


def fid(u, c):
    return hashlib.sha1((u + "|" + c).encode()).hexdigest()


def entry(dec, date, url, cap, cls, title, note, edit, files, exc, cit, legacy=False):
    e = {"finding_id": fid(url, cap), "decision": dec, "date": date, "source_url": url,
         "affected_capability": cap, "source_content_hash": S, "class": cls, "title": title, "note": note}
    if not legacy:
        e.update({"proposed_edit": edit, "affected_files": files, "source_excerpt": exc, "citation": cit})
    return e


state = {
    "watermark": {"last_changelog_version": "2.1.284", "docs_checked_at": "2026-09-28",
                  "community_checked_at": "2026-09-28", "changelog_gap": None},
    "decisions": [
        # LIVE: token still present in the one affected file
        entry("open", "2026-09-28", D("permissions"), "bx:save/writer-tools", "best_practice",
              "Bash permission specifiers: prefer `Bash(cmd *)` over `Bash(cmd:*)` for plugin agents", None,
              "`Bash(wc:*)` → `Bash(wc *)` in the save-writer agent's tools line",
              ["bx/agents/save-writer.md"], "## Bash specifiers\nPrefer the space form.", D("permissions") + "#bash"),
        # STALE: token absent from every affected file (the .ps1 was deleted in S59)
        entry("open", "2026-08-24", R("2.1.240"), "bx:save/session-start-hook", "breakage",
              "Hook scripts must be bash; drop the PowerShell twin from README and hooks.json", None,
              "remove `session-start-context.ps1` from README.md and bx/hooks/hooks.json",
              ["README.md", "bx/hooks/hooks.json"], "### 2.1.240\n- Hooks run under bash on every platform.", R("2.1.240")),
        # LEGACY: nine keys, no stored edit
        entry("open", "2026-06-10", R("2.1.157"), "bx:pain/plugin-cache-staleness", "opportunity",
              "Plugins in `.claude/skills` auto-load (no marketplace) — could eliminate the activation gap", None,
              None, [], None, None, legacy=True),
        # NO TOKEN: prose-only edit, nothing quotable to grep
        entry("open", "2026-09-28", D("plugin-evals"), "bx:pain/bx-health-never-run", "opportunity",
              "`claude plugin eval` could give bx a committed eval suite", None,
              "Design an eval suite for the bx plugin using the plugin-evals format; no existing text changes.",
              ["bx/skills/health/SKILL.md"], "## Plugin evals\n…", D("plugin-evals")),
        # NOT A CANDIDATE: deferred
        entry("deferred", "2026-07-05", R("2.1.190"), "bx:webdesign/stitch-design-engine", "opportunity",
              "Claude Design — candidate to replace Google Stitch", "revisit after the kaanarik run",
              "swap the Stitch MCP for Claude Design", ["bx/skills/webdesign/SKILL.md"], "### 2.1.190\n- Claude Design.", R("2.1.190")),
    ],
}
io.open(HERE / "state.json", "w", encoding="utf-8", newline="").write(json.dumps(state, indent=2, ensure_ascii=False) + "\n")

ids = [e["finding_id"][:8] for e in state["decisions"]]
expected = f"""# Expected outcome — phase 5 fixture (`--fix` pre-pass over Section 4 entries; no lane ran, so Section 2 is empty)

Five stored entries. Today 2026-10-20, session S61.

| entry | stored decision | edit stored? | re-grep | outcome |
|---|---|---|---|---|
| {ids[0]} `bx:save/writer-tools` | open | yes | token `Bash(wc:*)` found in bx/agents/save-writer.md (1 of 1 files) | **eligible**, gated normally |
| {ids[1]} `bx:save/session-start-hook` | open | yes | token `session-start-context.ps1` absent from README.md AND bx/hooks/hooks.json (0 of 2) | **auto-closed (stale)**: decision → applied, date → 2026-10-20, note → "closed at re-grep 2026-10-20: token absent in all affected_files" |
| {ids[2]} `bx:pain/plugin-cache-staleness` | open | no (legacy 9-key) | not attempted | display-only `[legacy — no stored edit]` |
| {ids[3]} `bx:pain/bx-health-never-run` | open | prose only | no token identifiable | display-only (fails rule 3: no existing text changes; would also be `[no re-grep token]`), stays open |
| {ids[4]} `bx:webdesign/stitch-design-engine` | deferred | yes | not attempted (rule 2: deferred is never offered) | display-only `[deferred 2026-07-05]` |

## Expected pre-pass summary
```
--fix pass: 1 findings eligible (0 from this run, 1 carried forward), 3 display-only (advisory/deferred/legacy/out-of-scope).
Auto-closed (stale): 1 carried-forward entries whose token is absent from every affected file — {ids[1]} Hook scripts must be bash; drop the PowerShell twin from README and hooks.json
Walking eligible findings in rank order (breakage first, then best-practice, then opportunities).
Allowlist candidates to offer after the findings: 0
```
(The `Allowlist candidates` line exists only after Phase 6 lands; before that the summary has three lines.)

## Expected gate display for the one eligible finding
`[Finding 1 of 1] best_practice · M — Bash permission specifiers …`, affected files: bx/agents/save-writer.md (1), diff replaces `Bash(wc:*)` with `Bash(wc *)` on that file's `tools:` line, prompt `Apply? [y / n / skip / abort]`. The rehearsal stops here without answering.

## Default-mode closing line (if this were a report run)
`Run /bx:evolve --fix to act on up to 3 fix-eligible findings (4 open in total, 1 legacy display-only, 1 deferred). The pass re-greps …` — N=3 is the stored-field upper bound ({ids[0]}, {ids[1]}, {ids[3]}); the pre-pass then auto-closes one and sets one aside, which the line says may happen.

## Checkpoint 2 (what would be written on abort/completion before any verdict)
Only the auto-close mutation: {ids[1]} → applied. Every other entry unchanged. `check-state.py` passes (one legacy warning; the missing registry is a warning, not a failure).

"""
io.open(HERE / "expected.md", "w", encoding="utf-8", newline="").write(expected)
print("phase5 fixture written:", ids)
