# --plan Mode (bx:tests)

ultrathink — sequencing coverage gaps, T01-T05 rewrites, and economics findings into a coherent phased plan benefits from deep reasoning. Each phase boundary is a judgment call (provably-safe deletions vs. judgment-required rewrites vs. coverage fills).

Transform the report's findings into a phased rewrite/fill brief that hands off cleanly to `/bx:plan`. Each phase becomes a self-contained payload the user can drop into a fresh session.

The shape mirrors `bx:arch/references/plan-mode.md` but the phases and hand-off snippets are test-specific.

## Phase grouping

After the report is built, group findings into phases:

1. **Phase 1: Quick wins (deletions)**
   - All findings with `effort_estimate ∈ {trivial, small}` AND `respects_documented_decision: true` AND `deletable_lines > 0`
   - Ordered: T01 first (provably safe), then snapshot_heavy (largest deletions earn the leverage), then qualifying T05
   - **Hand-off:** these go straight to `/bx:tests --fix` for T01s, or a one-shot rewrite session for snapshot_heavy / T05.

2. **Phase 2: Coverage gaps on critical paths**
   - All findings with `dimension == coverage` AND `respects_documented_decision: true`
   - Ordered by `priority_score × certainty`
   - **Hand-off:** one `/bx:plan` brief per high-priority gap; the high-rank gaps deserve dedicated test-writing sessions.

3. **Phase 3: Strategic rewrites (T02/T03/T04)**
   - Findings with `dimension == quality` AND `smell_id ∈ {T02, T03, T04}` AND `respects_documented_decision: true`
   - Order by rank score
   - **Hand-off:** these need human judgment about *what* to assert / how to decouple from mocks / how to make fixtures explicit. One `/bx:plan` per finding or per cluster.

4. **Phase 4: Suspects to measure**
   - Findings with `economic_signal ∈ {flakiness_marker, flakiness_history}` (always suspects — don't delete flaky tests blindly)
   - Findings with `economic_signal ∈ {ratio_over, ratio_under}` (signal, not prescription)
   - Frame the phase: "Investigate root cause before any rewrite/delete."

5. **Phase 5: Documented-decision confirmations** (last)
   - Findings with `respects_documented_decision: false`
   - Frame as: "These conflict with documented testing posture. Confirm intent before action."
   - For each: propose either *update the documented decision* or *honor it and dismiss the finding*. Do NOT propose the rewrite as the default action.

## Output shape

Replace Section 4 of the standard report with:

```
## Phased Rewrite / Fill Brief

### Phase 1 — Quick Wins (deletions, N findings, -<deletable_total> LOC)

Low-risk, high-leverage. Run a single follow-up session.

**1.1** T01 — Assertion-free test (`tests/auth/login.test.ts:142-156`)
- Effort: trivial | Lines Δ: -14
- Action: run `/bx:tests --fix` to delete after diff preview.

**1.2** snapshot_heavy — `tests/components/Page.test.tsx` (82% snapshot)
- Effort: small | Lines Δ: -705
- Action:
\`\`\`
/bx:plan "Convert tests/components/Page.test.tsx from a single bulk toMatchSnapshot to 3 focused property assertions: title, child count, aria-attributes. Delete the __snapshots__/Page.test.tsx.snap file. Behavior coverage stays the same; LOC drops by ~705."
\`\`\`

Hand-off for T01s: `/bx:tests --fix` (per-finding gate).

---

### Phase 2 — Coverage Gaps on Critical Paths (N findings)

High-priority uncovered code, ordered by blast radius.

**2.1** No test coverage on `verifySession` (`src/auth/verifySession.ts:14-62`)
- Priority: 14.2 | Effort: small | Gap: 48 LOC

Hand-off:
\`\`\`
/bx:plan "Add unit tests for verifySession in src/auth/verifySession.ts (48 LOC, priority 14.2, security_density 0.18, fan_in 9). Cover: valid happy path, expired session, tampered token, missing session header, malformed session payload. Use existing test conventions from the codebase. Place the new test file at src/auth/verifySession.test.ts. Aim for 100% branch coverage on this file; the orchestrator-level coverage target stays as-is."
\`\`\`

(... more entries ...)

---

### Phase 3 — Strategic Rewrites (T02/T03/T04, N findings)

These require interview-level context: what should be asserted, how to decouple from mocks, how to surface mystery-guest dependencies.

**3.1** T03 — Mock-heavy test in `tests/api/users.test.ts:80-220`
- Severity: medium | Effort: medium
- Impl/behavior ratio: 5:1

Hand-off:
\`\`\`
/bx:plan "Rewrite tests/api/users.test.ts to verify observable behavior instead of mock interactions. Currently: 16 toHaveBeenCalledWith assertions across 3 tests, no return-value/state assertions. Goal: keep mocks ONLY at the HTTP boundary (msw); assert on returned data shapes, persisted DB state (in-memory adapter), and response status codes. Mock setup lives in test/setup.ts (do not duplicate). Keep test names as-is so coverage attribution doesn't shift."
\`\`\`

---

### Phase 4 — Suspects to Measure (N findings)

These signals point at issues, but the fix isn't a delete or rewrite — it's an investigation.

Setup task (before any individual investigation):
\`\`\`
/bx:plan "Investigate flake history on tests/scheduler.test.ts. Read the flake-fix commits surfaced in /bx:tests report (commits abc1234, def5678, ghi9012). Form a hypothesis about the underlying race / timing / order dependence. If the hypothesis is testable, add a deterministic repro test; if not, propose isolation (use vitest --shard, or move the test to an integration-only suite). Do not simply add a longer retry."
\`\`\`

Per suspect:

**4.1** flakiness_history — `tests/scheduler.test.ts` (3 flake-fix commits)
- ... (link to setup task above)

---

### Phase 5 — Documented-Decision Confirmations (N findings)

These conflict with documented testing posture. **Confirm intent before action.**

**5.1** T03 finding in `tests/repositories/userRepo.test.ts` — conflicts with `tests/README` ("Repository unit tests are mock-heavy by design")
- Action options:
  - **Honor the posture:** dismiss this finding. Optionally annotate the file header with a reference to the convention so future scans see the deliberate choice.
  - **Update the posture:** if the rationale no longer holds, edit `tests/README` to reflect the new conventions, then `/bx:plan` the rewrite.

---
```

## Hand-off contract

Each `/bx:plan <brief>` snippet must be **fully self-contained**:

- Quote file path + line range
- For coverage gaps: list specific scenarios to cover (don't say "add tests"; say "cover the expired-session branch and tampered-token branch")
- State the invariant: "test names stay the same so coverage attribution doesn't shift", "mocks remain at HTTP boundary"
- State the success criterion: "100% branch coverage on this file", "no toHaveBeenCalledWith except at boundary"
- Assume the receiver has no context from the bx:tests pass

## What this mode does NOT do

- Apply edits (use `--fix` for T01s)
- Spawn subagents
- Hydrate tasks directly (user runs `/bx:plan` per brief → that hydrates tasks via its own flow)
- Run coverage tooling (that's `--coverage` in default mode, never inside `--plan`)
