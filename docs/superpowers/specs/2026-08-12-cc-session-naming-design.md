# Design: Per-project session name + color in the `cc` launcher

**Date:** 2026-08-12 (Session 55)
**Status:** Approved, pending implementation plan
**Files touched:** `.claude/scripts/start-claude.ps1`, `.claude/scripts/start-claude.sh`, `README.md`

---

## Problem

Running several Claude Code sessions on one machine — one per repo — makes windows
indistinguishable. Alt-tabbing lands in the wrong project, and once inside a session
nothing on screen names the repo.

Claude Code ships per-session naming and coloring, but neither is wired to how sessions
actually start here (`cc` / `cc <project>`). Every session launches anonymous.

## Goal

`cc horowell` — or `cc` plus a pick from the numbered menu — launches a session already
named after the project and colored distinctly from the other projects, with no manual
step and no per-project configuration to maintain.

---

## Upstream constraints (verified 2026-08-12, Claude Code 2.1.228)

These determine the whole design, so they are recorded with their evidence.

| Capability | Status | Evidence |
|---|---|---|
| Set session **name** at launch | **Supported.** `-n, --name <name>` — "Set a display name for this session (shown in the prompt box, /resume picker, and terminal title)" | `claude --help` on 2.1.228; [CLI reference](https://code.claude.com/docs/en/cli-reference); [Manage sessions](https://code.claude.com/docs/en/sessions#name-your-sessions) |
| Set session **color** at launch | **Not supported.** No CLI flag, no settings key. Requests closed `not_planned`: [#44800](https://github.com/anthropics/claude-code/issues/44800) (flag or settings key), [#47332](https://github.com/anthropics/claude-code/issues/47332) (project-level color), [#40393](https://github.com/anthropics/claude-code/issues/40393) (`--color`). Still open: [#58588](https://github.com/anthropics/claude-code/issues/58588), [#78203](https://github.com/anthropics/claude-code/issues/78203) | GitHub issue search, 2026-08-12 |
| `/color` as a **local** command | Accepts `red blue green yellow purple orange pink cyan` or `default`; bare `/color` picks at random. Available in non-interactive mode since v2.1.205 | [Slash commands](https://code.claude.com/docs/en/commands) |
| `/color` passed as a **prompt argument** | Handled locally, no model turn. `claude -p --no-session-persistence "/color blue"` → `Session color set to: blue`, exit 0 | Run directly on this machine, 2026-08-12 |

**The color palette has exactly 8 entries and this machine has exactly 8 project folders.**
Any hash of the project name into 8 buckets collides — expected distinct buckets for 8 items
is ~5.2, not 8. Measured on the real folder names:

```
                    djb2 % 8    bytesum % 8
burakarik6          cyan        green
claude-config       pink        blue
horowell            blue        purple
kaanarik            cyan        green
maxitech-concierge  purple      cyan
maxitech-crm-sync   blue        purple
personal-tools      cyan        green
venture-compass     blue        purple
                    4 distinct  4 distinct
```

(Both land on the same partition because `33 mod 8 == 1`, which reduces djb2 mod 8 to a byte
sum. A better hash raises the count to ~5, not 8 — the ceiling is the birthday paradox, not
hash quality.) Hashing is therefore rejected as the assignment strategy.

---

## Design

### 1. Launch command

Step 5 of both launchers changes from `claude` to:

```
claude -n "<project>" "/color <color>"
```

- `-n` covers the outside-the-window need (terminal tab title) and the inside-the-window
  need (name chip on the prompt bar, `/resume` picker entry) in one flag.
- The `/color` prompt argument is the only launch-time route to the prompt-bar color.

Step 5's console line echoes the choice so a mis-assignment is visible immediately:

```
[5/5] Launching Claude Code as "horowell" (cyan)...
```

### 2. Color registry — sticky auto-assign

State lives in a machine-local file, **`~/.claude/cc-session-colors`**
(Windows: `%USERPROFILE%\.claude\cc-session-colors`). It sits outside the repo because the
project set is machine-specific: nothing to gitignore, nothing to sync, no merge conflicts.

Format — one `name=color` pair per line, so both PowerShell and bash parse it without `jq`:

```
# cc session colors - auto-assigned, safe to delete (colors get reassigned)
horowell=cyan
kaanarik=green
claude-config=blue
```

### 3. Allocation algorithm

Identical in both launchers, so the same project gets the same color on any machine that
starts from the same registry file.

**Palette, in allocation order:** `cyan, green, blue, purple, orange, pink, yellow, red`.
Calm colors first; `red` last so an early project does not permanently look like an error
state.

Given a project name:

1. Read the registry if it exists. Skip blank lines, lines starting with `#`, lines without
   exactly one `=`, and lines whose color is not in the palette. A malformed file degrades to
   an empty registry — never a fatal error.
2. If the project has a valid entry, use that color. Do not rewrite the file. Name matching is
   **case-insensitive** and preserves the casing already in the registry: PowerShell `-eq` is
   case-insensitive, so bash must lower both sides to match, or `cc Horowell` would append a
   second entry alongside `horowell` on a case-sensitive filesystem.
3. Otherwise assign:
   - the first palette color not used by any entry; or
   - if all 8 are in use, the least-used color, ties broken by palette order.
4. Append `<project>=<color>` and write the file back. Create the file (with its comment
   header) and `~/.claude/` if absent.
5. Any failure to read or write the registry falls back to launching with the name only —
   coloring is a convenience and must never block a session start.

Deleting the file reshuffles every project on the next launch; that is the documented reset.

### 4. Cross-platform parity

`start-claude.ps1` and `start-claude.sh` implement the same palette, file format, allocation
order, and echo line. The PowerShell version must gate on `$LASTEXITCODE` rather than
`try/catch` if it ever calls a native exe (existing repo rule from S40); the allocator itself
is pure PowerShell/bash and calls none.

---

## Out of scope

- **Two sessions on the same repo.** Both get the same name and color. The pain being solved
  is cross-project; disambiguating would require enumerating live sessions at launch. Revisit
  only if it becomes a real annoyance.
- **Sessions started with plain `claude`.** They stay unnamed and uncolored. Covering them
  would need a custom statusline or global settings; keeping all logic in the two launcher
  files was an explicit scope choice.
- **A hand-edited pin map.** The registry is auto-generated. Hand-editing a line works (it is
  read back as a valid entry), but no UX is built around it.

---

## Risk and fallback

**Unverified link:** `/color` as a prompt argument is proven for `-p`; the interactive path
could not be exercised from a tool call because it requires a TTY. The first real `cc` launch
settles it.

If the interactive path does *not* apply the color, the fallback is a custom `statusLine`
command that prints a per-project colored banner. The statusline receives
`workspace.project_dir` and `session_name` on stdin and supports ANSI escapes, so it can
reproduce both cues. It is deliberately not built up front: it is more moving parts, it
overrides the footer keyboard hints, and it would touch global `~/.claude` config, which the
launcher-only scope avoids.

---

## Verification

1. **Allocator unit check (no Claude involved).** Point the function at a temp registry path
   and confirm: a fresh name claims `cyan`; a second name claims `green`; re-running the first
   name returns `cyan` without duplicating its line; a malformed line is ignored; a 9th project
   reuses the least-used color.
2. **Live check.** `cc claude-config` — prompt bar colored, name chip reads `claude-config`,
   terminal tab title changed. Then `cc horowell` in a second window — different color, and
   the registry now holds both entries.
3. **Parity check.** Not runnable on this machine; the bash allocator is verified by reading
   the same registry file and printing the color it would pick for each project name.

---

## Notes

The launcher scripts are **not** plugin components — they live in `.claude/scripts/`, outside
`bx/`. This change therefore needs no `plugin.json` version bump (the S54 bump-on-`bx/**`-change
rule does not apply). README's setup section gains a sentence describing the behavior.
