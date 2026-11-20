# /bx:parallel: safe simultaneous sessions on one repo

Date: 2026-11-20 (S70) · Status: draft v2, awaiting approval

## Intent

Burak sometimes runs two or more Claude Code sessions on the same repo on one machine (today:
two horowell sessions, one busy for 5 h). Nothing defines how they share it. Whether a session
works in the main folder on `main` or in a worktree is up to whoever starts it. Two sessions in one
folder cause silent damage: one commits the other's half-finished edits, one switches branch under
the other, and the last write to a shared file wins. `/bx:save` adds silent bugs even across separate
folders:

- **Session number:** both sessions write S71.
- **Commit attribution:** save finds its commits from the last commit that wrote `docs/STATUS.md`.
  If another session saves in between, this session's commits go to the wrong entry or vanish.
- **Plugin version:** two different changes can both ship as one `plugin.json` version. The version
  is the update cache key, so users silently miss the second change.
- **STATUS.md / CLAUDE.md:** both sessions edit the same sections (a loud merge conflict, hand-resolved).

`/bx:save` is the main concern; commit, merge, rebase and push come second.

## Goals

1. Burak runs `/bx:parallel` **once, in any one session**, when he wants simultaneous sessions. That
   session finds the others on the repo, and from then on they keep each other informed.
2. Every session gets its own place to work: a worktree, or its own branch for the session that keeps
   the main folder. Each session moves only after one confirmation from Burak **in that session**.
3. **Each session saves only its own work**: its own session number, session entry, commit list
   and version bump. Every session saves; saves never fight.
4. Only one session moves `main` at a time.

## Non-goals

- Coordination across machines or with cloud sessions.
- Detecting parallel sessions automatically. The mode exists only when Burak turns it on.
- Merging conflicting **code** between sessions. On a code conflict, the session stops and asks.
- Bringing one session's unlanded work into another.

## Anti-goals

- Any change to single-session behaviour or to `/bx:save` when the mode is off.
- A session changing its own state on another session's say-so without its user's confirmation.
  (Verified behaviour, test 3: a session refuses a relayed "your user approved this".)
- A crashed session blocking the others' saves for long.
- Moving a branch that is checked out in another session's folder.

## Approaches

**How the mode starts:**
- Automatic detection by startup hooks plus a session registry. *Rejected by Burak:* he would rather
  turn the mode on himself than have sessions detect each other.
- **Explicit `/bx:parallel` in one session, which recruits the others over cross-session messaging
  (chosen).**
- Running `/bx:parallel` in every session. *Rejected:* Burak wants to run it once.

**How other sessions get reorganised:**
- **A. One confirmation per session at setup (chosen).** Each peer asks its user "move me into my
  own worktree?" once.
- B. A standing permission written into CLAUDE.md. *Rejected:* any message could use it, and peers
  may still ask, because they can't verify that a message really came from `/bx:parallel`.

**What a save lands:** code and docs together (chosen). Docs-only landing was rejected because
STATUS.md on `main` would describe work that isn't on `main`. `--no-land` keeps everything on the branch.

## Verified platform behaviour (spike, 2026-11-20, two claude-config sessions)

| Question | Result |
|---|---|
| Can a session find the others? | `ListAgents` lists local sessions as `name [ref]` with busy/idle. Name = folder name; same-repo sessions share it. The listing does **not** give a session's folder or branch, so ask each peer. |
| Does an idle peer get a message? | Yes, and it replies via `SendMessage`. |
| Does a busy peer get a message? | Yes, at its next tool call (it arrived on file 4 of 11). |
| Does a permission-mode mismatch block messages? | No (auto ↔ prompting, no approval needed). |
| Can a session be told when a peer is done? | Yes: `notify_when_idle` sends one idle notice. |
| Does a peer act on a relayed approval? | **No.** It waits for its own user's confirmation. |
| What does `EnterWorktree` do? | It creates `.claude/worktrees/<name>` on branch `worktree-<name>`, based on the current HEAD, marked `locked`. The name and ref survive the move. |
| Is that folder git-ignored? | **No.** The main folder's `git status` shows `.claude/worktrees/` as untracked, so `git add -A` there would try to stage the peer's worktree. |

## Design

### 1. Shared state

`<git-common-dir>/bx-parallel/` is the same path from every worktree, and git doesn't track it.
- `mode.json`: `{on: true, started, started_by, members: [{ref, folder, branch, session}]}`. It
  exists only while the mode is on.
- `land.lock/`: a directory created with `mkdir`, so creating it is atomic. It holds `owner.json`
  `{ref, since, step}`, refreshed at every step.

One script, `bx/scripts/parallel.sh`, owns every read and write: `on`, `off`, `join`, `leave`,
`status`, `lock`, `touch-lock`, `unlock`, `land`. The numbers below live there only.

Messages carry the news; the files enforce the rules. A message can arrive late; the lock can't be missed.

### 2. `/bx:parallel` (setup, run once)

1. `ListAgents`. Peers whose name matches this repo's folder name, or whose name is the same as this session's, are candidates.
2. Ask each candidate for its folder and branch. Drop any whose folder isn't a worktree of this repo.
3. Ensure `.claude/worktrees/` is in `.gitignore`. Commit that line on its own if it was missing,
   **before** any worktree is created.
4. Write `mode.json`. Decide placement:
   - The session in the main folder (this one, if it is there) keeps the folder and moves off `main`
     with `git switch -c s/<ref>`, keeping its uncommitted edits.
   - Every other session sharing the main folder moves into a worktree **based on `main`**.
   - Sessions already in their own worktree stay where they are.
5. Send each peer the setup request: the rules (section 4), its placement, and "ask your user once:
   *Parallel mode is on. Move me into my own worktree? (yes/no)*". Subscribe `notify_when_idle`.
6. Report a table: session · folder · branch · confirmed yes/no/pending.

Sub-commands: `/bx:parallel status`, `/bx:parallel land`, `/bx:parallel off`,
`/bx:parallel unlock --force` (shows the holder first).

### 3. Joining (in each peer, after its user says yes)

Enter the worktree from `main`. `EnterWorktree` bases it on the current HEAD; if that isn't `main`,
create it with `git worktree add -b s/<ref> .claude/worktrees/<ref> main` and enter that path. Add
itself to `mode.json`, then reply "joined: folder, branch". If its user says no, it replies "declined";
it stays where it is, and the others treat it as outside the mode.

### 4. Rules while the mode is on (carried in the setup message)

- Work only on your own branch. Never `git switch main`; stage named paths, never `git add -A` / `.`.
- Never `push --force`, `reset --hard`, or `checkout -- <path>` on work you didn't create.
- Anything that moves `main` or pushes goes through `land`.
- Before landing, message the others "landing"; after it, "landed S<n> at <sha>, catch up before
  your next save". Peers only take note; nobody acts on another's behalf.

### 5. `land`: the only way onto `main`

1. `lock`. If a peer holds it, report the holder and wait (or use `notify_when_idle` on it).
   **The lock is dead** only if it hasn't been refreshed for **15 minutes**, or its owner is no longer
   listed in `ListAgents`; then it's broken, and the break is logged.
2. If a rebase is already in progress in this worktree (an earlier crash), stop and ask:
   continue or abort.
3. Rebase onto `main`. On a code conflict: abort, unlock, report.
4. Fast-forward `main`: `git fetch . <branch>:main`. Git refuses if `main` is checked out anywhere
   or the move isn't a fast-forward. That is the safety net.
5. Push only if the user asked. `unlock`. Message the peers.

### 6. `/bx:save` while the mode is on

When `mode.json` exists and this session is a member, save runs this path; otherwise it is unchanged.

1. **Prompts first, nothing under the lock:** Part 8's "commit these?", plugin validate, `--full`
   consent. The code commit goes onto the session branch.
2. `lock`, then rebase onto `main`. This brings in only what has already **landed**, never a peer's
   unlanded work. On a code conflict: abort, unlock, report; no docs are written.
3. Read the **latest** STATUS.md / CLAUDE.md. Then:
   - **Own work only:** the commit list is `main..HEAD` (this branch), not the save anchor.
   - **Session number:** the number in the `Last Updated` line on `main` + 1 (CLAUDE.md on v1 repos).
     A `cont.` save stays the orchestrator's judgment.
   - **Version:** if this branch's `plugin.json` bump isn't above `main`'s, re-bump and fix this
     session's CHANGELOG header.
   - Build the packet's old-strings from this read; dispatch `save-writer`; commit the docs.
4. Land steps 4–5. `--no-land` stops after the docs commit (the lock is released).
5. `--silent`: wait for the lock up to 2 minutes, then stop with "saved on branch, not landed".

### 7. Ending

`/bx:parallel off` (any session), or the last member leaving, deletes `mode.json` and messages the
peers "parallel mode off". Each session's branch is landed or left as it is; nothing is deleted.
The main folder's session may switch back to `main` once its branch is landed and its tree is clean.
`/bx:parallel status` lists worktrees whose branch is already on `main` as safe to remove. It never
removes them itself.

## Acceptance (verify by running, on a throwaway clone)

1. Failing control: two sessions in one folder, both run today's `/bx:save`. Expect a duplicate S number
   or misattributed commits. Repeat with the mode on: distinct numbers, own commits only, distinct versions.
2. `/bx:parallel` in one session: the peer is asked once, joins a worktree based on `main`, and
   `.gitignore` covers `.claude/worktrees/` first.
3. A busy peer receives "landing" / "landed" mid-task.
4. Kill a session while it holds the lock: the next session breaks it once the owner leaves
   `ListAgents`, or after 15 minutes.
5. A crash mid-rebase: the next `land` in that worktree stops and asks.
6. With the mode off: `/bx:save` output is byte-identical to today's on a fixture.

## Left to the builder

- Exact message wording (first line self-contained, as `SendMessage` previews it).
- How `/bx:save` learns the session's own ref (e.g. from `ListAgents`' "This session is …" line).
- Whether to auto-remove a landed worktree on `off` after asking (default: list only).
