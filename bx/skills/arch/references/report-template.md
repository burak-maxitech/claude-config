# Report Template

Render the final report exactly in this order. Every section appears even if empty (with "None found" as content) so the output structure is predictable across runs.

## What this template consumes

Step 5 hands you a consolidated result. **This template renders it — it never re-derives it.**
If a field below is missing from the input, that is a bug in Step 5; render the affected cell as
`unknown` and note it in the footer. Do not recompute it yourself, and do not go read source files
to fill it in.

Per finding: `location`, `title`, `dimension`, `merged_dimensions`, `severity`, `certainty`,
`effort_estimate`, `rank`, `evidence`, `why_this_might_be_wrong`, `recommended_refactor`,
`respects_documented_decision`, `cite_catalog_entry` (absent on structure findings),
`lines_deletable`, the `ccn_*` / `cognitive_*` pairs (null where complexity is not the signal),
`category` (performance) or catalog family (robustness), and `theme` (absent means none).

Also: the theme list from Step 5.9, the group memberships from Step 5.8, the suppression lists
from Step 5.6, `catalog_gap_proposals`, aggregate deletion totals, the complexity heatmap, the
scope/tier/sampling counts, which complexity tool ran for each metric, whether the Intended
Architecture summary was **read or inferred**, and which of `--map` / `--plan` / `--fix` are set.

**Themes arrive already qualified.** Step 5.9 decided what is and is not a theme. Render exactly
the themes you were given, in the order given, numbered `1`/`2`/`3` — and label them `T1`/`T2`/`T3`
in that same render order, regardless of any identifier the input used. Never re-test a theme
against the qualification rule, never promote a cluster the input did not name, never drop one it
did.

## Where each Step 5.8 group renders

Step 5.8 hands you five groups. Every one has a destination; none is dropped.

| Group | Renders as |
|-------|-----------|
| Quick wins | Section 6, as a **Quick wins** list — location, title, effort, and the one-line action. This is the section's first block, above the strategic briefs. |
| Strategic refactors | Section 6's `/bx:plan` snippets, one per member, top 3 by rank |
| Documented-decision conflicts | Section 4 |
| Performance suspects | The Performance subsection of Section 3, with `Suspect? = Y` |
| Scanner conflicts | Section 5 |

**Section 6 is the one place you compose rather than transcribe.** The "render, never re-derive"
rule governs *findings data* — you must not recompute a finding's fields. Writing the skill-chain
bullets and the `/bx:plan` brief prose from the findings you were given is this section's job.

## Merged findings

A finding with more than one entry in `merged_dimensions` was two scanners' reports of one defect.
Render the primary row from the surviving finding's fields, then add **one line directly under the
detail block** naming the other perspective, its catalog entry, and its own certainty:

> Also reported by `arch-performance` as "Possible large payload serialization" (category `payload`,
> certainty 0.50) — counted as a performance suspect.

The secondary perspective still drives its own group membership (Step 5.4 keeps each perspective's
certainty for exactly this reason), so a merged finding can appear as a Performance suspect while
its primary row sits under Robustness.

## Global rendering rules

These apply to every section; sections below do not restate them.

- **`Rank` column** is the **ordinal position** within its table (1, 2, 3…), not the raw score.
  Sort by the raw score; never print it.
- **`Sev` column** abbreviates: `high` → `H`, `medium` → `M`, `low` → `L`. `Cert` prints two
  decimals.
- **Section headings** render as bare titles — `## Architecture Map`, `## Findings` — never with a
  "Section N —" prefix. The numbering in this file orders the sections; it is not output text.
- **`---` separators** are reproduced only where they appear inside a fenced example, never inserted
  between sections.
- **Fixed boilerplate is not customized.** The Architecture Map's "(from CLAUDE.md / README / ADRs)"
  is a label, not a claim about which file was read; the footer states the actual source.

- **Headings.** Every section renders its own `##` heading, including the ones whose examples below
  show only body content: `## Top-line Metrics`, `## Findings`, `## Disclosure` (the footer).
- **Empty counts.** Substitute the literal number, including `0` — except the deletion line, which
  has a defined prose alternate (see Section 1). Fix the grammar when a count is 1 ("1 finding",
  not "1 findings").
- **Empty sections.** Render the heading and `None found.` as the body. Two exceptions, both stated
  at their section: Section 5 is omitted entirely when empty; Section 4 always renders.
- **Complexity hotspot count** (Section 1) = functions with CCN > 10 **or** cognitive > 15 — the
  same thresholds `scan-structure.md` uses. Do not invent a different one.
- **Theme column.** Every findings table in Section 3 carries it, including the tables whose
  examples below predate it. Value is `T1`/`T2`/`T3` or blank.
- **Detail block.** Render one below **every** subsection table, expanding that subsection's #1
  finding. Use the generic Current state / Recommendation / Conflict shape, except Robustness and
  Design, which have their own shapes shown at their tables. Never render more than one per
  subsection.
- **Evidence citations** (Section 0) are `` `location` (ID) `` where ID is `cite_catalog_entry` when
  the finding has one and the dimension name otherwise (structure findings carry no catalog ID).
  Order them by rank, descending.
- **Ties and ordering.** Every table sorts by `rank` descending. Step 5.3 already broke ties
  deterministically — preserve the order you were given rather than re-sorting.

## Section 0 — The Read (top 3 architectural themes)

Render this **first, before any metric or table.** A quarterly architecture review's value is its
point of view; everything below is supporting material. Themes come from Step 5.9, which admits a
cluster by either of two paths: **cross-cutting** (≥3 findings spanning ≥2 catalog families) or
**single-mechanism** (≥3 findings sharing one concrete root cause that a single first move closes).
Count catalog families, never the `dimension` field — C/E/X all carry `dimension: robustness`.

```
## /bx:arch — <project name>

### The read

**1. <One-sentence thesis naming the structural cause.>**
<2-3 sentences: what pattern the evidence shows, and what it costs — the change that has become
expensive, the failure that has become likely.>

*Evidence (6 findings):* `src/api/orders.ts:88` (E03) · `src/api/users.ts:40` (E03) ·
`src/lib/http.ts:4` (C01) · `src/api/refunds.ts:12` (E01) · `src/api/orders.ts:130` (E07) ·
`src/lib/http.ts:22` (X06)

*First move:* Configure a timeout and a retry policy on the single shared axios instance in
`src/lib/http.ts` — five of the six findings resolve there.

**2. <thesis>** …

**3. <thesis>** …
```

Rules:

- **One first move per theme, not a list.** If you cannot name a single highest-leverage action,
  the theme is not coherent enough to lead the report.
- The thesis names a **cause**, not a category. "Error handling is inconsistent" is a category.
  "Every outbound call inherits an unconfigured shared HTTP client" is a cause.
- **Fewer than 3 qualifying themes:** render those that qualify and say so — "only 2 themes
  cleared the bar (cross-cutting or single-mechanism)."
- **No qualifying themes:** render
  `**No cross-cutting themes** — findings are independent; see the tables below.` This is a real
  result, not a failure: it means the codebase has local problems rather than a systemic one.
- Never invent a theme to fill the third slot.

---

## Section 1 — Top-line Metrics

```
**Code we can delete: <total_lines_deletable> lines across <files_affected> files.**
**Complexity hotspots: <count> functions above threshold (cyclomatic or cognitive).**
**Robustness: <n> concurrency · <n> error-safety · <n> scalability findings.**
**Performance suspects to measure: <count> findings.**
```

The deletion line uses bold to make it impossible to miss. Numbers come from Step 5 aggregation. If `total_lines_deletable == 0`, render the line as "**No over-engineering / almost-dead code detected** — this codebase is already lean." instead.

---

## Section 2 — Architecture Map

Default (lightweight):

```
## Architecture Map

**Intended architecture** (from CLAUDE.md / README / ADRs):
- <bullet 1>
- <bullet 2>
- ...

**Detected layout:**
<top-level dir tree, 2 levels deep>

**Complexity heatmap (top 10 by max(CCN, cognitive)):**

| File:Line                   | Function           | CCN | Cog | LOC |
|-----------------------------|--------------------|-----|-----|-----|
| src/api/handler.ts:45       | handleRequest      | 24  | 41  | 180 |
| src/billing/apply.ts:12     | applyDiscounts     | 8   | 28  | 64  |
| ...                         | ...                | ... | ... | ... |
```

Rank by `max(CCN, cognitive)`, not CCN. The second row above is the case a CCN-only heatmap
misses entirely: modest decision-point count, deeply nested — the exact shape R01 and R09 target.

If `--map` flag is set, additionally render an ASCII module-dep sketch (one node per top-level module, edges for imports). Skip if >15 top-level modules — it becomes unreadable.

## Section 3 — Findings

Six subsections, in order: **Simplification** (deletion-first, surfaced highest), **Robustness**, **Structure**, **Design**, **Refactors**, **Performance**. Each subsection is a table.

**Findings that belong to a Section 0 theme are still listed here**, with a `Theme` column marking
which one (`T1`/`T2`/`T3`, blank if none). The tables are the complete record; Section 0 is the
reading of it. Nothing is dropped, truncated, or moved out of its dimension.

```
### Refactors

| Rank | Location                    | Title                          | Sev | Cert | Effort | CCN Δ          | Cog Δ          | Catalog |
|------|-----------------------------|--------------------------------|-----|------|--------|----------------|----------------|---------|
| 1    | src/api/handler.ts:45-180   | Decompose god function         | H   | 0.85 | medium | 24 → 6 (-18)   | 41 → 9 (-32)   | R07     |
| 2    | src/util/parse.ts:12-40     | Replace flag arg with two fns  | M   | 0.9  | small  | 8 → 4 (-4)     | 11 → 5 (-6)    | R03     |
| 3    | src/auth/verify.ts:30-72    | Flatten nested ladder          | M   | 0.9  | small  | 9 → 9 (0)      | 26 → 11 (-15)  | R01     |
| ...  | ...                         | ...                            | ... | ...  | ...    | ...            | ...            | ...     |
```

Both delta columns are always rendered. Row 3 is the shape the old CCN-only gate deleted before
it could reach the report: flat CCN, large cognitive win.

For **Performance**, use the Refactors columns with `Catalog` replaced by `Category` (e.g. `N+1`,
`O(n²)`, `Hot-loop invariant`), a `Suspect?` column (Y/N) added, and **both complexity-delta columns
dropped** — performance findings do not carry them. Suspects are findings with `certainty < 0.7`.

For **Structure**, use the Refactors columns with `Catalog` dropped and both complexity-delta
columns kept — structure findings are the ones that most often carry them:

```
### Structure

| Rank | Location                  | Title                    | Sev | Cert | Effort | CCN Δ       | Cog Δ        | Theme |
|------|---------------------------|--------------------------|-----|------|--------|-------------|--------------|-------|
| 1    | src/api/orders.ts:7-30    | God function createOrder | H   | 0.90 | medium | 12 → 5 (-7) | 29 → 8 (-21) | T2    |
```

For **Simplification**, replace `CCN Δ` with `Lines Δ`, sort primarily by `lines_deletable × certainty` (deletion impact), and use this column ordering — `Catalog` last because S-IDs are short:

```
### Simplification (— lines deletable: <subtotal>)

| Rank | Location                            | Title                                    | Sev | Cert | Effort | Lines Δ | Catalog |
|------|-------------------------------------|------------------------------------------|-----|------|--------|---------|---------|
| 1    | src/services/PaymentProvider.ts:1-12| Inline single-impl interface             | M   | 0.9  | small  | -12     | S01     |
| 2    | src/util/withRetry.ts:5-18          | Pass-through wrapper around fetch        | M   | 0.85 | small  | -14     | S02     |
| ...  | ...                                 | ...                                      | ... | ...  | ...    | ...     | ...     |
```

Below each table, render a "Top finding detail" block expanding the #1 ranked finding:

```
**#1 — Decompose god function (`src/api/handler.ts:45-180`)**

Current state: 180-line `handleRequest` with CCN 24 across 6 distinct concerns (auth check, validation, dispatch, persistence, response shaping, error handling).

Recommendation: extract each concern to a helper function (apply R07). Top-level reads as 6 calls. Per-function CCN drops to 3-6.

Conflict with documented decision? No.
```

Only render the detail block for #1 of each subsection — the table covers the rest.

### Robustness

| Rank | Location                    | Title                                   | Sev | Cert | Effort | Cat | Entry | Theme |
|------|-----------------------------|-----------------------------------------|-----|------|--------|-----|-------|-------|
| 1    | src/payments/charge.ts:88   | Provider call has no timeout            | H   | 0.90 | trivial| E   | E03   | T1    |
| 2    | src/cache/warm.ts:22        | Check-then-fill race on shared cache    | H   | 0.75 | small  | C   | C02   |       |
| 3    | src/reports/export.ts:14    | Unbounded result set streamed to client | M   | 0.80 | medium | X   | X01   |       |

`Cat` is the catalog family: `C` concurrency · `E` error safety · `X` scalability. Robustness
findings never carry complexity deltas and are never `--fix`-eligible — they route to `--plan`.

The "Top finding detail" block for this subsection must state **the failure**, not the rule:

```
**#1 — Provider call has no timeout (`src/payments/charge.ts:88`)**

The shared axios instance in `src/lib/http.ts:4` is constructed with no `timeout`, so this call
waits indefinitely. If the provider hangs, each in-flight charge holds a connection until the pool
is exhausted and unrelated endpoints begin failing.

Evidence: traced `http` to src/lib/http.ts:4 — `axios.create({ baseURL })`, no timeout key.
Grepped `timeout` in src/lib/: 0 hits. 3 other call sites share the instance.

Might be wrong if: the deployment sets a proxy-level timeout shorter than the pool's idle limit.

Conflict with documented decision? No.
```

### Design

| Rank | Location                        | Title                                  | Sev | Cert | Effort | Entry | Theme |
|------|---------------------------------|----------------------------------------|-----|------|--------|-------|-------|
| 1    | src/domain/Order.ts:1-40        | Anemic domain model — rules in service | M   | 0.75 | large  | D05   | T2    |
| 2    | src/domain/pricing.ts:8         | Domain imports Prisma client directly  | H   | 0.85 | medium | D03   | T2    |

Design findings carry no complexity delta and are never `--fix`-eligible. Each must name **the
change that becomes expensive**, not the principle that is bent.

Design's detail block uses the Robustness shape, with the cost sentence in place of the failure
sentence:

```
**#1 — Domain imports PrismaClient directly (`src/domain/pricing.ts:1-3`)**

Pricing rules cannot be tested without a database, and the ORM's types have propagated into three
domain signatures. Every rule added on top inherits the coupling.

Evidence: line 1 imports @prisma/client; docs/architecture.md states domain must not import
infrastructure.

Might be wrong if: this is a type-only import.

Conflict with documented decision? Yes — docs/architecture.md, "domain must not import infrastructure".
```

---

## Section 4 — Documented-Decision Conflicts

If any findings have `respects_documented_decision: false`:

```
## ⚠ Documented-Decision Conflicts

**Confirm intent before action.** These findings recommend changes that conflict with documented architecture decisions.

| Location                | Finding                              | Documented decision conflicting       |
|-------------------------|--------------------------------------|---------------------------------------|
| src/cli/main.py:1-200   | Split monolithic CLI into modules    | "Monolith by choice — see ADR-0007"   |
| ...                     | ...                                  | ...                                   |
```

If empty, render `## ⚠ Documented-Decision Conflicts\n\nNone — all findings respect documented architecture decisions.`

## Section 5 — Scanner Conflicts

Rendered only when Step 5.8 handed you a scanner-conflict group. **"Same location" was already
decided in Step 5.4** (same file, overlapping or nested line ranges) — do not re-test it with a
stricter or looser rule here. The group also contains the self-contradictions Step 5.7 routed in
(a scanner that both flagged and suppressed the same location).

```
## ⚠ Scanner Conflicts

Two scanners reached opposite conclusions about the same code. One of them missed a suppression;
which one is a judgment call, so both readings are shown unresolved.

| Location            | Simplification says          | Robustness says                     |
|---------------------|------------------------------|-------------------------------------|
| src/api/parse.ts:31 | S06 — type proves non-null   | E01 — input crosses a trust boundary |
```

If empty, omit the section entirely (unlike Section 4, which always renders).

## Section 6 — Suggested Next Actions

```
## Suggested Next Actions

**Skill chains:**
- <e.g. "Run `/bx:clean` first — 4 unused-module candidates appeared above the architectural findings.">
- <e.g. "Run `/code-review src/api/handler.ts` for diff-level quality on the top hotspot before refactoring.">

**Top strategic refactors (copy-paste into a fresh session):**

```bash
/bx:plan "Decompose handleRequest in src/api/handler.ts (currently 180 LOC, CCN 24) into 6 named steps per refactor catalog R07. Extract auth/validation/dispatch/persistence/response/error blocks into top-level functions. Goal: parent CCN drops from 24 to ~6, each child stays under 8."
```

```bash
/bx:plan "..."
```
```

If `--plan` flag is set, this section is replaced by the full phased brief (see `plan-mode.md`).
If `--fix` flag is set, this section is replaced by the per-finding gate flow (see `fix-mode.md`).

## Footer — Disclosure

```
---

Cyclomatic complexity: eslint (`complexity` rule, threshold 10)   [or: radon | ruff | lizard | heuristic Grep-based]
Cognitive complexity: heuristic (nesting-weighted)                [or: eslint-plugin-sonarjs]
Files in scope: 312
Files sampled: 50 (priority-ranked by LOC × churn × fan-in)
Files via drill-down: 18
Files skipped: 244

Top skipped (low priority): src/types/__generated__/*.ts, src/migrations/*.sql, ...

[On the `full` or `bounded` tier nothing is sampled. Render instead:
 Files in scope: 7
 Files read: 7 (full tier — no sampling applied)
 Files skipped: 0]

Deletion totals (from Simplification dimension):
- total_lines_deletable: 184
- files_affected: 22
- breakdown by category: S01 (5 findings, 78 lines), S02 (3 findings, 42 lines), S06 (8 findings, 45 lines), ...

Catalog gap proposals (from scanners, for review — not findings):
- arch-refactors: "repeated manual null-coalescing chain", 7 occurrences, proposed R15.
- (render `none` when no scanner returned any)

Findings filtered:
- Dropped 7 refactor findings that reduced neither cyclomatic nor cognitive complexity (sanity gate)
- Dropped 4 findings with certainty < 0.5 and severity != high (and lines_deletable < 20)

Suppressed by design (not findings — disclosed so the coverage is honest):
- S01 × 3 at Dependency Inversion boundaries: src/ports/PaymentGateway.ts, src/ports/Clock.ts,
  src/ports/EventBus.ts — one implementation is the expected shape of a port.
- S06 × 5 at trust boundaries: 3 × request handler, 1 × JSON deserialization, 1 × env read.
- Intended Architecture summary was read from docs/architecture.md.
  [or: **was inferred from directory structure** — suppression accuracy follows inference accuracy;
   re-run after documenting the layering if these counts look wrong.]
```

The suppression block is **mandatory even when both counts are zero** (render
`Suppressed by design: none.`). A reader cannot tell a clean codebase from a silently narrowed
scan unless the skill says which one it is. When one count is zero and the other is not, render
both lines — `S06 × 0` is information, not noise.

`breakdown by category` renders `none` when no simplification finding survived.
