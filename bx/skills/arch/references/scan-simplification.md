# Scan: Simplification (over-engineering / least-code-possible)

Loaded by the orchestrator and passed to the `arch-simplification` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Workspaces` — list or "none"
- `Tier` — full | bounded | sample
- `Scope file list` — exact paths to scan
- `Intended Architecture summary` — 3-5 bullets
- `Refactor catalog` — full content of `refactor-catalog.md`. Use only S-prefixed entries. Cite by ID.

## Approach

For each S-entry in the catalog whose `languages` tag matches the file's language, run the entry's "detect when" trigger across the scope. Surface a finding only if **`lines_deletable >= 1`** and the certainty heuristic passes.

## Per-entry scanning hints

### S01 — Inline single-implementation interface/abstract class
```
Step 1: List interfaces/abstract classes/Protocols/traits in scope:
  TS/JS:    Grep "^(export )?(interface|abstract class) " or "type \w+ = "
  Python:   Grep "class \w+\(Protocol\)" or "class \w+\(ABC\)" or "@abstractmethod"
  Rust:     Grep "^pub trait " or "^trait "
  Java/Kt:  Grep "interface \w+" or "abstract class \w+"
Step 2: For each, count concrete implementations:
  TS:       Grep "implements <Name>" or `class \w+ extends <Name>`
  Python:   Grep "class \w+\(<Name>\)" or "<Name>\.register"
  Rust:     Grep "impl <Name> for"
Step 3: If exactly 1 impl AND no documented multi-impl intent in CLAUDE.md/ADRs → flag.

False-positive guard: Check if a mock/fake exists in tests directories — that's a legitimate test seam, do NOT flag.
```

### S02 — Pass-through wrapper
```
Step 1: Find functions whose entire body is a single statement of the form:
  `return <other_function>(<args>)` or
  `<other_function>(<args>)` (void)
  with `<args>` either identical to the wrapper's params or trivially renamed.

Step 2: Check the wrapper does no:
  - logging
  - validation
  - type translation (boundary use)
  - default value injection
  - error mapping

Step 3: If wrapper has ≥3 callers (for impact), flag.

False-positive guard: API/persistence boundary wrappers (translate external↔internal types) are legitimate. Skip if name suggests boundary (DTO/Mapper/Adapter prefix, or file in `adapters/`/`api/serialization/`).
```

### S03 — Always-same parameter
```
Step 1: For each function with ≥3 callers, check each parameter's argument across calls.

Step 2: If a parameter is passed the SAME LITERAL at every call site (≥3 sites), flag.
  - Same string: "always 'utf-8'"
  - Same number: "always 0"
  - Same boolean: "always true" — note: this overlaps with R03 (flag-arg refactor); that's fine, the orchestrator deduplicates

Step 3: Estimate lines_deletable: number of call sites × ~1 line saved + parameter declaration line.
```

### S04 — Unread config option
```
Step 1: Enumerate config keys from declared schemas:
  - JS/TS: zod/joi/yup schemas, env var schemas, .env.example
  - Python: pydantic Settings, dataclass with __init_fields__
  - Generic: read .env files for keys

Step 2: For each key, Grep the codebase for actual reads:
  - process.env.<KEY>
  - os.environ['<KEY>']
  - config.<key> or settings.<key>
  - schema.parse / Settings()

Step 3: Keys with zero reads → flag. lines_deletable = lines defining the key.

False-positive guard: Some keys are read via `process.env` destructuring with computed names (`process.env[varName]`). If you see dynamic env access in the codebase, lower certainty for all env-key findings.
```

### S05 — Same-value config across environments
```
Step 1: For each environment config (dev/staging/prod), parse and compare values.
Step 2: Keys with identical values across ALL envs → flag for hard-coding.
Step 3: lines_deletable = (envs - 1) × 1 line + config-loading code that may now be unnecessary.

False-positive guard: Some configs are "same now but designed to differ" (e.g. SECRET_KEY happens to be the same in two non-prod envs, but should differ). Skip keys whose name implies environment-specific intent (SECRET_*, *_TOKEN, *_API_KEY, *_PASSWORD).
```

### S06 — Defensive code for impossible states
```
Languages with strong static null-safety: ts (strict mode), rust, kotlin, swift, java (with @NonNull).

Step 1: Find null/undefined checks on values whose type does NOT include null/undefined:
  TS strict: Grep "if (!\w+)" or "<param> == null" where <param>'s type is non-nullable.
  Rust: explicit `Option::None` check on a non-Option value (compiler usually catches, but custom enums may slip through).
  Kotlin: `?.let` or null check on non-nullable type.

Step 2: Find try/catch around operations that don't throw:
  - try/catch around array index access (JS doesn't throw on out-of-bounds, returns undefined)
  - try/catch around plain dict/object access
  - try/catch around pure arithmetic (no division-by-zero or BigInt context)

Step 3: Flag with high certainty when type system proves the impossibility.

False-positive guard: Dynamic-language code (Python without strict typing, plain JS) — skip entirely. The check may still catch real bugs.
```

### S07 — Speculative generic / type parameter
```
Step 1: Find generic functions/classes:
  TS: `function foo<T>(...)` or `class Foo<T>`
  Rust: `fn foo<T>` or `struct Foo<T>`
  Kotlin/Java/C#: similar

Step 2: For each, find call sites and infer the concrete type used.

Step 3: If ALL call sites use the same concrete type for T → flag. Replace generic with concrete type.

False-positive guard: Public-API generics may be used by external consumers. Lower certainty if the symbol is exported from a package entry point.
```

### S08 — Near-duplicate functions
```
Step 1: For each pair of functions with similar names or in the same file, compare line-by-line ignoring whitespace.

Step 2: If ≥80% of lines match exactly AND the differing lines are ≤2 → flag.

Step 3: Recommend either:
  - Collapse into one function with a small parameter (when the difference is data-like)
  - Keep both (when the difference is conceptual — e.g. `validate_email` vs `validate_phone`, even if implementation similar)

Make the call in `recommended_refactor` and explain the reasoning.

lines_deletable = roughly (lines_in_smaller_function - 2 (for added param)).
```

### S09 — Unused exported symbol
```
Step 1: For each exported function/class/constant in scope:
  TS/JS: `export function|class|const` or `export { ... }`
  Python: lib API as defined by __all__ or all top-level non-underscore symbols
  Rust: `pub fn|struct|enum|trait` (excluding `pub(crate)`)

Step 2: Grep for importers of that symbol across the codebase:
  TS/JS: `import { <name> } from` or `import <name> from`
  Python: `from <module> import <name>` or `import <module>.<name>`
  Rust: `use <crate>::<name>`

Step 3: Zero importers → flag.

If also no internal usage in the same file → recommend deleting entirely (overlaps with /bx:clean at file level; here it's symbol-level).
If internal usage exists → recommend removing the export keyword (make it private).

lines_deletable = symbol body length (when deletable) OR 0 + 1 word change (when just unexporting). Surface unexport as `lines_deletable: 0` with a note — the orchestrator's filter (`lines_deletable >= 1`) will drop these. **Special case: surface unexport findings under `catalog_gap_proposals` with intent "low-impact but valuable hygiene" so the user can opt in via a future flag.**
```

## Output ordering

Sort by `lines_deletable × certainty` descending. Cap at 30 findings.

## Final output addendum

At the end of your findings, append two extra lines:

```
total_lines_deletable: <sum of all flagged findings' lines_deletable>
files_affected: <count of distinct files touched by your findings>
```

The orchestrator surfaces these in the report's top-line metric.
