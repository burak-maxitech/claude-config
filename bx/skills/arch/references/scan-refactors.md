# Scan: Refactor Opportunities (catalog-driven)

Loaded by the orchestrator alongside `refactor-catalog.md` and passed to the `arch-refactors` subagent.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Workspaces` — list or "none"
- `Linter` — name + invocation, OR "heuristic"
- `Tier` — full | bounded | sample
- `Scope file list` — exact paths to scan
- `Intended Architecture summary` — 3-5 bullets
- `Refactor catalog` — full content of `refactor-catalog.md` (you must cite entries by ID)

## Approach

For each catalog entry whose `languages` tag matches the file's language, scan for the entry's "detect when" trigger. Report a finding when:

1. The trigger matches in code
2. You can estimate `ccn_projected < ccn_current` (or for non-CCN-changing refactors like R09, the catalog notes it explicitly)
3. The refactor would not violate the Intended Architecture summary

## Per-entry scanning hints

### R01 — Guard-clause flatten
```
Grep: functions with indentation depth ≥3, body shape "if (X) { ... } else { ... }"
Heuristic: any line in a function indented ≥12 spaces (or 3 tabs) inside conditional branches.
```

### R02 — Extract pure function
```
Look for: functions >30 LOC with internal blank-line-separated blocks, where one block:
  - reads only locals
  - assigns to one local
  - has no I/O or async calls
  - is 5-20 lines long
```
Cite the block's lines as the extraction target.

### R03 — Replace flag argument with two functions
```
Grep functions with parameter type matching: boolean | bool | True/False default.
For each match, scan the function body: does the FIRST conditional check that parameter?
For each match, scan callers (Grep): do all callers pass a literal true/false?
If yes to both: this is R03.
```

### R04 — Discriminated union (TS/JS/Rust/Swift/Kotlin/Scala)
```
Grep for patterns: `kind: '<literal>'` or `type: '<literal>'` in object literals or class instances.
For each "kind" string, count distinct values.
Then Grep for dispatch ladders: `if (x.kind === ` or `match x.kind` or `switch (x.kind)`.
Count occurrences. If ≥2 dispatch sites and the language supports tagged unions: R04 candidate.
```

### R05 — Sum type / Enum dispatch (Python/Ruby)
Same logic as R04 but Python-flavored: `isinstance` ladders or `if x.kind == '...':` chains. R05 only if Python ≥3.10 (for `match`) — otherwise propose dispatch dict.

### R06 — Table-lookup dispatch
```
Look for: switch/if-elif ladder, ≥4 branches, all branches CALL a function with the same signature.
The handlers are all in the same file (key restriction).
The dispatch key is a primitive value.
```

### R07 — Decompose god function
Already covered by `arch-structure` Step 3. Still surface here if the function's body has a *clear* decomposition (visible blank-line separated blocks). Otherwise leave to structure subagent and let consolidation deduplicate.

### R08 — Hoist invariant
```
Grep for inside-loop computations:
  - new RegExp(...) inside `for`/`while`
  - JSON.parse(<literal>) inside loop
  - `re.compile(<literal>)` inside loop (Python)
  - `datetime.strptime` of a literal format inside loop
```

### R09 — Named predicate
```
Grep: `if (<expr1> && <expr2> && (<expr3> || <expr4>))` — 3+ joined boolean clauses.
```

### R10 — Iterator/pipeline chain
```
Look for: imperative loop:
  result = []
  for x in coll:
    if cond: continue        // optional
    y = f(x)                 // optional
    if other_cond: continue  // optional
    result.append(y)
With NO break/return inside the loop.
With NO state mutated outside `result`.
```

### R11 — Replace inheritance with composition
```
Look for:
  - subclass class definitions
  - downcasting in callers (e.g. `if (x instanceof SubClass)`, `isinstance(x, SubClass)`)
  - parent class with fields/methods unrelated to the subclass's purpose

Only surface when downcasting is observable. Otherwise certainty too low.
```

### R12 — Memoize pure recursive function
```
Grep for: function calls itself by name (recursive).
Check: arguments are all primitive/hashable (no objects, no callbacks).
Check: no I/O, no print/log, no global mutation, no async.
Check: no existing @cache/@lru_cache decorator (Python) or memo wrapper (JS/TS).
```

### R13 — Strategy (rare)
All four conditions must hold (see catalog). If any fail, prefer R06 instead.

### R14 — Command (rare)
Only when undo/queue/log is documented as a need. If not, do not surface.

## Output per finding

Same JSON-shaped format as `scan-structure.md`. Required additional field: `cite_catalog_entry` set to the entry ID (e.g. `"R03"`).

Cap output at 30 findings, ordered by `severity × certainty / effort_weight`.

## Special: catalog gaps

If during scanning you encounter a recurring code smell that no catalog entry covers, do not silently surface a finding. Instead, append to the very end of your output:

```
catalog_gap_proposals:
  - smell: <description of the recurring pattern>
    occurrences: <count>
    proposed_entry: <skeleton: name, detect-when, replace-with, languages tag>
```

The orchestrator will surface these in the report footer for the user to review later.
