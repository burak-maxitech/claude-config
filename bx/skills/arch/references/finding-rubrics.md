# Finding Rubrics — the shared contract every arch subagent scores against

**Canonical owner** for `severity`, `certainty`, `effort_estimate`, `evidence`, and
`why_this_might_be_wrong`. Every scan reference file and every `arch-*` agent cites this file;
none of them restates the anchors. If a band moves, it moves here.

Why this file exists: five subagents score findings independently and never see each other's
output, yet the orchestrator gates on `certainty`, ranks on
`severity × certainty / effort`, and groups on `effort_estimate`. Without shared anchors those
three numbers are four or five private scales, and a ranked list built from them means nothing.
Calibrate against the tables below, not against how confident the finding feels.

---

## `severity` — blast radius × likelihood × reversibility

| Band | Anchor |
|------|--------|
| `high` | Crosses a module boundary or has ≥5 dependents, **or** can produce incorrect results, data loss, or an outage. Hard to reverse once shipped. |
| `medium` | Contained to one module. Measurably degrades maintainability or performance, but nothing is wrong today. |
| `low` | Local readability or hygiene. Trivially reversible. |

Severity is about **consequence**, never about how much code is involved or how confident you
are. A one-line missing timeout on a shared HTTP client is `high`. A 400-line god function nobody
calls is `low`.

Worked anchors, one per dimension:

| Dimension | `high` looks like | `low` looks like |
|-----------|-------------------|------------------|
| structure | A circular dependency between two top-level modules | A 120-line file that could be split |
| refactor | A god function on the request path, 6 concerns, every change touches it | A three-clause conditional worth naming |
| simplification | An abstraction layer that 5 modules route through and nothing varies behind | An unread config key in one file |
| performance | N+1 on a list endpoint | A regex recompiled in a 10-iteration loop |
| robustness | A swallowed exception on a payment write; a network call with no timeout | `unwrap()` in a one-off script path |

## `certainty` — an evidence class, not a feeling

Pick the band whose description matches **what you actually did**, then report that work in
`evidence`. Do not round up because the pattern looks obvious.

The bands are ordered on **one axis: how much of the finding's dependency set you examined.**
Read them top-down and stop at the first row that is *not* true of what you did.

| Band | You did this |
|------|--------------|
| `0.90–1.00` | Read the definition **and** every call site / implementer in scope. Nothing rests on inference. |
| `0.70–0.89` | Read the definition, **and** enumerated the callers (grep + count) without reading them all. |
| `0.50–0.69` | Read or matched within one file only. **Callers not enumerated at all.** |
| `< 0.50` | Inferred from naming, directory layout, or partial context. |

The 0.70 / 0.50 boundary is exactly this: **did you enumerate the callers?** Reading one file
thoroughly does not by itself reach 0.70 — depth within a file and breadth across the dependency
set are different things, and this scale measures breadth.

**When a dependency cannot be resolved at all** — the import target is not in scope, the schema is
not in the repo, the client is constructed in a file you were not given — that is *not* the same as
not having looked. Report the finding at the band your actual examination reached, and name the
unresolvable dependency explicitly in `evidence` ("traced `db` to `../lib/db`; that file is not in
scope"). **Do not silently omit the finding** because you could not complete the trace: an
unverifiable gap the user can check in five seconds is worth more than silence, provided you say
which part is unverified.

**Defects with no dependency set.** Some findings are provable from one function body and do not
depend on who calls it — a mutable default argument, a swallowed exception, a resource never
released. The breadth axis does not apply: score these on whether you **read the whole enclosing
function** (0.80–0.95) or only pattern-matched it (0.50–0.69). A grep confirming *zero* callers is
not caller enumeration and does not by itself lift a finding into the 0.70+ band.

**Scan files may cap, never redefine.** A scan reference may impose a certainty *ceiling* on
findings resting on an inferred premise — an entry-point map built from a naming convention rather
than a framework pattern, for instance. That is a cap applied on top of these bands, not a new
scale. The bands themselves move only in this file.

Findings below `0.50` are dropped by the orchestrator's gate unless `severity: high` or
`lines_deletable >= 20` — so a low band is not a wasted finding, it is an honest one. Two things
force a band **down** regardless of how much you read: dynamic dispatch or reflection anywhere in
the path, and a symbol exported from a package entry point (consumers you cannot see).

## `effort_estimate`

| Band | Anchor |
|------|--------|
| `trivial` | One edit site, <10 lines, no signature change. |
| `small` | One file, <50 lines, no public API change. |
| `medium` | 2–5 files, or a signature change with a bounded, enumerable caller set. |
| `large` | Cross-module, public API, or needs a migration or a staged rollout. |

Estimate the **whole** change including test updates, not just the primary edit.

---

## `evidence` — mandatory on every finding

One to three lines showing the work behind the `certainty` band. Quoted code, grep counts, or
enumerated call sites — whatever the band claims you did.

```
evidence: "createOrder() at line 34 calls await db.user.findUnique() inside `for (const id of ids)`.
           Grepped `findUnique` in src/orders/: 1 site. Read all 3 callers of createOrder
           (api/orders.ts:22, jobs/backfill.ts:88, cli/seed.ts:14) — ids is unbounded in 2 of 3."
```

A finding without evidence is an assertion. The orchestrator cannot verify it, the user cannot
audit it, and the certainty number is unearned. **Bad:** `"this looks like an N+1"`.

## `why_this_might_be_wrong` — mandatory on every finding

One sentence naming the most plausible way this finding is mistaken. Architectural findings are
opinion-adjacent and nothing else in this skill challenges them, so this field is the only
adversarial pressure in the pipeline. Write the objection a defensive author would raise.

```
why_this_might_be_wrong: "If ids is always the 3-element set from the caller in api/orders.ts,
                          the batch rewrite adds indirection for no measurable gain."
```

Rules: it must be **specific to this finding** — "I might be wrong" is not an answer — and
writing one that convinces you means the finding should be dropped or its certainty lowered
before you return it, not surfaced with a caveat attached.

**One exception, and it is explicit:** where a catalog entry or a scan instruction states that a
condition should be *reported as a question* rather than dropped (the `X` entries do this for
deployment topology the code cannot carry), that instruction wins. Report it at the certainty band
it earns, phrased as a question. The drop-if-convinced rule governs findings you could have
verified and did not; it does not govern findings that are unverifiable from code alone by their
nature.

---

## `respects_documented_decision`

Trusted by the orchestrator to route findings into a confirmation section, and never defined
anywhere else — so, precisely:

**Answer these two questions in order. Do not set the flag any other way.**

1. Does the Intended Architecture summary contain a statement that my **recommendation** would
   violate if it were applied? If you cannot quote that statement, the answer is no.
2. If no → **`true`**. If yes → **`false`**, and quote the statement in `evidence`.

That is the whole rule. `true` is the default and the overwhelmingly common case, including for
every ordinary defect the project has never written anything about.

**The most common error is setting `false` because the code looks like it violates something.**
That is backwards. The flag is about your *fix*, not the code:

| Situation | Flag | Why |
|-----------|------|-----|
| A race with no lock; nothing documented about locking | `true` | Adding a lock violates no stated intent |
| A missing timeout; nothing documented about timeouts | `true` | Same |
| A finding whose fix would *restore* a documented goal the code currently breaks | `true` | You are serving the decision, not colliding with it |
| Deleting an abstraction the docs say to keep ("Stripe is replaceable mid-2026") | `false` | Your recommendation contradicts a stated intent |
| Splitting a monolith an ADR chose deliberately | `false` | Same |

The third row is the one that trips scanners: finding a defect that *breaks* a documented goal is
still `true`, because fixing it honors that goal. `false` is rare. If most of your findings carry
`false`, you have inverted the flag — re-read this table before returning them.

Setting `false` is consequential: the orchestrator treats that group as **exclusive**, so the
finding leaves the actionable lists entirely and waits on user confirmation. Never set it without a
quotable statement.

## `coverage_negatives` — the channel for "I looked and there was nothing"

Alongside your findings, return a `coverage_negatives` list: categories you swept that came up
genuinely empty, each with the evidence that makes the negative credible.

```
coverage_negatives:
  - category: "C — locking primitives"
    evidence: "Grepped flock|lockfile|\.lock|LockFileEx|Mutex across all 13 files: 0 hits."
  - category: "D01/D02/D08 — class-based design entries"
    evidence: "Only class in scope is CredentialError, a single-method exception type. No implementers."
```

**A negative result is not a finding.** Do not emit it as a `severity: low` finding with
`recommended_refactor: "None"` — that ranks, groups, and pollutes the report's tables with rows
nobody can act on. Put it here. The orchestrator renders these in the footer, where they do the job
a negative belongs in: separating a clean codebase from an unscanned one.

Report a category here when you swept it and it was empty. Do not list every entry you did not
match — only categories a reader would otherwise wonder about.

## Complexity fields

`ccn_current` / `ccn_projected` and `cognitive_current` / `cognitive_projected`.

Populate both pairs on complexity and refactor findings; leave them `null` where complexity is
not the signal (coupling, layering, circular deps, most robustness and simplification findings).

The orchestrator's sanity gate drops a refactor finding only when it reduces **neither** metric.
Several catalog entries state "CCN direction: unchanged" and earn their place on cognitive
complexity alone — a finding citing one of those with no cognitive pair is dropped as
unsubstantiated. See `scan-structure.md` Step 1b for how cognitive complexity is computed when no
linter reports it (which is every stack except JS/TS with `eslint-plugin-sonarjs`).
