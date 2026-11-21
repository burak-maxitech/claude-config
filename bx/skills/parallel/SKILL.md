---
name: parallel
description: "Turns on parallel mode for several Claude Code sessions on one repo: finds the other sessions, gives each its own worktree or branch after its own user says yes, and makes main move only through a locked land step. Run once, in any one session, when you want simultaneous sessions; then status, land, off, join or unlock --force."
disable-model-invocation: true
effort: low
argument-hint: "[status|land|off|join|unlock --force]"
allowed-tools: Read, Edit, Bash(bash:*), Bash(git:*), ListAgents, SendMessage, EnterWorktree, AskUserQuestion
---

# /bx:parallel - simultaneous sessions on one repo

Several sessions in one folder damage each other without noticing: one commits the other's half-done
edits, one switches branch under the other, and both `/bx:save` the same session number. Parallel
mode gives every session its own place to work and makes `main` move only through `land`, one
session at a time. Burak runs `/bx:parallel` once, in any one session. That session recruits the
others over `SendMessage`, and each of them moves only after its own user says yes **in that session**.

Messages carry the news; the files under `<git-common-dir>/bx-parallel/` enforce the rules. A
message can arrive late; the lock can't be missed.

## Arguments

| Argument | What runs |
|---|---|
| *(none)* | Setup: find the peers, place every session, send the setup message |
| `join` | A peer joins after its user says yes |
| `status` | Mode, members, lock, and landed worktrees that are safe to remove |
| `land` | Rebase onto `main` and fast-forward `main`, under the lock |
| `off` | Tell the peers, turn the mode off |
| `unlock --force` | Release a lock someone else holds, after showing it and confirming |

Anything else: print this table and stop.

## Values every step uses

- **`P`** is `bash <skill-dir>/scripts/parallel.sh`, with `<skill-dir>` resolved against **this
  skill's base directory** to an absolute path. Run every script call as `P <subcommand> ...`. Its
  output is `key=value` lines; read the exit code too. `P help` lists the subcommands. Exit 10,
  `error=not-a-git-repo`, from any subcommand: this folder is not in a git repo; say so and stop.
- **This session's name and ref:** call `ListAgents`. Its first line is
  `This session is <name> [<ref>]`. Peer rows follow as
  `<name> [<ref>] · interactive · busy|idle · started …`.
- **Live refs:** this session's ref plus the ref of every peer row, joined with commas
  (`a,b,c`). It is never empty, because this session's own ref is always in it.
- **Naming a peer:** sessions on the same repo share the folder-derived name, so always write a peer
  as `name [ref]`, never by name alone.
- **Messaging the members:** the `members` file holds refs only. To message "each other member",
  take each `member ref=<r>` from `P status` other than this session's ref, find the peer row with
  `[<r>]` in the `ListAgents` listing you just read, and send to that row's `name [<r>]`. A member
  with no row has closed; pruning removes it.
- **Main folder:** the first `worktree` line of `git worktree list --porcelain`.
- **This folder / branch:** `git rev-parse --show-toplevel` and `git branch --show-current`.

When comparing folders, compare them as git prints them, with `/` separators; on Windows ignore case.

## Pruning (every argument runs this first)

A session that closed never says goodbye. Before anything else:

1. `P status`. If it prints `mode=off`, skip the rest of pruning.
2. For each `member ref=<r> ...` line whose `<r>` is not in the live refs, run `P leave <r>`.
   `leave` also releases a lock that member held. If a `leave` prints `mode=off`, the last member
   has gone and the mode is off; say so.

This is how a closed session leaves, and how the last one leaving turns the mode off.

## Setup (no argument)

1. **Find the candidates.** After pruning, if `P status` still says `mode=on`, the mode is already
   on: print the status and stop (`/bx:parallel join` joins it, `/bx:parallel off` ends it).
   Otherwise take this session's name and ref from `ListAgents`. A peer is a candidate when its
   name equals this session's name or the main folder's last path segment. No candidates: say
   "No other sessions on this repo." and stop.

2. **Ask each candidate where it works.** The listing does not show folders or branches. Send each
   candidate one `SendMessage` whose first line stands alone (the recipient sees only that line as a
   preview):

   ```
   bx:parallel question from <name> [<ref>]: which folder and git branch are you working in? Reply "folder=<absolute path> branch=<branch>".
   ```

   Then tell the user you are waiting for these replies and end the turn. Replies arrive as
   messages; a busy peer answers at its next tool call. Go on to step 3 once every candidate has
   answered, or when the user says to go on without the rest. A candidate that never answered is
   left out and listed as `no reply` in step 6.

   Drop a candidate whose folder is not in this repo's `git worktree list --porcelain`. Then work
   out every session's placement by the rules in step 4.

   **The main folder is on `main` and no session here keeps it.** Then nobody in the mode will
   move it off `main`, and every `ff-main` would refuse. What to do depends on whether every
   candidate answered step 2:
   - **Some candidate did not reply.** It may be working in the main folder on `main`, so its
     owner is unknown. Offer no detach and leave the folder alone. Tell the user that the main
     folder's owner is unknown and that landing will need `main` freed there later (`land` reports
     it when `ff-main` refuses).
   - **Every candidate replied and none is in the main folder** (and neither is this session).
     Check `git -C <main folder> status --porcelain --untracked-files=no`. If it prints anything,
     stop and tell the user: the main folder has uncommitted changes on `main` and no session to
     own them, so it must be cleaned up by hand before parallel mode can start. If it prints
     nothing, setup will run `git -C <main folder> switch --detach` in step 4, and the
     confirmation below says so.

   Show the placement as a table (session · folder · branch now · placement), plus the detach line
   when it applies, and ask the user with `AskUserQuestion`: "Turn parallel mode on with this
   placement?" On no, stop; nothing has changed.

3. **Ignore the worktree folder before any worktree exists.** Run `P ensure-ignore`. It adds
   `.claude/worktrees/` to `<git-common-dir>/info/exclude`, the exclude file every worktree of this
   repo shares. That file is untracked, so nothing is committed and no session's branch or tree
   changes. `ignore=present` means git already ignores the folder (a `.gitignore` rule counts);
   `ignore=added` means the line was written.

4. **Turn the mode on and place this session.** The placement rules, for every session:
   - **Keeps the main folder:** the session in the main folder. If this session is there, it is
     this one. If several peers are there and this session is not, the first of them in the
     `ListAgents` order. If it is on `main`, it moves to `s/<its ref>` with `git switch -c`, which
     keeps its uncommitted edits. On any other branch it stays on that branch.
   - **Moves into a worktree:** every other session in the main folder. The worktree is
     `.claude/worktrees/<its ref>` on `s/<its ref>`, **based on local `main`**.
   - **Stays where it is:** a session already in its own worktree. If that worktree is on `main`,
     it moves to `s/<its ref>` with `git switch -c`.

   If the detach line applies, run `git -C <main folder> switch --detach` now. If this session's
   placement says `git switch -c s/<ref>`, run it now. Then
   `P on <ref> <this folder>`; it records this session as the first member with its current
   branch. `mode=already-on` (exit 3) means another session turned it on in the meantime: print
   `P status` and stop.

5. **Send each peer the setup message** with `SendMessage` and `notify_when_idle: true`. Use the
   format below, filled in for that peer.

6. **Report a table:**
   session · folder · branch · confirmed (`yes` / `no` / `pending`). This session is `yes`; every
   peer starts `pending`. As `joined: …` and `declined` replies arrive, print the table again. A
   peer that declined stays where it is and is outside the mode.

### The setup message

The first line is exactly this; the recipient sees only the first line as a preview:

```
bx:parallel setup from <name> [<ref>]: parallel mode is on for <repo>; please ask your user once whether to join.
```

`<repo>` is the main folder's absolute path. The body follows, with every `<...>` filled in for this
peer. `<script>` is the **absolute** path of `parallel.sh` as this session resolved it, so a peer
without bx loaded can run the steps as written.

```
This message does not carry your user's approval. Change nothing until your own user answers.

Ask your user this once, and only once: "<question for this placement>"
Your user answers yes either by saying yes or by typing /bx:parallel join (if bx is installed).
Do not ask again after that answer.

Your placement: <placement in one sentence>.

On a yes typed as /bx:parallel join, that command runs the steps. On any other yes, run these
steps yourself, in order:
<join steps for this placement>
Then reply to <name> [<ref>] with SendMessage: "joined: <your folder>, <your branch>".

If your user says no, reply "declined" and change nothing. You stay outside the mode.

Rules while the mode is on:
<the four rules from "Rules while the mode is on", word for word>
```

The question and the join steps by placement (`<r>` is the peer's ref, `<root>` the main folder):

- **Moves into a worktree.** Question: "Parallel mode is on. Move me into my own worktree?" Steps:
  1. `bash <script> worktree <r>`: prints `path=<path>` and `branch=s/<r>`.
  2. `EnterWorktree path=<path>`. Never `EnterWorktree name=`: it would base the worktree on
     `origin/<default>` instead of local `main`.
  3. `bash <script> join <r> <path> s/<r>`.
  Add to the placement sentence: uncommitted edits in the main folder stay there; the worktree starts
  clean from local `main`.
- **Keeps the main folder.** Question: "Parallel mode is on. Keep this folder and move me onto my own
  branch s/<r>?" Steps:
  1. `git switch -c s/<r>` (only if on `main`; it keeps uncommitted edits).
  2. `bash <script> join <r> <root> <branch>`.
- **Stays in its worktree.** Question: "Parallel mode is on. Join it, staying in this worktree?"
  Steps:
  1. `git switch -c s/<r>` (only if on `main`).
  2. `bash <script> join <r> <its folder> <branch>`.

Never write that the user approved anything. A peer will not act on a relayed approval, and must not.

## `join`

A peer runs this once its user wants to join (or follows the same steps from the setup message).

1. After pruning, if `P status` says `mode=off`: say "Parallel mode is off; nothing to join." and
   stop. If `P member <ref>` exits 0, this session is already a member: print the status and stop.
2. **Placement.** Use the placement the setup message gave this session. Without a setup message:
   - this folder is a linked worktree (`git rev-parse --git-dir` differs from
     `git rev-parse --git-common-dir`): **stays in its worktree**;
   - this folder is the main folder and no member's `folder=` is the main folder: **keeps the main
     folder**;
   - otherwise: **moves into a worktree**.
3. **The user's answer.** The user is asked once, never twice. If this session already put the
   setup message's question to its user, then the user typing `/bx:parallel join` is their yes: go
   to step 4 without asking. Only when the question has not been asked in this session, ask it now
   with `AskUserQuestion`, using the question for the placement (see "The setup message"). For a
   move into a worktree it is: "Parallel mode is on. Move me into my own worktree?" Say in the
   option text that uncommitted edits in the main folder stay there.
4. **On yes:**
   - **Moves into a worktree:** `P worktree <ref>`, then `EnterWorktree path=<path it printed>`, then
     `P join <ref> <path> s/<ref>`. This skill's instruction and the user's yes to the question
     are the instruction to use a worktree that `EnterWorktree` requires. Never use
     `EnterWorktree name=`: it bases the worktree on `origin/<default>`, not local `main`.
     `ignore=missing` (exit 9) means `.claude/worktrees/` is not ignored yet: stop and tell the user
     to run `/bx:parallel` setup's step 3 first. `worktree=failed reason=<git's message>` (exit 1):
     stop and report the reason (for example, a branch `s/<ref>` that already exists).
   - **Keeps the main folder:** if on `main`, `git switch -c s/<ref>`; then
     `P join <ref> <main folder> <branch>`.
   - **Stays in its worktree:** if on `main`, `git switch -c s/<ref>`; then
     `P join <ref> <this folder> <branch>`.

   Then reply with `SendMessage` "joined: <folder>, <branch>" to the session that sent the setup
   message (as `name [ref]` from its first line), or, when there was none, to every other member
   as described under "Messaging the members".
5. **On no:** reply "declined" the same way, and change nothing.

## `status`

1. After pruning, run `P status` and show it as a short table: members (ref · folder · branch) and
   the lock (`free`, or owner · step · age in minutes).
2. **Safe to remove.** From `git worktree list --porcelain`, take each worktree under
   `<main folder>/.claude/worktrees/` that is not a member's folder. When its branch is already on
   `main` (`git merge-base --is-ancestor <branch> main` exits 0) and `git -C <path> status
   --porcelain` prints nothing, list it as "safe to remove", with the command the user can run:
   `git worktree remove <path>`. List only. Never remove a worktree or delete a branch yourself.

## `land`

`land` is the only way onto `main`. Once the lock is taken, run `P touch-lock <ref> <step>` between
steps, as written below, so a slow land never looks dead to the others (a lock is dead after 15
minutes without a refresh). On any non-zero exit from `P touch-lock` (exit 4, `lock=not-owner`:
a peer broke the lock as dead), stop at once and report "lock lost; not landed", naming any edits
left uncommitted in the tree. Do **not** run `P unlock`: the lock is no longer this session's.

**Version steps** apply only when `bx/.claude-plugin/plugin.json` exists and
`git diff --quiet main...HEAD -- bx/` exits 1 (this branch changes `bx/`). Every such branch bumps
the same `version` line and adds its entry at the same place in `CHANGELOG.md`, so the bump is
written under the lock, on top of `main`'s version, never earlier. `/bx:save`'s Parallel Path does
the same when it lands, and leaves the bump to this command under `--no-land`.

1. After pruning, `P member <ref>` must exit 0; otherwise say this session is not in parallel mode
   and stop. If `git rev-list --count main..HEAD` is 0, say "Nothing to land." and stop.
   **Version steps, before the lock:**
   - If `git status` shows `bx/.claude-plugin/plugin.json` or `CHANGELOG.md` modified, or
     `git diff --quiet main...HEAD -- bx/.claude-plugin/plugin.json CHANGELOG.md` exits 1, stop
     with nothing changed and tell the user: "Found changes to `bx/.claude-plugin/plugin.json`
     and/or `CHANGELOG.md` on s/<ref>, either your own edits or edits from an interrupted parallel
     save or land. In parallel mode these two files are rewritten under the land lock, on top of
     main's version. Undo those changes (keep any entry text) and run `/bx:parallel land` again."
     When the change is committed, also name the commit to drop: the commits that touch the files
     are listed by `git log --oneline main..HEAD -- bx/.claude-plugin/plugin.json CHANGELOG.md`.
     An interrupted save left them in `docs: S<n> save (parallel)` (its docs are rewritten by the
     next save), an interrupted land in `chore: v<x> — …`. Name that commit's sha and subject, and
     give the user the command that drops it, `git rebase --onto <sha>^ <sha>`. Never rewrite the
     branch yourself.
   - Draft one CHANGELOG line from `git log --format=%s main..HEAD`. Ask one `AskUserQuestion`
     whose text shows that draft: "Version bump for this land, and its CHANGELOG line?", with the
     options patch, minor and major (PATCH for fixes and doc corrections, MINOR for a new
     skill/agent/flag, MAJOR for breaking renames or removed behavior). A typed answer may change
     the line. Keep the level and the line.
2. **Lock.** `P lock <ref> land --live-refs <live refs>`.
   - `lock=acquired`: go on. A `lock=broken prev_owner=… reason=stale|gone` line before it means a
     dead lock was broken; report that line.
   - Exit 4, `lock=held owner=<o> age=<s> step=<step>`: report the holder and stop. To be told when
     it is done, send `<o>` one message with `notify_when_idle: true`:
     `bx:parallel from <name> [<ref>]: waiting for the land lock you hold; nothing for you to do.`
     Run `/bx:parallel land` again after the idle notice.
   - Any other exit (for example exit 2, `mode=off`, or exit 1, `lock=error ...`): report the output
     and stop.
3. **Tell the peers**, now that the lock is held. `SendMessage` each other member:
   `bx:parallel from <name> [<ref>]: landing s/<ref> onto main now; nothing for you to do.`
4. **Catch up.** `P touch-lock <ref> catch-up`, then `P catch-up`.
   - `caught_up=<n>`: go on.
   - Exit 5, `rebase=interrupted` (an earlier crash left a rebase): `P unlock <ref>`, then ask the
     user with `AskUserQuestion`: continue or abort the rebase. Run `git rebase --continue` or
     `git rebase --abort` as chosen, then tell the user to run `land` again.
   - Exit 6, `tree=dirty`: `P unlock <ref>`. Tell the user to commit or stash first. Never stash
     for them.
   - Exit 7, `conflict files=…` or `rebase=failed reason=…`: the rebase was aborted. `P unlock
     <ref>`, report the files or reason, and stop. Code conflicts are the user's to resolve.
     When every conflicting file is a docs file (`CLAUDE.md`, `docs/…`) and the branch carries a
     `docs: S<n> save (parallel)` commit from a `/bx:save --no-land`, that commit is the cause: its
     `Last Updated` lines collide with a save a peer landed since. Name it, give the command that
     drops it, `git rebase --onto <sha>^ <sha>`, and say to run `/bx:save`, which writes the docs
     again on top of `main` and lands.

   **Can `main` move?** Before anything is written, `P ff-main --check`. It runs step 5's two
   tests and moves nothing.
   - `ok=1`: go on.
   - Exit 8, `main=checked-out path=<p>`: handle it exactly as step 5's exit 8 (unlock first, then
     the member-folder report or the detach offer). Nothing has been written or committed, so the
     user frees `main` and runs `land` again.
   - Exit 7, `main=not-ff`, or exit 2, `error=detached-head`: `P unlock <ref>`, report, stop.
     Nothing has been written.

   **Version steps, under the lock** (only when step 1 kept a level): `P touch-lock <ref> version`,
   then `P version-check --level <level>`.
   - `main=<v> level=<level> next=<x>`: set `version` in `bx/.claude-plugin/plugin.json` to `<x>`.
     Insert at the top of `CHANGELOG.md`, directly above the first `## ` version heading (newest
     first): `## <x> — <today>`, a blank line, then the kept line. Stage the two files by name and
     commit them with `git commit -m "chore: v<x> — <the line, shortened to a summary>"`. Then
     `P touch-lock <ref> version-done`.
   - `version=n/a`: nothing to do.
   - Exit 1, `version=error …`: `P unlock <ref>`, report, and stop.
5. **Fast-forward `main`.** `P touch-lock <ref> ff-main`, then `P ff-main`.
   - `landed=<sha>`: go on.
   - Exit 8, `main=checked-out path=<p>`: `main` is checked out in `<p>`. `P unlock <ref>`.
     `main` did not move. Step 4's check makes this rare (`main` was checked out after it ran), but
     a version commit made under the lock is now on the branch: name it and the command that drops
     it, as step 1's guard does, because the next `land` refuses until it is gone. If `<p>` is a
     member's folder, report that the session in `<p>` has to move onto its own branch first, and
     stop. Otherwise:
     1. Say "`<p>` is not a parallel-mode member's folder". Never say that no session holds it: a
        live session that declined the mode can be working there on `main`.
     2. Read `ListAgents` again and list the live peer sessions on this repo (the candidate rule
        from setup step 1) whose refs are not members, as `name [ref]`.
     3. If `git -C <p> status --porcelain --untracked-files=no` prints anything, tell the user `<p>`
        has uncommitted changes on `main` that must be cleaned up by hand, and stop.
     4. Otherwise ask with `AskUserQuestion`: "Detach main in <p> with
        `git -C <p> switch --detach`? If any of these sessions works in <p>, it would be left on a
        detached HEAD: <the list, or 'none listed'>." Make "Do nothing" the first, default
        option. Only on an explicit detach answer run it, then tell the user to run `land` again.
        On anything else, change nothing.
   - Exit 7, `main=not-ff`, or exit 2, `error=detached-head`: `P unlock <ref>`, report, stop.
6. **Push only if the user asked** in this conversation: `git push origin main`.
7. **Unlock.** `P unlock <ref>`.
8. **Tell the peers.** `SendMessage` each other member:
   `bx:parallel from <name> [<ref>]: landed <sha>, catch up before your next save.`
   This is the `/bx:parallel land` form. A land from `/bx:save` knows its session number and sends
   `landed S<n> at <sha>, catch up before your next save.` instead.

## `off`

1. After pruning, run `P status` and show it. If it says `mode=off`, say so and stop.
2. **A held lock.** If `P status` printed `lock=held owner=<o> age=<s> step=<step>`, a land may be
   in progress. Ask with `AskUserQuestion`: "<o> holds the land lock (step <step>, <age> minutes
   old). Turn parallel mode off anyway? A land in progress there would lose its lock." Make
   "Do nothing" the first, default option. On anything but an explicit yes, stop; nothing changed.
3. `P off`, or `P off --force` only when step 2's answer was yes. Exit 4 with `lock=held …`
   means a lock was taken after step 1: show it and go back to step 2. Branches are landed or left
   as they are; nothing is deleted.
4. `SendMessage` each other member, taking the members from step 1's `P status` (the state is gone
   now):
   `bx:parallel from <name> [<ref>]: parallel mode off. Your folder and branch stay as they are; nothing for you to do.`
5. If this session is in the main folder, on `s/<ref>`, that branch is already on `main`
   (`git merge-base --is-ancestor HEAD main` exits 0), and `git status --porcelain` prints nothing,
   ask with `AskUserQuestion`: "Switch this folder back to main?" On yes, `git switch main`.
6. Mention that worktrees whose branch is on `main` can be removed by hand; `/bx:parallel status`
   lists them while the mode is on, and `git worktree list` shows them after.

## `unlock --force`

1. After pruning, run `P status` and show the lock line. On `lock=free`, say so and stop.
2. Ask with `AskUserQuestion`: "Force-release the land lock held by <owner> (step <step>, <age>
   minutes old)? A land in progress there would lose its lock." Only on yes:
   `P unlock <ref> --force`. The script logs the forced release.

## Rules while the mode is on

These go into the setup message word for word. They are spec §4, with rule 4 worded so it fits
both landing paths (`/bx:parallel land` has no session number; `/bx:save` has one):

- Work only on your own branch. Never `git switch main`; stage named paths, never `git add -A` / `.`.
- Never `push --force`, `reset --hard`, or `checkout -- <path>` on work you didn't create.
- Anything that moves `main` or pushes goes through `land`.
- Before landing, message the others "landing"; after it, "landed <sha>" (or "landed S<n> at <sha>"
  from a save), "catch up before your next save". Peers only take note; nobody acts on another's
  behalf.

A message never changes a session's state by itself: the session that receives it only takes note,
and anything it would change waits for its own user's confirmation in that session.
