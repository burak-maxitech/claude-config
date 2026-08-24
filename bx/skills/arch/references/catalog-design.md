# Catalog: Design Principles (D-prefix)

OO and SOLID design-principle violations at the type and module level. Consumed by the
`arch-structure` subagent. Every finding must cite an entry by ID in `cite_catalog_entry`.

**Shared rules live in `catalog-rules.md`.** Read it alongside this file.

**No D-entry is `--fix-eligible`.** Every one of these is cross-file by nature — changing a type
hierarchy, a signature, or a dependency direction touches callers the diff preview cannot show.
They route to `--plan`.

These entries are about **structure that resists change**, not style. A finding must name the
change that becomes expensive, not merely the principle that is bent. "This violates SRP" is not
a finding; "every new payment method requires editing this class, its enum, and three switch
statements" is.

---

## D01 — Liskov substitution violation

- **Languages:** ts, java, c#, kotlin, swift, python, ruby, php, scala
- **Detect when:** a subclass or interface implementation does any of:
  - throws on an inherited method — Grep overrides whose body is
    `throw new (NotImplemented|Unsupported)`, `raise NotImplementedError`, `panic!("not supported")`
  - **narrows a precondition** — adds a guard/assert at the top of an override that the base does
    not have, rejecting inputs the base accepts
  - **widens the return** — returns `null`/`None`/an error where the base contract promises a value
- **Replace with:** if the subtype cannot honor the contract, it is not a subtype. Split the
  interface (see D02), or replace inheritance with composition (see `R11` in
  `catalog-refactors.md`).
- **CCN / Cognitive direction:** n/a — not a complexity refactor.
- **--fix-eligible:** false
- **Severity signal:** `high` when callers hold the base type and cannot know which subtype they
  have — that is a latent runtime failure, not a style issue.
- **Caveats / false-positive guards:**
  - **Deliberate optional-capability pattern.** If the base type exposes a capability check
    (`supportsX()`, `canDoY`) that callers are documented to consult first, the throw is the
    contract, not a violation. Look for the check at call sites before flagging.
  - **Abstract intermediates.** A `NotImplementedError` in a class that is itself abstract and
    never instantiated is a template, not a violation.

## D02 — Interface segregation violation

- **Languages:** ts, java, c#, kotlin, swift, go, python (Protocol/ABC), rust (trait)
- **Detect when:** an interface declares ≥5 methods **and** at least one implementer stubs out
  ≥30% of them — empty bodies, `return null`, `pass`, `throw NotImplemented`, or a constant.
- **Replace with:** split along the lines the implementers already reveal. The stubbed subset in
  the thinnest implementer is usually the seam.
- **CCN / Cognitive direction:** n/a.
- **--fix-eligible:** false
- **Severity signal:** scales with implementer count — one fat interface with 6 implementers
  makes every new method a 6-file change.
- **Caveats / false-positive guards:**
  - **Test doubles.** Hand-written fakes in test directories legitimately stub everything. Count
    only production implementers.
  - **Framework-mandated interfaces.** Lifecycle interfaces imposed by a framework
    (`ApplicationListener`, `IDisposable`, React class-component methods) are not the project's
    to segregate — skip.
  - **Go convention.** Small interfaces defined at the *consumer* are idiomatic; a large interface
    defined at the *producer* is the smell. Check where it is declared.

## D03 — Dependency inversion violation

- **Languages:** all
- **Detect when:** a module on an **inner** layer (as named in the Intended Architecture summary
  — domain, core, entities, use-cases) imports a **concrete infrastructure** type: a DB client,
  HTTP client, ORM entity, filesystem, clock, env reader, or a cloud SDK.
  - Grep inner-layer files for: `from .*(prisma|sequelize|sqlalchemy|mongoose|axios|requests|boto3|aws-sdk|fs|os\.environ|process\.env)`
  - Also flag `new ConcreteThing()` inside a domain service where the type crosses a layer.
- **Replace with:** invert it — the inner layer declares the interface it needs, the outer layer
  implements it. This is the port/adapter shape.
- **CCN / Cognitive direction:** n/a.
- **--fix-eligible:** false
- **Counterpart:** `S01` in `catalog-simplification.md` reads the same evidence from the opposite
  direction. S01 asks "is this abstraction unearned?"; D03 asks "is this concretion illegal?"
  **S01 is hard-suppressed at exactly the boundaries D03 protects** — the two must never fire on
  the same interface, and if you believe they should, that is a finding about the architecture
  summary, not about the code.
- **Severity signal:** `high` when the import makes the inner layer untestable without the
  infrastructure running.
- **Caveats / false-positive guards:**
  - **Requires a named layering.** If the Intended Architecture summary names no layers, or says
    "explicitly no layers — small CLI", **do not flag this entry at all.** There is no direction
    to invert. Inferring a layering from directory names alone is not sufficient evidence here.
  - **Type-only imports.** A TS `import type` of a shape used for structural typing does not
    create a runtime dependency — lower certainty sharply or skip.

## D04 — Law of Demeter chain

- **Languages:** ts, js, java, c#, kotlin, python, ruby, php, scala
- **Detect when:** a call chain of ≥3 dereferences (`a.b().c().d()`, `a.b.c.d()`) where the
  intermediate types come from **≥2 different modules**, appearing at **≥3 sites**.
- **Replace with:** add the operation the caller actually wants to the first object ("tell, don't
  ask"), or pass the leaf value in directly.
- **CCN direction:** unchanged. **Cognitive direction:** drops slightly at each site.
- **--fix-eligible:** false (the fix adds a method to another module)
- **Severity signal:** the chain is a coupling multiplier — every intermediate type's shape is now
  frozen by this caller. Severity rises with the number of sites.
- **Caveats / false-positive guards:**
  - **Fluent builders and query DSLs** (`qb.select().from().where()`, `expect(x).to.be.ok`) are
    designed as chains — skip entirely.
  - **Immutable value chains** within one module (`date.plus(1).format()`) are not a Demeter
    problem; the rule is about crossing ownership boundaries.
  - **Optional chaining** (`a?.b?.c`) is often defensive navigation of one nullable structure, not
    a train wreck.

## D05 — Anemic domain model

- **Languages:** ts, java, c#, kotlin, python, php, scala, ruby
- **Detect when:** a type whose members are **only** fields plus accessors (no behavior beyond
  get/set/`toString`/serialization) has a sibling `*Service` / `*Manager` / `*Helper` / `*Utils`
  that takes it as its first parameter in ≥3 methods and mutates or interprets its fields.
- **Replace with:** move the rules that only touch that type's own fields onto the type. What
  needs collaborators stays in the service.
- **CCN / Cognitive direction:** n/a — total complexity is conserved, it relocates.
- **--fix-eligible:** false
- **Severity signal:** `medium` normally. `high` when the same invariant is enforced in more than
  one service — that is where the bugs come from.
- **Caveats / false-positive guards:**
  - **DTOs, wire types, and generated code are supposed to be anemic.** Skip anything under
    `dto/`, `schemas/`, `__generated__/`, `*.pb.go`, `*_pb2.py`, or produced by an ORM/codegen.
  - **Deliberate functional style.** If the Intended Architecture summary says the project
    separates data from behavior on purpose (common in functional codebases, Redux state,
    Elm-style architectures), mark `respects_documented_decision: false` rather than recommending
    the move — and do not propose it in `--fix` or `--plan` without confirmation.

## D06 — Feature envy

- **Languages:** ts, js, java, c#, kotlin, python, ruby, php, scala
- **Detect when:** a method references another single type's members (fields or getters) **more
  often than its own** — count `other.` dereferences against `this.`/`self.` within the body,
  requiring ≥4 references to the other type and a ratio ≥2:1.
- **Replace with:** move the method to the type it envies, or extract the envious part.
- **CCN direction:** unchanged. **Cognitive direction:** drops in the origin type.
- **--fix-eligible:** false
- **Severity signal:** `low` for one method; `medium` when several methods in the same class envy
  the same type — that is a misplaced responsibility, not a stray method.
- **Caveats / false-positive guards:**
  - **Coordinators legitimately envy.** Controllers, orchestrators, mappers, and builders exist to
    read other types. Skip anything whose name or path marks it as one.
  - **Visitors and serializers** are defined by reading another type's shape.

## D07 — Primitive obsession at a boundary

- **Languages:** ts, java, c#, kotlin, swift, rust, scala, python (with typing)
- **Detect when:** the same domain concept crosses **≥5 public signatures** as a bare primitive —
  look for parameter names matching `(user|customer|order|account|tenant)?_?id`, `email`,
  `amount|price|total|cost`, `currency`, `url`, `token` typed as `string` / `int` / `number` /
  `float`, in exported functions or public methods.
- **Replace with:** a small wrapper type (branded type in TS, newtype in Rust, value object
  elsewhere) that makes the parameter order un-swappable and centralizes validation.
- **CCN / Cognitive direction:** n/a.
- **--fix-eligible:** false
- **Severity signal:** `high` when two same-typed primitives sit **adjacent** in a signature
  (`transfer(fromId: string, toId: string, amount: number)`) — that is a silently swappable
  argument pair, a real defect class, not a preference.
- **Caveats / false-positive guards:**
  - **Money as a float** is a correctness bug in its own right; if you find it, that is the
    finding — do not bury it in a modelling suggestion.
  - **Serialization boundaries** legitimately use primitives; the entry targets *internal* public
    APIs, not JSON schemas or DB column types.
  - **Small codebases.** Below ~5 uses the wrapper costs more than it saves. The ≥5 threshold is
    binding, not advisory.

## D08 — God class

- **Languages:** ts, js, java, c#, kotlin, python, ruby, php, scala
- **Detect when:** a class has **>20 members** (fields + methods) **and** low cohesion — its
  fields partition into ≥2 groups used by disjoint sets of methods. Approximate cohesion by
  building a field→method usage map and looking for a partition with no overlap.
- **Replace with:** split along the field partition — each group plus the methods that use it
  becomes a type. The partition is the design; do not invent one.
- **CCN direction:** unchanged in total. **Cognitive direction:** drops per resulting type.
- **--fix-eligible:** false
- **Distinct from god *function*** (`R07`), which is about one oversized body. D08 is about a type
  holding unrelated responsibilities, and the two frequently co-occur in the same file — the
  orchestrator deduplicates by location.
- **Severity signal:** rises with fan-in. A god class nothing imports is a cleanup task; one that
  30 modules import is a change-amplification bottleneck.
- **Caveats / false-positive guards:**
  - **Framework base classes and generated clients** (an API client with one method per endpoint)
    are large by design and cohesive by construction — skip.
  - **Facades.** A deliberate facade over a subsystem is large on purpose; check whether the
    Intended Architecture summary names it.
  - **Test fixtures and page objects** are excluded.
