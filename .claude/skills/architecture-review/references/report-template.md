# Report Template

Render the final report exactly in this order. Every section appears even if empty (with "None found" as content) so the output structure is predictable across runs.

## Section 1 — Architecture Map

Default (lightweight):

```
## Architecture Map

**Intended architecture** (from CLAUDE.md / README / ADRs):
- <bullet 1>
- <bullet 2>
- ...

**Detected layout:**
<top-level dir tree, 2 levels deep>

**Complexity heatmap (top 10 by CCN):**

| File:Line                   | Function           | CCN | LOC |
|-----------------------------|--------------------|-----|-----|
| src/api/handler.ts:45       | handleRequest      | 24  | 180 |
| ...                         | ...                | ... | ... |
```

If `--map` flag is set, additionally render an ASCII module-dep sketch (one node per top-level module, edges for imports). Skip if >15 top-level modules — it becomes unreadable.

## Section 2 — Findings

Three subsections, in order: **Structure**, **Refactors**, **Performance**. Each subsection is a table:

```
### Refactors

| Rank | Location                    | Title                          | Sev | Cert | Effort | CCN  Δ          | Catalog |
|------|-----------------------------|--------------------------------|-----|------|--------|------------------|---------|
| 1    | src/api/handler.ts:45-180   | Decompose god function         | H   | 0.85 | medium | 24 → 6 (Δ -18)   | R07     |
| 2    | src/util/parse.ts:12-40     | Replace flag arg with two fns  | M   | 0.9  | small  | 8 → 4 (Δ -4)     | R03     |
| ...  | ...                         | ...                            | ... | ...  | ...    | ...              | ...     |
```

For Performance, replace the `Catalog` column with `Category` (e.g. `N+1`, `O(n²)`, `Hot-loop invariant`) and add a `Suspect?` column (Y/N). Suspects are findings with `certainty < 0.7`.

For Structure, drop the `Catalog` column.

Below each table, render a "Top finding detail" block expanding the #1 ranked finding:

```
**#1 — Decompose god function (`src/api/handler.ts:45-180`)**

Current state: 180-line `handleRequest` with CCN 24 across 6 distinct concerns (auth check, validation, dispatch, persistence, response shaping, error handling).

Recommendation: extract each concern to a helper function (apply R07). Top-level reads as 6 calls. Per-function CCN drops to 3-6.

Conflict with documented decision? No.
```

Only render the detail block for #1 of each subsection — the table covers the rest.

## Section 3 — Documented-Decision Conflicts

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

## Section 4 — Suggested Next Actions

```
## Suggested Next Actions

**Skill chains:**
- <e.g. "Run `/code-cleanup` first — 4 unused-module candidates appeared above the architectural findings.">
- <e.g. "Run `/code-review src/api/handler.ts` for diff-level quality on the top hotspot before refactoring.">

**Top strategic refactors (copy-paste into a fresh session):**

```bash
/plan-feature "Decompose handleRequest in src/api/handler.ts (currently 180 LOC, CCN 24) into 6 named steps per refactor catalog R07. Extract auth/validation/dispatch/persistence/response/error blocks into top-level functions. Goal: parent CCN drops from 24 to ~6, each child stays under 8."
```

```bash
/plan-feature "..."
```
```

If `--plan` flag is set, this section is replaced by the full phased brief (see `plan-mode.md`).
If `--fix` flag is set, this section is replaced by the per-finding gate flow (see `fix-mode.md`).

## Footer — Disclosure

```
---

Linter: eslint (with `complexity` rule, threshold 10)  [or: heuristic Grep-based]
Files in scope: 312
Files sampled: 50 (priority-ranked by LOC × churn × fan-in)
Files via drill-down: 18
Files skipped: 244

Top skipped (low priority): src/types/__generated__/*.ts, src/migrations/*.sql, ...

Findings filtered:
- Dropped 7 findings where projected CCN ≥ current CCN (sanity gate)
- Dropped 4 findings with certainty < 0.5 and severity != high
```
