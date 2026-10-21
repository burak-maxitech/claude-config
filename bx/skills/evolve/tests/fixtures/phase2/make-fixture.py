#!/usr/bin/env python3
"""Regenerates the phase-2 rehearsal fixture (Step 3 consolidation: same-source dedup,
applied branch, source_url match). Run from the repo root: python -I <this file>.
Outputs state.json, lane-output.json, inputs.json, expected.md beside this script."""
import hashlib, io, json, re, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent


def h(text):
    n = unicodedata.normalize("NFC", text).strip()
    return hashlib.sha1(re.sub(r"[ \t\n\r]+", " ", n).encode()).hexdigest()


def fid(u, c):
    return hashlib.sha1((u + "|" + c).encode()).hexdigest()


S = "0" * 40
R = lambda v: f"https://github.com/anthropics/claude-code/releases/tag/v{v}"
D = lambda p: f"https://code.claude.com/docs/en/{p}"


def entry(dec, date, url, cap, hsh, cls, title, note, edit, files, exc, cit):
    return {"finding_id": fid(url, cap), "decision": dec, "date": date, "source_url": url,
            "affected_capability": cap, "source_content_hash": hsh, "class": cls, "title": title,
            "note": note, "proposed_edit": edit, "affected_files": files, "source_excerpt": exc,
            "citation": cit}


def finding(cls, sev, cert, files, delta, edit, url, cap, exc, cit=None):
    return {"finding_id": None, "class": cls, "tier": "official", "severity": sev, "certainty": cert,
            "affected_files": files, "upstream_delta": delta, "proposed_edit": edit,
            "citation": cit or url, "source_url": url, "affected_capability": cap, "source_excerpt": exc}


EX = {
    "A": "### 2.1.300\n- `claude plugin validate` gains `--json` output for CI.",
    "Bold": "### SessionStart\nRuns when a session starts. Matchers: startup, resume, clear.",
    "Bnew": "### SessionStart\nRuns when a session starts. Matchers: startup, resume, clear, compact.",
    "C": "### 2.1.301\n- `/bx:health`-style routing advisors should use the `effort` key.",
    "Dnew": "### 2.1.302\n- TaskCreate/TaskList removed from the default toolset on current models.",
    "E": "### 2.1.233\n- Task tools are no longer in the default toolset.",
    "F": "### 2.1.303\n- New ReportFindings tool.",
    "G": "### 2.1.304\n- Releases API pagination.",
    "H": "## Findings\nRendered natively.",
}

state = {
    "watermark": {"last_changelog_version": "2.1.299", "docs_checked_at": "2026-10-01",
                  "community_checked_at": "2026-10-01", "changelog_gap": None},
    "decisions": [
        entry("applied", "2026-10-01", R("2.1.300"), "bx:save/plugin-validate", h(EX["A"]), "best_practice",
              "plugin validate --json for CI", "Part 8 step 2b uses --json",
              "Part 8 step 2b: add `--json`", ["bx/skills/save/references/mode-update.md"], EX["A"], R("2.1.300")),
        entry("applied", "2026-10-01", D("hooks"), "bx:save/session-start-hook", h(EX["Bold"]), "best_practice",
              "SessionStart matcher list", "hooks.json already lists startup|resume|clear",
              "hooks.json matcher: startup|resume|clear", ["bx/hooks/hooks.json"], EX["Bold"], D("hooks") + "#sessionstart"),
        entry("rejected", "2026-10-01", R("2.1.301"), "bx:health/routing", h(EX["C"]), "best_practice",
              "effort key on routing advisors", "health already declares effort: low",
              "add effort: low", ["bx/skills/health/SKILL.md"], EX["C"], R("2.1.301")),
        entry("applied", "2026-10-01", R("2.1.302"), "bx:plan/task-tools", S, "breakage",
              "Task tools removed from default toolset", "task-tools.md owns the degraded path",
              "cite task-tools.md", ["bx/skills/plan/SKILL.md"], None, R("2.1.302")),
        # legacy 9-key applied entry — the e1e67d43 / 5d1459d5 duplicate class
        {"finding_id": fid(R("2.1.233"), "bx:skills/task-tracker-tools"), "decision": "applied",
         "date": "2026-08-24", "source_url": R("2.1.233"),
         "affected_capability": "bx:skills/task-tracker-tools", "source_content_hash": h(EX["E"]),
         "class": "breakage", "title": "Task tools left the default toolset (v2.1.233)",
         "note": "task-tools.md created S58"},
    ],
}

lane = {
    "changelog": {"lane_status": "ok", "releases_scanned": 6, "newest_version_seen": "2.1.305", "findings": [
        finding("best_practice", "medium", 0.8, ["bx/skills/save/references/mode-update.md"],
                "plugin validate --json", "use --json", R("2.1.300"), "bx:save/plugin-validate", EX["A"]),
        finding("best_practice", "low", 0.7, ["bx/skills/health/SKILL.md"],
                "effort key", "add effort: low", R("2.1.301"), "bx:health/routing", EX["C"]),
        finding("breakage", "high", 1.0, ["bx/skills/plan/SKILL.md"],
                "Task tools removed", "cite task-tools.md", R("2.1.302"), "bx:plan/task-tools", EX["Dnew"]),
        finding("opportunity", "medium", 0.6, ["bx/skills/review/SKILL.md", "README.md"],
                "ReportFindings tool", "offer ReportFindings output", R("2.1.303"), "bx:review/report-findings", EX["F"]),
        finding("breakage", "high", 0.9, ["bx/skills/evolve/references/scan-changelog.md"],
                "gh api releases pagination default changed", "paginate", R("2.1.304"), "bx:evolve/changelog-window", EX["G"]),
        finding("breakage", "medium", 0.5, ["bx/skills/evolve/references/scan-changelog.md", "bx/skills/evolve/SKILL.md"],
                "window gap: the pagination default change breaks the 50-release assumption", "record a gap", R("2.1.304"), "bx:pain/changelog-window-gap", EX["G"]),
        finding("breakage", "high", 1.0, ["bx/skills/save/references/task-tools.md"],
                "Task tools not default", "document degraded path", R("2.1.233"), "bx:skills/task-tracker-tools-v2", EX["E"]),
    ]},
    "docs": {"lane_status": "ok", "findings": [
        finding("best_practice", "medium", 0.8, ["bx/hooks/hooks.json"],
                "SessionStart gained a compact matcher", "matcher: startup|resume|clear|compact",
                D("hooks"), "bx:save/session-start-hook", EX["Bnew"], D("hooks") + "#sessionstart"),
        finding("opportunity", "low", 0.5, ["bx/skills/review/SKILL.md"],
                "code-review doc describes host-native findings", "mention in ladder",
                D("code-review"), "bx:review/output-format", EX["H"]),
    ]},
    "community": {"lane_status": "skipped", "findings": []},
}

inputs = {"today": "2026-10-20",
          "capability_inventory": ["bx:save/plugin-validate", "bx:save/session-start-hook", "bx:health/routing",
                                   "bx:plan/task-tools", "bx:review/report-findings", "bx:review/output-format",
                                   "bx:evolve/changelog-window", "bx:skills/task-tracker-tools"],
          "pain_point_list": ["changelog window gap"]}

expected = f"""# Expected outcome — phase 2 fixture (Step 3 only)

Inputs: `state.json` (5 stored entries, one legacy 9-key), `lane-output.json` (7 changelog + 2 docs findings, community skipped), `inputs.json`.

## Step 3.2 same-source dedup
- The two changelog findings on {R("2.1.304")} share a URL and `scan-changelog.md` -> ONE finding, capability `bx:evolve/changelog-window` (same class breakage; higher severity x certainty: 3x0.9 > 2x0.5), `affected_files` = both files, citation stays one URL (identical), kept `upstream_delta` gains `(also addresses bx:pain/changelog-window-gap)`. Footer: 1 same-source collapse.
- {R("2.1.303")} vs docs `code-review`: different URLs -> NOT merged (3.5's capability rule does not merge them either: different capabilities).
- After dedup: 8 findings to hash.

## Step 3.4 decision-log filter
| live finding | match | branch | result |
|---|---|---|---|
| v2.1.300 plugin-validate | exact id, applied, hash == stored | applied unchanged | suppressed |
| docs hooks session-start-hook | exact id, applied, hash != stored | applied changed | surfaced `[re-raised — source changed since application]`; stored -> open, new hash {h(EX["Bnew"])[:8]}…, date 2026-10-20, note "was applied: hooks.json already lists startup|resume|clear", title <- "SessionStart gained a compact matcher", edit fields refreshed, class unchanged |
| v2.1.301 health/routing | exact id, rejected, hash == stored | rejected unchanged | suppressed |
| v2.1.302 plan/task-tools | exact id, applied, stored hash is the sentinel | applied + sentinel | suppressed; stored hash <- live hash {h(EX["Dnew"])[:8]}…, source_excerpt <- live excerpt |
| v2.1.233 task-tracker-tools-v2 | no exact id; same source_url as the legacy entry (affected_files absent, same class); passes 3.3 by that match | matched by source_url -> applied, hash == stored | suppressed; legacy entry upgraded to 13 keys from the live finding (decision/date/note untouched); NO new entry appended; footer "1 matched to a stored entry by source_url" |
| v2.1.303 review/report-findings | none | new | surfaced, written open |
| v2.1.304 evolve/changelog-window (merged) | none | new | surfaced, written open with union affected_files |
| docs code-review review/output-format | none | new | surfaced, written open |

## Expected footer block
```
Decision-log filters applied this run:
  1 rejected findings suppressed (source_content_hash unchanged — source not rewritten since rejection)
  0 rejected finding re-raised (source_content_hash changed → transitioned to open)
  3 applied findings suppressed (source_content_hash unchanged — includes 1 sentinel entry whose live hash is now stored)
  1 applied finding re-raised (source_content_hash changed → transitioned to open)
  1 matched to a stored entry by source_url (capability string differed from the stored one)
  1 same-source collapse at Step 3.2 (two lane findings merged before hashing)
```
Headline: Breakage 1 (v2.1.304 merged) · Best-practice 1 (re-raised hooks) · Opportunities 2 (v2.1.303, docs code-review) · Advisory 0.
Open entries written this run: 4 (3 new + 1 re-raised). Decisions array after Checkpoint 1: 8 entries (5 + 3), no duplicates; the former legacy entry now has 13 keys (same hash, decision, date, note); `check-state.py` passes on the written state with no legacy warning.
"""


def dump(name, obj):
    io.open(HERE / name, "w", encoding="utf-8", newline="").write(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


dump("state.json", state)
dump("lane-output.json", lane)
dump("inputs.json", inputs)
io.open(HERE / "expected.md", "w", encoding="utf-8", newline="").write(expected)
print("phase2 fixture written")
