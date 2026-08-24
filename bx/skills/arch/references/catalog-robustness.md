# Catalog: Robustness (C / E / X prefixes)

Concurrency and thread safety (`C`), error safety and resource lifecycle (`E`), and architectural
scalability (`X`). Consumed by the `arch-robustness` subagent. Every finding must cite an entry by
ID in `cite_catalog_entry`.

**Shared rules live in `catalog-rules.md`.** Read it alongside this file.

**No entry in this catalog is `--fix-eligible`.** Adding an `await`, a timeout, a lock, or a
`finally` changes runtime behavior in ways a diff preview cannot reveal, and `--fix` does not run
tests afterward. All of these route to `--plan`.

**Complexity direction is `n/a` throughout** — none of these are complexity refactors. Their
value is measured in failure modes removed, not in CCN.

**The counterpart rule.** `S06` in `catalog-simplification.md` *deletes* defensive code; this
catalog *finds missing* defensive code. They are not opposites in tension — S06 targets checks the
type system already proves inside the domain, and is hard-suppressed at every trust boundary,
which is precisely where `E` entries live. If you find yourself wanting to flag both on the same
line, the S06 suppression was missed.

---

# C — Concurrency and thread safety

The dominant failure mode here is **shared mutable state reachable from two flows of control**.
Per-language idioms differ; the shape does not.

## C01 — Module-level mutable state written from a request or event handler

- **Languages:** ts, js, python, go, java, c#, kotlin, rust, php, ruby
- **Detect when:** a module-scope binding that is mutable (`let`/`var`, a mutated object or array,
  a Python module global, a Go package var, a static field) is **assigned or mutated** inside a
  function reachable from a request handler, event consumer, or goroutine/task.
  - Grep module scope for `^(let|var) `, `^[A-Z_]+ = \{`, `^var \w+ =`, `static \w+`
  - then Grep for writes to that name inside handler-path files
- **Replace with:** move the state into the request/session scope, or put it behind a lock or an
  atomic, or make it immutable.
- **--fix-eligible:** false
- **Severity signal:** `high` when the value is read and written (a counter, a cache, an accumulator)
  rather than written once at init.
- **Caveats / false-positive guards:**
  - **Write-once initialization** at module load (config, a compiled regex, a connection pool
    handle) is the correct pattern — flag only if written *after* init.
  - **Single-threaded runtimes still race across `await`.** Node and Python asyncio interleave at
    await points, so "it's single-threaded" is not a defense if the write spans one.
  - **Deliberate process-local caches** with documented staleness tolerance — mark
    `respects_documented_decision: false` rather than flagging outright.

## C02 — Check-then-act without atomicity (TOCTOU)

- **Languages:** all
- **Detect when:** an existence/emptiness check is followed by a dependent write on shared state,
  with **no lock, transaction, or atomic primitive** between them, and at least one `await` /
  blocking call in the gap. Canonical shapes:
  - `if (!cache[k]) { cache[k] = await load(k) }`
  - `if not os.path.exists(p): open(p, 'w')`
  - `user = find(email); if (!user) create(email)` — the classic duplicate-account bug
  - check-then-`INSERT` with no unique constraint named nearby
- **Replace with:** an atomic primitive — `SETNX`, an upsert, a unique constraint plus catch, a
  single-flight/mutex wrapper, or `O_EXCL`.
- **--fix-eligible:** false
- **Severity signal:** `high` whenever the write creates a record or spends money; duplicates are
  user-visible and often unrecoverable.
- **Caveats / false-positive guards:**
  - **Single-writer contexts** — a migration, a CLI, a startup path that cannot run concurrently.
    Check whether the enclosing function is reachable from more than one caller.
  - **An idempotent write** makes the race harmless; look for an upsert or a unique key before
    flagging.

## C03 — Lock held across an await or blocking call

- **Languages:** rust, java, c#, kotlin, python, ts, js, go
- **Detect when:** a critical section contains a suspension or blocking I/O:
  - Rust: a `MutexGuard` (`.lock().unwrap()`) still alive across `.await`
  - Java/Kotlin/C#: `synchronized` / `lock` block containing a network, DB, or file call
  - Python: `with lock:` containing `await` or blocking I/O
  - Go: `mu.Lock()` … `defer mu.Unlock()` with an RPC in the body
- **Replace with:** compute the value outside the lock and hold it only to publish, or use an
  async-aware lock, or narrow the section.
- **--fix-eligible:** false
- **Severity signal:** `high` — this converts a concurrency primitive into a throughput ceiling,
  and in Rust `std::sync::Mutex` across `.await` can deadlock outright.
- **Caveats / false-positive guards:**
  - A **deliberately serialized** section (a migration lock, a leader election) is doing exactly
    this on purpose. Look for a comment or a name that says so.

## C04 — Floating async work

- **Languages:** ts, js, python, go, rust, c#, java
- **Detect when:** async work is started and its completion is never observed:
  - an async call whose promise is not awaited, returned, or `.catch`-ed (`void doThing()`,
    a bare `doThing()` on its own line in an async function)
  - `asyncio.create_task(...)` with the handle discarded
  - `go func(){...}()` with no `WaitGroup`, channel, or context tying it to a lifetime
  - Go: `_ = err` or an `err` value assigned and never checked
  - C#: `async void` outside an event handler
- **Replace with:** await it, return it, or attach it to an explicit supervisor with error
  handling and a shutdown path.
- **--fix-eligible:** false
- **Severity signal:** `high` when the work writes state or the process can exit before it
  finishes — errors vanish silently and the failure surfaces as missing data much later.
- **Caveats / false-positive guards:**
  - **Deliberate fire-and-forget** with an explicit `.catch(logError)` attached is handled, not
    floating.
  - **Long-lived daemons** started at boot legitimately outlive their caller.

## C05 — Unbounded concurrency

- **Languages:** ts, js, python, go, rust, c#, java
- **Detect when:** a fan-out primitive is applied to a collection whose size is not statically
  bounded — `Promise.all(items.map(...))`, `asyncio.gather(*[...])`, a goroutine per item in a
  `range` over a query result — with **no** semaphore, chunking, worker pool, or concurrency
  limit nearby.
- **Replace with:** a bounded pool (`p-limit`, a semaphore, a buffered worker channel) or explicit
  batching.
- **--fix-eligible:** false
- **Severity signal:** rises with what each task consumes. Unbounded DB connections or outbound
  HTTP is `high` — it exhausts a shared pool and takes down unrelated traffic.
- **Caveats / false-positive guards:**
  - **A literal/fixed-size collection** (`Promise.all([a, b, c])`) is bounded by construction.
  - **A documented small upper bound** — if the collection comes from a paginated query with a
    page size, it is already limited; say so rather than flagging.

## C06 — Unsafe lazy initialization

- **Languages:** java, c#, kotlin, python, ts, js, go, rust, php
- **Detect when:** a singleton or memo is populated on first use without synchronization —
  `if (instance == null) instance = new X()`, a module-level `_cache = None` filled on demand, or
  a double-checked-locking shape without a `volatile` / `Atomic` / memory-barrier guarantee.
- **Replace with:** the language's idiomatic once primitive — `sync.Once`, `lazy` / `Lazy<T>`,
  `functools.cache`, a static initializer, `OnceCell`/`LazyLock`.
- **--fix-eligible:** false
- **Severity signal:** `medium` when the worst case is duplicated construction; `high` when the
  object owns a limited resource (a connection pool, a file handle) or when double-checked locking
  is present without the memory barrier — that one is a genuine JMM/memory-model bug.
- **Caveats / false-positive guards:**
  - **Single-threaded by construction** (a CLI entry point, a module executed once at import).
  - **Idempotent, cheap construction** where a duplicate is harmless — note it and lower severity
    rather than dropping.

## C07 — Cancellation not propagated

- **Languages:** go, python, ts, js, c#, rust
- **Detect when:** an async boundary drops the cancellation token:
  - Go: a function takes `ctx context.Context` and calls something that accepts a context but
    passes `context.Background()` / `context.TODO()` instead — or takes no ctx while doing I/O
  - C#: a method with a `CancellationToken` parameter that never forwards it
  - JS/TS: an `AbortSignal` accepted but not passed to `fetch`
  - Python: a shielded or bare task that ignores `asyncio.CancelledError`
- **Replace with:** thread the token through every I/O call on the path.
- **--fix-eligible:** false
- **Severity signal:** `medium` normally; `high` on a request path where it means client
  disconnects do not free server work — the shape that turns a traffic spike into an outage.
- **Caveats / false-positive guards:**
  - **Deliberately uncancellable** cleanup, finalizers, and audit writes should ignore
    cancellation. Skip anything in a `finally` / `defer` / shutdown path.

## C08 — Shared-instance state idioms

- **Languages:** python, js, ts, java, ruby, php
- **Detect when:** a language-specific footgun that silently shares state:
  - Python: a **mutable default argument** (`def f(x, acc=[])`, `= {}`, `= set()`) — this one is
    near-certain, grep `def \w+\([^)]*=\s*(\[\]|\{\}|set\(\))`
  - Python/Ruby: a class-level mutable attribute mutated through instances
  - JS/TS: a module-scope object or array reused across requests in a server
  - Java: a non-final static collection
- **Replace with:** `None` + construct inside; instance-level init; per-request construction.
- **--fix-eligible:** false
- **Severity signal:** the mutable default argument is `high` when the function accumulates into
  it — the state leaks across every call in the process.
- **Caveats / false-positive guards:**
  - An **intentionally shared immutable** default (a frozen tuple, a constant string) is fine.
  - A module-scope object **only read**, never mutated, is fine.

---

# E — Error safety and resource lifecycle

## E01 — Swallowed exception

- **Languages:** all
- **Detect when:** a catch block that neither handles nor propagates — an empty body, a lone
  `pass`, a bare `.catch(() => {})`, `except Exception: pass`, `catch {}`, `rescue; end`,
  Go `if err != nil {}` with an empty body.
- **Replace with:** handle it meaningfully, re-raise, or — if it is genuinely ignorable — log at
  debug with a comment saying **why**. An empty catch is indistinguishable from a bug.
- **--fix-eligible:** false
- **Severity signal:** `high` when the `try` body performs a write, a payment, or a state
  transition; the operation now fails invisibly.
- **Caveats / false-positive guards:**
  - **Best-effort cleanup** in a `finally`/shutdown path where throwing would mask the original
    error is legitimate — but it should say so; flag as `low` with a comment recommendation.
  - **Expected control flow** (`except KeyError: pass` immediately followed by a default) is
    idiomatic — check the following lines before flagging.

## E02 — Catch-all that discards the cause

- **Languages:** all
- **Detect when:** an exception is caught and a **new** error is thrown without chaining the
  original — `throw new Error("failed")` inside a catch with no `{ cause }`, Python `raise X(...)`
  without `from e`, Go `fmt.Errorf("...")` without `%w`, C# `throw new X(msg)` without the inner
  exception.
- **Replace with:** chain it. `{ cause: e }`, `raise X(...) from e`, `%w`, inner-exception
  constructor.
- **--fix-eligible:** false
- **Severity signal:** `medium` — nothing breaks, but every incident using this path loses its
  stack trace, which is a permanent tax on debugging.
- **Caveats / false-positive guards:**
  - **Deliberate sanitization at a trust boundary** — an API layer converting an internal error to
    a safe client message *should* drop detail outward, provided it logs the original first. Check
    for a log call before flagging.

## E03 — External call with no timeout

- **Languages:** all
- **Detect when:** a network, DB, or subprocess call is issued with no timeout configured, at the
  call site or on the shared client:
  - `fetch(...)` with no `signal`; `axios` with no `timeout`; `requests.get/post` with no
    `timeout=` (its default is **infinite**); `http.Client{}` with a zero `Timeout`
  - `subprocess.run` / `exec` with no timeout
  - a DB driver connected without `statement_timeout` / `connectTimeout`
- **Replace with:** an explicit timeout at the client, plus a per-call override where the
  operation is known to be slow.
- **--fix-eligible:** false
- **Severity signal:** `high` on any request path. This is the highest-precision entry in the
  catalog and the single most common cause of cascading production hangs — a call with no timeout
  is a resource leak with a network trigger.
- **Caveats / false-positive guards:**
  - **A shared configured client.** If the module builds one client with a timeout and every call
    goes through it, individual call sites need nothing — trace to the client before flagging.
  - **Streaming or long-poll endpoints** legitimately have no total timeout, but should still set
    a read/idle timeout.
  - **Build scripts and one-shot CLIs** — `low`, not `high`.

## E04 — No retry or backoff at a transient boundary

- **Languages:** all
- **Detect when:** a call to a remote dependency known to fail transiently (network, cloud SDK,
  queue, DB connect) has no retry wrapper anywhere on the path, **and** the failure aborts a
  multi-step operation.
- **Replace with:** bounded retry with exponential backoff **and jitter**, applied only to
  idempotent operations.
- **--fix-eligible:** false
- **Severity signal:** `medium`. Raise to `high` only when the surrounding operation has already
  produced partial side effects (pairs with E07).
- **Caveats / false-positive guards:**
  - **Retrying a non-idempotent write is worse than not retrying.** If you cannot establish
    idempotency, say so in `why_this_might_be_wrong` and lower certainty.
  - **Retry at the wrong layer** compounds: if an outer layer already retries, adding an inner
    retry multiplies attempts. Check the whole path.
  - **A framework/SDK with built-in retry** (most cloud SDKs) needs none added.

## E05 — Resource acquired without a release path

- **Languages:** all
- **Detect when:** a resource is acquired and released on the happy path only — no `finally`,
  `with`, `defer`, `using`, `try-with-resources`, or RAII guard. Targets: file handles, DB
  connections and cursors, locks, sockets, subprocesses, temp files, spans/timers.
  - shape: `x = open(...)` / `conn = pool.acquire()` … `x.close()` at the end of the body, with a
    `return`, `throw`, or branch between them
- **Replace with:** the language's scoped-release construct.
- **--fix-eligible:** false
- **Severity signal:** `high` for pooled resources (a leaked connection exhausts a shared pool and
  takes down the process); `medium` for file handles.
- **Caveats / false-positive guards:**
  - **Ownership transfer** — a function that returns the resource for the caller to close is
    correct; check the return type.
  - **Process-lifetime resources** acquired at startup need no release.

## E06 — Panic-on-unexpected in a library path

- **Languages:** rust, swift, ts, kotlin, python, go
- **Detect when:** an assertion-style unwrap on a non-test, non-`main` path —
  Rust `.unwrap()` / `.expect()` / `panic!`, Swift `!` force-unwrap or `try!`, TS `!` non-null
  assertion, Kotlin `!!`, Python bare `assert` in production code (stripped under `-O`),
  Go `panic()` outside `main`/init.
- **Replace with:** propagate the error (`?`, `Result`, an explicit branch) and let the caller
  decide.
- **--fix-eligible:** false
- **Severity signal:** `high` in a library, a request handler, or anything long-running — one
  malformed input kills the process. `low` in `main`, tests, build scripts, or where a comment
  proves the invariant.
- **Caveats / false-positive guards:**
  - **Provably-safe unwraps** immediately after a check (`if x.is_some() { x.unwrap() }`) are
    safe, if ugly. Lower severity, do not drop.
  - **Rust `expect()` with a message documenting the invariant** is the idiomatic way to assert a
    real invariant — judge the message.

## E07 — Multi-step external mutation with no rollback or idempotency

- **Languages:** all
- **Detect when:** a function performs **≥2 externally-visible mutations** (DB write, payment,
  email, queue publish, third-party API call) with no transaction spanning them, no compensating
  action on failure, and no idempotency key on the retryable steps.
- **Replace with:** a transaction where the steps share a store; otherwise an outbox, a saga with
  explicit compensation, or idempotency keys so a retry converges.
- **--fix-eligible:** false
- **Severity signal:** `high` when the steps include an irreversible external effect — a charge
  that succeeds followed by a DB write that fails is a support ticket and a refund, and the code
  cannot tell it happened.
- **Caveats / false-positive guards:**
  - **A single transaction already spanning the writes** — trace for an enclosing transaction
    before flagging.
  - **Steps that are all idempotent** converge on retry and need no rollback.
  - Requires reading the whole function. If you only pattern-matched, cap certainty at 0.69 per
    the scoring contract.

## E08 — Exceptions as control flow across a module boundary

- **Languages:** all
- **Detect when:** an exception type is raised in one module and caught in another **to steer
  normal, expected outcomes** — `NotFound` raised on a routine lookup miss and caught to return a
  default, at ≥3 call sites.
- **Replace with:** an explicit result — `Option`/`Result`, a nullable return, a discriminated
  union (`R04`/`R05` in `catalog-refactors.md`).
- **--fix-eligible:** false
- **Severity signal:** `low`–`medium`. This is a maintainability finding: control flow becomes
  invisible in the signature, and every caller must know an undocumented protocol.
- **Caveats / false-positive guards:**
  - **Idiomatic in Python** (EAFP) — `try/except KeyError` is normal there. Only flag when the
    exception crosses a **module** boundary and represents an expected outcome.
  - **Framework-mandated** exceptions (`HTTPException` for a 404) are the framework's control
    flow, not the project's.

---

# X — Scalability

Static analysis cannot measure load. These entries target shapes whose **cost grows with data or
traffic** and that are visible in code — not micro-optimizations, and not guesses. When the
deployment context needed to judge one is absent (`X03`, `X04`, `X05`), say so in
`why_this_might_be_wrong` and score certainty by the scoring contract's evidence bands rather than
asserting.

## X01 — Unbounded result set

- **Languages:** all
- **Detect when:** a query or listing with no limit, pagination, or cursor on a table that grows
  with usage — `findMany()` / `SELECT *` with no `LIMIT`, `.all()`, `scan()`, `list_objects` with
  no paginator, `readdir` on a growing directory.
- **Replace with:** pagination or a cursor; a hard cap even on "small" tables.
- **--fix-eligible:** false
- **Severity signal:** `high` when the result crosses a network boundary or is returned to a
  client. This is the most reliably detectable entry in `X`.
- **Caveats / false-positive guards:**
  - **Bounded-by-nature tables** (config, enums, feature flags, country codes) are fine — judge by
    the entity, and if you cannot tell, say so.
  - **An aggregate/count query** returns one row regardless.

## X02 — Whole-collection load into memory

- **Languages:** all
- **Detect when:** an entire dataset is materialized before processing — `readFileSync` /
  `read()` on a data file, `list(cursor)` / `.fetchall()`, `json.load` of a bulk export, building
  a list comprehension over a query result purely to iterate it once.
- **Replace with:** stream — an iterator, a generator, a line reader, a server-side cursor,
  batched reads.
- **--fix-eligible:** false
- **Severity signal:** scales with input growth. `high` when the input is user-supplied or grows
  unboundedly (logs, uploads, exports).
- **Caveats / false-positive guards:**
  - **Fixed-size inputs** — a config file, a checked-in fixture, a template.
  - **Multiple passes genuinely needed** over the data make materialization correct; check whether
    the collection is iterated more than once.

## X03 — In-process state that blocks horizontal scaling

- **Languages:** all
- **Detect when:** authoritative state lives in the process — an in-memory session store, an
  in-memory rate limiter or counter, a local mutex used as a distributed lock, a scheduler that
  assumes it is the only instance, a local filesystem write treated as durable shared storage.
- **Replace with:** externalize to a shared store (Redis, the DB), or make the instance
  explicitly single-writer and say so.
- **--fix-eligible:** false
- **Severity signal:** `high` when correctness (not just efficiency) depends on there being one
  instance — a rate limiter that permits N× the limit at N replicas, or a cron that fires N times.
- **Caveats / false-positive guards:**
  - **Genuinely single-instance deployments** — a desktop app, a CLI, a single-node service.
    Check for deployment manifests, replica counts, or a statement in the architecture summary
    before flagging; if none exist, this is a question, not a finding.
  - **A cache used as a cache** (with the store as source of truth) is correct.

## X04 — Synchronous fan-out on a request path

- **Languages:** all
- **Detect when:** one inbound request triggers **sequential** calls to ≥3 downstream services or
  endpoints before responding, with no parallelism, caching, or aggregation.
- **Replace with:** parallelize the independent calls (bounded — see `C05`), aggregate upstream,
  or move non-essential work off the response path.
- **--fix-eligible:** false
- **Severity signal:** latency adds and availability multiplies — five 99.9% dependencies in
  series is a 99.5% endpoint. `high` on a user-facing path.
- **Caveats / false-positive guards:**
  - **Genuine data dependencies** between the calls make sequencing necessary — read the flow
    before flagging.
  - **Background jobs** are not on a request path.

## X05 — Unbounded queue or buffer with no backpressure

- **Languages:** all
- **Detect when:** a producer can outrun a consumer with nothing to slow it — an unbounded channel
  or `Queue()` with no `maxsize`, an in-memory array accumulating events, a batch that flushes on
  a timer with no size cap, a subscriber with no prefetch limit.
- **Replace with:** a bounded buffer plus an explicit policy — block, drop-oldest, or shed load.
- **--fix-eligible:** false
- **Severity signal:** `high` — the failure mode is memory exhaustion under exactly the load spike
  the queue exists to absorb.
- **Caveats / false-positive guards:**
  - **A bounded producer** (a fixed work list) cannot overrun.
  - **A broker-backed queue** already applies backpressure outside the process.

## X06 — Per-request connection creation

- **Languages:** all
- **Detect when:** a client or connection is constructed **inside** a handler or per-item loop
  rather than once at module scope — `new DbClient()`, `createConnection()`, `new HttpClient()`
  (the classic C# socket-exhaustion bug), a fresh SDK client per invocation.
- **Replace with:** hoist to a module-scope pooled client, injected or lazily initialized once
  (safely — see `C06`).
- **--fix-eligible:** false
- **Severity signal:** `high` for DB and HTTP clients — connection setup dominates the request and
  exhausts ports or pool slots under load.
- **Caveats / false-positive guards:**
  - **Per-tenant or per-credential clients** legitimately vary by request; the fix there is a
    keyed pool, not a singleton.
  - **Serverless cold-start patterns** already hoist to module scope — check placement.

## X07 — Full scan where a delta scan exists

- **Languages:** all
- **Detect when:** a recurring job reprocesses the entire dataset every run despite an available
  watermark — a cron that reads all rows with no `updated_at >` filter, a sync that re-uploads
  everything, a reindex over the full table on a schedule.
- **Replace with:** a watermark or change-feed driven delta, with a periodic full reconciliation.
- **--fix-eligible:** false
- **Severity signal:** cost grows with total data while the useful work grows with the delta — the
  job is fine until it silently exceeds its window.
- **Caveats / false-positive guards:**
  - **No watermark column exists** — then a full scan is the only correct option and the finding
    is about the schema, not the job.
  - **Reconciliation jobs are supposed to be full.** If the name or a comment says reconcile,
    skip.
  - **Small, bounded datasets** make the delta machinery a net loss.
