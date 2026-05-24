# My Claude Code Workflow

> Personal guide for using Claude Code effectively with my custom command system.

---

## Quick Reference

| Phase | Command | Purpose |
|-------|---------|---------|
| **Start Session** | `/resume-work` | Get up to speed, see what's next |
| **Not Sure Where to Start** | `/code-health-advice` | 30-sec routing advisor — reads repo state, recommends a skill sequence (read-only) |
| **Plan Feature** | `/plan-feature` | Interview before building |
| **During Development** | `/code-review` (quick) or `/review-deep` (thorough) | Review code quality |
| **During Development** | `/code-cleanup` | Find dead code & cruft |
| **Architecture Audit** | `/architecture-review` | Repo-wide complexity + refactor + perf + over-engineering audit (4 dimensions, reports `lines_deletable`) |
| **Test Suite Audit** | `/test-review` | Repo-wide test health — coverage gaps on critical paths + smells (T01-T05) + suite economics. Twin headline metric. |
| **SEO + GEO Audit** | `/seo-review` | Repo-wide SEO + Generative Engine Optimization audit for web projects. Fetches current best practices every run. Probes sitemap URL health. **Optional GSC integration via Search Console API** (Performance via `searchanalytics.query` + per-URL Indexing via `urlInspection.index.inspect`). Configure `.seo-data/gsc/config.yaml` `site_url:` after `gcloud auth application-default login`. Score `/100` tracked over time. |
| **End Session** | `/update-docs` | Save progress & context |

---

## Daily Workflow

### Quick Start

```bash
cc my-project    # launch directly
cc               # interactive project picker
```

> No `cc` alias? See [README.md](README.md#quick-start) for one-time setup.

**What the script does (5 steps):**
1. Pulls latest claude-config (syncs skills/agents across machines)
2. Verifies `~/.claude` symlinks are in place
3. Navigates to project and pulls latest changes
4. Checks for Claude Code updates
5. Launches Claude Code (tip: run `/resume-work` to get up to speed)

**What `/resume-work` does:**
- Checks auto-memory for stable project facts already in context
- Reads CLAUDE.md, README.md, and docs/ in parallel (single turn)
- Runs all git commands in parallel (log, diff, status)
- Shows current status + recommends next task
- Hydrates a live task list from CLAUDE.md using TaskCreate

### Manual Steps (what the script does under the hood)

<details>
<summary>Mac</summary>

```bash
# 1. Pull latest commands (in case you updated from another machine)
cd ~/Development/projects/claude-config && git pull && cd -

# 2. Verify config symlinks are in place
ls -d ~/.claude/skills ~/.claude/agents 2>/dev/null || echo "MISSING SYMLINKS — see Setup section"

# 3. Navigate to project
cd ~/projects/[project-name]

# 4. (Optional) Pull latest project changes
git pull

# 5. Check for Claude updates
claude update

# 6. Launch Claude Code
claude

# 7. Get up to speed
/resume-work
```

</details>

<details>
<summary>Windows (PowerShell)</summary>

```powershell
# 1. Pull latest commands (in case you updated from another machine)
cd C:\Development\projects\claude-config; git pull; cd -

# 2. Verify config symlinks are in place
Get-ChildItem ~\.claude | Where-Object { $_.LinkType -eq "SymbolicLink" } | Format-Table Name, Target

# 3. Navigate to project
cd C:\Development\projects\[project-name]

# 4. (Optional) Pull latest project changes
git pull

# 5. Check for Claude updates
claude update

# 6. Launch Claude Code
claude

# 7. Get up to speed
/resume-work
```

</details>

---

### During Development

#### Adding a New Feature

```bash
# 1. First, add feature to PRD
"Add a new feature section to the PRD for [feature name]: [brief description]"

# 2. Then plan it with interview
/plan-feature docs/[project]-prd.md

# Or if you have a separate feature doc:
/plan-feature docs/new-feature-spec.md
```

**What `/plan-feature` does:**
- Checks auto-memory, then reads all docs in parallel
- Auto-detects if greenfield or existing project
- Asks 3-4 questions at a time, covers all edge cases
- Enters Plan Mode → writes formal implementation plan → requires approval via ExitPlanMode
- Hydrates approved plan into live tasks with TaskCreate (with dependencies)
- Updates CLAUDE.md with decisions

#### Code Quality Checks

Two review skills are available — pick the right tier for the job:

- **`/code-review`** (built-in, lightweight) — quick diff scan for correctness bugs at a chosen effort level (low/medium/high/max). Supports `--comment` to post findings as inline PR comments. Use this as the daily driver.
- **`/review-deep`** (custom, thorough) — senior-engineer review with codebase-convention scanning, severity-ranked findings, mandatory `file:line` references. Supports `--security` (OWASP), `--verify` (run tests/lint), `--fix` (auto-fix simple findings), `--last-commit`. Reach for this when the diff is non-trivial or touches risky areas.
- **`/ultrareview`** (built-in, cloud) — 5+ verifying subagents for high-risk pre-merge (auth, payments, migrations).

```bash
# Quick review of uncommitted changes (default - most common)
/code-review

# Thorough review of specific files
/review-deep src/services/gmail_service.py

# Thorough review of staged changes before commit
/review-deep --staged

# Thorough review of a pull request
/review-deep 123

# Find dead code and cleanup opportunities (parallel scan)
/code-cleanup

# Focus on specific area or category
/code-cleanup src/services/
/code-cleanup --deps --code
```

**What `/review-deep` does:**
- Auto-detects review target (uncommitted changes, staged, PR, or specified files)
- Scans codebase conventions before reviewing (error handling, naming, imports, test patterns)
- Checks correctness, security, performance, maintainability
- Outputs severity summary (Critical/Important/Suggestions count) with mandatory `file:line` references
- Flags convention violations against project patterns

**What `/code-cleanup` does:**
- Scans multiple categories in parallel using subagents
- Produces a summary dashboard (item counts, removable lines, risk levels)
- Lists "Quick Wins" for zero-risk bulk deletions
- Categorizes findings by safety (Safe to Delete / Likely Safe / Needs Investigation)
- Supports filters (`--code`, `--deps`, `--css`, `--tests`, `--aggressive`)

---

### Mid-Session Context Hygiene

Long sessions bloat the context window with tool results, scan outputs, and early exploration that's no longer load-bearing. `/compact` rewrites the conversation into a terse summary while preserving loaded CLAUDE.md, which lets a long session keep going without token exhaustion.

**Run `/compact` proactively — earlier rather than later.** Once the context bar is visibly consumed and the main task ahead is well-defined, compacting immediately is cheaper than waiting until the context is full. A useful form is `/compact focus on <next task>` — Claude keeps the carry-forward summary pointed at what's about to happen next.

This generalizes the compact hints already emitted by `/resume-work` and `/update-docs`. Those two skills suggest compacting after their own substantial work; the same habit applies mid-session whenever a chunk of context (failed approach, large file read, long grep) is no longer needed.

Project-root `CLAUDE.md` survives compaction — Claude re-reads it from disk after `/compact` — so project-wide context is not lost. Nested CLAUDE.md files in subdirectories reload lazily the next time Claude reads a file there. Instructions given only in conversation (not in any CLAUDE.md) may not survive: put anything you want to persist into CLAUDE.md or a `.claude/rules/` file.

---

### Ending a Session

```bash
# Save your progress
/update-docs

# Commit your project work
git add .
git commit -m "feat: [description]"
git push

# If Claude modified any commands or workflow, sync those too
cd ~/Development/projects/claude-config
git status
# If changes exist:
git add .
git commit -m "Updated [what changed]"
git push
cd -
```

**What `/update-docs` does:**
- Drains live task list — syncs completed/in-progress/pending tasks back to CLAUDE.md
- Updates CLAUDE.md with session history, status, and next steps
- Archives old sessions (>3) to `docs/session-history.md` to keep CLAUDE.md lean
- Syncs stable project facts to auto-memory for instant context in future sessions
- Updates README.md and docs/*.md as needed

---

## Command Reference

### /resume-work

**When:** Start of every session

**Usage:**
- `/resume-work` - Standard summary (parallel doc reads + git scan)
- `/resume-work deep` - Verbose mode (includes full session history from archive, complete file tree, all env vars)

**Features:**
- Checks auto-memory for pre-loaded project context
- Reads all docs and runs all git commands in parallel (2 turns total)
- Hydrates CLAUDE.md tasks into live task tracker via TaskCreate

**Output:** Status summary + recommended next task + live task list

---

### /plan-feature

**When:** Before building any new feature

**Usage:**
```bash
/plan-feature                           # Interactive, asks what you're building
/plan-feature docs/feature-spec.md      # Uses specific plan file
```

**Modes:**
- **GREENFIELD** - Full architecture interview (new projects)
- **EXISTING** - Integration-focused interview (adding to existing code)

**Flow:** Interview → EnterPlanMode → implementation plan → ExitPlanMode (approval) → TaskCreate (hydrate tasks) → begin coding

**Output:** Exhaustive requirements gathered, formal plan approved, live task list created

---

### /update-docs

**When:** End of every session (or after major milestones)

**Modes:**
- **CREATE** - Generates all docs from scratch
- **REFACTOR** - Splits monolithic README into three files
- **UPDATE** - Refreshes existing documentation

**Updates:**
- Drains live task list back into CLAUDE.md (completed → Completed, pending → Next Steps)
- CLAUDE.md - Session history, status, next steps
- Archives sessions >3 to `docs/session-history.md`
- Syncs stable facts to auto-memory (`~/.claude/projects/.../memory/MEMORY.md`)
- README.md - Project overview, setup
- docs/*.md - PRD and specifications

---

### /review-deep

**When:** Before committing, or to check specific code, when you want more rigor than the built-in `/code-review` (which is fine for routine diffs but doesn't scan codebase conventions or run `--security`/`--verify`/`--fix`).

**Usage:**
```bash
/review-deep                             # Review uncommitted changes (default)
/review-deep src/file.py                 # Review specific file
/review-deep src/services/               # Review directory
/review-deep 123                         # Review PR #123 via gh
/review-deep --staged                    # Review only staged changes
/review-deep --last-commit               # Review the last commit
/review-deep --security                  # Add OWASP Top 10 deep-dive
/review-deep --verify                    # Also run tests/lint to validate findings
/review-deep --fix                       # Auto-fix simple findings (unused imports, formatting)
```

**Features:**
- Auto-detects review target from arguments
- Scans codebase conventions first (error handling, naming, imports, test patterns)
- Flags convention violations alongside standard issues
- Every finding includes mandatory `file_path:line_number` reference

**Checks:**
- Correctness & bugs
- Security vulnerabilities
- Performance issues
- Maintainability & convention consistency
- Error handling
- Test coverage gaps

**Output:** Severity summary table (counts) → Critical / Important / Suggestions / Convention Violations / What's Good

**Tiering:** built-in `/code-review` (quick) → `/review-deep` (this, thorough) → `/ultrareview` (cloud, pre-merge). Pick the tier that matches the risk of the diff.

---

### /architecture-review

**When:** First-time exploring an unfamiliar repo, quarterly architecture health check, or before proposing a major refactor

**Usage:**
```bash
/architecture-review                     # Default review-only report
/architecture-review src/api/            # Scope to a path
/architecture-review --plan              # Also emit a phased refactor brief with /plan-feature hand-offs
/architecture-review --fix               # Apply mechanical refactors with per-finding diff preview
/architecture-review --map               # Heavier architecture-map section with full module-dep ASCII graph
/architecture-review --full-scan         # Force full scan even on >500-file repos
```

**Three guardrails distinguish this from "apply GoF patterns" tools:**
1. **Refactor catalog over GoF patterns.** The catalog (in `references/refactor-catalog.md`) leans toward complexity-reducing techniques (guard clauses, pure-function extraction, flag-argument removal, discriminated unions, table-lookup dispatch). Patterns appear only when the *problem* matches.
2. **Reads intended architecture first.** Step 1 reads CLAUDE.md, README.md, `docs/architecture/`, and ADRs to summarize what the project's architecture is *supposed* to be. Findings that conflict with documented decisions are surfaced separately for user confirmation, not applied automatically.
3. **CCN delta sanity gate.** Each finding includes `ccn_current` (from detected linter) and `ccn_projected`. Findings whose projected ≥ current are filtered before report.

**Decomposition:** Four parallel Sonnet subagents — `arch-structure` (complexity, coupling, layering), `arch-refactors` (catalog-driven complexity reduction), `arch-performance` (high-precision categories only), `arch-simplification` (over-engineering / almost-dead code, reports `lines_deletable`).

**Top-line metric:** Report opens with **Code we can delete: N lines across M files** so "least amount of code possible" is the first signal. Quick-wins phase puts simplification deletions ahead of refactors.

**Scale tiers:** <100 files = full scan, 100-500 = bounded, >500 = smart sampling (LOC × churn × import fan-in priority) + drill-down on hotspots.

**Output:** Architecture Map → Findings (Structure / Refactors / Performance, ranked) → Documented-Decision Conflicts (separate, requires confirmation) → Suggested Next Actions (chained skill recommendations + copy-pasteable `/plan-feature` snippets).

**`--fix` is restricted to single-file, non-API-breaking refactors.** Anything cross-file or API-touching auto-routes to `--plan` instead. Each edit is gated by per-finding diff preview. Use `Esc Esc` or `/rewind` to undo.

**Useful chain:** `/code-cleanup` → `/architecture-review` → `/architecture-review --plan` → `/plan-feature` per phase.

---

### /code-cleanup

**When:** Periodic maintenance, before major releases

**Usage:**
```bash
/code-cleanup                            # Full codebase scan (parallel agents)
/code-cleanup src/                       # Specific directory
/code-cleanup --code                     # Dead code only
/code-cleanup --deps                     # Unused dependencies only
/code-cleanup --vulns                    # Add CVE scan (npm audit / pip-audit / cargo audit per stack); report-only
/code-cleanup --css                      # Unused CSS only
/code-cleanup --tests                    # Test cleanup only
/code-cleanup --files                    # Unused files only
/code-cleanup --aggressive               # Move "Likely Safe" into "Safe to Delete"
/code-cleanup src/ --code --deps         # Combined: scoped + filtered
```

**Features:**
- Launches parallel subagents to scan multiple categories simultaneously
- Produces a summary dashboard (item counts, removable lines, risk levels)
- Lists "Quick Wins" for zero-risk bulk-approvable deletions

**Finds:**
- Unused files and dead code
- Unused CSS classes
- Unused dependencies
- Vulnerable dependencies (CVEs) — *only when `--vulns` is passed*
- Obsolete patterns
- Configuration cruft
- Stale tests

**Vulnerability scanning (`--vulns`):** opt-in only. Runs the audit command appropriate to the detected stack — `npm audit` / `yarn audit` / `pnpm audit` for Node, `pip-audit` (or `safety check`) for Python, `cargo audit` for Rust, `composer audit` for PHP, `govulncheck` for Go, `bundle audit` for Ruby. Findings include CVE ID, severity, fixed version, and a fix command. **Never auto-applied by `--fix`** — version bumps can break the app, so you run the fix command yourself after reviewing.

**Output:** Summary dashboard → Quick Wins → Safe to Delete / Likely Safe / Needs Investigation

---

### /test-review

**When:** Repo-wide test suite audit — when you want to know both "what isn't tested that matters" and "what tests can we delete" in a single report. Complements diff-scoped `/review-deep` §7 (or built-in `/code-review` for a quick pass) and artifact-level `cleanup-styles-tests` §7.

**Usage:**
```bash
/test-review                             # Default review-only report
/test-review src/auth/                   # Scope to a path
/test-review --plan                      # Phased rewrite/fill brief with /plan-feature hand-offs
/test-review --fix                       # Apply T01 deletions with per-finding diff preview (T01 only — assertion-free tests)
/test-review --coverage                  # Read existing coverage reports (jest/vitest/pytest-cov/cargo-tarpaulin/go cover); never auto-runs the tool
/test-review --full-scan                 # Force full scan even on >500-file repos
```

**Three deliberate design choices:**
1. **Twin headline metric.** Section 0 of the report shows *both* `Coverage gaps in critical code: X lines across Y files` and `Tests we can delete: Z lines across W files`. A single number on either axis is misleading on its own.
2. **`--coverage` is opt-in only.** Coverage tooling hits network/runtime; the default scan is heuristic-only (test-neighbor presence + public-symbol enumeration). Even with `--coverage`, only *reading* an existing report is auto — never running the tool.
3. **`--fix` is T01-only.** Assertion-free tests are the one provably-safe deletion (a test that asserts nothing cannot fail meaningfully). T02-T05, snapshot bloat, coverage gaps, and flakiness all auto-route to `--plan` because they need human judgment.

**Decomposition:** Three parallel Sonnet subagents — `test-coverage` (priority-ranked gaps + bug-fix-without-regression scan), `test-quality` (T01-T05 catalog with project-defined-assertion-helper false-positive guard), `test-economics` (snapshot bloat / flakiness / LOC-ratio extremes).

**T01-T05 catalog** (full schema in `references/test-smell-catalog.md`):
- **T01** — Assertion-free test (only `--fix-eligible` entry; deletable)
- **T02** — Weak assertion (`toBeTruthy`, `not.toBeNull` standing alone; rewritable)
- **T03** — Implementation-coupled / mock-heavy (impl/behavior ratio >2:1; rewritable)
- **T04** — Mystery guest (depends on data not in test file; rewritable)
- **T05** — Redundant (≥80% body overlap, non-boundary inputs; conservative — routes to `--plan`)

**Non-overlap with `/code-cleanup`:** `/test-review` does **not** flag orphaned test files, >3mo skipped tests, unused helpers, or stale snapshots — `cleanup-styles-tests` §7 owns those. Bidirectional pointers in the report footer cross-reference. If you're auditing for those four categories, run `/code-cleanup --tests` instead.

**Scale tiers:** <100 files = full, 100-500 = bounded, >500 = smart sample (reuses `architecture-review/references/scale-strategy.md`).

**Output:** Twin headline → Testing posture summary → Findings (Coverage / Quality / Economics, ranked) → Documented-decision conflicts (separate, requires confirmation) → Suggested next actions (skill chains + copy-pasteable `/plan-feature` snippets for strategic rewrites).

**Useful chain:** `/code-cleanup` (deletes orphaned test artifacts) → `/test-review` (audits what remains) → `/test-review --plan` → `/plan-feature` per phase. Or post-ship: `/test-review` → `/review-deep --security` on the critical-path gaps it surfaces.

---

### /seo-review

**When:** Repo-wide SEO and Generative Engine Optimization audit. Web projects only (rejects non-web repos silently). Use frequently on web projects — SEO/GEO is high-leverage and the field evolves rapidly, so fresh-fetched best practices each run keep recommendations current.

**Usage:**
```bash
/seo-review                              # Default report (heuristic + sitemap URL probe)
/seo-review src/pages/                   # Scope to a path
/seo-review --plan                       # Phased improvement brief with /plan-feature snippets per phase
/seo-review --fix                        # Apply strict-allowlist mechanical scaffolds (never fabricates content)
/seo-review --url https://example.com    # Live HTML diff + synthesizes sitemap URL probe bases when sitemap has relative URLs
```

**Three deliberate design choices:**
1. **Fetches current best practices fresh every run** via `WebSearch` + `WebFetch` from 4 source categories (Google Search Central + web.dev, Schema.org + JSON-LD docs, GEO sources including llms.txt spec + Anthropic/OpenAI/Perplexity guidance, third-party authority blogs Moz/Ahrefs/SEJ). SEO/GEO field evolves fast — embedded static guidance ages instantly. The fetched ~50-line brief is passed verbatim to all 3 subagents as their primary source of truth.
2. **Probes sitemap URLs for HTTP health.** Locates `sitemap.xml`/`sitemap_index.xml` locally, parses URLs, caps at top 100 by document order or `<priority>` desc, probes in parallel via `WebFetch`. Classifies 4xx/5xx/redirect-chains-greater-than-1-hop/slow-responses. **Total URL-health score impact capped at 8 points** out of Technical SEO's 25 — a fully broken sitemap doesn't zero out the dimension. All HTTP work runs in the orchestrator; subagents never make network calls.
3. **`--fix` mode never fabricates content.** Every allowlist-eligible fix inserts a placeholder + TODO comment (missing viewport meta, canonical scaffold, robots.txt template, sitemap.xml stub, OG/Twitter Card templates, JSON-LD scaffolds with required-field placeholders, llms.txt scaffold). Titles, descriptions, alt text, JSON-LD values — these require human judgment and route to `--plan` instead. Per-finding diff gate; summary surfaces the TODO markers needing real values.

**Decomposition:** Three parallel Sonnet subagents by default — `seo-technical` (crawlability, canonicals, mobile, hreflang, redirect config, perf signals, **sitemap URL health**), `seo-content` (titles, metas, headings, alt text, OG/Twitter Cards, internal linking), `geo-generative` (JSON-LD coverage, schema validation, llms.txt, E-E-A-T, semantic content patterns, AI-bot crawl access). **Plus a 4th `seo-gsc-insights` subagent when `config.yaml.site_url` is set and ADC is authenticated** (12 info-only sub-dims covering page-indexing reasons via URL Inspection clusters, CTR opportunities, position-band query opportunities, traffic orphans).

**Rubric:** 5 weighted dimensions summing to 100 (Technical SEO 25 / On-Page SEO 25 / Structured Data 20 / Generative Engine 20 / Performance 10). Fetched best practices may tune weights ±5 per dimension per run; sum delta always 0. Score breakdown by dimension + sub-dimension shown in the report. **GSC findings carry `score_impact: 0`** — orchestrator enforces this at consolidation. The score stays purely heuristic so `docs/seo-history.md` is comparable across runs whether GSC API is configured or not.

**GSC mode (opt-in, API-based):** single setup, two endpoints, binary activation:

1. Install gcloud SDK and run `gcloud auth application-default login --scopes=https://www.googleapis.com/auth/webmasters.readonly,https://www.googleapis.com/auth/cloud-platform`
2. Create `.seo-data/gsc/config.yaml` with `site_url: sc-domain:example.com` (or your URL-prefix property)
3. Re-run `/seo-review`. Step 1.6 dispatches 3 parallel `curl searchanalytics.query` calls (queries digest + pages digest + url_impressions_map) followed by up to 100 parallel `curl urlInspection.index.inspect` calls (URL selection: top 80 by impressions + 20 git-changed). All within the 2,000/day per-property quota.

Mode resolution is binary: **enabled** (API reachable) or **heuristic-only** (no config, gcloud missing, ADC unauthenticated, or API probe fails — Section 1 banner fires once). The folder is auto-`.gitignore`'d on first detection (config.yaml included — non-secret but property-identifying). Setup banner is one-time + sentinel-gated. New report Section 3 surfaces indexing coverage from URL Inspection sample, top-impact GSC findings, CTR opportunities, position-band query opportunities, traffic orphans. **35-day git-history scan** annotates findings with `code_changed_since_gsc_window` when recent commits match affected paths — closes the 4-5 week GSC reporting-lag gap (recommendations no longer say "fix X" when commit abc123 already added it 18 days ago). Routing-rename + 404-cluster co-occurrence produces a `/plan-feature` bulk-redirect snippet (in `--plan` Phase 1).

**Score history:** Tracked in-repo at `docs/seo-history.md` (auto-created on first run, append-only). Each row = date + score + top-3 priorities (with `[gsc]` prefix on GSC-sourced priorities so readers see why a row's priorities shifted between runs). Delta from previous score shown in the headline when history exists. The file is git-tracked so progress is visible across machines / commits / team members.

**Output:** Single-headline score `/100` (with Δ when history present) + top-3 highest-impact opportunities (`[gsc]`-prefixed when GSC-sourced; unified rank includes traffic_weight × log10(impressions+1)). Section 1 detected-context + score breakdown. Section 2 findings per dimension. **Section 3 GSC Insights** (only when GSC mode enabled). Section 4 score-history table (when present). Section 5 next actions. Section 6 footer disclosure (sources fetched, sitemap probe results, GSC API call summary + URL Inspection budget, git-history-window status, subtotal-check arithmetic).

**Useful chain:** post-ship → `/code-cleanup` (delete dead pages) → `/seo-review` (audit what remains) → `/seo-review --plan` → `/plan-feature` per phase. Or ambient improvement → `/seo-review --fix` for safe scaffolds, then `/seo-review --plan` for the rest. **Re-run after shipping major content/routing changes** → `/seo-review` to confirm GSC has caught up (API is daily-fresh; no re-export step needed; GSC pipeline lag ~2 days).

---

### /code-health-advice

**When:** You have time and want to do *something*, but you're not sure which of the other skills to reach for. Read-only routing call — never invokes anything.

**Usage:**
```bash
/code-health-advice
```

No flags. No arguments. Always read-only.

**What it inspects (single parallel turn):**
- `git status --porcelain` — uncommitted file count
- `git log --oneline -10` and `git log -1 --format=%cr` — recent activity
- `git rev-parse --abbrev-ref HEAD` and ahead/behind counts
- `gh pr view` — open PR for current branch (if any)
- `CLAUDE.md` — `Current Status`, `In Progress`, `Next Steps`, `Last Updated`

**State buckets it routes between:**

| Bucket | Signal | Recommended starting skill |
|---|---|---|
| **A. Pre-commit cleanup** | Uncommitted changes on a feature branch | `/code-review` → `/review-deep` |
| **B. Pre-merge verification** | Clean tree, open PR | `/review-deep --security` |
| **C. Post-ship audit** | Clean tree on main, recent ship | `/code-cleanup` |
| **D. Orient + audit** | Long since last commit, or no `CLAUDE.md` | `/resume-work deep` |
| **E. Ambient improvement** | Clean tree, no urgent task | `/architecture-review` |

**Output:** ~10-line report — state summary, bucket name, recommended flow, one alternative flow with a "use this if…" qualifier, optional notes (≤2 bullets).

**What it never does:** invoke skills, edit files, hydrate tasks, run tests, or generate a plan. It is a 30-second routing call before you commit to a flow.

---

## Workflow Scenarios

### Scenario 1: Starting a New Project

```bash
# 1. Create project folder
mkdir ~/projects/new-project
cd ~/projects/new-project
git init

# 2. Create initial docs
# (manually create README.md with basic description)

# 3. Launch Claude
claude

# 4. Generate full documentation
/update-docs

# 5. Plan the first feature
/plan-feature

# 6. Build it!

# 7. End session
/update-docs
```

---

### Scenario 2: Continuing Existing Project

```bash
# 1. Navigate & launch
cd ~/projects/existing-project
claude update
claude

# 2. Get context
/resume-work

# 3. Continue recommended task (or pick your own)

# 4. Periodic code review (quick built-in or /review-deep for thorough)
/code-review [files you modified]

# 5. End session
/update-docs
```

---

### Scenario 3: Adding a Feature to Existing Project

```bash
# 1. Start session
/resume-work

# 2. Add feature to PRD
"Add a new feature section to the PRD: [Feature Name]
- Purpose: [what it does]
- Requirements: [key requirements]
- Integration: [what it touches]"

# 3. Plan the feature
/plan-feature docs/[project]-prd.md

# 4. Build it

# 5. Review before committing (quick built-in or /review-deep for thorough)
/code-review [new files]

# 6. End session
/update-docs
```

---

### Scenario 4: Maintenance / Tech Debt Session

```bash
# 1. Start session
/resume-work

# 2. Find cleanup opportunities
/code-cleanup

# 3. Review and fix issues

# 4. Verify changes (quick built-in or /review-deep for thorough)
/code-review [modified files]

# 5. End session
/update-docs
```

---

### Scenario 5: First Time in an Unfamiliar Repo / Architecture Health Check

```bash
# 1. Start session
/resume-work

# 2. Strip the easy stuff first (dead code is noise for architecture review)
/code-cleanup

# 3. Repo-wide architecture audit
/architecture-review

# 4. Repo-wide test suite audit (if the project has tests)
/test-review

# 5. Convert top architecture findings into a phased refactor brief
/architecture-review --plan

# 6. Drop each phase into a fresh /plan-feature session as you tackle it
#    (the brief is self-contained — paste and go)

# 7. End session
/update-docs
```

For mechanical refactors only (single-file, non-API-breaking) you can skip step 5 and run `/architecture-review --fix` directly — it gates per finding with a diff preview. Anything cross-file or API-touching gets auto-routed to `--plan` regardless. Similarly, `/test-review --fix` walks T01 (assertion-free) deletions with per-finding diff preview.

### Scenario 6: Not Sure Which Skill to Run

When you have time but no clear plan — uncommitted changes you might commit, a recently-shipped repo you might audit, or a stale repo you haven't touched in weeks — start with the routing advisor:

```bash
/code-health-advice
```

It reads `git status`, the current branch, recent commits, `CLAUDE.md` `In Progress` / `Next Steps`, and any open PR (via `gh`). Then it classifies the state into one of five buckets and prints a short report:

```
State:    7 uncommitted files · feature/auth · 2h since last commit
Branch:   feature/auth (3 ahead of main, 0 behind)
Context:  CLAUDE.md In Progress = "session refresh flow"
PR:       no open PR

Bucket:   A — Pre-commit cleanup

Recommended flow:
  /code-review → /review-deep → /review-deep --verify → commit → /update-docs

Alternative: if this touches auth/payments/migrations
  /code-review → /review-deep --security → /review-deep --verify → commit → push → /ultrareview <PR#> → merge → /update-docs
```

The buckets cover: pre-commit cleanup, pre-merge verification, post-ship audit, orient + audit (unfamiliar repo), and ambient improvement. **The advisor never invokes anything** — read the flow, then run it yourself.

It's useful when you'd otherwise stare at the prompt for 30 seconds wondering whether to reach for `/code-review`, `/review-deep`, `/code-cleanup`, or `/architecture-review`.

---

## Documentation Structure

Every project should have:

```
project/
├── README.md                  # Public overview, setup guide
├── CLAUDE.md                  # Session context (AI reads this first)
└── docs/
    ├── [project]-prd.md       # Full specifications
    ├── session-history.md     # Archived sessions (auto-managed by /update-docs)
    └── [other docs].md        # Supporting documentation
```

Additionally, Claude Code maintains auto-memory at:
```
~/.claude/projects/<project-path>/memory/
├── MEMORY.md                  # Stable project facts (auto-synced by /update-docs)
└── [topic].md                 # Detailed topic notes (optional)
```

| File | Purpose | Updated |
|------|---------|---------|
| **README.md** | Quick start, public docs | When features ship |
| **CLAUDE.md** | AI context, session tracking | Every session |
| **docs/*.md** | Detailed specs, PRD | When requirements change |
| **docs/session-history.md** | Archived session logs (>3 sessions) | Automatically by `/update-docs` |
| **auto-memory MEMORY.md** | Stable facts (tech stack, commands, paths) | When project fundamentals change |

---

## Tips & Best Practices

### Do's

- Always start with `/resume-work`
- Always end with `/update-docs`
- Plan features before building (`/plan-feature`)
- Review code before committing (`/code-review` quick or `/review-deep` thorough)
- Keep CLAUDE.md updated - it's your project memory
- Commit frequently with descriptive messages

### Don'ts

- Don't skip `/resume-work` - context matters
- Don't forget `/update-docs` - you'll lose session context
- Don't start coding without planning complex features
- Don't let CLAUDE.md get stale
- Don't ignore code review suggestions

### Recurring tasks: `/loop`

Claude Code ships a built-in `/loop` skill for running a prompt or slash command on a recurring interval within the current session. Handy for polling a long-running process or running a periodic sanity check without manually re-triggering.

```bash
/loop 5m /code-cleanup --dry-run   # dry-run cleanup every 5 minutes
/loop 2m "check deploy status"     # poll a deploy every 2 minutes
/loop /review-deep                 # omit interval — model self-paces
```

Two important caveats: `/loop` is **session-scoped** — it dies when the Claude Code session closes — and recurring jobs **auto-expire after 3 days** even if the session lives longer. Don't use it as a replacement for a real cron job or scheduled remote agent (see `/schedule` for persistent scheduling).

**Do not build a custom `/loop` skill in this repo.** The built-in already covers this use case; re-implementing it in `.claude/skills/` would be waste.

---

## New Machine Setup

See [README.md](README.md#setup-on-a-new-machine) for clone, symlink, and sync instructions.

---

## Keyboard Shortcuts & Tips

```bash
# Quick navigation
cd ~/projects && ls              # See all projects
cd ~/projects/[tab]              # Tab completion

# Git shortcuts
git status                       # What's changed
git diff                         # See changes
git log --oneline -5             # Recent commits

# Claude
claude update                    # Check for updates
claude                           # Launch
Ctrl+C                           # Exit Claude
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Claude doesn't know project context | Run `/resume-work` first |
| Lost track of what was done | Check CLAUDE.md Session History or `docs/session-history.md` for older sessions |
| Starting fresh on old project | Run `/update-docs` to rebuild context |
| Too many questions in `/plan-feature` | Say "let's skip that" or "good enough" |
| `/code-cleanup` too aggressive | Only delete "Safe to Delete" items, or avoid `--aggressive` flag |
| `/review-deep` reviewing too much | Use `--staged` or specify files instead of running with no args |
| Auto-memory out of date | Run `/update-docs` — it syncs stable facts automatically |
| CLAUDE.md too long | `/update-docs` auto-archives sessions >3 to `docs/session-history.md` |

---

## My Custom Commands Location

Commands are stored in:
```
~/Development/projects/claude-config/
├── .claude/
│   ├── agents/              # Subagent definitions
│   ├── scripts/             # Session startup scripts
│   │   ├── start-claude.sh          # Mac/Linux startup
│   │   └── start-claude.ps1        # Windows startup
│   ├── settings.local.json  # Shared Claude Code settings
│   └── skills/              # Skills (commands + references)
│       ├── architecture-review/
│       ├── code-cleanup/
│       ├── code-health-advice/
│       ├── plan-feature/
│       ├── resume-work/
│       ├── review-deep/
│       ├── seo-review/
│       ├── test-review/
│       └── update-docs/
├── .gitignore
├── Workflow.md              # This file
└── README.md
```

GitHub repo: `burak-maxitech/claude-config` (private)

Symlinked to: `~/.claude/skills`, `~/.claude/agents` (individual subdirectories)

---

## Version History

| Date | Changes |
|------|---------|
| Jan 2025 | Initial workflow created |
| | Added three-file documentation system (README, CLAUDE.md, docs/) |
| | Merged plan-feature and plan-feature-addon commands |
| | Integrated code-review and code-cleanup |
| | Set up GitHub sync across machines |
| Feb 2026 | Optimized all commands for Claude Opus 4.6 capabilities |
| | `/resume-work` — parallel doc reads, parallel git scans, auto-memory awareness, task hydration |
| | `/update-docs` — task list drain, session history archiving, auto-memory sync |
| | `/plan-feature` — parallel context loading, Plan Mode integration, task hydration from plan |
| | `/code-review` — git-aware diffing (uncommitted/staged/PR/last-commit), convention detection, enforced file:line refs |
| | `/code-cleanup` — parallel subagent scanning, summary dashboard, Quick Wins, scope filters (--code/--deps/--css/--aggressive) |
| | Added `docs/session-history.md` auto-archiving across all commands |
| | Added auto-memory integration across all commands |
| | Added TaskCreate/TaskUpdate live task tracking across workflow |
| Mar 2026 | Added startup scripts (`start-claude.sh`, `start-claude.ps1`) to automate session startup |
| | Replaced manual 8-step startup with single-command script (5 automated steps); shows tip to run `/resume-work` |
| Apr 2026 | Aligned with Opus 4.7 release (CC 2.1.111): added `effort: high` frontmatter to `/code-review` and `/plan-feature` for stronger reasoning on review/synthesis work |
| | Documented when to reach for built-in `/ultrareview` (high-risk pre-merge) vs custom `/code-review` (daily driver) in README |
| May 2026 | New `/architecture-review` skill — repo-wide complexity + refactor + perf + over-engineering audit, distinct from diff-scoped reviewers. Three guardrails: catalog-driven complexity-reducing refactors (not GoF pattern-mongering), reads intended architecture from CLAUDE.md/ADRs first, CCN delta sanity gate. **Four parallel subagents** (`arch-structure`, `arch-refactors`, `arch-performance`, `arch-simplification`). 4th dimension added mid-session after honest audit against user's three real goals (optimized / maintainable / least-code-possible) found `least-code-possible` was under-served — refactor catalog *trades* complexity, doesn't delete it. `arch-simplification` targets sub-file over-engineering: single-impl interfaces, pass-through wrappers, defensive code for impossible states, unread config, near-duplicates. Reports `lines_deletable` as top-line metric. |
| | New `/code-health-advice` skill — read-only routing advisor. Reads `git status`, branch, recent commits, `CLAUDE.md` `In Progress`/`Next Steps`, open PR; classifies repo state into one of five buckets (pre-commit cleanup / pre-merge verification / post-ship audit / orient + audit / ambient improvement); prints a ~10-line report with one recommended skill flow + one alternative. Never invokes anything, never edits files. Solves "I have time but I'm not sure which skill to reach for next." |
| | New `/test-review` skill — repo-wide test suite audit. Closes the biggest code-health gap surfaced in Session 23's audit (existing skills only covered diff-scoped or artifact-level test concerns). Three parallel Sonnet subagents (`test-coverage` / `test-quality` / `test-economics`). T01-T05 smell catalog. **Twin headline metric** so both directions (missing coverage on critical paths + wasteful/redundant tests) are equally visible. `--fix` restricted to T01 (assertion-free — provably safe deletion); everything else routes to `--plan`. `--coverage` opt-in for reading existing coverage reports (jest/vitest/pytest-cov/cargo-tarpaulin/go cover); never auto-invokes the tool. Defers entirely to `cleanup-styles-tests` §7 for orphans / >3mo skips / unused helpers / stale snapshots — non-overlap is deliberate. |
| | New `/seo-review` skill — repo-wide SEO + Generative Engine Optimization audit for web projects (rejects non-web silently). Three parallel Sonnet subagents (`seo-technical` / `seo-content` / `geo-generative`). **Fetches current best practices fresh every run** via WebSearch + WebFetch (4 source categories: Google Search Central + web.dev / Schema.org + JSON-LD / GEO sources + llms.txt spec / third-party authority blogs) — SEO/GEO evolves fast; embedded static guidance ages instantly. **Probes sitemap URLs for HTTP health** (4xx/5xx/redirect-chains/slow-responses; orchestrator-only HTTP, 100-URL cap, 8-point score-impact cap so a fully broken sitemap can't zero out Technical SEO). Single headline: score `/100` + top-3 opportunities + delta vs previous run when `docs/seo-history.md` exists. **`--fix` strict allowlist never fabricates content** — only inserts placeholders + TODO comments for the 11 eligible patterns (viewport, canonical, robots.txt, sitemap.xml stub, OG/Twitter scaffolds, JSON-LD scaffolds, llms.txt, decorative alt="", img dimensions from context, lazy-loading). `--url <deployed-url>` adds live HTML diff for SSR/runtime-rendered issues. Rubric: Technical SEO 25 / On-Page 25 / Structured Data 20 / Generative Engine 20 / Performance 10, with ±5-per-dim weight tuning from the fetched brief. |
| | **`/seo-review` v2: Google Search Console CSV ingestion + git-history awareness** (subagents 13→14). Closes the gap surfaced by dogfooding v1 — static signals can't tell which pages get impressions, which queries rank at position 5-20, or which pages Google crawled-but-didn't-index. User exports CSVs from GSC and drops them in `.seo-data/gsc/{performance,indexing}/` (auto-gitignored on first detection). Skill ingests 13 canonical CSVs (queries, pages, indexing summary + all 9 per-reason indexing CSVs), emits 12 sub-dim info-only findings via new `seo-gsc-insights` 4th parallel subagent. **Score stays /100 purely heuristic** (`score_impact:0` enforced agent-side and orchestrator-side — single point of enforcement) so `docs/seo-history.md` is comparable across runs whether CSVs present or not. **35-day git-history scan** (universal patterns + stack-specific overlays for 17 frameworks) annotates findings with `code_changed_since_gsc_window: true` when recent commits match affected paths — closes the 4-5 week GSC reporting-lag (recommendations no longer say "fix X" when commit abc123 already added it 18 days ago). **Routing-rename + 404-cluster co-occurrence** produces a `/plan-feature` bulk-redirect snippet (in `--plan` Phase 1, renamed from "Broken URL Triage" to "Indexing & Crawl Hygiene"). New report Section 3 "GSC Insights". Headline top-3 reranks by `traffic_weight × certainty × effective_impact / effort_weight` (heuristic + GSC findings ranked together). Sentinel-gated one-time setup banner when no CSVs present. Auto-generated `.seo-data/gsc/README.md` walks user through GSC export paths. Freshness policy: warn >30 days, never block. |
| | **`/seo-review` v3 (superseded — 3-path hybrid; BigQuery + CSV + heuristic) → simplified same session to v3.x API-only.** v3 shipped a 4-state matrix mixing BigQuery Bulk Data Export (Performance) + CSV exports (Page Indexing — CSV-only by Google product limit) + heuristic fallback. Same-session honest assessment found the skill had become "the most complicated skill of this repo" (user's framing) with marginal value: BigQuery only covered Performance, the more valuable Indexing + Experience signals lived elsewhere. Simplification cut BQ + CSV paths entirely; allowed-tools dropped `Bash(bq:*)`. See follow-up row for the surviving design. |
| | **`/seo-review` v3.x: Search Console API as canonical, single-path GSC integration** (subagent count unchanged, allowed-tools += `Bash(gcloud:*), Bash(curl:*)`). Single auth (gcloud ADC with `webmasters.readonly` scope) + single config key (`site_url:` in `.seo-data/gsc/config.yaml`) + two API endpoints (`searchanalytics.query` for Performance + `urlInspection.index.inspect` for per-URL Indexing) covers both signals through one interface. Binary mode: API-enabled or heuristic-only. URL Inspection selection algorithm picks 100 URLs/run (top 80 by impressions from Q3's `url_impressions_map` + 20 git-changed paths resolved via `page_type_map`) — well under the 2,000/day per-property quota. `coverageState` + `pageFetchState` joint lookup table maps API responses to the existing 9-reason cluster catalog (sub-dims 2-9 preserved); Performance Q1/Q2 feed sub-dims 10-12. 3 reference files: `gsc-api-schema.md` (3 endpoints + auth + quota + enums), `gsc-api-queries.md` (3 parametrized curl templates + URL selection + lookup table), `gsc-ingestion.md` (digest contract + 12 sub-dim finding catalog, simplified to API-only). Setup walkthrough: `gcloud auth application-default login --scopes=...,...` + `set-quota-project` + `config.yaml.site_url`. Active probe via `GET /webmasters/v3/sites` catches scope/permission issues upfront. No silent fallback when API configured + fails — print error, skip signal, never block. Net: 12 reference files → 9 (3 BigQuery files deleted); SKILL.md ~350 lines simpler; setup banner collapsed from 3 paths to 1. Score `/100` stays purely heuristic via `score_impact:0` invariant. |

---

*Last updated: May 2026*
