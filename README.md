# Claude Config

My personal Claude Code configuration: custom commands, skills, subagents, and workflow guide.

## Contents
```
claude-config/                         # marketplace repo
├── .claude-plugin/
│   └── marketplace.json               # "burak-tools" marketplace catalog
├── bx/                                # the installable `bx` plugin
│   ├── .claude-plugin/
│   │   └── plugin.json                # plugin manifest (skills invoke as /bx:<name>)
│   ├── agents/                        # 14 subagents (Sonnet-routed) → bx:<agent>
│   │   ├── arch-performance.md
│   │   ├── arch-refactors.md
│   │   ├── arch-simplification.md
│   │   ├── arch-structure.md
│   │   ├── cleanup-deps-config.md
│   │   ├── cleanup-files-code.md
│   │   ├── cleanup-styles-tests.md
│   │   ├── geo-generative.md
│   │   ├── seo-content.md
│   │   ├── seo-gsc-insights.md
│   │   ├── seo-technical.md
│   │   ├── test-coverage.md
│   │   ├── test-economics.md
│   │   └── test-quality.md
│   ├── hooks/
│   │   └── hooks.json                 # SessionStart project-orientation injection
│   ├── scripts/
│   │   ├── session-start-context.sh   # SessionStart hook (Mac/Linux)
│   │   └── session-start-context.ps1  # SessionStart hook (Windows)
│   └── skills/                        # 9 skills → /bx:<name> (each: SKILL.md + references/)
│       ├── arch/                      # /bx:arch  — repo-wide architecture audit
│       ├── clean/                     # /bx:clean — codebase cleanup audit
│       ├── docs/                      # /bx:docs  — documentation management
│       ├── health/                    # /bx:health — skill-routing advisor
│       ├── plan/                      # /bx:plan  — feature planning interview
│       ├── resume/                    # /bx:resume — resume a dev session
│       ├── review/                    # /bx:review — senior-engineer code review
│       ├── seo/                       # /bx:seo   — SEO + GEO audit
│       └── tests/                     # /bx:tests — test-suite audit
├── .claude/
│   ├── scripts/                       # Launchers (not plugin components)
│   │   ├── start-claude.sh            # Mac/Linux launcher
│   │   └── start-claude.ps1           # Windows launcher (PowerShell)
│   └── settings.local.json            # Local Claude Code settings
├── docs/                              # Reference files (overflow from CLAUDE.md)
│   ├── completed-work.md
│   ├── key-decisions.md
│   ├── modernization-roadmap.md
│   └── session-history.md
├── .gitignore
├── CLAUDE.md                          # AI session context
├── README.md                          # This file
└── workflow.md                        # Personal workflow guide
```

## Setup on a New Machine

The toolkit installs as a Claude Code **plugin** (`bx`) from a local marketplace — no symlinks, cross-platform, and skills are namespaced `/bx:<name>` so they never collide with built-ins.

```bash
# 1. Clone this repo (any platform)
git clone https://github.com/burak-maxitech/claude-config.git ~/Development/projects/claude-config
```

Then, inside Claude Code:

```
# 2. Register the marketplace + install the plugin
/plugin marketplace add ~/Development/projects/claude-config
/plugin install bx@burak-tools

# 3. Verify — skills register under the bx: namespace
/bx:health
```

Updates: `git pull` in the repo, then `/plugin marketplace update burak-tools` and `/plugin update bx`. Because the plugin omits an explicit `version`, every commit is treated as a new version.

### Migrating from the old symlink setup

Earlier versions symlinked `~/.claude/skills` and `~/.claude/agents` into this repo. After installing the plugin, retire those symlinks so the old `bx-*` skills don't shadow the namespaced `/bx:*` ones:

```bash
# Mac/Linux — only remove if they are symlinks pointing at this repo
[ -L ~/.claude/skills ] && rm ~/.claude/skills
[ -L ~/.claude/agents ] && rm ~/.claude/agents
```

```powershell
# Windows
(Get-Item "$env:USERPROFILE\.claude\skills").LinkType -eq "SymbolicLink" -and (Remove-Item "$env:USERPROFILE\.claude\skills")
(Get-Item "$env:USERPROFILE\.claude\agents").LinkType -eq "SymbolicLink" -and (Remove-Item "$env:USERPROFILE\.claude\agents")
```

## Quick Start

After setup, create a shell alias for quick access:

```bash
# Mac/Linux — run once, then restart terminal (or run: source ~/.zshrc)
echo 'alias cc="~/Development/projects/claude-config/.claude/scripts/start-claude.sh"' >> ~/.zshrc
```
```powershell
# Windows — run once, then restart PowerShell
Add-Content $PROFILE 'function cc { & "$env:USERPROFILE\Development\projects\claude-config\.claude\scripts\start-claude.ps1" @args }'
```

> **Mac/Linux first run:** Make the script executable first:
> `chmod +x ~/Development/projects/claude-config/.claude/scripts/start-claude.sh`

> **Windows first run:** You may need to unblock the script first:
> `Unblock-File "$env:USERPROFILE\Development\projects\claude-config\.claude\scripts\start-claude.ps1"`

Then start any session with:
```bash
cc my-project    # launch directly
cc               # interactive project picker
```

The script pulls project changes, checks for Claude updates, and launches Claude Code. (Note: the launcher's legacy symlink check is being retired alongside the move to the `bx` plugin.)

## Syncing Changes

After Claude or you edit any files:
```bash
cd ~/Development/projects/claude-config
git add .
git commit -m "Updated [what changed]"
git push
```

On other machines:
```bash
cd ~/Development/projects/claude-config
git pull
```

## Commands

| Command | Purpose | Format |
|---------|---------|--------|
| `/bx:resume` | Start session - get up to speed | Skill |
| `/bx:plan` | Interview before building features | Skill |
| `/bx:review` | Thorough senior-engineer code review (in-session, with `--security`/`--verify`/`--fix`/`--last-commit`). Slots between built-in `/code-review` (quick) and `/code-review ultra` (cloud, pre-merge). | Skill |
| `/bx:clean` | Find dead code & cruft (parallel subagents). Adds CVE scanning with `--vulns` (runs `npm audit` / `pip-audit` / `cargo audit` / equivalents per detected stack; report-only, never auto-fixed). | Skill |
| `/bx:arch` | Repo-wide architecture audit — complexity hotspots, refactor opportunities, perf suspects, **and over-engineering** (single-impl interfaces, pass-through wrappers, defensive code, unread config). Reports `lines_deletable` as a top-line metric. 4 parallel subagents, with `--plan`/`--fix`/`--map`/`--full-scan` | Skill |
| `/bx:tests` | Repo-wide test suite audit — missing coverage on critical paths AND wasteful/redundant tests, in a single report. **Twin headline metric** (`Coverage gaps in critical code: X lines | Tests we can delete: Y lines`). 3 parallel subagents (`test-coverage` / `test-quality` / `test-economics`), T01-T05 smell catalog, with `--plan`/`--fix` (T01-only safe deletion)/`--coverage` (opt-in report reading)/`--full-scan`. Defers entirely to `/bx:clean` for orphans / stale snapshots / >3mo skips. | Skill |
| `/bx:seo` | Repo-wide SEO + Generative Engine Optimization audit for **web projects only** (rejects non-web repos silently). **Fetches current best practices fresh every run** via WebSearch + WebFetch (4 source categories: Google Search Central+web.dev, Schema.org+JSON-LD, GEO sources, third-party authority blogs). **Probes sitemap URLs** for 4xx/5xx/redirect-chains/slow-responses (cap 100 URLs; score-impact capped at 8 points). **Optional GSC integration via Search Console API** — single auth (gcloud ADC with `webmasters.readonly` scope) + single config key (`site_url:` in `.seo-data/gsc/config.yaml`) + two endpoints (`searchanalytics.query` for Performance + `urlInspection.index.inspect` for per-URL Indexing). Binary mode: API-enabled or heuristic-only fallback. 35-day git-history overlap flags "may already be fixed" findings against the GSC reporting lag. **Score stays /100** (purely heuristic) so `docs/seo-history.md` is comparable across runs regardless of GSC availability. 3 parallel subagents (4 when GSC API enabled: `seo-technical` / `seo-content` / `geo-generative` / `seo-gsc-insights`). Single headline: **score /100 (Δ since last run) + top-3 highest-impact opportunities**. Score tracked over time in `docs/seo-history.md`. Flags: `--plan` / `--fix` (strict allowlist, never fabricates content — only inserts TODO placeholders) / `--url <deployed-url>` (live HTML diff). | Skill |
| `/bx:health` | Routing advisor — looks at `git status`, branch, recent commits, `CLAUDE.md`, open PR, then suggests which skills to run in what order. **Read-only, never invokes anything.** Use when unsure where to start. | Skill |
| `/bx:docs` | End session - save progress | Skill |

**Skills** are directories in `bx/skills/` (each `SKILL.md` + a `references/` folder) that use YAML frontmatter for tool permissions and can dispatch subagents. Installed via the plugin, they invoke as `/bx:<name>`.

> **The review ladder — pick the rung that matches the risk.** Naming churned twice: on 2026-05-23 Anthropic renamed built-in `/simplify` → `/code-review` (so this repo's custom `code-review` was renamed to `/bx:review` to dodge the collision); since then Anthropic **reinstated `/simplify`** as a separate built-in and folded the old `/ultrareview` cloud pass into `/code-review ultra`. Current ladder, lightest → heaviest:
>
> 1. **`/simplify`** (built-in) — quality-only pass on changed code (reuse, simplification, altitude); **applies fixes**. Does *not* hunt for bugs. Cheapest cleanup of what you just wrote.
> 2. **`/code-review [effort]`** (built-in, fast) — correctness bugs **+** cleanups at a chosen effort (`low`/`medium`/`high`/`max`). `--comment` posts inline PR comments; `--fix` applies findings. **Daily driver.**
> 3. **`/bx:review`** (this repo's custom skill, thorough) — senior-engineer review with codebase-convention scanning, severity-ranked findings, mandatory `file:line` references. Supports `--security` (OWASP Top 10), `--verify` (run tests/lint to validate), `--fix` (auto-fix simple findings), `--last-commit`. **Reach for when the diff is non-trivial or touches risky areas.**
> 4. **`/code-review ultra`** (built-in, cloud) — the `ultra` effort spins up 5+ verifying subagents in the cloud (10–20 min, scales to 20). **High-risk pre-merge only** (auth rewrites, payment flows, database migrations). *(Was `/ultrareview`, now a deprecated alias.)*

> **Picking among the review/audit skills.** All operate on different scopes:
>
> | Skill | Scope | When |
> |-------|-------|------|
> | `/simplify` | changed code | quality-only cleanup, applies fixes — no bug-hunting (built-in) |
> | `/code-review` | diff or commit | quick correctness scan, daily driver (built-in) |
> | `/bx:review` | diff or commit | thorough senior-engineer review with `--security`/`--verify`/`--fix` (custom) |
> | `/code-review ultra` | PR (cloud) | high-risk pre-merge verification (auth, payments, migrations) |
> | `/bx:clean` | whole repo | deletion-focused — whole unused files, unused deps, stale config |
> | `/bx:arch` | whole repo | structural audit — complexity hotspots, refactor opportunities, perf suspects, AND sub-file over-engineering (single-impl interfaces, pass-through wrappers, defensive code, unread config). Reports `lines_deletable`. |
> | `/bx:tests` | whole repo, test suite focus | test suite audit — coverage gaps on critical paths + test smells (T01-T05) + suite economics (snapshot bloat, flakiness, LOC ratio extremes). Reports twin headline (coverage gap LOC + deletable LOC). |
> | `/bx:seo` | whole web repo, SEO + GEO focus | SEO + Generative Engine Optimization audit. Fetches current best practices each run. Probes sitemap URL health (404/5xx/redirect-chain/slow). **Optional GSC integration via Search Console API** — install gcloud SDK, authenticate with ADC, drop a one-line `site_url:` in `.seo-data/gsc/config.yaml`. Two endpoints (`searchanalytics.query` for Performance + `urlInspection.index.inspect` for per-URL Indexing) cover both signals. Binary mode: API-enabled or heuristic-only. 35-day git-history overlap to flag "may already be fixed" findings against the GSC reporting lag. Single score `/100` headline + top-3 priorities. Tracked over time in `docs/seo-history.md` (comparable across runs whether GSC API is configured or not — score stays purely heuristic). Web projects only — rejects others silently. |
>
> Useful chain on an unfamiliar repo: `/bx:clean` → `/bx:arch` → `/bx:tests` → (if web) `/bx:seo` → `/bx:arch --plan` → `/bx:plan` per phase.
>
> Not sure where to start? `/bx:health` reads your repo state and suggests which of these skills to run in what order. It's a 30-second routing call, not a review.

## Subagents

The `bx/agents/` folder contains 14 subagent definitions used by skills (namespaced `bx:<agent>` once installed). These run on Sonnet for cost efficiency and have scoped tool permissions. Skills dispatch them automatically via the Task tool, and you can also reference them by name in `@`-mention typeahead inside the REPL (added in Claude Code 2.1.89).

| Agent | Used By | Purpose |
|-------|---------|---------|
| `cleanup-files-code` | `/bx:clean` | Scans for unused files and dead code |
| `cleanup-deps-config` | `/bx:clean` | Scans for unused deps and config cruft |
| `cleanup-styles-tests` | `/bx:clean` | Scans for unused CSS and stale tests |
| `arch-structure` | `/bx:arch` | Cyclomatic + cognitive complexity hotspots, coupling, layering violations, circular deps |
| `arch-refactors` | `/bx:arch` | Catalog-driven complexity-reducing refactor opportunities (cites entry IDs) |
| `arch-performance` | `/bx:arch` | High-precision performance findings (N+1, sync I/O in async, accidental O(n²), hot-loop invariants) |
| `arch-simplification` | `/bx:arch` | Over-engineering / almost-dead code at sub-file granularity — single-impl interfaces, pass-through wrappers, defensive code for impossible states, unread config, near-duplicates. Reports `lines_deletable`. |
| `test-coverage` | `/bx:tests` | Ranks coverage gaps by `security_keyword_density × churn × import_fan_in`. Heuristic mode (test-neighbor + public-symbol enum) by default; reads coverage reports when `--coverage` opted in. Also scans bug-fixes-without-regression-tests in last 50 commits. |
| `test-quality` | `/bx:tests` | Scans tests against T01-T05 smell catalog (assertion-free / weak / mock-heavy / mystery guest / redundant). Runs project-defined-assertion-helper allowlist scan FIRST as the critical T01 false-positive guard. |
| `test-economics` | `/bx:tests` | Suite-level cost vs value: snapshot-heavy (≥50% ratio), flakiness (markers + git-log signals), test:code LOC ratio extremes per module. Reports `deletable_lines` only for snapshot reductions — keeps twin-headline math honest. |
| `seo-technical` | `/bx:seo` | Technical SEO (25 pts) + Performance signals (10 pts): crawlability (robots.txt + sitemap.xml), canonicals, mobile viewport, hreflang, indexability, redirect config, image/font/script perf. Consumes orchestrator-passed sitemap URL probe results (4xx/5xx/redirect-chains/slow); score impact capped at 8 points so a fully broken sitemap can't zero out the dimension. No network access — orchestrator owns all HTTP. |
| `seo-content` | `/bx:seo` | On-Page SEO (25 pts): titles, meta descriptions, headings hierarchy, image alt text, OpenGraph + Twitter Cards, internal linking, content depth signals. Strict no-fabrication rule on `--fix` — only inserts TODO placeholders. |
| `geo-generative` | `/bx:seo` | Structured Data (20 pts) + Generative Engine readiness (20 pts): Schema.org JSON-LD coverage + rich-result eligibility, llms.txt presence + format, E-E-A-T signals (author bios, dates, citations), semantic content patterns (topic sentences, list/table structure, question-headings), AI-bot crawl access (GPTBot/ClaudeBot/PerplexityBot/etc.). Fetched best-practices brief is primary source of truth (GEO evolves fast); `brief_divergence` field surfaces when heuristic disagrees. |
| `seo-gsc-insights` | `/bx:seo` (only when `.seo-data/gsc/` present) | Ingests orchestrator-parsed Google Search Console CSV digests (queries, pages, 9 page-indexing per-reason CSVs) + 35-day git-history change digest. Emits 12 sub-dim info-only findings (`indexing_coverage`, `crawled_not_indexed`, `discovered_not_indexed`, `not_found_404` with routing-rename match for bulk-redirect detection, `redirect_hygiene`, `canonical_conflict`, `blocked_access`, `soft_404`, `server_errors`, `ctr_opportunity`, `position_band_opportunity`, `traffic_orphan`). `score_impact: 0` enforced agent-side AND orchestrator-side — GSC enriches recommendations, never the /100 score. Annotates each finding with `code_changed_since_gsc_window` (lowers certainty to 0.4 + rewrites recommendation when matched commit detected). |

## Optional: SessionStart hook for auto-orientation

The repo ships `.claude/scripts/session-start-context.{sh,ps1}` — a cheap (<1s) read-only script that emits project orientation as system context at the start of every Claude Code session, before the user's first prompt. It eliminates the need to type `/bx:resume` for routine starts (deep orientation still works via the explicit slash command).

**What it emits:**
- Branch + uncommitted-file count + age of last commit
- 5 most recent commit subjects
- CLAUDE.md `## Current Status` table + `Last Updated` line
- Stale-doc warning if commits are newer than CLAUDE.md by >2 days
- Open-PR title/number (best-effort via `gh`)

**Silent fallbacks:** emits nothing if outside a git repo; emits less when `gh` or `CLAUDE.md` are missing.

### Install (per-project)

Add to the target project's `.claude/settings.json`:

```jsonc
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear",
        "hooks": [
          {
            "type": "command",
            "command": "~/Development/projects/claude-config/.claude/scripts/session-start-context.sh",
            "timeout": 3
          }
        ]
      }
    ]
  }
}
```

On Windows, swap to `.ps1` and prefix with `pwsh -NoProfile -File `.

### Install (global, all projects)

Add the same block to `~/.claude/settings.json`. The script is silent on non-repo dirs, so it stays out of the way for one-off chats.

### Why a hook *and* `/bx:resume`

The hook gets you oriented for *free* on every session start. `/bx:resume` does the deeper work the hook deliberately skips: reads all docs in parallel, runs the health-check ladder, hydrates the task tracker via `TaskCreate`. Use the hook for routine starts; reach for `/bx:resume` when returning to a project after a long absence or when you want the live task list.

If `disableSkillShellExecution: true` is set, the hook still runs (it's a hook, not a skill's shell injection) — but skill-internal `` !`<cmd>` `` blocks (e.g., in `/bx:health`) won't. That setting is independently warned about by the `start-claude` scripts.

## Interop with Claude Code 2.1 features

These skills are standalone `.claude/` configuration, which is the approach [the official docs recommend](https://code.claude.com/docs/en/plugins#when-to-use-plugins-vs-standalone-configuration) for personal workflows. They coexist happily with installed marketplace plugins — no migration needed.

A few harness-level features worth knowing about when using these skills:

- **Gating destructive `--fix` runs in CI.** `bx:clean --fix` and `bx:review --fix` are intentionally not self-gating (see the note in each SKILL.md). If you run them headlessly via `claude -p` and want an external approval step, configure a `PreToolUse` hook in `~/.claude/settings.json` scoped via the `if` field (added in 2.1.85) to the patterns you want to guard — e.g. `"if": "Bash(rm:*)"` or `"if": "Edit(*)"` — and return `"permissionDecision": "defer"`. The session exits with `stop_reason: "tool_deferred"`; resume via `claude -p --resume <session-id>`. Note: `defer` only works when the turn makes a single tool call — useful for a `rm` guard, not for orchestrating a multi-step `--fix` run. See [hooks docs](https://code.claude.com/docs/en/hooks) for the full decision flow and the `if` field spec.
- **Auto mode compatibility** (requires 2.1.83+; Max/Team/Enterprise/API plan; Opus 4.6/4.7 or Sonnet 4.6; not available on Pro). Auto mode (`defaultMode: "auto"`) uses a classifier to auto-approve actions without prompts. On entering auto mode, broad allow rules like `Bash(*)` or `Bash(python*)` are dropped, but narrow patterns like `Bash(npm test)` carry over. The 5 skills in this repo all declare narrow `allowed-tools` (`Bash(git:*)`, `Bash(npm:*)`, `Bash(find:*)`, etc.), so `--fix`, `--verify`, and `deep` all work under auto mode. If the classifier denies something unexpectedly, configure a `PermissionDenied` hook (added 2.1.89) that returns `{"retry": true}` to tell the model it may retry. See [permission modes](https://code.claude.com/docs/en/permission-modes) for the full spec.
- **`disableSkillShellExecution`** (added 2.1.91). Hardens the harness by blocking inline shell from skills and slash commands. **Do not enable this here** — `bx:clean --fix`, `bx:review --verify`, and `bx:resume deep` all depend on shell execution and will break. Leave OFF. (The `start-claude` scripts warn if this flag is on in `~/.claude/settings.json`.)
- **Plugin `bin/` on PATH** (added 2.1.91). If you install a marketplace plugin that ships `bin/check` or `bin/test`, `bx:resume deep` picks it up automatically in the health check detection ladder.
- **MCP `maxResultSizeChars`** (added 2.1.91). If a future `bx:review` run hits an MCP-backed file reader that truncates, the MCP server can set `_meta["anthropic/maxResultSizeChars"]` up to 500K per tool to return fuller context in one call.
- **MCP server setup.** Add servers via `claude mcp add --transport {http|sse|stdio} <name> <target>`. Three scopes are available: **local** (default, personal-to-this-project, stored in `~/.claude.json`), **project** (team-shared via `.mcp.json` at repo root), and **user** (all your projects, stored in `~/.claude.json`). Project scope is the one to use when a server should travel with the repo. Tool-search deferral keeps context cost low even with multiple servers, so the practical ceiling is tool-menu clarity and permission-prompt volume, not token budget. See the [MCP docs](https://code.claude.com/docs/en/mcp) for transport-specific setup.

## Documentation

| File | Purpose |
|------|---------|
| [README.md](README.md) | Public overview, setup instructions (this file) |
| [CLAUDE.md](CLAUDE.md) | AI session context, status tracking, architecture |
| [Workflow.md](Workflow.md) | Detailed personal workflow guide |
| [docs/](docs/) | Reference files (session history, decisions, completed work) |

See `Workflow.md` for full usage guide.