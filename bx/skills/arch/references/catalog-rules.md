# Catalog Rules — the shared contract for every `/bx:arch` catalog

**Canonical owner** for the catalog schema and the rules that bind every entry, whatever its
prefix. A per-prefix catalog may carry a short preamble stating how these rules land for its own
family — but it states no rule that is not derivable from this file, and when the two disagree,
this file wins.

Each entry is a *technique* or a *defect class*, not a pattern name. Subagents must cite an entry
by ID in `cite_catalog_entry`. Entries marked `--fix-eligible: true` may be auto-applied in
`--fix` mode (still gated by per-finding diff preview).

## The catalogs

| File | Prefix | Consumed by |
|------|--------|-------------|
| `catalog-refactors.md` | `R` — complexity-reducing refactor techniques | `arch-refactors` |
| `catalog-simplification.md` | `S` — over-engineering and almost-dead code | `arch-simplification` |
| `catalog-design.md` | `D` — OO / SOLID design-principle violations | `arch-structure` |
| `catalog-robustness.md` | `C`, `E`, `X` — concurrency, error safety, scalability | `arch-robustness` |

**Each agent receives only its own catalog.** Splitting them is what keeps the token cost flat
while the entry count grows: the pre-split single file was ~16.5KB and was passed to two agents,
most of which neither could cite.

## Entry schema

Every entry states `Languages`, `Detect when`, `Replace with`, `--fix-eligible`, and
`Caveats / false-positive guards`. Beyond those four, which fields apply depends on what the
family is *for*:

| Field | Required on | Meaning |
|-------|-------------|---------|
| `CCN direction` + `Cognitive direction` | `R` entries | The expected change in each metric. `R` entries exist to reduce complexity, so this is their justification. |
| `Lines deletable` | `S` entries | What the deletion actually saves. |
| `Severity signal` | `D`, `C`, `E`, `X` entries | What determines consequence for this defect class — the input to the `severity` band, not a replacement for it. These families do not reduce complexity, so they carry no complexity direction; a file-level "complexity direction is n/a throughout" statement covers the whole catalog. |

Optional anywhere: `Citation`, `Counterpart`, `Hard suppression`.

`Severity signal` **informs** the severity choice; the binding anchors are still
`finding-rubrics.md`'s. Where an entry's signal and the rubric anchors disagree, the rubric wins
and the disagreement is worth a `catalog_gap_proposals` note.

## Binding rules

- **The languages tag is binding.** A subagent may not propose an entry on a file whose language
  is not listed. Do not recommend a TypeScript-only technique on a Python file.
- **A complexity reduction must be plausible on at least one metric.** Each R-entry states its
  expected direction for **both** cyclomatic and cognitive complexity. An entry whose CCN
  direction is "unchanged" earns its place on cognitive complexity alone, and findings citing it
  must carry the cognitive pair — see `R01` and `R09`. The orchestrator's Step 5.1 gate drops a
  refactor finding only when it reduces neither metric.
- **Only single-file, non-API-breaking refactors are `--fix-eligible.`** Multi-file or
  API-touching entries route to `--plan` instead. **No `D`, `C`, `E`, or `X` entry is
  `--fix-eligible`** — adding an `await`, a timeout, or a lock changes runtime behavior in ways a
  diff preview cannot reveal, and `--fix` does not run tests afterward.
- **No GoF patterns by default.** A few appear (Strategy, Command) but only with strict
  "detect when" triggers that catch the *problem*, not the *surface*.
- **A hard suppression is not a certainty penalty.** Where an entry declares one (`S01` at a
  Dependency Inversion boundary, `S06` at a trust boundary), the finding is not emitted at all —
  it is reported under the entry's `*_suppressed` key and counted in the report footer. Never
  silently discarded, never downgraded to a low-certainty finding.
- **Scoring is not defined here.** `severity`, `certainty`, `effort_estimate`, `evidence`, and
  `why_this_might_be_wrong` are owned by `finding-rubrics.md`, passed to every agent as the
  `Scoring contract`.

## Proposing a new entry

If a subagent finds a recurring smell that no entry covers, it must **not** surface a finding for
it. Instead it appends a `catalog_gap_proposals` block at the end of its output (smell,
occurrence count, proposed entry skeleton). The orchestrator surfaces these in the report footer
for later review — they are proposals about the *catalog*, never a side channel for findings that
failed a gate.

## What's deliberately NOT in these catalogs

- **Visitor, Singleton, Factory** — high indirection cost, rarely net-reduce complexity in modern code.
- **Decorator (the GoF version, not Python decorators)** — composition usually achieves the same with less ceremony.
- **Speculative interface extraction** — only extract an interface when there are ≥2 implementations *or* when testing demonstrably needs it (R11 covers the real cases).
- **Security vulnerabilities** — `/bx:review --security` owns those. `D`/`E` entries cover
  *architectural* robustness (where validation lives, whether failures are handled), not
  exploitability.

If a subagent thinks one of these is needed, it should propose it under `catalog_gap_proposals`
with a justification rather than surfacing the finding.
