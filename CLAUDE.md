<!-- bx-doc-schema: 2 -->
# CLAUDE.md

Last Updated: 2026-08-18 (Session 56)

## Project Overview

**claude-config** — Personal Claude Code configuration repo containing custom skills, subagents, and workflow documentation.

- **Repo:** [burak-maxitech/claude-config](https://github.com/burak-maxitech/claude-config) (public — went public S49 for easier teammate plugin install)
- **README.md** — Public overview, setup instructions, command reference
- **Workflow.md** — Detailed personal workflow guide (daily workflow, scenarios, tips)
- **docs/** — Reference files (session history, key decisions, completed work)

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| `/bx:clean` Step 1 dispatches dedicated Sonnet `cleanup-*` agents (S43) | Generic dispatch ran every scan on Opus; dispatching the named agents restores their `model: sonnet` routing + tool scoping. (commit 65179cd) |
| `/bx:clean` eval suite + measured skill value (S43) | Evals show the skill's edge is fix-mode discipline + prompt-independent coverage, not raw detection; `bx/skills/clean/evals/` committed as a regression suite. (commit 65179cd) |
| `/bx:save --silent` — zero-prompt runs (S44) | Auto-commits with the suggested message; every consent prompt resolves to its safe default (decline/skip) — the flag never answers "yes" for the user except the commit itself. (commit b82162d) |
| `/bx:seo` content-review hardening — doc-drift sweep rule (S45) | A rework isn't done until its stale echoes are swept from sibling files; `allowed-tools` must enumerate every command incl. plugin `bin/` helpers. (`1d6698a`) |
| `/bx:evolve` upstream-watch skill — design contract (S46) | Two-tier authority (official actionable with citations; community advisory-only), committed watermark + decision log, capability-relevance gate; orchestrator computes all hashes. Spec: `docs/superpowers/specs/2026-06-09-bx-evolve-design.md`. |
| Sentinel exit-point principle for /bx:evolve (S46) | `lane-unavailable-*` sentinels are lane-health reports, not findings — they exit at consolidation Step 3.1, and one principle replaces 7 scattered carve-outs. (`21b41bb`) |
| `/bx:evolve` relevance gate confirmed + user-directed registration path (S47) | Gate validated by dogfood; user-directed items register as proper `open` findings with re-fetched verbatim excerpts; lane digest one-liners are NOT citation-grade. |
| `CLAUDE_ENV_FILE` session env persistence (S47) | SessionStart writes UTF-8 env exports to `$CLAUDE_ENV_FILE` (CC 2.1.152+), persisting across Bash calls — the principled fix for the Windows-charmap class. |
| Cross-skill references must resolve against the skill base directory, not repo-rooted paths (S48) | Sibling-skill reads use `../<skill>/...` against the base dir announced at skill load; every background process a skill starts needs its stop mechanism named and permitted. |
| `Agent(model:…)` deny rules do NOT guard omitted-model dispatch (S50) | `Tool(param:value)` rules never match an omitted parameter, so they can't guard generic dispatch; the durable guard is frontmatter `model:` + dispatching agents by name. |
| `${CLAUDE_SKILL_DIR}` is real, but text-substitution — not a shell variable (S50) | Expanded in rendered markdown + `allowed-tools` rules, never by the shell — unexpanded in shell it yields an empty string; the `bin/`-launcher-on-PATH remedy stays correct. |
| `/bx:webdesign` first dogfood + 15-fix hardening (S52) | E2E run paused clean at `review_pending`; all 15 findings were in the delegation surface — key gotchas: `stitch-design:<name>` naming, Tailwind v4 `@theme`, lossy Stitch palette (verify via `get_project` before batch-generating). |
| Scoped `/bx:evolve` runs must freeze the watermark (S53) | Advancing the watermark on a narrowed run would record unexamined skills as audited; a scoped run reports the frozen watermark, leaving a full run still owed. |
| Checkpoints are per-user-prompt, not per-edit — and subagent edits aren't checkpointed at all (S53) | One checkpoint per user prompt (`/rewind` reverts the whole batch), and subagent/background-fork edits are never checkpointed — git is the only undo for those. |
| Explicit semver plugin versioning replaces commit-SHA versioning (S54) | `version` in plugin.json is the update cache key — every `bx/**` change must bump it (PATCH/MINOR/MAJOR; `/bx:save` Part 8 enforces); history in `CHANGELOG.md`. |
| `cc` names and colors sessions at launch — the name is supported, the color is not (S55, 2026-08-12) | `claude -n <name>` is official; no color flag exists (requests closed `not_planned`) — `/color` rides as the initial prompt argument, handled locally with no model turn; fallback is a `statusLine`, not a launcher patch. |
| Sticky color registry beats hashing when the palette is the same size as the project set (S55) | 8 colors × 8 projects makes any name-hash collide (measured 4/8 distinct); first-launch claim + registry in `~/.claude/cc-session-colors` is distinct AND stable. |
| Doc schema v2 — CLAUDE.md/STATUS.md split with consented migration (S56, 2026-08-18) | Always-loaded instructions stay in CLAUDE.md; state moves to `docs/STATUS.md`; `/bx:save` gained MIGRATE (eligibility → consent → `doc-migrator` → invariant checker → isolated commit), proven by 10 fixtures + 7 blind rehearsals. v2.0.0, merged `0eedfe2`. |
| Archives are disk-only and rotate at 100k (S56) | v2.0.1 closed the three linear archive-read paths (Part 3.0 exclusion, tail-anchored appends, windowed rollup); v2.1.0's Part 7.7 rotates >100k archives byte-verbatim into `docs/archive/` volumes (consent + sentinel, B ≤ A ≤ B+600, no count cap — manual `git rm` is the escape hatch). Nothing automatic reads a volume. |
| Blind rehearsals are the acceptance instrument for instruction files (S56) | Agents executing only the instruction text caught what 12+ readings could not (harness conflicts, gate holes, nondeterminism); the decision-log ambiguity count is the regression metric (doc-migrator 5→2; Part 7.7 started at 2). |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Known Issues / Blockers

**The S37 `/bx:seo` "messed up" breakage is RESOLVED (S39).** Root-caused to the `${CLAUDE_SKILL_DIR}` path bug (not a real Claude Code variable → the helper was never found → GSC silently fell back to heuristic-only) + an impossible "mint token once, reuse across Bash calls" auth model (shell state does not persist across Bash tool calls). Both fixed and verified against live GSC. See Session History S39 + Key Decisions.

**Plugin-versioning sharp edge (S54):** `version` in `bx/.claude-plugin/plugin.json` is the plugin's update cache key — a push that changes `bx/**` without bumping it is never offered to users (`/plugin update` reports "already at the latest version"). `/bx:save` Part 8 enforces the bump; manual committers follow the README contributors note. History in `CHANGELOG.md`.

**14 open upstream findings** live in `docs/upstream/state.json`; the watermark is current again (changelog 2.1.228 · docs/community 2026-08-11 — S54's full run released the S53 freeze). Correction from resume: the S53 "5 uncommitted files" claim was stale — they were committed in `e1bd066` and pushed before this session, and the plugin cache already carried them.

**`start-claude.ps1` cannot be parsed by Windows PowerShell 5.1 (pre-existing, found S55).** The file is BOM-less UTF-8 containing seven non-ASCII characters (em-dashes and an arrow); WinPS 5.1 decodes a BOM-less `.ps1` as the ANSI codepage, so `—` becomes `â€"` and the trailing quote terminates a string early — 2 parse errors on 5.1, 0 on pwsh 7. Predates this branch (`git show d78105e:` confirms), and the user runs pwsh 7, but README tells teammates to install `cc` without naming a host. Fix queued in the S55 fix wave: replace the seven characters with ASCII.

**The interactive `/color` path is still unverified (S55).** `/color <c>` as a *prompt argument* is proven for `-p` (`claude -p "/color blue"` → `Session color set to: blue`, exit 0, no model turn), but the interactive path needs a TTY and could not be exercised from a tool call. The `cc` launcher now ships that argument. If the live gate shows the prompt bar is not colored, the documented fallback is a custom `statusLine` printing a per-project colored banner — a fresh design decision, NOT a launcher patch.

> Session state: [docs/STATUS.md](docs/STATUS.md)
