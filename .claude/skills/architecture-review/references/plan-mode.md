# --plan Mode

Transform the report's findings into a phased refactor brief that hands off cleanly to `/plan-feature` (or directly to TaskCreate). Each phase becomes a self-contained payload the user can drop into a fresh session.

## Phase grouping

After the report is built, group findings into phases:

1. **Phase 1: Quick wins**
   - All findings with `effort_estimate ∈ {trivial, small}` AND `respects_documented_decision: true`
   - **Simplification findings come first within this phase** — deletions are the highest-leverage edits (negative LOC, lower maintenance surface). Then trivial refactors.
   - Ordered within sub-buckets by rank score
   - Goal: low-risk, high-leverage edits a single follow-up session can knock out. Often a substantial chunk of `total_lines_deletable` lands here.

2. **Phase 2: Strategic refactors**
   - Findings with `effort_estimate ∈ {medium, large}` AND `respects_documented_decision: true` AND `severity ∈ {medium, high}`
   - Each finding becomes its own phase entry — these warrant a dedicated `/plan-feature` interview
   - Order by rank score

3. **Phase 3: Performance suspects**
   - All findings with `dimension == performance` AND `certainty < 0.7`
   - Frame the phase as: "Measure these before refactoring." Recommend profiler/benchmark setup as the first task.

4. **Phase 4: Documented-decision confirmations** (last)
   - Findings with `respects_documented_decision: false`
   - Frame as: "These conflict with documented decisions. Confirm intent before action."
   - Each requires user disambiguation; do not propose the refactor as the recommendation. Propose either *update the documented decision* or *honor the decision and dismiss the finding*.

## Output shape

Replace Section 4 of the standard report with:

```
## Phased Refactor Brief

### Phase 1 — Quick Wins (2 findings)

Low-effort, single-file, no API change. Recommended for a single follow-up session.

**1.1** R03 — Replace flag arg with two fns (`src/util/parse.ts:12-40`)
- Effort: small | CCN: 8 → 4
- Action: `/plan-feature` not needed; run `/architecture-review --fix` to apply mechanically.

**1.2** R08 — Hoist invariant out of loop (`src/api/middleware.ts:67`)
- Effort: trivial | CCN unchanged, performance gain
- Action: same as above.

Hand-off: `/architecture-review --fix` (will gate per finding).

---

### Phase 2 — Strategic Refactors (1 finding)

These require interviews and broader context. Each gets its own `/plan-feature` brief below.

**2.1** R07 — Decompose god function `handleRequest` (`src/api/handler.ts:45-180`)
- Severity: high | Effort: medium | CCN: 24 → 6 (Δ -18)

Hand-off:

\`\`\`
/plan-feature "Decompose handleRequest in src/api/handler.ts (currently 180 LOC, CCN 24) into 6 named steps per refactor catalog R07. Extract auth/validation/dispatch/persistence/response/error blocks into top-level functions in the same file. Maintain the existing function signature so callers don't change. Goal: parent CCN drops from 24 to ~6, each child stays under 8. Tests in src/api/handler.test.ts must still pass without modification."
\`\`\`

---

### Phase 3 — Performance Suspects (3 findings)

These are framed as suspects. **Measure first.**

Setup task before any of these:
\`\`\`
/plan-feature "Add a benchmark harness for the hot paths flagged in /architecture-review output. Use [stack-appropriate tool: vitest --bench / pytest-benchmark / criterion / hyperfine]. Establish baseline numbers before any optimization."
\`\`\`

Then per suspect:

**3.1** Possible N+1 in `src/users/list.ts:34` (certainty 0.65)
- After benchmark exists, /plan-feature: "..."

(... rest of suspects)

---

### Phase 4 — Documented-Decision Confirmations (1 finding)

These conflict with documented architecture decisions. **Confirm intent before action.**

**4.1** Split monolithic CLI (`src/cli/main.py:1-200`) — conflicts with ADR-0007 ("Monolith by choice")
- Action options:
  - **Honor the decision:** dismiss this finding. Add a comment in `src/cli/main.py` linking ADR-0007 so future scans see the deliberate choice.
  - **Update the decision:** if the rationale in ADR-0007 no longer holds, write ADR-0008 superseding it, then `/plan-feature` the split.

---
```

## Hand-off contract

Each `/plan-feature <brief>` snippet must:

- Be **fully self-contained** — quote file paths, line numbers, current/projected CCN, citation to catalog entry
- State the **invariant the refactor preserves** (function signature, public API, observable behavior)
- State the **success criterion** (CCN target, test status)
- Not assume the next session has any context from the architecture-review pass

This is what makes the hand-off useful — a fresh `/plan-feature` session has everything it needs in the brief.

## What this mode does NOT do

- Apply edits (use `--fix` for that)
- Spawn subagents to refine briefs (the brief is what gets handed off)
- Hydrate tasks directly (the user runs `/plan-feature` per brief, which then hydrates tasks via its own flow)
