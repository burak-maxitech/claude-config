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

- **`true`** — acting on this finding does not contradict anything the Intended Architecture summary
  states. This is the default and the common case, including for ordinary defects the project has
  never written anything about.
- **`false`** — the project has **documented a decision that this finding argues against**. The flag
  is not about whether the code is good; it is about whether *your recommendation* collides with a
  stated intent. A deliberate, documented tradeoff ("in-memory cache is authoritative, rebuilt at
  boot"; "monolith by choice, see ADR-0007") gets `false` — you are still surfacing it, but the user
  must confirm before it is actioned.

Read it as *"my recommendation respects the documented decision"*, not *"this code respects it."*
When you set `false`, quote the documented decision in `evidence` so the orchestrator can render the
conflict without going to find it.

## Complexity fields

`ccn_current` / `ccn_projected` and `cognitive_current` / `cognitive_projected`.

Populate both pairs on complexity and refactor findings; leave them `null` where complexity is
not the signal (coupling, layering, circular deps, most robustness and simplification findings).

The orchestrator's sanity gate drops a refactor finding only when it reduces **neither** metric.
Several catalog entries state "CCN direction: unchanged" and earn their place on cognitive
complexity alone — a finding citing one of those with no cognitive pair is dropped as
unsubstantiated. See `scan-structure.md` Step 1b for how cognitive complexity is computed when no
linter reports it (which is every stack except JS/TS with `eslint-plugin-sonarjs`).
