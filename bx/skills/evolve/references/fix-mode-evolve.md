# --fix Mode — /bx:evolve

Apply upstream-driven edits to plugin files with per-finding diff preview. **Upstream fixes touch multiple sibling files in a single finding**, so this mode requires combined diffs and enforces the S45 completeness rule.

---

## Eligibility

A finding is fix-eligible only if **all** of the following hold. Check each in order; a single failure routes the finding to display-only (it appears in the report but is not offered for application).

1. **`tier: official`** — the finding originates from the changelog or docs lane, not the community lane. Advisory findings (community source) are never fix-eligible, regardless of the `--fix` flag. Why: community sources are not authoritative — acting on them without human review inverts the skill's risk model.

2. **Current decision-log state is `open` or re-raised** — the finding has `decision: "open"` in `docs/upstream/state.json`, including entries re-raised from `rejected` because their `source_content_hash` changed. `deferred` findings that were re-emitted by a lane re-surface in the report (Section 2 when re-emitted live, Section 4 when carried forward) but are not offered to `--fix` — they are deferred deliberately. `applied` findings are not surfaced at all. `rejected`-and-unchanged findings are suppressed from the report entirely. Why: acting on a deferred or rejected finding without explicit re-evaluation bypasses the decision log. (Sentinels never enter the decision log, so they can never satisfy this rule.)

3. **The proposed edit is a text change to files inside this repo** — the `affected_files` list contains only paths within this repo, excluding: historical archives (`docs/key-decisions.md`, `docs/session-history.md`, CLAUDE.md history sections) and `docs/upstream/state.json` (state writes are owned by the decision-log mechanics, not by finding edits). `README.md` and `workflow.md` ARE fix-eligible — they are operational docs and the lanes' Grep scope includes them deliberately (S45 sibling-echo rule). Changes that require external actions (updating a dependency, running a CLI, adding a new file not yet in the repo) are not mechanically applyable via Edit and are display-only. Why: the Edit tool requires an existing file with a unique old_string — non-text or out-of-repo changes cannot be expressed as Edit operations.

If all three hold, the finding is fix-eligible and joins the ordered gate flow below.

**Eligible set scope:** only findings consolidated THIS RUN (Section 2 of the report) are gated. Section 4 carried-forward entries are display-only — `state.json` lacks the diff-able `source_excerpt` field for them (they were never re-emitted this run). To act on a carried-forward entry, re-run `/bx:evolve` so a lane re-emits it and Section 2 picks it up.

---

## Pre-pass summary

Before showing the first finding, print a one-line summary:

```
--fix pass: N findings eligible, M display-only (advisory/deferred/out-of-scope).
Walking eligible findings in rank order (breakage first, then best-practice, then opportunities).
```

---

## Per-finding gate flow

Walk eligible findings in rank order: breakage (by sev DESC, cert DESC), then best_practice, then opportunity. For each:

```
─────────────────────────────────────────────────────────────────────
[Finding 1 of N] breakage · H — `allowed-tools` glob syntax changed

Upstream delta: MCP `allowed-tools` now accepts glob patterns (v2.1.169). The old exact-string
format will be removed in a future release. Four bx skills use the deprecated format.

Citation: https://code.claude.com/docs/en/settings#allowed-tools · v2.1.169 release notes

Affected files (all — applying to a subset leaves sibling echoes, reintroducing the drift this
finding exists to fix):
- bx/skills/seo/SKILL.md
- bx/skills/save/SKILL.md
- bx/skills/clean/SKILL.md
- bx/skills/arch/SKILL.md

Combined diff (all affected files in one block):
--- bx/skills/seo/SKILL.md
+++ bx/skills/seo/SKILL.md
@@ -12,1 +12,1 @@
-  - Bash(gsc-parse-helper*)
+  - Bash(gsc-parse-helper.py *)
--- bx/skills/save/SKILL.md
+++ bx/skills/save/SKILL.md
@@ -8,1 +8,1 @@
-  - Bash(wc)
+  - Bash(wc *)

Apply? [y / n / skip / abort]
```

**Show the diff BEFORE applying — never apply and ask later.**

The combined diff covers ALL files in `affected_files`. Partial application reintroduces the sibling echoes that the finding exists to eliminate (the S45 doc-drift rule); the orchestrator applies all or none.

**Verdicts:**

- `y` — apply the edit to every file in `affected_files` using the Edit tool, one file at a time in list order. After all edits succeed, record the verdict in the in-context decision object: `decision: "applied"`, `date`: today, `note`: one-line description of what was changed. The single state write happens at the end of the pass (or immediately on abort), per state-schema's checkpoint rule.
- `n` — record in-context: `decision: "rejected"`, `date`: today, `note`: reason. Advance to the next finding.
- `skip` — leave `decision: "open"` (no in-context change). Advance to the next finding. The finding re-surfaces next run.
- `abort` — stop the pass immediately. Findings already acted on in this pass keep their in-context verdicts. Write state immediately (Checkpoint 2 on abort). Remaining eligible findings stay `open`. Print the summary (below) with remaining counts as "aborted-remaining".

---

## Edit-tool edge cases

- **Non-unique `old_string` (partial-application failure):** if an Edit fails mid-finding (e.g. non-unique old_string) after some of the finding's files were already edited:
  - **(a) If none of the already-edited files were touched by a previously APPLIED finding this pass:** revert them with `git checkout -- <those files>` and mark the finding "skipped (could not apply mechanically)" — do NOT write `applied` to the decision log. Advance to the next finding. Surface in the post-pass summary.
  - **(b) If any of the already-edited files WERE touched by an earlier applied finding:** do NOT revert (you would destroy the other finding's edits). Disclose loudly which files are now partially edited, set this finding's decision to `deferred` with note "partial application — manual reconciliation needed", and continue. **Why:** silent partial application reintroduces exactly the sibling-echo drift this mode exists to prevent.
- **Multiple findings in the same file:** because this mode groups all affected files into one combined diff per finding, and findings are distinct upstream deltas, two findings are unlikely to target the same line. If they do, present them sequentially — the Edit tool matches `old_string` so line offsets are irrelevant.
- **Finding touches a references/ file alongside a SKILL.md:** include both in the same combined diff and the same `y`/`n` gate. The user approves the whole finding, not individual files.

---

## After the pass

Print a summary:

```
--fix pass complete.

Applied:          3 findings across 7 files
Rejected:         1
Skipped:          1 (including 0 could-not-apply-mechanically)
Aborted-remaining: 0

Next steps:
- Run `/plugin update bx` then `/reload-plugins` (or relaunch `cc`) — the plugin cache does not
  pick up edits until refreshed.
- For any SKILL.md that received non-trivial edits, consider the S42 content-review treatment:
  invoke skill-creator's qualitative review on the updated skill before the next real run.
- Use `Esc Esc` or `/rewind` to undo individual edits.
- If you ran this on a dedicated branch: `git checkout main && git branch -D <branch>` discards
  the entire pass.
```

The "applied" count shows findings, not files. Surface the file count separately so the scope is clear.

---

## What this mode does NOT do

- **Run other skills.** Verification (does the edit work?) is out of scope — call `/bx:review` or `/bx:tests` separately if needed.
- **Edit historical archives.** `docs/key-decisions.md`, `docs/session-history.md`, and the history sections of `CLAUDE.md` are repo records-of-past-state per the S32 convention. They are never touched by `--fix` mode.
- **Touch files outside the repo.** MCP configs, shell profiles, OS settings — out of scope.
- **Apply advisory findings.** Community-sourced findings (tier: community) are never fix-eligible; they render in Section 3 of the report only.
- **Advance the watermark.** The orchestrator advances the watermark at the end of every run (Step 6) regardless of whether `--fix` was passed. Fix-mode verdicts are written to the decision log; they do not alter the watermark logic. See `bx/skills/evolve/references/state-schema.md` Rule 4.