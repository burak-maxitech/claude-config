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

## What's deliberately NOT in this catalog

- **Visitor, Singleton, Factory** — high indirection cost, rarely net-reduce complexity in modern code.
- **Decorator (the GoF version, not Python decorators)** — composition usually achieves the same with less ceremony.
- **Speculative interface extraction** — only extract an interface when there are ≥2 implementations *or* when testing demonstrably needs it (R11 covers the real cases).

If a subagent thinks one of these is needed, it should *not* surface the finding — instead, propose adding to the catalog at the end of its output, with a justification.
