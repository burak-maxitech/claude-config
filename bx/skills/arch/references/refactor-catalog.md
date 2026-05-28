# Refactor Catalog — Complexity-Reducing Techniques

Each entry is a refactor *technique* (not a GoF pattern) that demonstrably reduces cognitive load. Subagents must cite an entry by ID in `cite_catalog_entry`. Entries marked `--fix-eligible: true` may be auto-applied in `--fix` mode (still gated by per-finding diff preview).

## Rules for the catalog

- **Languages tag is binding.** A subagent may not propose a refactor on a file whose language is not listed.
- **CCN reduction must be plausible.** Each entry states the expected direction of CCN change.
- **Only single-file refactors are `--fix-eligible`.** Multi-file or API-breaking refactors route to `--plan` instead.
- **No GoF patterns by default.** A few are included (Strategy, Command) but only with strict "detect when" triggers that catch the *problem*, not the *surface*.

---

## R01 — Guard-clause flatten (early return)

- **Languages:** all
- **Detect when:** function body is a single deeply nested `if/else` ladder where each branch returns or sets a result. Indentation depth ≥3 from method header.
- **Replace with:** invert each condition, return early on the negative path. Body becomes flat.
- **CCN direction:** unchanged (same decision points) but cognitive complexity drops sharply. Cognitive complexity is what the linter usually flags.
- **--fix-eligible:** true
- **Citation:** Refactoring (Fowler), "Replace Nested Conditional with Guard Clauses"

## R02 — Extract pure function

- **Languages:** all
- **Detect when:** a 30+ line function contains a self-contained block (5-20 lines) that operates on local variables and produces a single value with no side effects.
- **Replace with:** extract that block as a top-level (or sibling) pure function with explicit parameters. Caller becomes one line.
- **CCN direction:** parent function CCN drops by the extracted block's CCN; new function inherits it. Total stays the same, but per-function cap is what tools enforce.
- **--fix-eligible:** true (when extraction stays in the same file)

## R03 — Replace flag argument with two functions

- **Languages:** all
- **Detect when:** function takes a boolean parameter that is checked at the top to fork all behavior. Callers always pass a literal `true` or `false`.
- **Replace with:** two separate functions, each handling one branch. Drop the parameter.
- **CCN direction:** each new function is roughly half the original CCN.
- **--fix-eligible:** true (when call sites are all in the same file)

## R04 — Replace type-code with discriminated union

- **Languages:** ts, js (with JSDoc types), rust, swift, kotlin, scala
- **Detect when:** code uses a string/int "kind" field to dispatch behavior, with `if (x.kind === 'a') ... else if (x.kind === 'b') ...` ladders across multiple files.
- **Replace with:** discriminated union (TS), enum with associated data (Rust/Swift), sealed class (Kotlin). Compiler enforces exhaustiveness.
- **CCN direction:** removes the dispatch ladder entirely; per-variant code stays the same.
- **--fix-eligible:** false (cross-file API change)

## R05 — Replace type-code with sum type / Enum dispatch

- **Languages:** python (with `match` or `dataclass`), ruby
- **Detect when:** Python code uses string `kind` field with `if/elif` dispatch ladders.
- **Replace with:** Python 3.10+ `match` on a class hierarchy or dataclass union; or a dispatch dict `{'a': handle_a, 'b': handle_b}`.
- **CCN direction:** dispatch ladder collapses to one lookup.
- **--fix-eligible:** false (usually multi-file)

## R06 — Replace conditional dispatch with table lookup

- **Languages:** all
- **Detect when:** function dispatches on a small finite set of values (4+ branches) to call a different handler with the same signature, all in the same file.
- **Replace with:** dict/map from value to handler reference; call via `table[key](args)`.
- **CCN direction:** drops from N (number of branches) to 1.
- **--fix-eligible:** true (when handlers stay in the same file)

## R07 — Decompose god function

- **Languages:** all
- **Detect when:** function exceeds 100 LOC AND CCN > 15. Often a "do all the things" controller.
- **Replace with:** identify natural boundaries (typically marked by blank lines or comment headers), extract each as a function (apply R02 repeatedly). Top-level reads as a sequence of named steps.
- **CCN direction:** parent drops to ~3-5 (one call per step); each child inherits a portion of original CCN.
- **--fix-eligible:** false (judgment-heavy; route to --plan)

## R08 — Hoist invariant out of loop

- **Languages:** all
- **Detect when:** inside a `for/while` loop, a computation does not depend on the loop variable (regex compile, date parse, schema construction, dict literal that doesn't change).
- **Replace with:** move the computation above the loop, reference the bound variable inside.
- **CCN direction:** unchanged, but performance improves and cognitive load drops slightly.
- **--fix-eligible:** true

## R09 — Replace inline conditional with named predicate

- **Languages:** all
- **Detect when:** an `if` condition spans 3+ joined boolean clauses (`a && b && (c || d)`).
- **Replace with:** extract the condition into a named boolean function (or local variable for one-off use).
- **CCN direction:** unchanged but readability improves; sometimes enables further simplification.
- **--fix-eligible:** true

## R10 — Iterator/pipeline chain over imperative accumulator

- **Languages:** ts, js, python, rust, kotlin, scala, swift
- **Detect when:** an imperative loop builds a list by `push/append`, applying filter+map operations in the middle. The loop has no early exit and no accumulating state beyond the list.
- **Replace with:** pipeline (`.filter().map()` in JS/TS; comprehension in Python; iterator chain in Rust). Loop disappears.
- **CCN direction:** drops from ~4-6 to 1.
- **--fix-eligible:** true (single-file)
- **Caveat:** Do not apply if the loop has early exit (`break`/`return`) or mutates external state. Cap at loops with <20 iterations of complexity per the rule.

## R11 — Replace inheritance with composition

- **Languages:** all OOP
- **Detect when:** subclass overrides only a subset of parent methods AND parent class has fields/methods unrelated to the subclass's purpose. **Liskov violation actually observable** (callers downcast, or branch on subclass type).
- **Replace with:** make the parent a collaborator (constructor injection); subclass becomes a wrapper holding the parent instance and the specific behavior.
- **CCN direction:** roughly even, but coupling drops sharply.
- **--fix-eligible:** false (cross-file API change)
- **Caveat:** Only propose if the LSP violation is *observable in the code* — do not propose on speculation.

## R12 — Memoize pure recursive function

- **Languages:** all
- **Detect when:** function is recursive, all parameters are hashable values (numbers, strings, tuples), no side effects, no I/O. Classic shape: Fibonacci, recursive descent over a static structure.
- **Replace with:** add memoization (`@functools.cache` in Python, `useMemo` for React-local, custom Map in JS/TS).
- **CCN direction:** unchanged at function level, but performance impact often huge. Surface as both a refactor *and* a performance win.
- **--fix-eligible:** true (decorator/wrapper add)

## R13 — Strategy pattern (only when problem matches)

- **Languages:** all OOP
- **Detect when:** **all four** must hold:
  1. A `switch`/`if-elif` ladder dispatches on a stable, finite set of "modes" (≥4 branches).
  2. Each mode's logic is genuinely complex (multi-statement, calls multiple helpers, not a one-liner).
  3. New modes are added by *external code* (plugins, config-driven), not internal commits.
  4. The dispatch ladder appears in **3+ places** (i.e., the same modes are dispatched on repeatedly).
- **Replace with:** Strategy pattern (interface + per-mode class + registry).
- **CCN direction:** orchestrator CCN drops to 1; each strategy stays at its current CCN.
- **--fix-eligible:** false
- **Caveat:** If any of the four conditions fails, prefer R06 (table lookup) — it solves the same problem with much less indirection.

## R14 — Command pattern (only when problem matches)

- **Languages:** all
- **Detect when:** code passes a function reference plus a bag of arguments around together repeatedly, OR needs undo/redo/queue/audit-log of operations.
- **Replace with:** Command object encapsulating action + args + optional undo.
- **CCN direction:** flat in CCN; reduces parameter passing and enables uniform handling.
- **--fix-eligible:** false
- **Caveat:** Only when the undo/queue/log requirement is *real*. Don't introduce Command for "future flexibility."

---

---

# Simplification Entries (S-prefix)

S-entries target **over-engineering and almost-dead code** — the "least amount of code possible" goal. Used by the `arch-simplification` subagent. Every S-finding must report `lines_deletable >= 1`.

These are deletion-biased: the recommendation is usually *remove* code, not transform it. CCN columns are usually null (unless the deletion also lowers CCN as a side effect, e.g. removing defensive branches).

## S01 — Inline single-implementation interface/abstract class

- **Languages:** ts, java, c#, kotlin, swift, python (Protocol/ABC), rust (trait, lower certainty)
- **Detect when:** an interface / abstract class / Protocol / trait has exactly one concrete implementation in the codebase, and CLAUDE.md/ADRs do not document an intent for a second.
- **Replace with:** delete the interface; update callers to reference the concrete class directly.
- **CCN direction:** unchanged.
- **Lines deletable:** size of the interface declaration + any factory plumbing.
- **--fix-eligible:** false (cross-file: callers must update)
- **Caveats:**
  - **Test seam:** if a mock/fake implementation exists in tests, the abstraction is legitimate — do not flag.
  - **Public API:** if the interface is exported from a package entry point, lower certainty.
  - **Recently added:** if added <30 days ago, the second impl may be in flight — lower certainty, mention recency.

## S02 — Pass-through wrapper

- **Languages:** all
- **Detect when:** function body is a single statement forwarding all args to another function with no logging, validation, type translation, default injection, or error mapping.
- **Replace with:** callers call the inner function directly; delete the wrapper.
- **CCN direction:** unchanged (wrapper had CCN 1, inner is independent).
- **Lines deletable:** wrapper body + signature.
- **--fix-eligible:** false (cross-file: callers update)
- **Caveats:** boundary wrappers (DTO/Mapper/Adapter prefix, files in `adapters/` or `api/serialization/`) translate external↔internal types and are legitimate. Do not flag.

## S03 — Always-same parameter

- **Languages:** all
- **Detect when:** function has a parameter where every one of ≥3 call sites passes the same literal.
- **Replace with:** drop the parameter; hard-code the value inside the function.
- **CCN direction:** parent unchanged; per-callsite call expression simplifies.
- **Lines deletable:** roughly (#callsites + 1 for parameter declaration).
- **--fix-eligible:** false (cross-file API change)
- **Caveats:** overlaps with R03 when the parameter is a boolean — orchestrator deduplicates.

## S04 — Unread config option

- **Languages:** all (config-format-dependent)
- **Detect when:** config key is declared (in schema, env file, settings class) but no code reads it.
- **Replace with:** delete the key from all configs and schemas.
- **CCN direction:** unchanged.
- **Lines deletable:** definition lines + any docs strings about the key.
- **--fix-eligible:** true (config edit only, single-file when key lives in one place; if key is duplicated across env files, it auto-routes to `--plan`)
- **Caveats:** dynamic env access (`process.env[varName]`) — if observed anywhere in the codebase, lower certainty for all env-key findings.

## S05 — Same-value config across environments

- **Languages:** all
- **Detect when:** config key has identical values across all environment configs (dev / staging / prod).
- **Replace with:** hard-code the value in code; delete the key from all configs.
- **CCN direction:** unchanged.
- **Lines deletable:** (envs - 1) × 1 line + config-loading code that may now be unnecessary.
- **--fix-eligible:** false (cross-file: code + multiple configs)
- **Caveats:** skip keys whose names imply environment-specific intent (`SECRET_*`, `*_TOKEN`, `*_API_KEY`, `*_PASSWORD`) — current sameness may be coincidental.

## S06 — Defensive code for impossible states

- **Languages:** ts (strict mode), rust, kotlin, swift, java (with `@NonNull`)
- **Detect when:**
  - null/undefined checks on values whose static type excludes null/undefined
  - try/catch around operations that don't throw (JS array index, plain dict access, pure arithmetic)
- **Replace with:** delete the defensive block.
- **CCN direction:** drops by the number of removed branches.
- **Lines deletable:** the defensive block.
- **--fix-eligible:** true (single-file)
- **Caveats:** dynamic-language code (Python without strict typing, plain JS without TS) — skip entirely; the check may catch real bugs.

## S07 — Speculative generic / type parameter

- **Languages:** ts, rust, kotlin, java, c#, swift
- **Detect when:** generic function or class where every call site uses the same concrete type for the type parameter.
- **Replace with:** monomorphize — drop the generic, use the concrete type directly.
- **CCN direction:** unchanged.
- **Lines deletable:** generic syntax overhead (small, but compiler complexity drops).
- **--fix-eligible:** false (API change)
- **Caveats:** public-API generics may be used by external consumers — lower certainty if exported from package entry point.

## S08 — Near-duplicate functions

- **Languages:** all
- **Detect when:** ≥2 functions in scope share ≥80% of body lines exactly, differing in 1-2 lines, and the difference is **data-like** (a string, a constant, a single method call) rather than **conceptual** (different domain meaning).
- **Replace with:** collapse into one function with a small parameter for the differing line(s). If the difference is conceptual (`validate_email` vs `validate_phone`), keep both even if implementation overlaps.
- **CCN direction:** unchanged or slightly higher in the collapsed function (one extra param check); total LOC drops.
- **Lines deletable:** roughly (lines_in_smaller_function - 2 added param lines).
- **--fix-eligible:** false (cross-call-site impact, judgment-heavy)

## S09 — Unused exported symbol

- **Languages:** ts, js, py, rust, java, kotlin
- **Detect when:** an exported function/class/constant has zero importers in the codebase.
- **Replace with:**
  - If also no internal usage in the same file → delete the symbol entirely.
  - If used internally → remove the export keyword (make it private).
- **CCN direction:** unchanged or drops if symbol body deleted.
- **Lines deletable:**
  - Delete entirely: full symbol body (often ≥5 lines).
  - Unexport only: 0 (one keyword change). **Surface unexport findings only as `catalog_gap_proposals`, not standard findings**, since they don't meet the `lines_deletable >= 1` bar.
- **--fix-eligible:** depends — full-delete is often single-file (true); cross-file deletes auto-route to `--plan`.
- **Caveats:** library/SDK code with public API contracts — even unimported symbols may be intentional. Lower certainty when scope includes a published package.

---

## What's deliberately NOT in this catalog

- **Visitor, Singleton, Factory** — high indirection cost, rarely net-reduce complexity in modern code.
- **Decorator (the GoF version, not Python decorators)** — composition usually achieves the same with less ceremony.
- **Speculative interface extraction** — only extract an interface when there are ≥2 implementations *or* when testing demonstrably needs it (R11 covers the real cases).

If a subagent thinks one of these is needed, it should *not* surface the finding — instead, propose adding to the catalog at the end of its output, with a justification.
