---
name: arch
description: Repo-wide architecture audit across six dimensions — structural debt and complexity hotspots (cyclomatic AND cognitive), catalog-cited refactors, OO/SOLID design-principle violations, thread safety and concurrency defects, error safety and resource lifecycle gaps, architectural scalability limits, performance suspects, and over-engineering/almost-dead code. Opens with the top 3 architectural themes, not a flat finding list.
when_to_use: When user mentions architecture review, refactoring opportunities, technical debt at the repo level, SOLID/OO design quality, thread safety or race conditions, error handling gaps, scalability limits, "is this codebase over-engineered", "make the codebase smaller", "is this production-ready", or "where's the complexity in this codebase". Different from `/code-review` (diff-scoped, daily driver), `/bx:review` (thorough senior-engineer review), `/code-review ultra` (PR-scoped cloud review), and `/bx:clean` (file-level deletion only).
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Edit, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(sort:*), Bash(uniq:*), Bash(jq:*), Bash(npx:*), Bash(npm:*), Bash(pip:*), Bash(python:*), Bash(python3:*), Bash(cargo:*), Bash(cat:*), Bash(head:*), Agent
effort: high
argument-hint: "[path] [--plan] [--fix] [--full-scan] [--map]"
---

# Architecture Review — Repo-Wide Architectural Audit

Audit this codebase like a staff engineer doing a quarterly architecture health check.

Six dimensions, scanned in parallel:

| Dimension | Asks |
|-----------|------|
| **Structure** | Where is complexity concentrated, and what depends on what? |
| **Design** (`D`) | Do the types and modules honor the principles that keep change cheap — SOLID, cohesion, boundaries? |
| **Refactors** (`R`) | Which catalog techniques *demonstrably* reduce cognitive load here? |
| **Simplification** (`S`) | What exists but earns nothing? |
| **Robustness** (`C`/`E`/`X`) | What happens when this runs twice at once, when the network hangs, or when the table has ten million rows? |
| **Performance** | What is statically detectable, and what merely needs measuring? |

The report opens with the **top 3 architectural themes** — a judgment, not a list. Findings that
do not cluster into a theme still appear in full below it; nothing is dropped.

This skill is distinct from the diff-scoped reviewers in this repo:

- **`/code-review`** — diff/commit scope, lightweight single-pass quality review (built-in, daily driver)
- **`/bx:review`** — diff/commit scope, thorough senior-engineer review with `--security`/`--verify`/`--fix`
- **`/code-review ultra`** — PR-scoped cloud review with verifying subagents (high-risk pre-merge)
- **`/bx:clean`** — repo-wide deletion focus at *file/dependency* granularity (whole unused files, unused deps, stale config)
- **`/bx:arch` (this)** — repo-wide *structural, complexity, and over-engineering* focus, with deletion at *symbol/abstraction* granularity

The two are complementary: `/bx:clean` deletes whole files; this skill deletes abstractions, wrappers, defensive code, and almost-dead symbols inside files that are still in use. If the user asks about per-commit quality, suggest `/code-review` (quick) or `/bx:review` (thorough) instead.

---

## Step 0 — Detect Project Context

Mirror `/bx:clean` Step 0: gather stack, workspaces, linter, and repo size before any heavy work.

**Stack auto-detect** (read each, skip silently if missing):

- `package.json` → Node/JS/TS. Check for monorepo: `workspaces` field or sibling `pnpm-workspace.yaml`/`yarn.lock`. Each workspace is an independent scan target.
- `pyproject.toml` / `requirements.txt` / `Pipfile` → Python
- `Cargo.toml` → Rust. If root has `[workspace] members = [...]`, scan each member crate separately.
- `go.mod` → Go (with optional `go.work` workspaces)
- `composer.json` → PHP, `Gemfile` → Ruby, `pom.xml` / `build.gradle` → JVM
- `tsconfig.json` → TypeScript (richer pattern detection)

**Linter auto-detect for complexity measurement** (record availability, do not run yet). Two
metrics are measured, not one — see `references/finding-rubrics.md` for why both are needed:

| Stack | Tool | Metric | Detection |
|-------|------|--------|-----------|
| JS/TS | `eslint` with `complexity` rule | cyclomatic | `.eslintrc*` references `complexity` rule |
| JS/TS | `eslint-plugin-sonarjs` (`sonarjs/cognitive-complexity`) | **cognitive** | plugin present in deps or `.eslintrc*` |
| Python | `radon` | cyclomatic | `radon` in `pyproject.toml`/requirements deps |
| Python | `ruff` (mccabe `C901`) | cyclomatic | `pyproject.toml` `[tool.ruff]` enables `C` rules |
| Multi-lang | `lizard` | cyclomatic | `lizard` in deps (any stack) |
| JVM | `pmd` / `checkstyle` config | cyclomatic | `pmd-ruleset.xml`, `checkstyle.xml` |

**No tool outside `eslint-plugin-sonarjs` computes cognitive complexity** — `radon`, `ruff`,
`lizard`, and `pmd` are cyclomatic-only. On every other stack, cognitive complexity comes from
the heuristic in `references/scan-structure.md` Step 1b.

If no cyclomatic linter is detected either, fall back to the Grep heuristic for both metrics.
Record the two independently — `cyclomatic: <tool|heuristic>` and `cognitive: <sonarjs|heuristic>`
— so the report footer discloses each accurately. They are frequently different.

**Repo size tier** (`git ls-files | wc -l`):

| Files | Tier | Behavior |
|-------|------|----------|
| <100 | full | Subagents read every file in scope |
| 100-500 | bounded | Subagents read all, but cap deep-reads; quick-scan others |
| >500 | sample | Smart sampling + drill-down (see `references/scale-strategy.md`) |

Override with `--full-scan` to force `full` regardless of size.

**Tell the user what you detected** in one line, e.g.:
> Detected: TypeScript pnpm monorepo (5 workspaces), 312 files. Cyclomatic: eslint `complexity`. Cognitive: heuristic (no sonarjs). Tier: bounded. Scanning structure+design / refactors / simplification / robustness / performance.

---

## Step 1 — Read Intended Architecture

**This is the guardrail against imposing an opinion.** Before subagents evaluate anything, summarize what *this* project's architecture is supposed to look like.

Read in parallel (single turn, multiple Read calls):

- `CLAUDE.md` — usually has Architecture Summary, Key Decisions
- `README.md` — high-level structure
- `docs/architecture/*.md` (Glob)
- `docs/decisions/*.md` and `ADR-*.md` (Glob)
- `ARCHITECTURE.md` if present at root

From these, write a 3-5 bullet **Intended Architecture summary**:

- Layering model (e.g. "hexagonal: domain / adapters / infrastructure" or "flat by feature folder" or "explicitly no layers — small CLI")
- Module boundaries and naming conventions
- Deliberate non-conventions (e.g. "monolith by choice — see ADR-0007", "we avoid DI containers")
- Out-of-scope concerns (e.g. "no perf tuning until v2 ships")
- Testing boundary expectations

If no architecture docs exist, say so and infer from top-level directory structure — but flag in the report that findings are evaluated against an *inferred* architecture.

**Pass this summary verbatim to all five subagents** in their task prompts. Subagents must mark any finding that conflicts with the documented intent as `respects_documented_decision: false`. Those surface in a separate report section the user has to confirm before action — they are *not* automatically actioned, even in `--fix` mode.

---

## Step 2 — Mode Dispatch

Interpret `$ARGUMENTS`:

| Argument | Effect |
|----------|--------|
| (none) | Default review-only: produce report and stop |
| path (e.g. `src/api/`) | Scope subagents to that path only; everything else applies normally |
| `--plan` | After the report, transform top findings into a phased brief ready to hand off to `/bx:plan` (read `references/plan-mode.md`) |
| `--fix` | After the report, apply mechanical refactors with per-finding diff preview gate (read `references/fix-mode.md`). Restricted to single-file, non-API-breaking. End with `/rewind` reminder. |
| `--full-scan` | Force `full` tier regardless of repo size |
| `--map` | Include the heavier architecture-map section (default has lightweight version) |

`--plan` and `--fix` are mutually exclusive. If both supplied, error out: "Pick one — `--plan` emits a brief, `--fix` applies edits."

---

## Step 3 — Scope Selection

- If a path argument was given, scope subagents to that path
- Else apply the tier from Step 0:
  - `full` → all source files
  - `bounded` → all source files but with deep-read budget
  - `sample` → read `references/scale-strategy.md` and apply smart sampling (LOC × churn × import-fan-in priority, not random)

Compute the file lists once and pass them to subagents so all three see the same scope. Record what was sampled vs skipped — this goes into the report's footer.

---

## Step 4 — Parallel Subagent Dispatch

Launch all five subagents in a single turn (one Agent tool call per agent). Mirror `/bx:clean` Step 1.

For each subagent, **read its corresponding reference file** (it contains the detailed scan instructions) and pass the contents in the task prompt along with the shared context.

**Read `references/finding-rubrics.md` once and pass its full contents to every subagent** as the
`Scoring contract` block below. It is the canonical owner of the severity / certainty / effort
anchors and the two mandatory justification fields. Do not paraphrase it per-agent — five agents
scoring against five paraphrases is the problem it exists to solve.

### Shared context to pass to all subagents:

```
Detected stack: <from Step 0>
Workspaces: <list or none>
Linter: <name + how to invoke, or "heuristic">
Tier: <full|bounded|sample>
Scope file list: <paths>

Intended Architecture summary:
<3-5 bullets from Step 1>

Findings format: structured JSON-like blocks. Do NOT format a final report — return raw findings only.

Scoring contract: <full contents of references/finding-rubrics.md>

Each finding must include:
  dimension: structure | refactor | performance | simplification | design | robustness
  location: <path>:<line-range>
  title: <one-line>
  severity: low | medium | high          (anchors: scoring contract)
  certainty: 0.0–1.0                     (evidence class: scoring contract)
  effort_estimate: trivial | small | medium | large
  evidence: <the work behind the certainty band — quoted lines, grep counts, call sites>
  why_this_might_be_wrong: <one sentence, specific to this finding>
  ccn_current: <int or null>
  ccn_projected: <int or null>
  cognitive_current: <int or null>
  cognitive_projected: <int or null>
  lines_deletable: <int>  (mandatory for simplification, default 0 for others)
  respects_documented_decision: true | false
  recommended_refactor: <prose>
  cite_catalog_entry: <catalog ID; required for refactor and simplification dimensions>
```

### Agent 1: arch-structure
Read `references/scan-structure.md` AND `references/catalog-rules.md` AND `references/catalog-design.md`, then dispatch the `arch-structure` subagent with all three + shared context. Targets: cyclomatic/cognitive complexity hotspots, coupling, cohesion, layering violations, circular deps, **and the D-prefix design-principle entries** (LSP/ISP/DIP violations, Law of Demeter, anemic domain model, feature envy, primitive obsession, god class).

### Agent 2: arch-refactors
Read `references/scan-refactors.md` AND `references/catalog-rules.md` AND `references/catalog-refactors.md`, then dispatch the `arch-refactors` subagent with all three + shared context. The catalog is mandatory context — every finding must cite a catalog entry by ID.

### Agent 3: arch-performance
Read `references/scan-performance.md`, then dispatch the `arch-performance` subagent with those instructions + shared context. Restricted to high-precision categories (N+1, sync I/O in async paths, accidental O(n²), missing memoization, hot-loop invariants). Other performance hunches are framed as "suspects to measure," not fixes.

### Agent 4: arch-simplification
Read `references/scan-simplification.md` AND `references/catalog-rules.md` AND `references/catalog-simplification.md`. Dispatch the `arch-simplification` subagent with both + shared context. Targets: over-engineering and almost-dead code (single-impl interfaces, pass-through wrappers, always-same params, unread config, defensive code for impossible states, near-duplicates, speculative generics, unused exports). Every finding must report `lines_deletable >= 1`.

### Agent 5: arch-robustness
Read `references/scan-robustness.md` AND `references/catalog-rules.md` AND `references/catalog-robustness.md`, then dispatch the `arch-robustness` subagent with all three + shared context. Targets: concurrency and thread safety (`C`), error safety and resource lifecycle (`E`), and architectural scalability (`X`) — races and TOCTOU, locks held across await, floating async work, swallowed exceptions, missing timeouts and retries, unreleased resources, unbounded result sets, missing backpressure.

This agent asks a different question from the other four: not "is this hard to read or bigger than it needs to be?" but "what happens when this runs twice at once, when the network hangs, or when the table has ten million rows?" Its findings are usually about something *absent*, which is why its scan file requires an entry-point map before scoring.

**Dispatch note.** Name every agent explicitly, as above. Generic dispatch loses each agent's frontmatter `model: sonnet` routing and its tool scoping (S43/S50) — a `Agent(model:…)` deny rule cannot guard an omitted model parameter.

---

## Step 5 — Consolidate, Filter, Score

After all five subagents return:

1. **Sanity gate (complexity delta)** — drop a refactor-dimension finding only when it reduces
   *neither* metric: `ccn_projected >= ccn_current` **AND**
   `cognitive_projected >= cognitive_current`. A finding that lowers either one survives.

   This gate is dual-metric because the catalog reasons about both. `R01` (guard-clause flatten)
   and `R09` (named predicate) state **"CCN direction: unchanged"** — they move cognitive load,
   not decision-point count. A CCN-only gate deletes them before the report, which is exactly
   what it used to do. Any entry whose CCN direction is "unchanged" **must** carry a cognitive
   delta; a finding citing such an entry with no cognitive numbers is dropped as unsubstantiated,
   not passed through.

   Simplification findings are not gated on complexity at all — they're gated on
   `lines_deletable >= 1` (the subagent already enforces this).
2. **Certainty gate** — drop findings with `certainty < 0.5` unless `severity = high` OR `lines_deletable >= 20`. Big deletions earn a pass through the certainty filter so user can review even uncertain large wins.
3. **Deduplicate** — if two subagents report the same location, merge into one finding with both perspectives. Common overlap: `arch-refactors` R03 (flag arg) and `arch-simplification` S03 (always-same param) — keep one with the higher rank score.
4. **Rank score** — `severity_weight × certainty / effort_weight` where severity {low: 1, medium: 2, high: 4} and effort {trivial: 1, small: 2, medium: 4, large: 8}. For simplification findings, also factor `log(lines_deletable + 1)` into the score so big deletions float up.
5. **Aggregate lines_deletable totals** — sum across all simplification findings (and any other findings reporting `lines_deletable > 0`). Track distinct files affected. These are the top-line numbers in Section 0 of the report.

5b. **Collect suppressions** — `arch-simplification` returns `s01_suppressed` (Dependency
   Inversion boundaries) and `s06_suppressed` (trust boundaries) alongside its findings. These are
   *not* findings and never enter ranking, but they are never silently discarded either: count
   them, keep their locations, and hand them to the report footer. If the Intended Architecture
   summary was inferred rather than read from docs, the footer must say so — suppression quality
   follows inference quality.
6. **Group**:
   - **Quick wins** — top rank, effort ∈ {trivial, small}. Heavily favors simplification deletions and trivial refactors (R01, R08, R09, S04, S06).
   - **Strategic refactors** — high severity, effort ∈ {medium, large}
   - **Documented-decision conflicts** — `respects_documented_decision == false`, regardless of dimension. Separate section, requires user confirmation. (Especially important for simplification: documented "we keep this abstraction for X" must override deletion suggestions.)
   - **Performance suspects** — `dimension == performance` AND `certainty < 0.7`. Framed as "measure, don't refactor blindly."

---

## Step 6 — Output

Read `references/report-template.md` for exact formatting. The shape:

0. **Top-line metric** — "Code we can delete: N lines across M files" (from Step 5 aggregation). This is the first line of the report, before the architecture map. Makes "least amount of code" a primary signal.
1. **Architecture Map** (lightweight by default; full ASCII dep graph behind `--map`)
   - Detected layers (from Step 1) + observed file/dir tree alignment
   - Complexity heatmap: top 10 hotspots by current CCN with file:line and CCN value
2. **Findings** — four subsections in the template's order (Simplification first — deletion-first — then Structure / Refactors / Performance), each ordered by rank score. CCN delta column (`current → projected`, Δ) for refactors. `Lines Δ` column for simplification.
3. **Documented-Decision Conflicts** — separate, prefixed with "**Confirm intent before action:**"
4. **Suggested Next Actions**
   - Skill chains: e.g. "If many `Unused module` candidates appeared, run `/bx:clean` first and rerun this."
   - Copy-pasteable `/bx:plan <brief>` snippets for top 3 strategic refactors
5. **Footer** — disclosure: linter used (or "heuristic"), files scanned, files sampled vs skipped, deletion totals

---

## Step 7 — Mode-Specific Tail

### If `--plan` in $ARGUMENTS:
Read `references/plan-mode.md`. Transform the top quick-wins + strategic refactors into a phased brief. Each phase becomes a self-contained `/bx:plan <brief>` payload the user can drop directly into another session. Documented-decision conflicts become their own confirmation phase, ordered last.

### If `--fix` in $ARGUMENTS:
Read `references/fix-mode.md`. Walk findings whose `recommended_refactor` qualifies as **single-file, non-API-breaking** (extract method within file R02, guard-clause flatten R01, hoist invariant R08, named predicate R09, table-lookup dispatch *if* the table stays in the same file R06, defensive-code removal S06, unread-config deletion S04 when the key lives in one file, single-file unused-export deletion S09). Anything cross-file or API-touching is auto-routed to `--plan` instead — fix-mode.md's eligibility rules are canonical.

For each qualifying finding:
1. Show the current snippet
2. Show the proposed diff
3. Wait for user approval (yes / no / skip)
4. Apply via `Edit` if approved
5. Move to next

End with:
> Done. Run `/rewind` (or press `Esc Esc` on an empty prompt) to undo this pass — checkpoints are captured per user prompt, not per edit, so one rewind reverts the whole batch. If you ran this on a dedicated branch, `git checkout main && git branch -D <branch>` discards the whole pass.

---

## Step 8 — Closing

If running default mode, end with one line:
> Run `/bx:arch --plan` to convert top findings into a phased refactor brief, or `/bx:arch --fix` for in-place mechanical refactors. Run `/bx:clean` first if dead-code findings appeared above the architectural ones.

---

## Quick Reference

| Want... | Use... |
|---------|--------|
| Per-commit / diff quality review (quick) | `/code-review` |
| Per-commit / diff quality review (thorough) | `/bx:review` |
| Dead code, unused deps | `/bx:clean` |
| Pre-merge multi-agent verification | `/code-review ultra` |
| **Repo-wide architecture + complexity audit** | **`/bx:arch` (this)** |
