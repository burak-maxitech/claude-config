# /bx:parallel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `/bx:parallel`. Burak runs it in one session; it recruits the other sessions on the repo over cross-session messaging. Each session gets its own worktree or branch, landings on `main` are serialized by a lock, and `/bx:save` saves only its own session's work.

**Architecture:** One bash script, `parallel.sh`, owns all shared state under `<git-common-dir>/bx-parallel/` and every git step that touches `main`. The skill prose (`/bx:parallel` and a new Parallel Path in `/bx:save`) owns everything that needs conversation context: `ListAgents`, `SendMessage`, user confirmation and `EnterWorktree`. Messages carry the news; the lock file enforces one-at-a-time.

**Tech Stack:** bash 3.2-compatible scripts (Git Bash on Windows, LF line endings), git ≥ 2.38, Claude Code skill markdown, bash PASS/FAIL test scripts in this repo's existing style (`bx/skills/save/tests/*.sh`).

**Spec:** `docs/superpowers/specs/2026-11-20-bx-parallel-design.md`

## Global Constraints

- Scripts are bash 3.2 compatible, LF line endings, no `jq`, and no network.
- Shared state lives only under `$(git rev-parse --git-common-dir)/bx-parallel/`; never in the working tree.
- A lock is dead when it hasn't been refreshed for **900 seconds (15 minutes)**, or when its owner isn't in the live-ref list the caller passes. Nothing else breaks a lock, except `unlock --force`.
- `--silent` save waits for the lock for **120 seconds (2 minutes)** at most.
- Worktrees are created at `.claude/worktrees/<ref>` on branch `s/<ref>`, **based on local `main`**. Never use `EnterWorktree name=`: its default base is `origin/<default>`. Create the worktree with the script, then `EnterWorktree path=`.
- `.claude/worktrees/` must be in `.gitignore` before any worktree is created.
- With the mode off, `/bx:save` behaves exactly as today.
- The session that receives a message never changes its state on that message alone; its own user must confirm in that session.
- Every `bx/**` change ships with a `plugin.json` bump (MINOR → **2.21.0**) and a CHANGELOG entry.

**Deviations from the spec (builder calls):**
- The script lives at `bx/skills/parallel/scripts/parallel.sh`, not `bx/scripts/`, following the per-skill `scripts/` convention. `/bx:save` calls it as `<skill-dir>/../parallel/scripts/parallel.sh`.
- `mode.json` becomes two line files, `mode` (`key=value`) and `members` (tab-separated), so no JSON parser is needed.

## Review Focus

1. **Two sessions run `lock` in the same instant.** Exactly one gets `lock=acquired`; the other gets `lock=held`. *(Task 2 test: `test_lock_race`.)*
2. **`main` is still checked out in the main folder when a worktree session lands.** `ff-main` refuses, names the folder, and changes nothing. *(Task 3 test: `test_ff_main_refuses_checked_out`.)*
3. **A save with uncommitted edits reaches `catch-up`.** `catch-up` refuses with `tree=dirty` instead of auto-stashing. *(Task 3 test: `test_catch_up_dirty`.)*
4. **STATUS.md on `main` has `Last Updated: … (Session 70 (cont.))` or no session number at all.** `next-session` prints `next=71` and `next=unknown` respectively, and never guesses. *(Task 4 test: `test_next_session_forms`.)*
5. **A member leaves while holding the lock.** `leave` releases its lock, and the last `leave` turns the mode off. *(Task 1 test: `test_leave_releases_lock_and_last_turns_off`.)*

---

### Task 1: Parallel state (`on` / `join` / `leave` / `off` / `status` / `member`)

**Files:**
- Create: `bx/skills/parallel/scripts/parallel.sh`
- Create: `bx/skills/parallel/tests/test-parallel.sh` (the harness: `make_repo` builds a temp repo with one commit on `main`, plus `pass`/`fail` helpers in the `assert-doc-schema.sh` style; exit 1 on any failure)

**Interfaces:**
- Produces: `parallel.sh <subcommand> …`, run from anywhere inside the repo or one of its worktrees. All output is `key=value` lines on stdout. The state directory is `$(git rev-parse --git-common-dir)/bx-parallel/`.
  - `on <ref> <folder>` → `mode=on`, and the caller becomes the first member (branch from `git -C <folder> branch --show-current`). Exit 3 with `mode=already-on` if the mode is already on.
  - `join <ref> <folder> <branch>` → `joined=<ref>`. Re-joining replaces that ref's row. Exit 2 if the mode is off.
  - `leave <ref>` → `left=<ref>`. If the ref holds the lock, it also releases it (`lock=released`). If no members remain, it also prints `mode=off` and deletes the state.
  - `off` → `mode=off`. Deletes `mode`, `members` and `land.lock/`, and appends to `log`.
  - `status` → `mode=on|off`, then one `member ref=… folder=… branch=…` line per member, then `lock=free` or `lock=held owner=… age=<s> step=…`.
  - `member <ref>` → exit 0 if it's a member, 1 if not. No output.
- The env var `BXP_NOW` overrides the epoch "now" (tests only).

- [ ] **Step 1: Write the failing tests** `test_on_status`, `test_on_twice` (exit 3), `test_join_requires_on` (exit 2), `test_join_replace` (joining the same ref twice gives one row), `test_member`, `test_state_shared_across_worktrees` (a `join` from a linked worktree is visible to `status` run in the main folder), and `test_leave_releases_lock_and_last_turns_off` (this needs Task 2's `lock`; mark it `skip` until Task 2, then enable it).
- [ ] **Step 2: Run** `bash bx/skills/parallel/tests/test-parallel.sh`. Expected: FAIL (script missing).
- [ ] **Step 3: Implement the subcommands above** in `parallel.sh`. Write rows with tab-separated fields, and rewrite `members` through a temp file + `mv`.
- [ ] **Step 4: Run the tests.** Expected: every Task 1 test passes (one skip).
- [ ] **Step 5: Commit** `feat(parallel): state script — on/join/leave/off/status`

### Task 2: Land lock (`lock` / `touch-lock` / `unlock`)

**Files:**
- Modify: `bx/skills/parallel/scripts/parallel.sh`
- Modify: `bx/skills/parallel/tests/test-parallel.sh`

**Interfaces:**
- Consumes: Task 1's state directory and `log`.
- Produces:
  - `lock <ref> <step> [--live-refs a,b,c]`. The lock is acquired with `mkdir land.lock` (atomic), then `land.lock/owner` holds `ref=`, `since=` (epoch) and `step=`.
    - Success: exit 0 with `lock=acquired`.
    - Held: exit 4 with `lock=held owner=<ref> age=<s> step=<step>`.
    - Dead lock (refreshed ≥ 900 s ago, or `--live-refs` given and the owner not in it): print `lock=broken prev_owner=<ref> reason=stale|gone`, log it, and acquire.
    - Re-locking by the current owner: refresh it and exit 0 with `lock=acquired`.
  - `touch-lock <ref> <step>` → refreshes `since` and `step`. Exit 4 if `<ref>` isn't the owner.
  - `unlock <ref> [--force]` → `lock=released`. Exit 4 if not the owner and no `--force`; `--force` prints `prev_owner=`.

- [ ] **Step 1: Write the failing tests**
  - `test_lock_acquire_and_held` (exit 0, then exit 4 for another ref)
  - `test_lock_stale_broken` (`BXP_NOW` = since + 900 → `reason=stale`; since + 899 → held)
  - `test_lock_gone_broken` (`--live-refs x,y` without the owner → `reason=gone`)
  - `test_touch_extends` (touch at +800, check at +1600 → still held)
  - `test_unlock_not_owner` (exit 4), `test_unlock_force`
  - `test_lock_race`: two background `lock` calls in a 20-iteration loop; each iteration, exactly one gets exit 0.
  - Enable Task 1's skipped test.
- [ ] **Step 2: Run.** Expected: the new tests FAIL.
- [ ] **Step 3: Implement** `lock`, `touch-lock` and `unlock`. Breaking a lock removes `land.lock/` and then retries the `mkdir` once. If that retry loses to another session, report `lock=held` (exit 4).
- [ ] **Step 4: Run.** Expected: all tests pass.
- [ ] **Step 5: Commit** `feat(parallel): land lock with 15-minute heartbeat`

### Task 3: Git steps (`ensure-ignore` / `worktree` / `catch-up` / `ff-main`)

**Files:**
- Modify: `bx/skills/parallel/scripts/parallel.sh`
- Modify: `bx/skills/parallel/tests/test-parallel.sh`

**Interfaces:**
- Produces:
  - `ensure-ignore` → `ignore=present|added`. It appends `.claude/worktrees/` to `.gitignore` in the main worktree and never commits; the caller commits.
  - `worktree <ref>` → `path=<abs path>` and `branch=s/<ref>`, via `git worktree add -b s/<ref> <main-root>/.claude/worktrees/<ref> main`. Exit 9 with `ignore=missing` if `.claude/worktrees/` isn't ignored. If the path already exists, print it with `existing=yes` and exit 0.
  - `catch-up` rebases the current branch onto local `main`. Outcomes:

    | Condition | Exit | Output |
    |---|---|---|
    | A rebase is already in progress | 5 | `rebase=interrupted` |
    | Uncommitted changes | 6 | `tree=dirty` |
    | The rebase conflicts | 7 | `conflict files=<comma list>`, after `git rebase --abort` |
    | Success | 0 | `caught_up=<n commits from main>` |

  - `ff-main` → `git fetch . <current-branch>:main`. Outcomes:

    | Condition | Exit | Output |
    |---|---|---|
    | `main` is checked out in a worktree (check `git worktree list --porcelain` first) | 8 | `main=checked-out path=<p>` |
    | Not a fast-forward | 7 | `main=not-ff` |
    | Success | 0 | `landed=<short sha>` |

- [ ] **Step 1: Write the failing tests**
  - `test_ensure_ignore_idempotent`
  - `test_worktree_requires_ignore` (exit 9)
  - `test_worktree_based_on_local_main`: the base equals `git rev-parse main`, even when an `origin/main` remote ref points elsewhere.
  - `test_catch_up_dirty` (exit 6)
  - `test_catch_up_conflict_aborts` (exit 7; afterwards no `rebase-merge` dir, branch unchanged)
  - `test_catch_up_interrupted` (start a conflicting rebase by hand → exit 5)
  - `test_ff_main_refuses_checked_out` (main folder on `main` → exit 8, `main` unchanged)
  - `test_ff_main_success` (main folder switched to `s/a` → exit 0, `main` == branch head)
  - `test_two_branches_land_in_turn`: branches A and B each change a different file. A lands, then B's `catch-up` + `ff-main` succeed, and `main` contains both changes.
- [ ] **Step 2: Run.** Expected: the new tests FAIL.
- [ ] **Step 3: Implement the four subcommands.** Resolve the main worktree root as the first entry of `git worktree list --porcelain`.
- [ ] **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `feat(parallel): worktree, catch-up and fast-forward-only landing`

### Task 4: Save helpers (`next-session` / `version-check`)

**Files:**
- Modify: `bx/skills/parallel/scripts/parallel.sh`
- Modify: `bx/skills/parallel/tests/test-parallel.sh`

**Interfaces:**
- Produces:
  - `next-session`
    - Reads `git show main:docs/STATUS.md`, falling back to `main:CLAUDE.md`.
    - Takes the first line matching `Last Updated` and pulls the first `Session <N>` from it, then prints `current=<N> next=<N+1> source=<file>`.
    - No match: prints `next=unknown`, exit 0.
  - `version-check`
    - Runs only when `bx/.claude-plugin/plugin.json` exists; otherwise prints `version=n/a`.
    - Compares `"version"` in `main:` against the working tree: `main=<v> branch=<v> ok=yes|no suggest=<v>`.
    - `ok=yes` when the branch version is semver-greater than main's.
    - `suggest` takes main's version and applies the bump level the branch made relative to its merge-base: patch, minor or major. If the branch made none, it suggests a patch bump.

- [ ] **Step 1: Write the failing tests**
  - `test_next_session_forms`:
    - `Session 70` → `next=71`
    - `**Last Updated:** 2026-11-20 (Session 70 (cont.))` → `next=71`
    - no number → `next=unknown`
    - STATUS.md absent → read from CLAUDE.md, `source=CLAUDE.md`
  - `test_version_check`:
    - main 2.20.0, branch 2.21.0 → `ok=yes`
    - main 2.21.0 (another session landed it), branch 2.21.0 with base 2.20.0 → `ok=no suggest=2.22.0`
    - the same case with a patch-level base bump → `suggest=2.21.1`
    - no plugin.json → `version=n/a`
- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Implement** both subcommands with `sed`/`awk`. Compare semver field by field as integers.
- [ ] **Step 4: Run.** Expected: all pass.
- [ ] **Step 5: Commit** `feat(parallel): session-number and version helpers for /bx:save`

### Task 5: The `/bx:parallel` skill

**Files:**
- Create: `bx/skills/parallel/SKILL.md`
- Create: `bx/skills/parallel/tests/check-skill-commands.sh`. Every `parallel.sh <word>` named in `SKILL.md` and `bx/skills/save/references/*.md` must be a subcommand the script accepts (run `parallel.sh help`, which Step 3 adds).

**Interfaces:**
- Consumes: every subcommand from Tasks 1–4.
- Produces:
  - The frontmatter:
    - `name: parallel`, `disable-model-invocation: true`, `effort: low`
    - `argument-hint: "[status|land|off|join|unlock --force]"`
    - `allowed-tools: Read, Bash(bash:*), Bash(git:*), ListAgents, SendMessage, EnterWorktree, AskUserQuestion`
  - The **setup message format** that peers recognise:
    - first line: `bx:parallel setup from <name> [<ref>]: parallel mode is on for <repo>; please ask your user once whether to join.`
    - body: the rules from spec §4, the placement, and the exact join steps.
  - `/bx:parallel join` is the entry a peer runs once its user says yes. It runs the spec §3 join steps.

- [ ] **Step 1: Write `check-skill-commands.sh`, then run it.** Expected: FAIL (no SKILL.md, no `help`).
- [ ] **Step 2: Add a `help` subcommand to `parallel.sh`** that prints one subcommand name per line.
- [ ] **Step 3: Write SKILL.md** covering:
  - **No args (setup):** spec §2 steps 1–6. Step 1 takes this session's own ref from `ListAgents`' "This session is … [ref]" line. Step 3 runs `ensure-ignore` and commits `.gitignore` alone with `chore: ignore .claude/worktrees for bx:parallel`.
  - **`join`:**
    - Ask the user (AskUserQuestion) "Parallel mode is on. Move me into my own worktree?".
    - If yes: run `parallel.sh worktree <ref>`, then `EnterWorktree path=<path>`, then `parallel.sh join`, then reply "joined: folder, branch".
    - If no: reply "declined".
  - **The main-folder session:** `git switch -c s/<ref>`, then `join` with that branch.
  - **`status`:** run `parallel.sh status`, plus worktrees whose branch is already on `main`, marked "safe to remove" (list only).
  - **`land`:**
    - Message the peers "landing".
    - Run `lock <ref> land --live-refs <refs from ListAgents>`, then `catch-up`, then `ff-main`, then `unlock`.
    - Message the peers "landed <sha>, catch up before your next save".
    - Run `touch-lock` between steps.
  - **Pruning:** every subcommand first runs `leave <ref>` for each member whose ref is missing from `ListAgents`. That is how a closed session leaves, and how the last one leaving turns the mode off.
  - **`off`:**
    - Message the peers, then run `off`.
    - If this session is on `s/<ref>`, its branch is already on `main`, and its tree is clean, offer `git switch main`.
  - **`unlock --force`:** show `status` first, confirm, then run it.
  - **A rule section** quoting spec §4 verbatim.
- [ ] **Step 4: Run** `bash bx/skills/parallel/tests/check-skill-commands.sh` and `claude plugin validate ./bx --strict --json`. Expected: PASS and `"success": true`.
- [ ] **Step 5: Commit** `feat(parallel): /bx:parallel skill — setup, join, status, land, off`

### Task 6: `/bx:save` Parallel Path

**Files:**
- Modify: `bx/skills/save/references/mode-update.md`
  - Step 0.1 gets one extra parallel Bash read: `bash <skill-dir>/../parallel/scripts/parallel.sh status`.
  - Step 0.1 "Path Routing" gets a routing line.
  - Add a new `## Parallel Path` section after `## Save Path (default)`.
- Modify: `bx/skills/save/SKILL.md`
  - Add `--no-land` to `argument-hint`.
  - Add one line in the flag list pointing at the Parallel Path.
- Modify: `bx/skills/parallel/tests/check-skill-commands.sh` (it already scans save references; nothing new is expected).

**Interfaces:**
- Consumes: `member`, `lock`, `touch-lock`, `catch-up`, `next-session`, `version-check`, `ff-main` and `unlock`.
- Produces: the routing rule. Parallel Path runs if `status` prints `mode=on` **and** `member <own ref>` exits 0. Otherwise nothing changes, and the `status` call is the only addition.

- [ ] **Step 1: Write the Parallel Path,** following spec §6 in this order:
  1. **Prompts before the lock:**
     - Run Part 0 drain.
     - Run Part 8 step 3 (commit the code onto the branch, with the usual consent).
     - Run Part 8 step 2b (validate).
     - Run the `--full` consents.
  2. **Lock and catch up:**
     - Run `lock <ref> save --live-refs …`. In `--silent`, retry every 15 s for up to 120 s, then stop with "saved on branch, not landed: lock held by <owner>".
     - Run `catch-up`. On exit 7, unlock and report.
  3. **Read the latest docs:** STATUS.md and CLAUDE.md. Commits come from `git log main..HEAD`, replacing the save anchor. The session number comes from `next-session` (`next=unknown` → ask the user, or in `--silent` keep the doc's form and warn).
  4. **Version:** run `version-check`; on `ok=no`, apply `suggest` to `plugin.json` and rewrite this branch's CHANGELOG header.
  5. **Write the docs:** dispatch `save-writer` with old-strings from step 3's read, then commit the docs with `docs: S<n> save (parallel)`.
  6. **Land:** `ff-main` (skip on `--no-land`), then `unlock`, then message the peers "landed S<n> <sha>". Call `touch-lock` before steps 3, 5 and 6.
- [ ] **Step 2: Run** `check-skill-commands.sh`, `bash bx/skills/save/tests/check-doc-rule-consistency.sh` and `claude plugin validate ./bx --strict --json`. Expected: all pass.
- [ ] **Step 3: Check the mode-off path is unchanged.**
  - Run `git diff bx/skills/save/references/mode-update.md`.
  - Confirm every changed line sits inside the new section, the routing line or the one added Step 0.1 read.
  - Confirm Part 8 and the Save Path text are untouched.
- [ ] **Step 4: Commit** `feat(save): Parallel Path — own-work saves under the land lock`

### Task 7: Docs and version

**Files:**
- Modify: `bx/.claude-plugin/plugin.json` (`2.21.0`)
- Modify: `CHANGELOG.md` (new top entry)
- Modify: `README.md` (one row in the command table, plus a short "Parallel sessions" paragraph next to the session-naming one at line ~69)
- Modify: `Workflow.md` (one scenario: "two sessions on one repo")

- [ ] **Step 1: Make the edits.** The CHANGELOG entry names the spike findings: the busy-delivery behaviour, the relayed-approval refusal, and the `.claude/worktrees/` ignore trap.
- [ ] **Step 2: Run** `bash scripts/check-plugin-version-bump.sh` and `claude plugin validate ./bx --strict --json`. Expected: pass.
- [ ] **Step 3: Commit** `chore: v2.21.0 — /bx:parallel: one-session setup, messaging, own-work saves`

### Task 8: Acceptance by running (with Burak, on a throwaway clone)

**Files:**
- Create: `docs/superpowers/specs/2026-11-20-bx-parallel-acceptance.md` (results log)

This needs two real sessions and Burak's confirmations. It is not automatable. Run it against a scratch clone (`git clone . ../bxp-accept`) with the plugin loaded from this branch (`claude --plugin-dir ./bx`). Record each result as pass or fail, with output.

- [ ] **Step 1: Failing control.** Mode off, both sessions in one folder, both run today's `/bx:save`. Record the duplicate S number or the misattributed commits.
- [ ] **Step 2:** `/bx:parallel` in session 1. Expected:
  - `.gitignore` is committed first;
  - session 2 is asked once, joins `.claude/worktrees/<ref>` based on `main`;
  - session 1 moves to `s/<ref>`.
- [ ] **Step 3:** both sessions make a commit and run `/bx:save`. Expected:
  - distinct S numbers;
  - each entry lists only its own commits;
  - distinct versions if `bx/` changed;
  - both land.
- [ ] **Step 4:** session 2 is busy while session 1 lands. Expected: session 2 receives "landed" mid-task.
- [ ] **Step 5:** kill session 1 while it holds the lock (close the terminal during save). Expected: session 2's `land` breaks the lock with `reason=gone` (owner no longer listed). Also record whether SessionEnd fired.
- [ ] **Step 6:** interrupt a rebase by hand in a worktree. Expected: `land` stops with `rebase=interrupted`.
- [ ] **Step 7:** with the mode off, run `/bx:save` on a single session. Expected: same output and same files as before the change.
- [ ] **Step 8: Commit the results log.** Open known-issues for any failure; do not paper over it.
