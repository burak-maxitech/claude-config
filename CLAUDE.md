# CLAUDE.md

Last Updated: 2026-05-06 (Session 20)

## Project Overview

**claude-config** — Personal Claude Code configuration repo containing custom skills, subagents, and workflow documentation.

- **Repo:** [burak-maxitech/claude-config](https://github.com/burak-maxitech/claude-config) (private)
- **README.md** — Public overview, setup instructions, command reference
- **Workflow.md** — Detailed personal workflow guide (daily workflow, scenarios, tips)
- **docs/** — Reference files (session history, key decisions, completed work)

## Current Status

| Area | Status |
|------|--------|
| Skills (5) | Complete |
| Subagents (3) | Complete |
| Startup scripts | Complete |
| Mac/Linux setup | Complete |
| Windows setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 5 skills, 3 subagents, cross-platform setup, and documentation system are complete.

See [docs/completed-work.md](docs/completed-work.md) for full checklist.

## In Progress

Nothing currently in progress.

## Next Steps

1. Add more skills as new workflow needs emerge
2. Improve existing skill reference files based on usage patterns
3. Consider adding hooks for automated pre-commit workflows
4. Explore MCP server integration for external tool access

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Scripts don't auto-run /resume-work | User controls when to run /resume-work; avoids forced context load on every launch |
| Setup instructions in README.md only | One-time setup (clone, symlinks, alias) belongs in README; Workflow.md links to it to avoid duplication |
| Don't filter claude-config from project picker | User may want to work on the config repo itself |
| CI gating documented, not implemented in-skill | `defer` PermissionDecision only works for single-tool-call turns and is meant for SDK/subprocess callers; skills can't self-gate. Document the PreToolUse recipe in README instead of adding a `--gated` flag. |
| Plugin `bin/` helpers in resume-work health check | CC 2.1.91 puts enabled plugins' `bin/` on `$PATH`; prefer plugin-provided smoke tests over the generic `package.json → Makefile → pyproject.toml → Cargo.toml` ladder. |
| Standalone skills + installed marketplace plugins coexist | Claude Code docs explicitly recommend standalone `.claude/` for personal config and plugins for sharing. No migration needed; the symlink model is the recommended personal-workflow pattern. |
| Verify every external-repo claim before shipping | Session 13 research on shanraisshan/claude-code-best-practice surfaced 14 candidate patterns. Spot-verification via direct raw.githubusercontent.com fetches found the catalog had conflated skills `paths:` with `.claude/rules/` `paths:`, and that "curation/start narrow" and "/compact at 50%" were community wisdom, not Anthropic guidance. Ship only what docs.claude.com confirms; soften or drop the rest. |
| `plan-feature` Step 0 triviality check + `AskUserQuestion`-driven interview | Session 14 audit against code.claude.com/docs/en/best-practices. Doc explicitly recommends `AskUserQuestion` for the interview pattern and explicitly tells users to skip planning for one-sentence changes ("typo, log line, rename"). Step 0 returns control to the user before the interview overhead; interview itself uses multi-choice prompts with an "Other / explain" escape. Falls back to numbered Q&A when `AskUserQuestion` is unavailable. |
| Surface `/rewind` in destructive `--fix` output | Same Session 14 audit. Doc treats checkpointing as a core safety net for risky operations. Both `code-cleanup --fix` and `code-review --fix` now end with a one-liner pointing the user at `Esc Esc` / `/rewind`. For `code-cleanup`, the existing `git branch -D` instruction stays as the coarse-grained option and `/rewind` is added for finer-grained per-edit undo. |
| Per-skill `effort:` frontmatter tuning | Sessions 15-16. Reasoning-heavy skills on `effort: high`: `/code-review`, `/plan-feature`. Mechanical skills on `effort: low`: `/update-docs`, `/resume-work` (added Session 16 after ~20min real-project run). `/code-cleanup` orchestrator stays at session default — heavy work lives in its Sonnet-pinned subagents. Frontmatter scope is per-invocation; auto-reverts to session default when the skill returns. |
| Parallel batch reads + single `git log` in `/update-docs` Parts 3 and 6 | Session 16. Part 3 now pre-loads all `docs/*.md` in a single parallel-Read turn before editing; Part 6 rollup uses one pre-fetched `git log` across the full compressible date range instead of per-session calls. Pure wins — no functionality change, only faster. Addresses the ~20min user-reported run. |
| Keep custom `/code-review`; position `/ultrareview` as complementary | Session 15. Built-in `/ultrareview` (CC 2.1.111) runs 5-20 verifying subagents in cloud, 10-20min — best for high-risk pre-merge (auth, payments, migrations). Custom skill is faster, in-session, and has `--security`/`--verify`/`--fix` modes that `/ultrareview` lacks. Documented the when-to-use-which split in README. |
| Dropped Session 12 `defer` hook dogfood | Session 15. Carried forward 12→13→14→15. Recipe in README:177 remains untested but documented; user accepted the small risk that it's subtly wrong rather than spend a session verifying. Removed the carry-forward bullet from CLAUDE.md so it stops surfacing in `/resume-work`. |
| Session-history rollup pattern | Session 15. `docs/session-history.md` auto-compresses sessions older than the 5 most recent into one-liners with commit hashes; full prose preserved in git. Implemented as Part 6 in `update-docs/mode-update.md` with `--skip-rollup` escape and a Step 6.2 first-run confirmation prompt (rollup-format note acts as per-project sentinel). Keeps the file bounded across all projects without surprising legacy ones. |
| Active CLAUDE.md cap enforcement (Session 17) | `/update-docs` now runs Part 1.10 every UPDATE: Current Status ≤10 (collapses `Complete` runs), Next Steps ≤10 (warn), In Progress ≤5 (warn). Replaces passive 35k-char warning with active per-section caps. Gated by `--skip-caps`. Root-cause fix for CLAUDE.md growing unboundedly across sessions despite "keep ~20 max" guidance — adding was mechanical, pruning required judgment the model deferred on. |
| Key Decisions rollup + commit-last ordering (Session 17) | Mirrors the session-history rollup. New Part 6 in `update-docs/mode-update.md`: when CLAUDE.md's Key Decisions table > 20 rows, oldest (topmost = FIFO) rows move to `docs/key-decisions.md`. First-run `AskUserQuestion` consent gate with sentinel note in the reference file for silent subsequent runs. Gated by `--skip-decisions-rollup`. Commit checkpoint moved to Part 7 (last) so both rollups land in the same commit. "Pruning is preservation" codified in `doc-structure-rules.md` as canonical backing. |
| `/update-docs --fast` + Step 0 upfront batch + plan-then-batch (Session 18) | Daily `/update-docs` was still 12-14 min despite Session 16's `effort: low`. Fast Path runs the daily subset (drain → CLAUDE.md updates → drift probes → commit) and skips Parts 0.5/2/3/4/5/6/1.10. Step 0 collapses 5-6 sequential read turns into 1 parallel turn (benefits both paths). Plan-then-batch turns 10 per-section Edits in Part 1 into one Write. **No functionality trimmed from `--full`.** Drift warnings are the safety valve: Fast Path surfaces accumulated debt instead of enforcing. Verified by dogfooding `/update-docs --fast` this session. |
| Interop polish (commit `14546ff`, 2026-04-22; backfilled S19) | Modernized README defer recipe to use the 2.1.85 `if` field (e.g. `"if": "Bash(rm:*)"`) so PreToolUse `defer` only fires for matching tool calls, refining the existing CI-gating recipe. Added README auto mode compatibility paragraph (2.1.83+ classifier behavior + `PermissionDenied` hook fallback added 2.1.89). Startup scripts now warn when `disableSkillShellExecution=true` in user settings (would silently break `--fix`/`--verify`/`deep`). |
| Parallelize `/code-review --verify` (commit `ff89cbb`, 2026-04-22; backfilled S19) | Step 1.5 launches test/lint with `run_in_background` so they complete during review work (Steps 2-4); Step 5 collects output instead of running synchronously. Saves ~10-60s per `--verify` invocation on projects with non-trivial test suites. Mirrors the parallelization pattern from `/update-docs` Part 3.0 (Session 16). |
| `/code-cleanup` references — git ls-files + batched Grep + monorepo workspaces (Session 20) | Usage-pattern improvements per Next Steps #2. (1) **Perf:** `git ls-files` over `find` (honors `.gitignore` natively); per-item grep loops collapse into single batched `Grep` calls with regex alternation (`\b(name1\|name2\|...)\b` + `output_mode: count`). (2) **Coverage:** `scan-deps-config.md` detects npm/yarn/pnpm/Cargo workspaces, scans each child manifest separately, tags findings with workspace name; new "Misplaced Dependencies" output section. SKILL.md Step 0 surfaces monorepo state in the "Detected:" line. (3) **Mid-edit correctness fix:** literal `rg ...` shell-command examples → `Grep` tool syntax — the cleanup-* agents have `Bash(grep:*)` not `Bash(rg:*)`, and runtime guidance pins use of the `Grep` tool. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
claude-config/
├── .claude/
│   ├── agents/              # Subagent definitions (Sonnet-routed)
│   │   ├── cleanup-deps-config.md
│   │   ├── cleanup-files-code.md
│   │   └── cleanup-styles-tests.md
│   ├── scripts/             # Session startup scripts
│   │   ├── start-claude.sh          # Mac/Linux
│   │   └── start-claude.ps1        # Windows (PowerShell)
│   ├── settings.local.json  # Shared Claude Code settings
│   └── skills/              # Skills (SKILL.md + references/)
│       ├── code-cleanup/
│       ├── code-review/
│       ├── plan-feature/
│       ├── resume-work/
│       └── update-docs/
├── docs/                    # Reference files (overflow from CLAUDE.md)
│   ├── completed-work.md
│   ├── key-decisions.md
│   └── session-history.md
├── .gitignore
├── CLAUDE.md                # This file — AI session context
├── README.md                # Public overview
└── Workflow.md              # Personal workflow guide
```

**Symlink approach:** Only `.claude/skills/` and `.claude/agents/` are symlinked into `~/.claude/` on each machine. This preserves local credentials and settings while sharing skills and agents across machines via Git.

**Skills** are directories containing `SKILL.md` (main logic with YAML frontmatter) and a `references/` folder with supporting documents. They are user-invocable via `/skill-name`.

**Subagents** are markdown files in `.claude/agents/` dispatched by skills (not user-invocable). They run on Sonnet for cost efficiency and have scoped tool permissions.

## Known Issues / Blockers

None currently.

## Environment Variables

None required. This is a pure configuration repo — no runtime dependencies or secrets.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 20) - 2026-05-06
- **Acted on Next Steps #2** ("improve existing skill reference files based on usage patterns") narrowed to `/code-cleanup`. Presented three gaps (perf, monorepo deps, CSS-in-JS/Tailwind detection) via `AskUserQuestion`; user chose perf + monorepo.
- **Perf (all three reference files):** replaced `find` with `git ls-files` for source enumeration (honors `.gitignore`, no hardcoded skip list, faster on large repos). Replaced per-item grep loops in unused-files, dead-functions, unused-classes, and unused-CSS-variable searches with single batched `Grep` calls using regex alternation (`\b(name1|name2|...)\b` + `output_mode: count`). Same shape as Session 16's Part 3.0 batch-read pattern, applied at finer grain.
- **Monorepo coverage (`scan-deps-config.md`):** new §4.0 workspace detection block — npm/yarn/pnpm via `package.json` `workspaces` or `pnpm-workspace.yaml`; Cargo via `[workspace] members`. Each detected workspace is an independent scan target; sibling-workspace usage doesn't count. Output gains `workspace:` field; new "Misplaced Dependencies" section. SKILL.md Step 0 detection surfaces monorepo state in the "Detected:" one-liner.
- **Mid-edit correctness fix:** first-pass examples used literal `rg ...` shell-command form, but the cleanup-* agents have `Bash(grep:*)` not `Bash(rg:*)` in their whitelists and runtime guidance pins use of the `Grep` tool. Refactored all batched-search examples across the three reference files to `Grep` tool parameter shape (`pattern:`, `output_mode:`, `glob:`, `path:`).
- **Part 5 picked up two compressions** — S14 had been left in full prose by S19's rollup despite already being past the 5-most-recent threshold (apparent single-pass bug in S19; this run iterates further). Both S14 and S15 compressed to one-liners. Part 6 silent FIFO of 1 row (table 21 → 20). Auto-memory and README/Workflow.md unchanged. Subagent definition files unchanged — references already describe Grep-tool-batched pattern, agents already have `Grep` whitelisted.
