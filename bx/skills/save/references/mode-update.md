# MODE: UPDATE (Refresh Existing Docs)

When documentation structure exists, update to reflect current state.

## Step 0: Scoped Context Gather

Gather only what the orchestrator needs to *route* and *compose the packet*. The big append-only archives (`docs/key-decisions.md`, `docs/completed-work.md`, `docs/session-history.md`, `docs/known-issues.md`) are NOT read here on the default (fast) path — the `save-writer` subagent reads `session-history.md` off the main thread, and the other two are append-only (the orchestrator never reads *from* them to write the packet). Reading all archives up front was the single biggest cost of the old flow (~60k tokens/run).

### 0.1 Single parallel turn — issue these together

**Reads (parallel):**
- `CLAUDE.md` — read in full.
- `docs/STATUS.md` — the session-state file (schema v2). On a v1 repo this does not exist;
  MIGRATE runs first, so by the time UPDATE executes the repo is always v2 unless migration
  was skipped or declined. Handle both: if STATUS.md is absent, target CLAUDE.md's state
  sections exactly as v1 did.
- Auto-memory `MEMORY.md` — usually already in conversation context; read explicitly only if absent.

**Bash (parallel):**
- `git log -20 --name-only --pretty=format:'@%h %ad %s' --date=short` — commits and the files each touched, in one call
- `git log -1 --format=%h -- docs/STATUS.md` — the **save anchor**: the last commit that wrote the state file (on a v1 repo where STATUS.md does not exist, use `-- CLAUDE.md`)
- `git status`
- `bash <skill-dir>/../parallel/scripts/parallel.sh status` — the parallel-mode check for Path Routing (prints `mode=off`, or `mode=on` with the members and the lock)

**Other:**
- `TaskList` — only if the task tools are present (`references/task-tools.md`); skip silently if not.

**Deferred to `--full` only:** `README.md`, `docs/*.md` archive reads. If routing lands on `--full`, read those at the top of the Full Path (Step 0.3, which applies Part 3.0's exclusions), not here.

### 0.2 Derive

From the gathered context:
- **Filtered commit list** — the `@` lines above the save anchor in the 20-commit log (the anchor itself and everything older belong to earlier saves). Feeds the session entry + drift probes. Filter by commit, never by the `Last Updated` date: a date cutoff re-counts the earlier saves' commits whenever a day has more than one save (S65 saved three times on 2026-10-26). If the anchor is not among the 20 commits, run one more `git log --name-only --pretty=format:'@%h %ad %s' --date=short <anchor>..HEAD`; if there is no anchor (the state file was never committed), take all 20.
- **Diff file list** — the file names under those commits, plus `git status`'s uncommitted files → tells you whether README/`docs/` changed (drift signal; drives the `--full` recommendation).
- **TaskList state** → drives the task drain (Part 0) and the In Progress / Next Steps deltas.
- **Sizes + Key Decisions row count + session count** — cheap. Sizes come from one call to this skill's measuring script (resolve the path against **this skill's base directory**):

  ```bash
  bash <skill-dir>/scripts/size-budget.sh .
  ```

  It prints each live file against its size budget (`file` records: size, budget, stop point, state, need), every section's size largest first, both `Last Updated:` line lengths, the five archives against the rotation threshold, and the consecutive-skip counter. It skips files that do not exist and writes nothing. Count the Key Decisions table rows with the **Grep tool** (`output_mode: count`, pattern `^\| `); and (for the drift probe only) count sessions with the **Grep tool** (`output_mode: count`, pattern `^### Session`) on `docs/session-history.md` — not a full read. Use the Grep tool (not shell `grep`) for the two counts so no extra Bash permission is needed. These drive the drift warnings and the `--full` rollup gates.

## Step 0.1: Path Routing

After Step 0:

- **Parallel mode, checked first.** When the Step 0.1 `status` read printed `mode=on`, learn this session's ref the way `/bx:parallel` does (its SKILL.md, "Values every step uses") and run `bash <skill-dir>/../parallel/scripts/parallel.sh member <ref>`. Exit 0 → run the **Parallel Path** below in place of the Save Path, whatever the path flag (with `--full`, still read `references/mode-update-full.md` now). When `status` printed `mode=off` or failed, or `member` exits non-zero, check nothing more: route exactly as the bullets below say.
- **Default (no path flag), or `--fast`** → run the **Save Path** below. (`--fast` is a no-op alias kept for muscle memory; it now matches the default.)
- **`--full`** → run the **Full Path**: the Save Path with the heavy sweep (README + `docs/*.md` sync + rollups) spliced in **before** the writer dispatch, so the session entry records it. **Read `references/mode-update-full.md` now** — it holds the Full Path sequence, Step 0.3, Part 0.5, Parts 1.9–1.10 and Parts 2–7. The default path never loads it.

The old behavior (full sweep by default) is inverted: the daily save is fast; the heavy sweep is opt-in. Drift warnings (emitted at the end of the Save Path) tell the user when a `--full` is due.

**`--silent` (combinable with any path):** zero user prompts for the entire run. **The binding rule: every consent prompt anywhere in this skill — present or future — resolves to its safe default (declined / skip) with no sentinel written, so the next interactive run asks as usual. The Part 8 commit is the sole exception:** it auto-commits with the suggested message, the one prompt the flag exists to bypass. Concretely today: first-run rollup consent (5.2, 6.2) → declined; the Part 7.4 size-budget consent → skip, so no content moves (the plan still prints, and the skip is not counted); the Part 1.10.1 row collapse → warn only; the Part 7.7 per-file rotation consent → declined. A consent gate added to any Part later inherits this rule without needing its own clause.

## Prose Caps (apply when composing any new entry)

New entries are capped — this keeps writing fast and keeps `/bx:resume` lean. Existing entries are never rewritten to fit.

- **Session-history entry:** ≤5 "What happened" bullets. Detail that doesn't fit becomes a commit-hash reference (`see commit abc1234`), not prose.
- **docs/STATUS.md last-session block:** ≤5 bullets, the most architecturally significant.
- **Key Decision rationale:** ≤2–3 sentences, and the whole row 400 chars at most. Longer context goes only into `docs/key-decisions.md`, referenced by commit hash. A row over 400 chars is the first thing the size budget shortens.
- **In Progress / Next Steps items:** one line each + file paths; no multi-paragraph narration.
- **The `Last Updated:` line:** this session only — `Last Updated: <today> (Session <N>)`, optionally ` — ` plus one clause about this session, **250 chars at most**. Never carry the previous line forward and never add an `Earlier, Session …` clause: earlier sessions are in `docs/session-history.md`, and this line is injected into every session by the SessionStart hook. Unlike the caps above, this one applies to the existing line too: it is replaced whole on every save.

## Save Path (default)

The orchestrator owns everything that needs conversation context or user input; the `save-writer` subagent owns the file reads/writes. The orchestrator does NOT edit `CLAUDE.md`, `docs/STATUS.md`, `session-history.md`, `completed-work.md`, `key-decisions.md`, or `known-issues.md` itself — it composes the packet and dispatches.

**Sequence:**

1. **Drain the task list (Part 0 logic).** Run the Part 0 / Drain Validation rules below to reconcile `TaskList` against docs/STATUS.md (CLAUDE.md's state sections on a v1 repo). Respect `--skip-tasks`, and Part 0's availability gate (absent task tools ⇒ same behavior as `--skip-tasks`). The result (completed → completed-work items; in-progress → In Progress; new pending → Next Steps) becomes part of the packet, NOT inline edits.
2. **Compose the update packet** (see "Update Packet" below) from: the conversation (what happened this session — only the orchestrator knows this), the filtered commit list, the diff file list, and the drained task state. Apply the Prose Caps.
3. **Dispatch the `save-writer` subagent** (see "Dispatch" below) and await its change report.
4. **Drift probes** (cheap, on already-gathered data — no new reads): emit the drift warning block if anything fired. Do NOT enforce.
5. **Commit checkpoint (Part 8).** Run Part 8 as written; respects `--skip-commit` and `--silent` (auto-commit, no prompt). The git diff is the user's review surface.
6. **Report** using the Change Report format from `verification-checklists.md` — assembled from the subagent's report + drift warnings. Never echo file contents.

**Skipped on the Save Path** (these are `--full` only): Part 0.5 (legacy-layout archive split), Part 2 (README), Part 3 (`docs/*.md`), Part 4 (auto-memory), Parts 5/6/7 (rollups), Part 1.9 size advisory and Part 1.10 cap enforcement (replaced by drift warnings). All of these live in `mode-update-full.md`.

### Update Packet

Compose this structure and pass it to `save-writer` as the task prompt (fill every field; use the section references in Part 1 to decide *what* each field contains):

- `project_root` — absolute repo path.
- `today` — current date (e.g. `2026-05-29`). Resolve it from the session's current date supplied by the environment; if that's unavailable, fall back to the most recent commit date from the Step 0.1 `git log` (`git log -1 --date=short`). Do not invoke a bare `date` command — it isn't in `allowed-tools`.
- `session` — this session's number as the docs write it (e.g. `322`, or `321 cont.`). The writer stamps it into both `Last Updated:` lines.
- `last_updated_note` — optional: one clause about this session to follow the session number, 160 chars at most, naming no other session. Omit it when the session block says it well enough. **The `Last Updated:` lines are not deltas:** do not put either line in `claude_md_deltas` or `status_md_deltas`. The writer composes both from `today`, `session` and this note (Prose Caps above).
- `claude_md_deltas` — exact `old → new` string pairs (or "replace block under `## Section` with: …") for CLAUDE.md sections the session changed: `## Key Decisions` (Part 1.6) and `## Known Issues / Blockers` (Part 1.7 — a blocker added or reworded this session; a blocker **resolved** this session goes in `known_issue_moves`, not here). For `## Known Issues / Blockers` use exact `old → new` pairs only, never the block-replace form, and never a pair that touches an entry listed in `known_issue_moves`: deltas are applied before the archive step, so either would remove an issue before it is archived. **Instructions only** — no state sections. Source the *old* strings verbatim from the CLAUDE.md you read in Step 0.
- `status_md_deltas` — the same, for `docs/STATUS.md`: Current Status rows (Part 1.2), the `## Completed` summary line if the drain changed the completed count (Part 0 / Part 1.3), In Progress (Part 1.4) and Next Steps (Part 1.5). Source the *old* strings verbatim from the docs/STATUS.md you read in Step 0 (or, on a v1 repo where STATUS.md is absent, from CLAUDE.md's state sections, per Step 0.1).
- `status_md_session_block` — the full replacement text for STATUS.md's `## Session History` last-session block (Part 1.8 format, ≤5 bullets). New field name under schema v2 — the block lives in STATUS.md now, not CLAUDE.md.
- `session_history_entry` — the detailed entry for `docs/session-history.md` (Part 1.8 format, capped).
- `completed_items` — `- [x] …` lines from the task drain (may be empty).
- `decision_rows` — a list of `| decision | rationale |` rows, **one per** genuinely architectural decision made this session (Part 1.6 criteria); empty list if none. Most sessions have 0–1, but a session that locks in several architectural decisions lists each as its own row (don't drop the extras).
- `known_issue_moves` — a list, **one item per** issue this session resolved (Part 1.7); empty list if none. Each item carries: `entry` (the entry's full text, verbatim from the CLAUDE.md you read in Step 0 — it is both the archive body and the removal `old_string`), `title` (≤10 words, taken from the entry's lead), `status` (`resolved`), `session` (e.g. `S60`), and `commit` (the short hash that resolved it, or `none`).

### Dispatch

Dispatch one `save-writer` subagent via the Agent tool with `subagent_type: "bx:save-writer"`, passing the packet as the prompt (serialize as labeled sections). Await its change report.

`save-writer` reports on two channels, matching `doc-migrator.md`'s convention: `notes:` is advisory, `warnings:` is the channel that compels action. `warnings:` itself carries three distinct sub-cases (see `save-writer.md`'s Output section) that call for different responses — do not treat every non-`none` `warnings:` as a re-dispatch trigger. Handle each:
- **`notes:` non-`none`** (a density-cap: a field exceeded the prose caps) → tighten the offending field, note it in your report, do NOT re-dispatch.
- **`warnings:` non-`none`, unmatched delta** (an `old_string` didn't match, so that CLAUDE.md or docs/STATUS.md section was left un-updated) → re-source the exact current string from the CLAUDE.md / docs/STATUS.md you read in Step 0 (or re-read the affected lines) and re-dispatch **only** those deltas. This is the one case where re-dispatch IS warranted — silently leaving a section stale is the failure mode this guards against.
- **`warnings:` non-`none`, unmatched known-issue removal** (the entry was archived, but its text was not found verbatim in CLAUDE.md, so it was not removed) → re-read the affected lines of CLAUDE.md and re-dispatch **only** a `claude_md_deltas` removal for that entry. This is the one case where a delta may remove a Known Issues entry, and it is safe because the archive copy already exists. Do NOT re-send the `known_issue_moves` item.
- **`warnings:` non-`none`, schema-v1 `docs/STATUS.md`-absent fallback** (save-writer routed `status_md_deltas` and `status_md_session_block` to CLAUDE.md because `docs/STATUS.md` doesn't exist yet) → confirm the v1 routing was expected (migration hasn't run on this repo), log it in your report, do NOT re-dispatch.
- Both `notes:` and `warnings:` read `none` → done, no re-dispatch.

### Drift warning format (show only lines whose probe fires)

> "Drift detected — run `/bx:save --full` when convenient:
>  - [N] sessions in `docs/session-history.md` ready for rollup (count > 5)
>  - Key Decisions table in CLAUDE.md at [M] rows (cap 20)
>  - README.md or `docs/*.md` touched in [K] commits since last full sweep
>  - Size budget: CLAUDE.md [X]k / 12k, STATUS.md [Y]k / 15k → run /bx:save --full
>  - CLAUDE.md at [X]k chars — over the 10k advisory rung; largest section `## [name]` ([N] chars); nothing is shrunk below 12k
>  - Loaded at session start: [T]k chars against a 25k guide — largest: [name] ([N]k)
>  - MEMORY.md at [M]k chars (guide 12k, hard limit 25KB) — `--full` Part 4.2 moves detail into topic files
>  - `Last Updated:` line in [file] was [N] chars (cap 250) — replaced with this session's line; the old line is in docs/completed-work.md
>  - docs/[archive].md at [Z]k chars — rotation fires at 100k on `--full` (Part 7.7)"

The size-budget line is the output of `bash <skill-dir>/scripts/size-budget.sh . --line`, printed verbatim, and shown only when a file is over its budget. From the third consecutive `--full` run in which the shrink was skipped, the script words that line as an escalation; then it is the **first** line of the Change Report, above the per-file lines, not a drift bullet. Show the advisory-rung line when CLAUDE.md is over 10k and at or under 12k — never together with the budget line for CLAUDE.md. Show the loaded-at-session-start line when the script's `loaded_total` record reads `over`, and the MEMORY.md line when its `memory` record reads `over`. Show the `Last Updated:` line when the writer reported replacing an over-long one. Show the archive line only for an archive at ≥90k chars (approaching or over the 100k rotation threshold); `docs/next-steps-backlog.md` is one of the five.

If no probe fires, omit the warning entirely.

## Parallel Path

Runs only when Path Routing found parallel mode on and this session a member. Several sessions share
this repo, each on its own branch `s/<ref>`, and `main` moves only under the land lock. This path saves
**this session's own work only**, under that lock, and lands it. Everything that can prompt runs before
the lock; nothing under the lock asks the user anything.

**Values.** `P` is `bash <skill-dir>/../parallel/scripts/parallel.sh`, with `<skill-dir>` resolved
against this skill's base directory. Its output is `key=value` lines; read the exit code too. This
session's name and ref, the live refs, and how to message the members are defined in
`/bx:parallel`'s SKILL.md ("Values every step uses", "Messaging the members"); use them as written
there. `<n>` below is the session field as step 3 settles it.

**A lost lock stops the save.** A lock that goes 15 minutes without a refresh is dead, and a peer may
break it. So on any non-zero exit from a `P touch-lock` below (exit 4, `lock=not-owner`), stop at once
and report "lock lost; saved on branch, not landed", naming any doc edits left uncommitted in the
tree. Do **not** run `P unlock`: the lock is no longer this session's.

**Version and CHANGELOG.** Every session that changes `bx/` bumps the same `version` line and adds
its entry in the same place at the top of `CHANGELOG.md`, so a code commit carrying them conflicts
with the first peer that lands its own. On this path the code commit therefore never touches
`bx/.claude-plugin/plugin.json` or `CHANGELOG.md`: step 1 records the bump level and the entry text,
and step 4 writes both under the lock, on top of `main`'s version.

**Flags.** `--no-land` stops after the docs commit: the lock is released and nothing lands
(`/bx:parallel land` lands it later). `--skip-commit` cannot be honoured, because this path saves
through commits on the branch: say so and stop before step 1, with nothing changed. Every other flag
means what it means on the Save Path, and `--silent` keeps its binding rule.

**Sequence:**

1. **Prompts, before the lock.**
   - Drain the task list (Save Path step 1).
   - Session number preview: `P next-session`. On `next=unknown`, ask the user for this session's
     number now (in `--silent`, do not ask). Step 3 uses the answer only if the number is still unknown.
   - Version files untouched (only when `bx/.claude-plugin/plugin.json` exists). If `git status`
     shows either `bx/.claude-plugin/plugin.json` or `CHANGELOG.md` modified, or
     `git diff --quiet main...HEAD -- bx/.claude-plugin/plugin.json CHANGELOG.md` exits 1 (this
     branch already committed a change to them), stop with nothing changed. Tell the user that the
     parallel path writes the version and the CHANGELOG entry itself, under the lock; they undo their
     own edits to those files (keeping the entry text to give this save) and run `/bx:save` again.
   - Commit the code onto the branch: Part 8 steps 1, 2b and 3, in Part 8's order, with two changes.
     **Step 2 is replaced** (same repo-only condition): when an uncommitted file is under `bx/`, or
     `git diff --quiet main...HEAD -- bx/` exits 1, record the bump **level** (patch, minor or major,
     by Part 8 step 2's semver rule) and the CHANGELOG **entry text** (the body under the version
     heading, without the heading); edit neither file now. In `--silent`, the level is patch and the
     text comes from the suggested commit message, as Part 8 step 2 says. **Step 3's question** is
     asked once, covering the whole save: "Commit these to s/<ref>, then write the docs, commit them
     and land on main?" (drop "and land on main" under `--no-land`; with no uncommitted changes, ask
     "Write the docs, commit them to s/<ref> and land on main?"). Stage the listed files by name,
     never `git add -A` or `.`. On no: stop, nothing changed. `--silent` commits without asking, as
     Part 8 says.
   - `--full`: read Step 0.3, settle the packet's lists (Full Path step 3), and work out the plan of
     each sweep Part that asks for consent (5.2, 6.2, 1.10.1, 7.4, 7.7). Ask those questions now and
     keep the answers. Record a 7.4 **Choose** answer by file, section and move, not by row number.
2. **Lock and catch up.**
   - `P lock <ref> save --live-refs <live refs>`.
     - `lock=acquired`: go on. Report a `lock=broken prev_owner=… reason=…` line printed before it.
       Unless `--no-land`, now send each other member
       `bx:parallel from <name> [<ref>]: landing s/<ref> onto main now; nothing for you to do.`
     - Exit 4 (`lock=held owner=<o> …`), interactive: report the holder and stop. The code commit
       stays on the branch. Send `<o>` one message with `notify_when_idle: true`:
       `bx:parallel from <name> [<ref>]: waiting for the land lock you hold; nothing for you to do.`
       and tell the user to run `/bx:save` again after the idle notice.
     - Exit 4 in `--silent`: retry every 15 s for up to 120 s, as one Bash call (timeout 150000):
       `bash -c 'for i in 1 2 3 4 5 6 7 8 9; do bash "$0" lock "$1" save --live-refs "$2"; rc=$?; [ "$rc" -ne 4 ] && exit "$rc"; [ "$i" -lt 9 ] && sleep 15; done; exit 4' <script> <ref> <live refs>`,
       where `<script>` is the resolved path of `parallel.sh`. Exit 0: go on as for `lock=acquired`,
       message included. Still exit 4: stop with "saved on branch, not landed: lock held by <owner>".
     - Any other exit (exit 2 `mode=off`, exit 1 `lock=error …`): report the output and stop.
   - `P catch-up`. It rebases this branch onto `main`, which brings in only what has already landed.
     - `caught_up=<k>`: go on.
     - Exit 5, `rebase=interrupted`: `P unlock <ref>`. Then ask the user to continue or abort the
       rebase and run the choice (`git rebase --continue` or `--abort`); in `--silent`, report it
       and do not ask. Stop; the user runs `/bx:save` again.
     - Exit 6, `tree=dirty`: `P unlock <ref>`. Tell the user to commit or stash first; never stash
       for them. Stop.
     - Exit 7, `conflict files=…` or `rebase=failed reason=…`: the rebase was aborted.
       `P unlock <ref>`, report the files or reason, and stop. No docs are written.
3. **Read the latest docs.** `P touch-lock <ref> read`. When `caught_up` is above 0, read
   `docs/STATUS.md` and `CLAUDE.md` again: the Step 0.1 copies predate what landed. Then:
   - **Own work only.** The filtered commit list is
     `git log --name-only --pretty=format:'@%h %ad %s' --date=short main..HEAD`. It replaces the save
     anchor's list from Step 0.2, for the packet and for the drift probes.
   - **Session number.** `P next-session`. `current=<c> next=<x> source=…`: the session is `<x>`. A
     `cont.` save stays your judgment: when `<c>` is a save this session already landed earlier in
     this conversation, write `<c> cont.`. On `next=unknown`, use the user's answer from step 1; in
     `--silent`, or with no answer, pass the session in the form the `Last Updated` line on `main`
     already has, and add a warning line to the report: session number unknown.
4. **Version (only when step 1 recorded a level).** `P version-check --level <level>`.
   - `main=<v> level=<level> next=<x>`: set `version` in `bx/.claude-plugin/plugin.json` to `<x>`.
     Insert the entry at the top of `CHANGELOG.md`, directly above the first `## ` version heading
     (newest first): `## <x> — <today>`, a blank line, then the recorded entry text. Both edits go
     into the docs commit in step 5. Report `version <v> → <x>`.
   - `version=n/a`: nothing to do.
   - Exit 1, `version=error …`: `P unlock <ref>`, report, and stop.
5. **Write the docs.** `P touch-lock <ref> write`.
   - `--full`: run the sweep (Full Path step 4) on the latest files, with the answers kept in step 1.
     A move answered yes runs if it still applies; one the latest files no longer need is skipped and
     reported. A consent that step 1 did not ask resolves to its safe default, as under `--silent`.
     Then `P touch-lock <ref> dispatch`: the sweep can be long.
   - Compose the packet (Save Path step 2), with every `old` string taken from step 3's read (or
     from the files as the sweep left them, as Full Path step 5 says), the commit list from step 3,
     and `session` from step 3. Dispatch `save-writer` and handle its report (Save Path step 3,
     "Dispatch"). Run the drift probes (Save Path step 4).
   - Commit the docs: stage by name the files the writer and the sweep changed, plus the two files
     step 4 changed, and run `git commit -m "docs: S<n> save (parallel)"`. This is the commit the
     step 1 answer covered; do not ask again.
6. **Land.**
   - `--no-land`: `P unlock <ref>`, report "saved on s/<ref>, not landed (`--no-land`)", and stop.
   - `P touch-lock <ref> ff-main`, then `P ff-main`.
     - `landed=<sha>`: go on.
     - Exit 8, `main=checked-out path=<p>`: `P unlock <ref>`, then follow `/bx:parallel`'s `land`
       step 5 for exit 8. In `--silent`, ask nothing: report
       "saved on branch, not landed: main is checked out in <p>". Stop.
     - Exit 7 `main=not-ff`, or exit 2 `error=detached-head`: `P unlock <ref>`, report
       "saved on branch, not landed" with the output, and stop.
   - Push only if the user asked in this conversation: `git push origin main`.
   - `P unlock <ref>`.
   - Send each other member
     `bx:parallel from <name> [<ref>]: landed S<n> at <sha>, catch up before your next save.`
7. **Report** as Save Path step 6, plus the branch, `landed <sha>` or the reason it did not land,
   any lock break, and any version change.

Step 0.2's save anchor is not used on this path, and Part 8 does not run a second time: its prompts
ran in step 1 and its commit is step 5's.

## Part 0: Drain Task List into docs/STATUS.md

Before updating documentation, **capture any task progress from the current session's live task tracker:**

**Availability gate.** The task tools are absent by default on current models — see
`references/task-tools.md` (this skill owns that file). If `TaskList` is not in your toolset,
treat this Part exactly as `--skip-tasks`: no drain, no stale-task warning. The In Progress /
Next Steps deltas then come from the conversation alone, which the orchestrator has either
way, and the drain summary line reports it once. Everything below is the tracker path.

1. **Run `TaskList`** to get all tasks and their statuses
2. **For each completed task:**
   - Add it to `docs/completed-work.md` as `- [x] [task subject] - [files modified]`
   - Update docs/STATUS.md's `## Completed` summary line (increment count)
   - Remove it from `## In Progress` or `## Next Steps` if it appears there
3. **For each in-progress task:**
   - Ensure it's listed in `## In Progress` with current state
4. **For pending tasks that were created during the session:**
   - Add them to `## Next Steps` in priority order
5. **Skip tasks that already exist in docs/STATUS.md** — don't duplicate

This ensures work tracked via TaskCreate/TaskUpdate during the session is persisted back to docs/STATUS.md for the next session's `/bx:resume`.

**If `--skip-tasks` is in `$ARGUMENTS`, skip this step entirely.**

### Drain Validation

After draining, verify completeness:

1. **Run `TaskList`** again to confirm all tasks have been processed
2. **Ad-hoc tasks** (tasks created during the session that don't map to existing docs/STATUS.md sections):
   - If completed → add to `docs/completed-work.md`
   - If pending/in-progress → add to `## Next Steps` in docs/STATUS.md
3. **Report drain summary** to the user:
   > "Task drain complete: [N] completed, [M] in-progress, [K] pending synced to docs."

## Part 1: Update CLAUDE.md and docs/STATUS.md

> **Who runs Part 1.** On both paths `save-writer` applies 1.0–1.8 from the packet; only 1.9–1.10 run on the orchestrator, during the `--full` sweep (both in `mode-update-full.md`). **Plan-then-batch (orchestrator-side edits on the Full Path — 1.10, Part 6 row removals, Part 7 shrinkers):** gather every change you intend to make from the evidence cached in Step 0 and Step 0.3. Then apply all changes to each file in a **single Write** of its full contents, or as non-overlapping parallel Edits in one turn — per the routing table below, some sub-sections target CLAUDE.md and some target docs/STATUS.md; batch each file's edits separately. Do NOT issue one Edit per sub-section — that's the dominant turn-count cost.

**Target file per sub-section (schema v2):**

| Sub-section | Target |
|---|---|
| 1.0 Last Updated | **both** CLAUDE.md and docs/STATUS.md |
| 1.1 Documentation Links | CLAUDE.md |
| 1.2 Current Status | docs/STATUS.md |
| 1.3 Completed | docs/STATUS.md (+ append to docs/completed-work.md) |
| 1.4 In Progress | docs/STATUS.md |
| 1.5 Next Steps | docs/STATUS.md |
| 1.6 Key Decisions | CLAUDE.md (+ append to docs/key-decisions.md) |
| 1.7 Known Issues / Blockers | CLAUDE.md (+ append to docs/known-issues.md) |
| 1.8 Session History | docs/STATUS.md (+ append to docs/session-history.md) |

1.1 Documentation Links stays in CLAUDE.md and is unrelated to the `> Session state:` pointer
line: 1.1 maintains the **Key Documentation** list of PRD/spec/sample files inside CLAUDE.md's
Project Overview, which schema v2 still carries there; the pointer line only names
`docs/STATUS.md` itself. The two do not duplicate each other.

### 1.0 Update Timestamp
**Always update the "Last Updated" field at the top of BOTH files** — CLAUDE.md and docs/STATUS.md carry independent `Last Updated:` lines (doc-schema.md), and the staleness signal must follow the state:
```markdown
Last Updated: [TODAY] (Session [N]) — [optional: one clause about this session]
```
The line holds the current session only and is 250 chars at most (Prose Caps). `save-writer` composes it from the packet's `today`, `session` and `last_updated_note`, keeps whatever label form the file already uses (`**Last Updated:**` stays bold), and replaces the old line whole. A line that grew past the cap under earlier versions is archived to `docs/completed-work.md` before it is replaced.

### 1.1 Documentation Links
Update the "Key Documentation" section with actual files:
```markdown
**Key Documentation:**
- [docs/PRD.md](docs/PRD.md) - Project requirements
- [docs/api-spec.md](docs/api-spec.md) - API documentation
- [docs/sample-emails.md](docs/sample-emails.md) - Example data
```

### 1.2 Current Status Table
Target: **docs/STATUS.md's `## Current Status` table.** Update phase/task statuses based on code changes:
- Change Not Started -> In Progress when work starts
- Change In Progress -> Complete when work completes
- Add new rows for new components

### 1.3 Completed Section
Target: **docs/STATUS.md's `## Completed` section**, plus the `docs/completed-work.md` archive. When items are completed:
1. **Append the detailed entry to `docs/completed-work.md`:**
   - If the file doesn't exist, create it with header:
     ```markdown
     # Completed Work

     > Full checklist of completed tasks. Referenced from [STATUS.md](STATUS.md).

     ---
     ```
   - Append: `- [x] [What was finished] - [files modified]`
2. **Keep docs/STATUS.md's `## Completed` section as a brief summary:**
   ```markdown
   ## Completed

   [N] tasks completed across [areas]. See [completed-work.md](completed-work.md) for full checklist.
   ```
   Update the count and areas description as needed. Do NOT maintain a full checkbox list in docs/STATUS.md.

### 1.4 In Progress Section
Target: **docs/STATUS.md's `## In Progress` section.** Update current work state:
```markdown
- [ ] [Current task] - [files being modified]
```

### 1.5 Next Steps Section
Target: **docs/STATUS.md's `## Next Steps` section.** Refresh prioritized task list:
- Remove completed items
- Add new tasks discovered
- Reorder by priority
- Include relevant file paths

### 1.6 Key Decisions Made
Target: **CLAUDE.md's `## Key Decisions` table** (unchanged from v1 — this stays in CLAUDE.md under schema v2), plus the `docs/key-decisions.md` archive. When adding new decisions:
1. **Always append to `docs/key-decisions.md`:**
   - If the file doesn't exist, create it with header:
     ```markdown
     # Key Decisions

     > Full decision log. Referenced from [CLAUDE.md](../CLAUDE.md).

     | Decision | Rationale |
     |----------|-----------|
     ```
   - Append: `| [New decision] | [Why we chose this] |`
2. **Only add to CLAUDE.md's condensed table if it's a truly important architectural decision** — API gotchas, naming conventions, critical tech choices, patterns that affect multiple files.
   - Do NOT add implementation details like "removed field X", "renamed method Y", or one-off fixes to CLAUDE.md.
   - Keep CLAUDE.md's Key Decisions table to ~20 rows max. If it grows beyond that, remove the least important entries (they're preserved in `docs/key-decisions.md`).
   - Include a link at the bottom: `> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)`

### 1.7 Known Issues / Blockers
Target: **CLAUDE.md's `## Known Issues / Blockers` section** (unchanged from v1), plus the
`docs/known-issues.md` archive (format owned by `doc-schema.md`'s Archives section).

An **entry** starts at a **lead** and runs to just before the next lead, the next block
whose first line starts with `>`, or the end of the section. A lead is a line that opens with
a bold phrase (`**…**`) or a top-level bullet (`- `, `* `, `1. `, with or without a
`[ ]`/`[x]` checkbox). Everything under a lead belongs to that entry: continuation
paragraphs, code blocks, nested bullets, sub-headings. If the section has no bold or bullet
leads at all, each blank-line-separated paragraph is an entry and its first sentence is the
lead.

Not entries, and never moved: a block whose first line starts with `>` (the
`> Session state:` pointer line that follows the section, and the `> Archived issues:` link
Part 7.3 adds), and the placeholder `None currently.` in any emphasis or with any trailing
note. An entry's **title** is its lead without bold markers, bullet or checkbox, or trailing
punctuation.

- **Add** new issues discovered this session, as new entries after the last entry and above
  any `>` block.
- **Relocate resolved issues; do not delete them.** Put each issue this session resolved in
  the packet's `known_issue_moves` with `status: resolved`, the resolving session, and the
  commit hash where one exists. Do not also write a `claude_md_deltas` removal for it:
  `save-writer` archives the entry first and removes it second, so a failed append can
  never lose it.
- **An issue is resolved when the session that resolved it says so — never inferred from
  absence of mention.** A blocker nobody discussed this session is still a blocker.
- An entry an earlier session marked resolved in place stays where it is on the Save Path.
  Part 7.3's shrinker moves it on `--full`.
- Write `None currently.` when the last entry leaves; replace that line when the first
  entry arrives.

### 1.8 Session History
Target: **docs/STATUS.md's `## Session History` section** (brief), plus the `docs/session-history.md` archive (detailed). Session history is split between docs/STATUS.md (brief) and docs/session-history.md (detailed).

**1. Write the DETAILED session log to `docs/session-history.md`:**
   - If the file doesn't exist, create it with this header:
     ```markdown
     # Session History Archive

     > Auto-managed by `/bx:save`. Last session summary is in [STATUS.md](STATUS.md).

     ---
     ```
   - Append the full detailed entry:
     ```markdown
     ### Session [N] - [DATE]
     **What happened:**
     - [Accomplishment 1]
     - [Accomplishment 2]
     - [Any issues encountered]

     **Files created/modified:**
     - `path/to/file.py` - [what changed]
     - `path/to/another.js` - [what changed]

     **Next session should:**
     - [Priority 1 for next time]
     - [Priority 2 for next time]
     ```

**2. Write only a brief summary to docs/STATUS.md's `## Session History`:**
   - Replace (not append) the previous last-session block with the new one:
     ```markdown
     ## Session History

     > Full history: [session-history.md](session-history.md)

     ### Last Session (Session [N]) - [DATE]
     - [3-5 bullet points summarizing key accomplishments and state]
     ```
   - docs/STATUS.md should only ever contain ONE session block (the most recent).
   - All previous sessions live exclusively in `docs/session-history.md`.

## Part 8: Commit Checkpoint

After all documentation updates **and rollups** are complete, remind the user to commit. This runs last so that Parts 5, 6, and 7 changes are included in the same commit as the session updates.

**If `--skip-commit` is in `$ARGUMENTS`, skip this step entirely.**

1. **Run `git status`** to show all uncommitted files (staged and unstaged)
2. **Plugin version bump (claude-config repo only — skip silently when `bx/.claude-plugin/plugin.json` doesn't exist).** If any uncommitted file is under `bx/`, the commit MUST also bump `version` in `bx/.claude-plugin/plugin.json` and add a matching entry to the repo-root `CHANGELOG.md` (newest first). The version is the plugin's update cache key: a pushed commit that doesn't bump it is never offered to users — `claude plugin update` reports "already at the latest version". Semver: PATCH for fixes and doc corrections, MINOR for a new skill/agent/flag, MAJOR for breaking renames or removed behavior. In `--silent` mode, default to PATCH and derive the CHANGELOG line from the suggested commit message.
2b. **Validate the plugin (same repo-only condition as step 2 — skip silently when
   `bx/.claude-plugin/plugin.json` doesn't exist).** After the version bump and before the commit,
   run the official local smoke test:

   ```
   claude plugin validate ./bx --strict --json
   ```

   `--strict` treats warnings as errors, which is what you want at a commit checkpoint: unrecognized
   frontmatter keys and missing metadata are tolerated by the runtime but are exactly the drift this
   step exists to catch. Also validate the marketplace manifest with `claude plugin validate . --json`
   when `.claude-plugin/marketplace.json` exists at the repo root.

   `--json` (Claude Code 2.1.259+) returns a machine-readable report. **Judge the outcome from its
   fields, not from prose:** the top-level `success` boolean is the verdict; `manifest.errors`,
   `manifest.warnings` and `contents` carry the specifics. If the CLI rejects `--json` (older Claude
   Code), re-run without the flag and read the prose output instead.

   - **Passes** (`"success": true`) → report one line (`plugin validate: passed`) and continue to step 3.
   - **Fails or warns** (`"success": false`, or any non-empty `manifest.errors` / `manifest.warnings`)
     → surface the `errors` and `warnings` entries verbatim and ask whether to fix now or commit anyway.
     Do NOT block the commit on your own judgement; a validation warning is information for the
     user, not a veto. In `--silent` mode, report the failure in the run summary and commit anyway —
     the flag's contract is zero prompts, and silently *skipping* the commit would be worse than
     committing something that warns.
   - **Command not found** (older Claude Code, or a non-interactive environment without the CLI on
     PATH) → skip silently. This step must never fail a save because the harness lacks the command.

   This is the "install smoke-test" half of the S37 plugin-packaging leftovers, closed by
   `/bx:evolve` finding `b5659902` (docs lane, 2026-08-24).

3. **If there are uncommitted changes:**
   - Show the list of modified/untracked files
   - Suggest a conventional commit message based on what was done this session, e.g.:
     > Suggested commit: `docs: update session progress and documentation`
   - **If `--silent` is in `$ARGUMENTS`:** commit immediately with the suggested message — no prompt. This is the only path that commits without confirmation; the user opted in explicitly via the flag. Do NOT push.
   - **Otherwise, ask the user:** "Would you like to commit these changes?"
   - **Never auto-commit without `--silent`** — always wait for user confirmation
4. **If there are no uncommitted changes**, skip silently
