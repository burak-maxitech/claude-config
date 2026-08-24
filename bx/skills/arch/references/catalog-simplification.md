# Catalog: Simplification (S-prefix)

S-entries target **over-engineering and almost-dead code** — the "least amount of code
possible" goal. Consumed by the `arch-simplification` subagent. Every S-finding must report
`lines_deletable >= 1`.

These are deletion-biased: the recommendation is usually *remove* code, not transform it.
Complexity columns are usually null, unless the deletion also lowers complexity as a side
effect (removing defensive branches does).

**Two entries carry a hard suppression** — `S01` at a Dependency Inversion boundary and
`S06` at a trust boundary. Both block a finding that would make the codebase *worse*, not
merely noisier. Suppressed instances are reported and counted, never silently dropped.

**Shared rules live in `catalog-rules.md`.** Read it alongside this file.

---

## S01 — Inline single-implementation interface/abstract class

- **Languages:** ts, java, c#, kotlin, swift, python (Protocol/ABC), rust (trait, lower certainty)
- **Detect when:** an interface / abstract class / Protocol / trait has exactly one concrete implementation in the codebase, and CLAUDE.md/ADRs do not document an intent for a second.
- **Replace with:** delete the interface; update callers to reference the concrete class directly.
- **CCN direction:** unchanged.
- **Lines deletable:** size of the interface declaration + any factory plumbing.
- **--fix-eligible:** false (cross-file: callers must update)
- **Hard suppression — Dependency Inversion boundary:** a port has exactly one adapter *by
  design*. Suppress (do not flag, do not lower certainty) when the interface's module maps to a
  layer boundary named in the Intended Architecture summary, when its name or path carries a
  boundary marker (`port`, `adapter`, `gateway`, `repository`, `provider`, `client`, `store`), or
  when implementer and consumer sit in different named layers. Suppressed instances are reported
  under `s01_suppressed` and counted in the report footer, never silently dropped.
  **Counterpart:** `D03` (DIP violation) reads the same evidence from the opposite direction —
  S01 asks "is this abstraction unearned?", D03 asks "is this concretion illegal?"
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
- **Hard suppression — trust boundary:** a type annotation is a compile-time claim about a
  runtime the compiler never sees. Suppress when the enclosing function is within one hop of a
  boundary marker: an entry-point path (`handlers`, `controllers`, `routes`, `api`, `cmd`,
  `adapters`, `middleware`), deserialization (`JSON.parse`, `json.loads`, `unmarshal`, `pickle`,
  `serde_json::from_`), an environment or config read, FFI, ORM row mapping, or a parameter of an
  exported entry point. The check you would delete is what makes the annotation true. Suppressed
  instances are reported under `s06_suppressed` and counted in the footer.
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
