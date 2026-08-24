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

**Apply `references/scan-exclusions.md` before anything else.** It is the canonical owner of what a
repo-wide scan must never read — synthetic/fixture trees, vendored and generated dirs, immutable
history — and it governs stack detection in Step 0 as well as file scope here. The fixture rule is
the one that matters: planted eval fixtures yield true-shaped findings that are false by
construction, and the run looks successful while producing them.

Compute the file lists once and pass them to subagents so all five see the same scope. Agents never
widen their own scope. Record what was excluded, sampled, and skipped — with counts — for the
report's footer; a reader cannot tell a clean codebase from a narrowed scan unless the scan says
which it was.

---

## Step 4 — Parallel Subagent Dispatch

Launch all five subagents in a single turn (one Agent tool call per agent). Mirror `/bx:clean` Step 1.

For each subagent, **read its corresponding reference file** (it contains the detailed scan instructions) and pass the contents in the task prompt along with the shared context.

**Pass reference files by absolute path, not by contents.** Each subagent has `Read`; instruct it to
read its scan file, `catalog-rules.md`, its own catalog, and `references/finding-rubrics.md` in full
before scanning, giving the absolute paths resolved against this skill's base directory. Inlining
the contents would require the orchestrator to hold ~95k chars to compose five prompts, for no gain
— the agent ends up with the same text either way.

`finding-rubrics.md` is the **`Scoring contract`** every agent must read: the canonical owner of the
severity / certainty / effort anchors and the two mandatory justification fields. Never paraphrase it
per-agent — five agents scoring against five paraphrases is the problem it exists to solve.

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

After all five subagents return. **Run these in the order given — the order is load-bearing**, and
each sub-step names what it consumes.

### 5.1 Sanity gate (complexity delta)

Applies to **any finding that claims a complexity reduction** — i.e. any finding returning a
non-null `ccn_*` or `cognitive_*` pair, whatever its dimension or catalog entry. `R01` and `R09`
are named below as illustrations, not as the only entries the gate covers. Drop it only when it reduces
*neither* metric: `ccn_projected >= ccn_current` **AND** `cognitive_projected >= cognitive_current`.
A finding that lowers either one survives.

This gate is dual-metric because the catalog reasons about both. `R01` (guard-clause flatten) and
`R09` (named predicate) state **"CCN direction: unchanged"** — they move cognitive load, not
decision-point count. A CCN-only gate deletes them before the report, which is exactly what it used
to do. Any entry whose CCN direction is "unchanged" **must** carry a cognitive delta; a finding
citing such an entry with no cognitive numbers is dropped as unsubstantiated, not passed through.

Findings with both pairs null are not claiming a complexity reduction and pass through untouched —
that is most robustness, design, and simplification findings. Simplification is gated instead on
`lines_deletable >= 1` (the subagent already enforces this).

### 5.2 Certainty gate

Drop findings with `certainty < 0.5` unless `severity = high` OR `lines_deletable >= 20`. Big
deletions earn a pass through the certainty filter so the user can review even uncertain large wins.

### 5.3 Rank score

**Computed before deduplication, because dedup needs it.**

```
rank = severity_weight × certainty × leverage / effort_weight
```

- severity {low: 1, medium: 2, high: 4}; effort {trivial: 1, small: 2, medium: 4, large: 8}
- The schema field is **`effort_estimate`**; `effort` anywhere in this step means that same field.
- **`leverage = 1 + churn_norm + fan_in_norm`** for the finding's file, both normalized 0..1
  across the scope (Step 3 computes them — see `references/scale-strategy.md`). A CCN-30 function
  nobody touches is not the problem; a CCN-15 function changed 40 times in 90 days and imported by
  30 modules is. Without this term the ranking treats a leaf utility and a load-bearing module
  identically, which is the difference between a linter's output and an architecture review's.
- Simplification findings are additionally multiplied by **`ln(lines_deletable + 1)`** — natural
  log, multiplicative — so big deletions float up.
- **Ties** break by, in order: **higher** severity, **higher** certainty, **lower** effort, then
  `location` string ascending. Ranking must be deterministic across runs.

### 5.4 Deduplicate

**Dedup targets the same *defect* reported twice — not two defects that happen to sit in the same
code.** Both conditions must hold:

1. **Same file, and line ranges that overlap or nest.** (Exact-string matching is not enough:
   `orders.ts:22` and `orders.ts:20-24` are one defect seen twice.)
2. **The same claim.** Either both cite the *same* `cite_catalog_entry`, or they cite a
   **known-overlapping pair** — the entries two scanners are expected to both find:

   | Pair | Why both fire |
   |------|---------------|
   | `R03` (flag argument) / `S03` (always-same parameter) | Same parameter, two framings |
   | `R12` (memoize recursion) / performance `missing memoization` | Same function |
   | `X01` (unbounded result set) / performance `payload size` | Same query |
   | `R07` (decompose god function) / structure `god function` | Same function, two scanners |

   Performance findings carry no `cite_catalog_entry` (the schema requires it only for refactor and
   simplification dimensions). Match those rows on the performance finding's **`category`** instead —
   the right-hand column above names it. A candidate pair where neither side has a catalog entry or a
   category never merges.

**Co-location is not duplication.** A god-function finding spanning `orders.ts:7-30` *contains* a
swallowed exception at `:22`, a race at `:16-19`, and a deletable null check at `:11` — four
different defects in one function. Merging them would erase three of them, zero a
`lines_deletable`, and empty the performance group. They stay four findings; what relates them is a
**theme**, which is exactly what 5.9 is for. If a rule here would collapse findings that a reader
would want listed separately, it is the wrong rule.

Merging is **not** discarding:

- The **higher-ranked** finding supplies `location`, `title`, and the scalar fields — severity,
  effort, dimension, complexity pairs.
- The lower-ranked one contributes its `title`, `evidence`, and `cite_catalog_entry` as an
  additional perspective on the merged finding.
- **`lines_deletable` is never inherited or zeroed** — the merged finding keeps the highest value
  any member reported. Merging must not destroy a deletion total.
- **Each perspective keeps its own `certainty`.** Dimension-keyed filters in 5.8 read the certainty
  *of the perspective they matched*, not the merged scalar — otherwise a certainty-0.5 performance
  suspect absorbed into a certainty-0.85 robustness finding stops being a suspect, which is the
  same disappearing act `merged_dimensions` exists to prevent.
- **Rank is not recomputed** after merging. The pre-merge rank of the surviving finding stands.
- Merges are pairwise and repeat to a fixed point: if A merges with B and B with C, the result is
  one finding — but only where each pair independently satisfies both conditions above.
- The merged finding carries **`merged_dimensions`** — every dimension and catalog family that went
  into it. **Every dimension-keyed filter downstream reads `merged_dimensions`, not `dimension`.**
  Without this, a performance suspect merged into a robustness finding silently vanishes from the
  "Performance suspects" group — a filter bug, not a judgment.
- A merged finding inherits the **highest** leverage among its members.

Common overlap: `arch-refactors` R03 (flag arg) and `arch-simplification` S03 (always-same param).

**Ordering note:** 5.1 and 5.2 run before this, so a finding dropped by a gate never reaches merge.
That is deliberate — a finding that substantiates nothing should not survive by attaching itself to
one that does — but it means that finding's perspective is lost. When a gate drops a finding sharing
a location with a survivor, record it in the footer's filtered list *with its location*, so the loss
is visible rather than silent.

### 5.5 Aggregate `lines_deletable`

Sum across the **post-5.4** findings reporting `lines_deletable > 0`. Track distinct files affected.
These are the top-line numbers in Section 1 of the report.

Running this after the merge is what prevents double counting: 5.4 keeps the *highest* value among a
merged finding's members rather than summing them, so two scanners reporting the same 12 deletable
lines contribute 12 here, not 24.

### 5.6 Collect suppressions and coverage negatives

Scanners return **`coverage_negatives`** — categories they swept and found genuinely empty, with the
evidence that makes the negative credible ("grepped `flock|lockfile|Mutex`: 0 hits"; "the only class
in scope is a single-method exception type"). These are **not findings**: they never rank, never
group, never enter a theme. Collect them for the footer.

A negative result is worth reporting — it separates a clean codebase from an unscanned one — but it
is not actionable, and a scanner with nowhere else to put it will encode it as a `severity: low`
finding with `recommended_refactor: "None"`, which then pollutes the ranked tables. If you receive
one in that shape, move it here rather than ranking it.

`arch-simplification` returns `s01_suppressed` (Dependency Inversion boundaries) and
`s06_suppressed` (trust boundaries) alongside its findings. These are *not* findings and never enter
ranking, but they are never silently discarded either: count them, keep their locations, and hand
them to the report footer. If the Intended Architecture summary was inferred rather than read from
docs, the footer must say so — suppression quality follows inference quality.

### 5.7 Validate the trust flags

Two subagent-declared fields are trusted by later steps, so check them against their own evidence
before using them:

- **`respects_documented_decision: true` whose `evidence` cites a documented decision the finding
  contradicts** — e.g. a `D03` finding whose evidence quotes the architecture doc naming that layer.
  The flag is unreliable; route the finding to **Documented-Decision Conflicts** for confirmation
  rather than treating it as clean. Never silently flip the flag.
- **A finding whose location also appears in that same scanner's `*_suppressed` list** — the scanner
  contradicted itself. Compare against the finding's **original** pre-merge location. Surface it under **Scanner Conflicts** with both of its own stated reasons.
- **`respects_documented_decision: false` whose `evidence` quotes no documented statement the
  *recommendation* would violate** — the flag is inverted. This is the common failure: a scanner
  marks `false` because the code appears to break something documented, when the correct reading is
  whether the **fix** collides with a stated intent (a finding that restores a documented goal is
  `true`). Treat the flag as `true` for grouping, and **say so in the report** — name the finding and
  the reason. Do not route it to Documented-Decision Conflicts on an unsubstantiated `false`;
  that group is exclusive, so an inverted flag silently removes a finding from every actionable list.
  **Sanity check:** if a scanner returned `false` on the majority of its findings, assume inversion
  and re-check every one.

### 5.8 Group

- **Quick wins** — every finding with effort ∈ {trivial, small}, ranked. **No cutoff** — the table
  is the complete list and the reader stops where they like. Silently truncating it would read as
  "that is all there was."
- **Strategic refactors** — severity high, effort ∈ {medium, large}
- **Documented-decision conflicts** — `respects_documented_decision == false`, plus anything 5.7
  routed here. Separate section, requires user confirmation. (Especially important for
  simplification: a documented "we keep this abstraction for X" must override a deletion.)
  **Exclusive:** a finding in this group appears *only* here, never also in Quick wins or Strategic
  refactors — it is not actionable until the user confirms intent.
- **Performance suspects** — `performance` ∈ `merged_dimensions` AND that perspective's own
  `certainty < 0.7` (see 5.4 — not the merged scalar). Framed as "measure, don't refactor blindly."
  Groups other than Documented-decision conflicts are **not** mutually exclusive: a finding may
  appear in both Quick wins and Performance suspects.
- **Scanner conflicts** — the same location where `arch-simplification` wants to delete a check and
  `arch-robustness` wants one added (S06 vs an `E` entry), plus the self-contradictions from 5.7.
  Both readings surface together; the orchestrator does **not** silently pick a winner. One of the
  two scanners missed a suppression, and which one is a judgment the user should see.

### 5.9 Synthesize themes

The report opens with a judgment, not a list.

**Count findings as they stand after 5.4** — a merged finding counts once. Because 5.4 only merges
genuine duplicates, co-located findings arrive here intact, which is what makes a
"one function concentrates six defects" cluster visible as a theme at all.

1. **Cluster** the surviving findings three ways — by shared module or directory prefix, by shared
   layer-boundary crossing (from Step 1), and by shared root mechanism (one concrete construct: a
   single client, a single function, a single shared object).
2. **A cluster qualifies as a theme by either path:**
   - **Cross-cutting** — ≥3 findings spanning **≥2 catalog families** (`R`, `S`, `D`, `C`, `E`, `X`).
     Count families, **not** the `dimension` field: C/E/X all carry `dimension: robustness`, so a
     dimension-based test would reject genuinely diverse robustness clusters.
   - **Single-mechanism** — ≥3 findings sharing **one concrete root cause**, where a single first
     move closes all of them. This path may be a single family: four `E` findings that are all "the
     shared HTTP client is unconfigured" is the strongest kind of theme, not a disqualified one.

   What neither path admits: a cluster that is merely *everything one scanner returned*, with no
   shared mechanism and no family diversity. That is a well-ranked table, not a theme.
3. **Overlapping clusters** — when one cluster is a subset of another, report only one. Choose by
   asking, for each member of the larger cluster, **whether the candidate first move plausibly
   remedies it** — not by member count. A directory-prefix cluster that picks up one extra finding
   the first move does not touch is *worse* than the tighter cluster, not better: the theme would
   claim coverage it does not have. Never report both, and never let one finding be evidence for two
   themes.

   The same closure test governs qualification: the **single-mechanism** path in rule 2 requires one
   first move to close every member. A cluster clearing only the **cross-cutting** path has no
   closure requirement — but if you cannot name a first move touching most of it, it is a weak theme
   and should not outrank one you can.
4. **Rank themes** by summed rank score of their members; take the **top 3**.
5. Each theme renders three things: a **one-sentence thesis** naming the structural cause, the
   **evidence set** (its member findings, by location), and the **single highest-leverage first
   move** — one action, not a list. Draw it from the `recommended_refactor` of the member that
   **most other members depend on** — the structural or root-cause finding, not necessarily the
   highest-ranked one. In a cluster where a god function contains a swallowed exception, decomposing
   the function is the first move even though the exception outranks it, because the decomposition
   is what makes the rest separately fixable. Where no member is foundational, use the
   highest-ranked member's. If none carries a `recommended_refactor`, synthesize from titles and
   evidence and say that you did.
6. **Findings in no theme are not dropped.** They render below, in the per-dimension tables, exactly
   as before. Theming reorganizes the top of the report; it never filters it.

**Notable pairs.** A cluster of exactly **2** findings sharing one concrete root mechanism does not
qualify as a theme and must not be promoted to one — but it is not nothing, and dropping it silently
loses a real cross-file pattern. Render it as a single line under the themes:
`**Notable pair:** <mechanism> — <location A>, <location B>.` Cap at three such lines, ranked by
summed rank score. Only genuine single-mechanism pairs qualify; two findings that merely share a
directory do not.

If fewer than 3 themes clear the bar, render the ones that do and say so. If none do, say
**"No cross-cutting themes — findings are independent"** and go straight to the tables. That is a
real and useful result: it means the codebase has local problems rather than a systemic one. Never
invent a theme to fill a slot.

---

## Step 6 — Output

Read `references/report-template.md` for exact formatting. The shape:

0. **The read** — the top 3 architectural themes from Step 5.9, each with its thesis, evidence set,
   and first move. This is the **first thing in the report**, before any metric or table. A
   quarterly architecture review's value is its point of view; the tables are the supporting
   material.
1. **Top-line metrics** — "Code we can delete: N lines across M files", complexity hotspot count,
   robustness findings by category (`C`/`E`/`X`), performance suspects to measure.
2. **Architecture Map** (lightweight by default; full ASCII dep graph behind `--map`)
   - Detected or inferred layers (from Step 1 / Step 5b) + observed file/dir tree alignment
   - Complexity heatmap: top 10 hotspots by `max(CCN, cognitive)`, both scores shown
3. **Findings** — six subsections in the template's order (Simplification first — deletion-first —
   then Robustness / Structure / Design / Refactors / Performance), each ordered by rank score.
   CCN **and** cognitive delta columns for refactors. `Lines Δ` for simplification. Category
   (`C`/`E`/`X`) for robustness.
4. **Documented-Decision Conflicts** — separate, prefixed with "**Confirm intent before action:**"
5. **Scanner Conflicts** — S06-vs-`E` collisions, both readings shown, unresolved by design
6. **Suggested Next Actions**
   - Skill chains: e.g. "If many `Unused module` candidates appeared, run `/bx:clean` first and rerun this."
   - Copy-pasteable `/bx:plan <brief>` snippets for the top 3 strategic refactors
7. **Footer** — disclosure: both complexity tools (or "heuristic"), files scanned, files sampled vs
   skipped, deletion totals, **suppression counts** (S01/S06 — mandatory even at zero), and any
   `catalog_gap_proposals` the scanners returned

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
