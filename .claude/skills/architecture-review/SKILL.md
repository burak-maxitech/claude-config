---
name: architecture-review
description: Repo-wide architecture audit. Surfaces structural debt, complexity hotspots, missed refactor opportunities, and performance suspects across the whole codebase — not just diffs. Use when user mentions architecture review, refactoring opportunities, technical debt at the repo level, restructuring proposals, or "where's the complexity in this codebase". Different from /code-review (diff-scoped), /simplify (recent changes only), /ultrareview (PR-scoped cloud review), and /code-cleanup (deletion-focused).
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Edit, Bash(git:*), Bash(find:*), Bash(wc:*), Bash(jq:*), Bash(npx:*), Bash(npm:*), Bash(pip:*), Bash(python:*), Bash(python3:*), Bash(cargo:*), Bash(cat:*), Bash(head:*), Task
effort: high
argument-hint: "[path] [--plan] [--fix] [--full-scan] [--map]"
---

# Architecture Review — Repo-Wide Architectural Audit

Audit this codebase like a staff engineer doing a quarterly architecture health check. Surface structural debt, complexity hotspots, refactor opportunities that *demonstrably* reduce cognitive load (not pattern-mongering), and high-precision performance suspects.

This skill is distinct from the diff-scoped reviewers in this repo:

- **`/code-review`** — diff or commit scope, single-pass quality review
- **`/simplify`** — recent changes only, post-hoc cleanup
- **`/ultrareview`** — PR-scoped cloud review with verifying subagents
- **`/code-cleanup`** — repo-wide *deletion* focus (dead code, unused deps)
- **`/architecture-review` (this)** — repo-wide *structural and complexity* focus

If the user asks about dead code, unused dependencies, or per-commit quality, suggest the appropriate sibling skill instead.

---

## Step 0 — Detect Project Context

Mirror `/code-cleanup` Step 0: gather stack, workspaces, linter, and repo size before any heavy work.

**Stack auto-detect** (read each, skip silently if missing):

- `package.json` → Node/JS/TS. Check for monorepo: `workspaces` field or sibling `pnpm-workspace.yaml`/`yarn.lock`. Each workspace is an independent scan target.
- `pyproject.toml` / `requirements.txt` / `Pipfile` → Python
- `Cargo.toml` → Rust. If root has `[workspace] members = [...]`, scan each member crate separately.
- `go.mod` → Go (with optional `go.work` workspaces)
- `composer.json` → PHP, `Gemfile` → Ruby, `pom.xml` / `build.gradle` → JVM
- `tsconfig.json` → TypeScript (richer pattern detection)

**Linter auto-detect for CCN measurement** (record availability, do not run yet):

| Stack | Tool | Detection |
|-------|------|-----------|
| JS/TS | `eslint` with `complexity` rule | `.eslintrc*` references `complexity` rule, or `eslint-plugin-sonarjs` present |
| Python | `radon` | `radon` on `$PATH` or in `pyproject.toml` deps |
| Python | `ruff` (mccabe `C901`) | `pyproject.toml` `[tool.ruff]` enables `C` rules |
| Multi-lang | `lizard` | `lizard` on `$PATH` |
| JVM | `pmd` / `checkstyle` config | `pmd-ruleset.xml`, `checkstyle.xml` |

If none detected, fall back to **Grep heuristic** (count decision points: `if|else if|for|while|case|catch|&&|\|\||\?` per function). Record this as `linter: heuristic` so the report disclosure is accurate.

**Repo size tier** (`git ls-files | wc -l`):

| Files | Tier | Behavior |
|-------|------|----------|
| <100 | full | Subagents read every file in scope |
| 100-500 | bounded | Subagents read all, but cap deep-reads; quick-scan others |
| >500 | sample | Smart sampling + drill-down (see `references/scale-strategy.md`) |

Override with `--full-scan` to force `full` regardless of size.

**Tell the user what you detected** in one line, e.g.:
> Detected: TypeScript pnpm monorepo (5 workspaces), 312 files, eslint with complexity rule. Tier: bounded. Scanning structure / refactors / performance.

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

**Pass this summary verbatim to all three subagents** in their task prompts. Subagents must mark any finding that conflicts with the documented intent as `respects_documented_decision: false`. Those surface in a separate report section the user has to confirm before action — they are *not* automatically actioned, even in `--fix` mode.

---

## Step 2 — Mode Dispatch

Interpret `$ARGUMENTS`:

| Argument | Effect |
|----------|--------|
| (none) | Default review-only: produce report and stop |
| path (e.g. `src/api/`) | Scope subagents to that path only; everything else applies normally |
| `--plan` | After the report, transform top findings into a phased TaskCreate-ready brief (read `references/plan-mode.md`) |
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

Launch all three Task subagents in a single turn (one Task call per agent). Mirror `/code-cleanup` Step 1.

For each subagent, **read its corresponding reference file** (it contains the detailed scan instructions) and pass the contents in the task prompt along with the shared context.

### Shared context to pass to all three subagents:

```
Detected stack: <from Step 0>
Workspaces: <list or none>
Linter: <name + how to invoke, or "heuristic">
Tier: <full|bounded|sample>
Scope file list: <paths>

Intended Architecture summary:
<3-5 bullets from Step 1>

Findings format: structured JSON-like blocks. Do NOT format a final report — return raw findings only.

Each finding must include:
  dimension: structure | refactor | performance
  location: <path>:<line-range>
  title: <one-line>
  severity: low | medium | high
  certainty: 0.0–1.0
  effort_estimate: trivial | small | medium | large
  ccn_current: <int or null>
  ccn_projected: <int or null>
  respects_documented_decision: true | false
  recommended_refactor: <prose>
  cite_catalog_entry: <catalog ID, refactors only>
```

### Agent 1: arch-structure
Read `references/scan-structure.md`, then dispatch the `arch-structure` subagent with those instructions + shared context. Targets: cyclomatic/cognitive complexity hotspots, coupling, cohesion, layering violations, circular deps.

### Agent 2: arch-refactors
Read `references/scan-refactors.md` AND `references/refactor-catalog.md`, then dispatch the `arch-refactors` subagent with both + shared context. The catalog is mandatory context — every finding must cite a catalog entry by ID.

### Agent 3: arch-performance
Read `references/scan-performance.md`, then dispatch the `arch-performance` subagent with those instructions + shared context. Restricted to high-precision categories (N+1, sync I/O in async paths, accidental O(n²), missing memoization, hot-loop invariants). Other performance hunches are framed as "suspects to measure," not fixes.

---

## Step 5 — Consolidate, Filter, Score

After all three subagents return:

1. **Sanity gate (CCN delta)** — drop any finding where `ccn_projected >= ccn_current` (when both populated). This is guardrail #3: if the projected refactor doesn't reduce complexity, it's not a finding.
2. **Certainty gate** — drop findings with `certainty < 0.5` unless `severity = high`. Low-certainty noise is worse than missing edge findings.
3. **Deduplicate** — if two subagents report the same location, merge into one finding with both perspectives.
4. **Rank score** — `severity_weight × certainty / effort_weight` where severity {low: 1, medium: 2, high: 4} and effort {trivial: 1, small: 2, medium: 4, large: 8}.
5. **Group**:
   - **Quick wins** — top rank, effort ∈ {trivial, small}
   - **Strategic refactors** — high severity, effort ∈ {medium, large}
   - **Documented-decision conflicts** — `respects_documented_decision == false`, regardless of dimension. Separate section, requires user confirmation.
   - **Performance suspects** — `dimension == performance` AND `certainty < 0.7`. Framed as "measure, don't refactor blindly."

---

## Step 6 — Output

Read `references/report-template.md` for exact formatting. The shape:

1. **Architecture Map** (lightweight by default; full ASCII dep graph behind `--map`)
   - Detected layers (from Step 1) + observed file/dir tree alignment
   - Complexity heatmap: top 10 hotspots by current CCN with file:line and CCN value
2. **Findings** — three subsections (Structure / Refactors / Performance), each ordered by rank score with CCN delta column (`current → projected`, Δ)
3. **Documented-Decision Conflicts** — separate, prefixed with "**Confirm intent before action:**"
4. **Suggested Next Actions**
   - Skill chains: e.g. "If many `Unused module` candidates appeared, run `/code-cleanup` first and rerun this."
   - Copy-pasteable `/plan-feature <brief>` snippets for top 3 strategic refactors
5. **Footer** — disclosure: linter used (or "heuristic"), files scanned, files sampled vs skipped

---

## Step 7 — Mode-Specific Tail

### If `--plan` in $ARGUMENTS:
Read `references/plan-mode.md`. Transform the top quick-wins + strategic refactors into a phased brief. Each phase becomes a self-contained `/plan-feature <brief>` payload the user can drop directly into another session. Documented-decision conflicts become their own confirmation phase, ordered last.

### If `--fix` in $ARGUMENTS:
Read `references/fix-mode.md`. Walk findings whose `recommended_refactor` qualifies as **single-file, non-API-breaking** (extract method within file, guard-clause flatten, dedupe local helper, hoist invariant, replace inline conditional with table lookup *if* table stays in same file). Anything cross-file or API-touching is auto-routed to `--plan` instead.

For each qualifying finding:
1. Show the current snippet
2. Show the proposed diff
3. Wait for user approval (yes / no / skip)
4. Apply via `Edit` if approved
5. Move to next

End with:
> Done. Use `Esc Esc` or `/rewind` to undo any individual edit. Use `git branch -D <branch>` if you want to discard the whole pass.

---

## Step 8 — Closing

If running default mode, end with one line:
> Run `/architecture-review --plan` to convert top findings into a phased refactor brief, or `/architecture-review --fix` for in-place mechanical refactors. Run `/code-cleanup` first if dead-code findings appeared above the architectural ones.

---

## Quick Reference

| Want... | Use... |
|---------|--------|
| Per-commit / diff quality review | `/code-review` |
| Dead code, unused deps | `/code-cleanup` |
| Recent-change cleanup | `/simplify` |
| Pre-merge multi-agent verification | `/ultrareview` |
| **Repo-wide architecture + complexity audit** | **`/architecture-review` (this)** |
