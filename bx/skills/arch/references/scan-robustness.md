# Scan: Robustness (concurrency, error safety, scalability)

Loaded by the orchestrator alongside `catalog-rules.md` + `catalog-robustness.md` and passed to
the `arch-robustness` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Workspaces` — list or "none"
- `Tier` — full | bounded | sample. `full`: read every file in scope. `bounded`: read every file,
  but deep-trace only the entry-point-reachable set. `sample`: the orchestrator already narrowed
  the scope file list — scan exactly what you were given and do not widen it.
- `Workspaces` — list or "none". When several, treat each as a separate scope: an entry-point map
  per workspace, and never trace a dependency across a workspace boundary you were not given.
- `Scope file list` — exact paths to scan
- `Intended Architecture summary` — 3-5 bullets
- `Scoring contract` — the full contents of `finding-rubrics.md`. It is the canonical owner
  of the `severity` / `certainty` / `effort_estimate` anchors and of the two mandatory
  justification fields, `evidence` and `why_this_might_be_wrong`. Score against it rather than
  against your own sense of confidence — five scanners never see each other's output, and the
  orchestrator gates, ranks, and groups on exactly these numbers.
- `Robustness catalog` — full content of `catalog-rules.md` + `catalog-robustness.md`. You receive
  the C/E/X entries only. Cite by ID.

## Core principle

You are looking for **failure modes the code cannot recover from**, not for style. The other
scanners ask "is this hard to read, or bigger than it needs to be?" You ask a different question:
**what happens when this runs twice at once, when the network hangs, or when the table has ten
million rows?**

Two consequences:

1. **Every finding must name the failure**, concretely, in `recommended_refactor` — not the rule
   it breaks. "No timeout on the payment-provider call" is not the finding; "if the provider hangs,
   this request holds a connection until the pool is exhausted and unrelated endpoints start
   failing" is.
2. **Absence is the signal.** Unlike the other scanners you are frequently detecting something
   *missing* — a timeout, a `finally`, a bound. That means you must trace far enough to know it is
   actually absent (the client may configure it; an outer layer may retry) before you claim it.
   That tracing is what your `certainty` band reports.

## Entry-point map — build this first

Half these entries depend on knowing what runs concurrently and what sits on a request path.
Before scanning, spend one pass identifying:

- **Request handlers** — route definitions, controllers, framework decorators
  (`@app.route`, `@router.get`, `http.HandleFunc`, `@Controller`), Lambda/Cloud Function handlers
- **Background workers** — queue consumers, cron entry points, schedulers, `setInterval`
- **Concurrency spawn points** — `go func`, `create_task`, `Promise.all`, thread pools, workers
- **Process entry points** — `main`, CLI commands, migration scripts

**When no framework pattern matches** — plain exported functions, no decorators, the router file
out of scope — fall back in this order and **say which rung you used** in the evidence of every
finding that depends on it:

1. A framework pattern matched (above). Full confidence in the map.
2. Signature convention — `(req, res)`, `(request)`, `(event, context)`, `(ctx)` — **plus** a
   statement in the Intended Architecture summary placing that directory at the HTTP boundary.
   Treat as a handler; cap dependent findings at 0.8.
3. Neither. Say the map could not be built and cap every dependent finding at 0.69.

Record which files are reachable from each. `C01`, `C07`, `X03`, `X04`, and `X06` all key off
"is this on a request path?" and are unscorable without it.

**Unresolvable imports.** When a reachable module imports something that is not in scope
(`../lib/db` with no such file), you cannot complete the trace — and that is *not* a reason to drop
the findings that depend on it. Follow `finding-rubrics.md`'s rule: report at the band your actual
examination reached and name the unresolvable dependency in `evidence`. Silence here is the worst
outcome, because a missing timeout on an untraceable DB client is exactly the finding the user
needs and exactly the one a strict "trace before you claim" reading deletes.

## Per-entry scanning hints

Language-specific triggers live in the catalog entries themselves. What follows is how to scan
efficiently — grep-first, then read to confirm. **Never report a finding from a grep hit alone**;
the catalog's false-positive guards all require reading the surrounding code, and the scoring
contract caps pattern-match-only findings at 0.69.

### Highest-precision first (do these even under a tight budget)

These three have the best signal-to-noise ratio in this catalog and are worth a full pass on any
tier:

- **`E03` missing timeout** — grep `fetch(`, `axios`, `requests\.(get|post|put|delete)`,
  `http.Client{`, `subprocess.run`, then check for a `timeout` / `signal` / `Timeout` field at the
  call **or** on the shared client the call uses. Trace to the client before flagging.
- **`E01` swallowed exception** — grep `catch\s*\([^)]*\)\s*\{\s*\}`, `except.*:\s*pass`,
  `\.catch\(\(\)\s*=>\s*\{\}\)`, `rescue\s*$`. Then read the `try` body: a swallowed error around
  a write is `high`, around a cache read is `low`.
- **`C08` mutable default argument** (Python) — grep `def \w+\([^)]*=\s*(\[\]|\{\}|set\(\))`.
  Near-zero false positives; confirm only that the parameter is mutated.

### Concurrency (`C`)

Work from the entry-point map outward. For each spawn point and handler:

```
1. List module-scope mutable bindings in the files it reaches      -> C01
2. Find check-then-write pairs spanning an await/blocking call     -> C02
3. Find lock acquisitions; check the body for I/O or await         -> C03
4. Find async calls whose result is discarded                      -> C04
5. Find fan-out over a non-literal collection with no limiter      -> C05
6. Find first-use initialization of shared objects                 -> C06
7. Follow ctx/token parameters to see if they reach the I/O call   -> C07
```

For `C02` specifically: the shape is two statements, not one pattern — an existence check and a
dependent write. Grep candidates (`if not`, `if (!`, `exists`, `find`, `get`) then read forward a
few lines. A unique constraint or upsert nearby kills the finding.

### Error safety (`E`)

Grep-driven, then read:

| Entry | First grep | Then confirm |
|-------|-----------|--------------|
| `E01` | empty catch bodies | what the `try` body does — that sets severity |
| `E02` | `throw new`/`raise`/`fmt.Errorf` inside a catch | whether the cause is chained |
| `E03` | the call list above | no timeout at call **or** client |
| `E04` | remote calls in a multi-step function | no retry anywhere on the path; **and** the op is idempotent |
| `E05` | `open(`, `.acquire(`, `.connect(`, `Lock()` | no `finally`/`with`/`defer`/`using`, and a branch can skip the close |
| `E06` | `.unwrap()`, `.expect(`, `!!`, `try!`, bare `assert` | the file is not a test/`main`/build script |
| `E07` | functions with ≥2 external mutations | no enclosing transaction, no compensation, no idempotency key |
| `E08` | custom exception types | raised in one module, caught in another, ≥3 sites, expected outcome |

`E07` cannot be pattern-matched — it requires reading the whole function and knowing what each
call does externally. If you did not do that, do not report it above 0.69.

### Scalability (`X`)

Every `X` entry needs context the code may not carry. Be explicit about what you could not
determine:

- `X01` / `X02` need to know whether the collection **grows with usage**. A query against a config
  table is bounded; the same query against events is not. If the entity is ambiguous, say so in
  `why_this_might_be_wrong` and score accordingly — do not assume growth.
- `X03` needs to know whether the service runs multiple replicas. Look for deployment manifests,
  replica counts, a `Procfile`, or a statement in the Intended Architecture summary. **If none
  exists, this is a question, not a finding** — report it at `certainty <= 0.5` and phrase the
  recommendation as "confirm the deployment topology."
- `X04` / `X05` need the request path from the entry-point map.

## Overlap with other scanners

- **`arch-performance`** also looks at N+1 and sync-I/O-in-async. Where its trigger and yours both
  fire, report yours only if the **failure mode** differs from the throughput concern — an
  unawaited write (`C04`) is a correctness bug, not a slow one. The orchestrator deduplicates by
  location, so a genuine overlap costs nothing; a duplicate framing costs a slot.
- **`arch-simplification` (`S06`)** deletes defensive code. It is hard-suppressed at trust
  boundaries, which is where your `E` entries live. If you flag a missing check on the same line
  S06 wants to delete a check, one of you is wrong — report it, with both readings, and let the
  orchestrator surface the conflict.

## Skip

- Vendored / generated dirs: `node_modules`, `venv`, `.git`, `dist`, `build`, `__pycache__`,
  `.next`, `.cache`, `vendor`, `target/`, `coverage/`, `*.generated.*`, `__generated__/`
- Test files, **except** `E06` and `C08`, which are worth reporting anywhere
- Anything the Intended Architecture summary places out of scope

## Output format (return per finding)

```
{
  "dimension": "robustness",
  "location": "src/payments/charge.ts:88-104",
  "title": "Payment provider call has no timeout — pool exhaustion under provider latency",
  "severity": "high",
  "certainty": 0.9,
  "effort_estimate": "trivial",
  "ccn_current": null,
  "ccn_projected": null,
  "cognitive_current": null,
  "cognitive_projected": null,
  "respects_documented_decision": true,
  "recommended_refactor": "The shared axios instance in src/lib/http.ts is constructed with no `timeout`, so this call waits indefinitely. If the provider hangs, each in-flight charge holds a connection until the pool is exhausted and unrelated endpoints begin failing. Set a default timeout on the shared client and override per-call for the known-slow settlement endpoint.",
  "evidence": "charge.ts:88 calls `http.post('/charges')`. Traced `http` to src/lib/http.ts:4 — `axios.create({ baseURL })`, no timeout key. Grepped `timeout` in src/lib/: 0 hits. 3 other call sites share the instance.",
  "why_this_might_be_wrong": "If the deployment sets a proxy-level or ingress timeout shorter than the pool's idle limit, the hang is already bounded outside the process.",
  "category": "E",
  "cite_catalog_entry": "E03"
}
```

Do not return prose. Return only structured findings, ordered by `severity × certainty`.
**Cap output at 15 findings** — three categories share this budget, so rank across all of them
rather than reserving slots per category. If one category dominates a codebase, that is itself the
signal, and the theme synthesis in the orchestrator's Step 5.9 will surface it — a cluster of
findings sharing one root cause qualifies as a theme on its own, without needing a second catalog
family alongside it.
