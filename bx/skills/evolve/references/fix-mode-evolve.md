# --fix Mode — /bx:evolve

Apply upstream-driven edits to plugin files with per-finding diff preview. **Upstream fixes touch multiple sibling files in a single finding**, so this mode requires combined diffs and enforces the S45 completeness rule.

---

## Eligibility

A finding is fix-eligible only if **all** of the following hold. Check each in order; a single failure routes the finding to display-only (it appears in the report but is not offered for application).

1. **`tier: official`** — the finding originates from the changelog or docs lane, not the community lane. A carried-forward (Section 4) entry always passes this rule: advisory findings are never written to the decision log, so every stored entry is official by construction (no `tier` field is stored). Advisory findings (community source) are never fix-eligible, regardless of the `--fix` flag. Why: community sources are not authoritative — acting on them without human review inverts the skill's risk model.

2. **Current decision-log state is `open` or re-raised, with a stored edit** — the finding has `decision: "open"` in `docs/upstream/state.json` (including entries re-raised from `rejected` or `applied` because their `source_content_hash` changed) AND its stored `proposed_edit` is non-null and `affected_files` is non-empty. A legacy entry (no stored edit) is display-only, badged `[legacy — no stored edit]`, until a lane re-emits it (Rule 6 fills the fields) or the one-time triage does. `deferred` findings that were re-emitted by a lane re-surface in the report (Section 2 when re-emitted live, Section 4 when carried forward) but are not offered to `--fix` — they are deferred deliberately. `applied`-and-unchanged findings are suppressed from the report (state-schema Rule 6); an applied finding whose source changed re-enters as `open` and is eligible like any other. `rejected`-and-unchanged findings are suppressed from the report entirely. Why: acting on a deferred or rejected finding without explicit re-evaluation bypasses the decision log. (Sentinels never enter the decision log, so they can never satisfy this rule.)

3. **The proposed edit is a text change to files inside this repo** — the `affected_files` list contains only paths within this repo, excluding: historical archives (`docs/key-decisions.md`, `docs/session-history.md`, CLAUDE.md history sections) and `docs/upstream/state.json` (state writes are owned by the decision-log mechanics, not by finding edits). `README.md` and `workflow.md` ARE fix-eligible — they are operational docs and the lanes' Grep scope includes them deliberately (S45 sibling-echo rule). Changes that require external actions (updating a dependency, running a CLI, adding a new file not yet in the repo) are not mechanically applyable via Edit and are display-only. Why: the Edit tool requires an existing file with a unique old_string — non-text or out-of-repo changes cannot be expressed as Edit operations.

If all three hold, the finding is fix-eligible and joins the ordered gate flow below.

**Eligible set scope:** findings consolidated THIS RUN (Section 2) and carried-forward `open` entries (Section 4) are both gated — since bx 2.11.0 every open entry stores its `proposed_edit`, `affected_files`, `source_excerpt` and `citation`, so a Section 4 entry is as applyable as a live one. Section 4 entries go through the **staleness re-grep** below before they enter the gate flow; Section 2 findings were Grep-populated minutes ago and skip it.

**Staleness re-grep (Section 4 entries only).** For each candidate, take the old token from its `proposed_edit` (the left side of its `old → new`, or the quoted token when the edit is prose) and Grep it across the entry's `affected_files` only:
- **Hit in every file** → gate normally.
- **Hit in some files** → gate normally with `affected_files` narrowed to the files that still contain the token; say so in the per-finding display ("affected_files narrowed from N to M at re-grep").
- **Hit in no file** → the edit has already happened or the surface is gone. Do NOT gate. Record in-context `decision: "applied"`, `date`: today, `note`: `"closed at re-grep <today>: token absent in all affected_files"`, and list the entry under **Auto-closed (stale)** in the pre-pass summary so the user sees every verdict the pass took without asking. The decision log keeps the entry, so the user can reopen it by hand. Auto-closed entries are counted on their own line, not in the display-only count.
- **No token can be identified** (prose-only `proposed_edit`, after rules 1–3 passed) → display-only, badged `[no re-grep token]`; it stays `open`. An entry that already failed rule 3 (new file, external action) is display-only by that rule and gets no re-grep.

The token is the text between the backticks on the left of `→` (or the first backticked token in a prose edit), matched literally — escape regex metacharacters when you Grep. For a carried-forward entry the gate display uses the stored `title` as the upstream delta and renders `—` for severity and certainty, which are not stored.

---

## Allowlist candidates

After the finding gate flow, walk the run's `allowlist_candidates` (Step 3.1) in order. Each becomes a synthetic fix item: the edit is one new row in `bx/skills/evolve/references/scan-docs.md`'s pinned-allowlist table (URL, capability area from the candidate's reason, note `added <today> (S<N>)`) plus the date clause in the sentence above that table. Show the row as a diff and take `y` / `n` / `skip` exactly like a finding; `n` records nothing in the decision log (candidates are not findings) but the report notes the refusal so the candidate is not re-proposed from the same lane note next run — put the URL and `declined <today>` in the lane's row note instead. `y` appends the row; the docs lane fetches the page from the next run on. Candidates are never auto-applied.

## Pre-pass summary

Before showing the first finding, print a one-line summary:

```
--fix pass: N findings eligible (A from this run, B carried forward), M display-only (advisory/deferred/legacy/out-of-scope).
Auto-closed (stale): K carried-forward entries whose token is absent from every affected file — <finding_id prefix> <title>, …
Walking eligible findings in rank order (breakage first, then best-practice, then opportunities).
Allowlist candidates to offer after the findings: C
```

Render the `Auto-closed (stale)` line every pass, with `0` and no list when nothing was closed. Singular/plural wording is free; the numbers are fixed.

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

- `y` — apply the edit to every file in `affected_files` (as narrowed by the re-grep, for a carried-forward entry) using the Edit tool, one file at a time in list order. After all edits succeed, record the verdict in the in-context decision object: `decision: "applied"`, `date`: today, `note`: one-line description of what was changed. The single state write happens at the end of the pass (or immediately on abort), per state-schema's checkpoint rule.
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
  pick up edits until refreshed. Since Claude Code 2.1.260 `/reload-plugins` is also available in
  headless (`-p` / SDK) sessions, so a scripted pass can refresh without an interactive relaunch. (Claude Code 2.1.216 fixed mid-session skill/command edits not
  appearing in the slash menu until restart, and v2.1.221 made plugins installed from `/plugin`
  activate immediately "when safe", and v2.1.268 made a plugin installed, enabled or disabled
  from `/plugin` take effect when the menu closes. None of the three has been verified to cover
  a plugin-cache refresh pulling a new marketplace commit — and "when safe" is undefined
  upstream — so keep running the refresh until a smoke-test confirms otherwise.)
- For any SKILL.md that received non-trivial edits, consider the S42 content-review treatment:
  invoke skill-creator's qualitative review on the updated skill before the next real run.
- To undo, run `/rewind` (or `Esc Esc` on an empty prompt) — one rewind reverts the whole pass
  applied this turn (checkpoints are per user prompt, not per edit).
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