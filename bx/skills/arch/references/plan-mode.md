# --plan Mode

ultrathink — phased briefs require synthesizing across six dimensions of subagent output (structure, design, refactors, simplification, robustness, performance) and sequencing for risk + leverage. Deep reasoning materially improves phase grouping and hand-off snippet quality.

Transform the report's findings into a phased refactor brief that hands off cleanly to `/bx:plan`. Each phase becomes a self-contained payload the user can drop into a fresh session.

**Hand-off target:** `/bx:plan` is the unconditional path — it owns its own task hydration, including what to do when the task tools are missing. Loading a phase straight into the task tracker (`TaskCreate`) is a *conditional* path: those tools are absent by default on current models. The rule lives in `../save/references/task-tools.md` — resolve it against **this skill's base directory** (`bx/skills/arch/`), not against this file's directory. Do not restate its version, model list, or env-var name here. When the tools are absent, hand the phase to `/bx:plan` or paste it into a fresh session.

## Phase grouping

After the report is built, group findings into phases:

1. **Phase 1: Quick wins**
   - All findings with `effort_estimate ∈ {trivial, small}` AND `respects_documented_decision: true`
   - **Simplification findings come first within this phase** — deletions are the highest-leverage edits (negative LOC, lower maintenance surface). Then trivial refactors.
   - Ordered within sub-buckets by rank score
   - Goal: low-risk, high-leverage edits a single follow-up session can knock out. Often a substantial chunk of `total_lines_deletable` lands here.

2. **Phase 2: Strategic refactors**
   - Findings with `effort_estimate ∈ {medium, large}` AND `respects_documented_decision: true` AND `severity ∈ {medium, high}`
   - Each finding becomes its own phase entry — these warrant a dedicated `/bx:plan` interview
   - Order by rank score

3. **Phase 3: Robustness**
   - All findings with `dimension == robustness`, ordered `E` → `C` → `X` within the phase.
   - These are **behavior changes, not refactors** — none was `--fix`-eligible, and each needs a
     test that reproduces the failure before the fix lands. Say so in the phase framing.
   - Group by shared root cause where the report's themes already did so: "configure the shared
     HTTP client" is one plan item that closes five findings, not five items.
   - `C` findings need a concurrency test (two callers racing) and `X` findings need a load or
     data-volume assumption stated explicitly in the brief — a scalability fix with no stated
     threshold cannot be verified.

4. **Phase 4: Design (D-entries)**
   - All findings with `dimension == design`. Each is cross-file and interface-touching, so each
     becomes its own `/bx:plan` brief.
   - The brief must carry the **change that becomes expensive** from the finding — that is the
     justification the next session needs, and without it a design refactor reads as taste.

5. **Phase 5: Performance suspects**
   - All findings with `dimension == performance` AND `certainty < 0.7`
   - Frame the phase as: "Measure these before refactoring." Recommend profiler/benchmark setup as the first task.

6. **Phase 6: Documented-decision confirmations** (last)
   - Findings with `respects_documented_decision: false`
   - Frame as: "These conflict with documented decisions. Confirm intent before action."
   - Each requires user disambiguation; do not propose the refactor as the recommendation. Propose either *update the documented decision* or *honor the decision and dismiss the finding*.

## Output shape

Replace Section 6 of the standard report with:

```
## Phased Refactor Brief

### Phase 1 — Quick Wins (2 findings)

Low-effort, single-file, no API change. Recommended for a single follow-up session.

**1.1** R03 — Replace flag arg with two fns (`src/util/parse.ts:12-40`)
- Effort: small | CCN: 8 → 4
- Action: `/bx:plan` not needed; run `/bx:arch --fix` to apply mechanically.

**1.2** R08 — Hoist invariant out of loop (`src/api/middleware.ts:67`)
- Effort: trivial | CCN unchanged, performance gain
- Action: same as above.

Hand-off: `/bx:arch --fix` (will gate per finding).

---

### Phase 2 — Strategic Refactors (1 finding)

These require interviews and broader context. Each gets its own `/bx:plan` brief below.

**2.1** R07 — Decompose god function `handleRequest` (`src/api/handler.ts:45-180`)
- Severity: high | Effort: medium | CCN: 24 → 6 (Δ -18)

Hand-off:

\`\`\`
/bx:plan "Decompose handleRequest in src/api/handler.ts (currently 180 LOC, CCN 24) into 6 named steps per refactor catalog R07. Extract auth/validation/dispatch/persistence/response/error blocks into top-level functions in the same file. Maintain the existing function signature so callers don't change. Goal: parent CCN drops from 24 to ~6, each child stays under 8. Tests in src/api/handler.test.ts must still pass without modification."
\`\`\`

---

### Phase 3 — Robustness (6 findings)

**Behavior changes, not refactors.** None of these was `--fix`-eligible. Each needs a test that
reproduces the failure *before* the fix lands.

Grouped by root cause where the report's themes already found one:

**3.1** E03 ×2 + E04 + X06 — the shared HTTP client is unconfigured (`src/lib/http.ts:4`)
- Severity: high | Effort: small | closes 4 findings at one site

\`\`\`
/bx:plan "src/lib/http.ts:4 constructs a shared axios instance with no timeout, no retry policy, and is re-created per request in 2 call sites. Configure a default timeout and bounded retry with jitter on the single instance; hoist construction to module scope. Findings closed: E03 at src/api/orders.ts:88 and src/api/users.ts:40, E04 at src/payments/charge.ts:88, X06 at src/lib/http.ts:22. Add a test that asserts the client rejects after the configured timeout using a stalled server. Invariant: no call-site signatures change."
\`\`\`

**3.2** C02 — check-then-fill race on the shared cache (`src/cache/warm.ts:22`)
- Severity: high | Effort: small | needs a concurrency test (two callers racing)

---

### Phase 4 — Design (2 findings)

Each is cross-file and interface-touching, so each gets its own brief. The brief must carry **the
change that becomes expensive** — without it a design refactor reads as taste.

**4.1** D03 — domain imports the Prisma client directly (`src/domain/pricing.ts:8`)
- Severity: high | Effort: medium
- Cost today: pricing rules cannot be tested without a database, and the ORM's types have
  propagated into three domain signatures.

---

### Phase 5 — Performance Suspects (3 findings)

These are framed as suspects. **Measure first.**

Setup task before any of these:
\`\`\`
/bx:plan "Add a benchmark harness for the hot paths flagged in /bx:arch output. Use [stack-appropriate tool: vitest --bench / pytest-benchmark / criterion / hyperfine]. Establish baseline numbers before any optimization."
\`\`\`

Then per suspect:

**5.1** Possible N+1 in `src/users/list.ts:34` (certainty 0.65)
- After benchmark exists, /bx:plan: "..."

(... rest of suspects)

---

### Phase 6 — Documented-Decision Confirmations (1 finding)

These conflict with documented architecture decisions. **Confirm intent before action.**

**6.1** Split monolithic CLI (`src/cli/main.py:1-200`) — conflicts with ADR-0007 ("Monolith by choice")
- Action options:
  - **Honor the decision:** dismiss this finding. Add a comment in `src/cli/main.py` linking ADR-0007 so future scans see the deliberate choice.
  - **Update the decision:** if the rationale in ADR-0007 no longer holds, write ADR-0008 superseding it, then `/bx:plan` the split.

---
```

## Hand-off contract

Each `/bx:plan <brief>` snippet must:

- Be **fully self-contained** — quote file paths, line numbers, current/projected complexity (both metrics), citation to catalog entry
- For robustness briefs, state **the failure being prevented** and the test that reproduces it — a fix with no failing test to prove it is unverifiable
- State the **invariant the refactor preserves** (function signature, public API, observable behavior)
- State the **success criterion** (CCN target, test status)
- Not assume the next session has any context from the bx:arch pass

This is what makes the hand-off useful — a fresh `/bx:plan` session has everything it needs in the brief.

## What this mode does NOT do

- Apply edits (use `--fix` for that)
- Spawn subagents to refine briefs (the brief is what gets handed off)
- Hydrate tasks directly (the user runs `/bx:plan` per brief, which then hydrates tasks via its own flow)
