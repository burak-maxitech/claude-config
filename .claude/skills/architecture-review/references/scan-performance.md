# Scan: Performance (high-precision categories only)

Loaded by the orchestrator and passed to the `arch-performance` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Workspaces` — list or "none"
- `Tier` — full | bounded | sample
- `Scope file list` — exact paths to scan
- `Intended Architecture summary` — 3-5 bullets

## Core principle (repeated for emphasis)

**Static analysis cannot replace a profiler.** This subagent reports only categories where pattern-matching is statically reliable. Lower-confidence findings (`certainty < 0.7`) are framed as **suspects to measure**, not fixes. The orchestrator routes them to a separate report section.

If you catch yourself writing "this could be faster if we...", that's a suspect. Set certainty <0.7 and move on.

## High-precision categories (certainty ≥ 0.7)

### N+1 query patterns
Triggers (per language):

```
JS/TS:
  Grep: `for ... of` or `.map(async` containing `await <orm>.findOne|findById|get|fetchOne`

Python:
  Grep: `for ... in` containing `<orm>.objects.get(` or `.query(...).filter(...).first()` or `await session.get(`

Rails / SQLAlchemy / Sequelize / Prisma — all have characteristic per-item fetch shapes.
```

Severity: `high`. Recommend batch fetch (`findMany({ where: { id: { in: ids } } })`, `select_related`, `eager_load`).

### Sync I/O in async / hot paths
Triggers:

```
JS/TS:
  Grep inside `async function` bodies for: `fs.readFileSync|fs.writeFileSync|execSync|.deasync`

Python:
  Grep inside `async def` bodies for: `open(` (without `aiofiles`), `requests.get|post`, `time.sleep` (vs `asyncio.sleep`).
  Grep inside FastAPI/Django request handlers for the same.
```

Severity: `high`. Recommend the async equivalent.

### Accidental O(n²) — nested loops on same collection
Triggers:

```
Pattern A: outer `for x of collA`, inner `.find(item => item.id === x.id)` or `.includes(...)` over `collB` where `collB.length ~ collA.length`.

Pattern B: outer `for x of coll`, inner `for y of coll` (or same `coll`) with index-comparison filtering.
```

Severity: `medium-high` depending on collection size hints (literal arrays vs unbounded). Recommend Set/Map preprocessing (`new Map(collB.map(i => [i.id, i]))`).

### Missing memoization on pure recursive functions
Same trigger as catalog entry R12 in `refactor-catalog.md`. This subagent and `arch-refactors` both find it; the orchestrator deduplicates. Surface here only when the *recursion depth* (estimated by # of recursive calls per invocation) and *base-case branching* suggest non-trivial cost.

Severity: `medium`. Recommend memoization.

### Hot-loop invariants
Triggers:

```
Inside `for`/`while`/`.map`/`.forEach`:
  - `new RegExp("<literal>")`
  - `JSON.parse("<literal>")`
  - `<schema>.compile()` (zod, joi, ajv) of a literal
  - `re.compile(r"...")` (Python) of a literal
  - `datetime.strptime(s, "<literal-format>")` (literal format string)
```

Severity: `low-medium`. Recommend hoisting.

### Repeated hashing / parsing
Triggers:

```
Patterns to flag:
  - `JSON.parse(JSON.stringify(<x>))` — deep-clone via roundtrip
  - `new RegExp(<same-pattern>)` called multiple times in the same scope
  - `crypto.createHash('sha256')` per item where a single accumulating digest would do
```

Severity: `low`. Recommend the dedicated approach (`structuredClone`, hoisted regex, single accumulating hash).

## Suspect categories (certainty < 0.7, frame as "measure first")

These belong in your output but tagged as suspects. The orchestrator separates them.

- "Consider a cache here" — set certainty 0.4-0.6, add reason: "cache invalidation logic non-obvious from local code"
- "This list comprehension could be a generator" — useful only if the list is large; you can't tell statically
- "Possible parallelization" — can't infer dependency structure statically with high confidence
- "Lazy evaluation here" — same

## Hard exclusions

- Micro-optimizations (loop unrolling, struct packing, branch prediction)
- "This sync code should be async" — only flag if it's *demonstrably* in a hot path (request handler, render loop, cron job header)
- Speculative database index recommendations — that requires the schema and query plan, not just the code
- Generic "consider switching libraries" suggestions

## Honor Intended Architecture

If the Intended Architecture summary says "no perf tuning until v2," cap your output at the **top 3 highest-impact findings only**, all marked as suspects. Note the constraint in the orchestrator's hand-off back.

## Output per finding

```
{
  "dimension": "performance",
  "location": "src/users/list.ts:34-52",
  "title": "Possible N+1: per-user permission lookup inside list iteration",
  "severity": "high",
  "certainty": 0.85,
  "effort_estimate": "medium",
  "ccn_current": null,
  "ccn_projected": null,
  "respects_documented_decision": true,
  "recommended_refactor": "Batch fetch permissions for all user IDs once before the loop. Use `findMany({ where: { userId: { in: ids } } })` and convert to a Map for O(1) lookup inside the iteration.",
  "category": "N+1",
  "is_suspect": false
}
```

`ccn_*` fields are usually null for performance findings — populate only when the fix also reduces complexity (hot-loop hoist often does both).

Cap output at 20 findings.
