# Design: `/bx:arch` Review Depth v2 — calibration, robustness, and a point of view

**Date:** 2026-08-24
**Status:** Approved (design + plan), implementing
**Author:** Session 58 with Claude
**Ships as:** bx plugin v2.3.0

---

## Problem

`/bx:arch` describes itself as "a staff engineer doing a quarterly architecture health check."
Reading the full skill surface — `SKILL.md`, eight reference files, four agent definitions —
shows it is something narrower: a very good **function-level refactor scanner**. Of ~23 catalog
entries, roughly 20 are function-local. Three distinct problems.

### 1. Three rules are actively wrong

Following the skill as written makes the architecture worse in three places.

**S01 recommends deleting Dependency Inversion.** `arch-simplification` flags any
interface / Protocol / trait with exactly one concrete implementation and reports
`lines_deletable`. Its only guards are "a mock exists in a test directory" and "documented
multi-impl intent." But a port in a hexagonal architecture has exactly one adapter *by design* —
that is DIP working. The skill will confidently recommend inlining the one abstraction keeping
the domain independent of infrastructure.

**S06 deletes validation at trust boundaries.** "Defensive code for impossible states" removes
null checks whose declared types prove non-nullability. A type annotation is a compile-time
claim about a runtime the compiler never sees: deserialized JSON, request bodies, env vars, FFI
returns, and ORM row mappings all cross into the type system carrying no such proof. The current
guard is only "skip dynamic languages," which addresses a different risk entirely.

**The CCN sanity gate deletes the catalog's own quick wins.** Step 5.1 drops refactor-dimension
findings where `ccn_projected >= ccn_current`, and `arch-refactors` is instructed not to emit
them at all. But the catalog states **"CCN direction: unchanged"** for both `R01`
(guard-clause flatten) and `R09` (named predicate) — two of the six `--fix-eligible` entries, and
two of the three Step 5.6 names as quick wins. They can never reach the report.

The root cause is a metric mismatch: **the catalog reasons about cognitive complexity while the
skill only measures cyclomatic complexity.** R01's own entry says so — "CCN direction: unchanged
(same decision points) but cognitive complexity drops sharply. Cognitive complexity is what the
linter usually flags" — yet nothing in Step 0, `scan-structure.md`, or the finding schema ever
measures it. Both agent descriptions advertise "cyclomatic/cognitive complexity hotspots."

### 2. Whole dimensions are absent

| Dimension | Current coverage |
|---|---|
| Cyclomatic complexity | The one well-covered area |
| Cognitive complexity | Named in two agent descriptions, never measured |
| OOP / SOLID | None. SRP only via a >100-LOC proxy; DIP actively inverted by S01 |
| Architectural patterns | Layering checked **only if documented** (`scan-structure.md` Step 5 skips otherwise) |
| Thread safety / concurrency | None, in any of the four scanners |
| Error safety / robustness | None — and S06 actively removes error handling |
| Scalability | Micro only (N+1, O(n²), hot loops); nothing architectural |

### 3. The finding contract is uncalibrated

Four agents are asked for `severity: low|medium|high` and `certainty: 0.0–1.0` with **no
rubric**. The orchestrator then gates on `certainty < 0.5`, ranks by
`severity_weight × certainty / effort_weight`, and groups by `effort_estimate`. The entire
pipeline rests on three numbers calibrated independently by four agents that never see each
other's output. Nothing obliges a finding to cite the evidence behind its confidence, and there
is no adversarial pass anywhere in the skill.

---

## Decisions (locked with user)

| # | Decision | Choice |
|---|---|---|
| 1 | Scope | Everything in one pass |
| 2 | Where C/E/X live | New 5th agent `arch-robustness`; D goes to `arch-structure` |
| 3 | Catalog organization | Split per prefix; each agent receives only its own entries |
| 4 | S01 vs DIP | **Hard suppression** at layer boundaries named in the Step 1 summary |
| 5 | CCN gate | **Measure cognitive complexity**; gate on whichever metric the finding claims |
| 6 | Report shape | Thesis on top; findings regrouped by theme |
| 7 | New dimensions | On by default; per-agent caps 30 → 15 |
| 8 | `--fix` for D/C/E/X | **None.** Report and plan only |
| 9 | S06 | Keep, with trust-boundary suppression |
| 10 | Acceptance | Blind rehearsal on changed surfaces (ambiguity ≤ 2), then ship |

Rationale for the close calls:

- **(2) A fifth agent, not four broader ones.** `arch-performance`'s system prompt is built
  around "static analysis cannot replace a profiler" — the correct frame for an O(n²) suspect
  and the wrong frame for a missing timeout, which is a high-precision static finding. Merging
  C/E into it would blunt both mandates.
- **(4) Suppression, not merge.** Merging S01 with a D03 counter-finding only works when both
  agents happen to hit the same location, and needs cross-agent consolidation logic. Suppression
  is deterministic and makes the Step 1 Intended Architecture summary — which already exists and
  is already passed to every agent — actually load-bearing rather than advisory.
- **(8) Nothing new is `--fix`-eligible.** Adding an `await`, a timeout, or a lock changes runtime
  behavior in ways a diff preview cannot reveal, and `--fix` explicitly does not run tests
  afterward (`fix-mode.md`, "What this mode does NOT do"). Design findings are cross-file by
  nature and were already excluded.

---

## Architecture

### Finding contract (`references/finding-rubrics.md`)

Canonical owner for the three rubrics and the two new fields, per the S57 named-owner principle.
All five scan files and all five agents cite it; none restates the anchors.

**Severity** = blast radius × likelihood × reversibility.

| Band | Anchor |
|---|---|
| `high` | Crosses a module boundary or has ≥5 dependents, **or** can produce incorrect results, data loss, or an outage. Hard to reverse once shipped. |
| `medium` | Contained to one module; measurably degrades maintainability or performance. |
| `low` | Local readability or hygiene; trivially reversible. |

**Certainty** by *evidence class*, never by confidence feeling.

| Band | Anchor |
|---|---|
| `0.90–1.00` | Read the definition **and** every call site / implementer in scope. |
| `0.70–0.89` | Read the definition; grepped and counted callers; did not read all of them. |
| `0.50–0.69` | Pattern matched within one file; callers not examined. |
| `< 0.50` | Inferred from naming or partial context. Dropped by the Step 5.2 gate unless `severity: high` or `lines_deletable >= 20`. |

**Effort** — `trivial`: one edit site, <10 lines, no signature change · `small`: one file,
<50 lines, no public API change · `medium`: 2–5 files, or a signature change with a bounded
caller set · `large`: cross-module, public API, or needs a migration or rollout.

**Two new mandatory fields on every finding, every dimension:**

- `evidence` — the quoted lines, grep counts, or enumerated call sites justifying the certainty
  band. This is what makes certainty auditable instead of asserted; `/bx:seo` learned the same
  lesson with verbatim excerpts (S47).
- `why_this_might_be_wrong` — one sentence. Architectural claims are opinion-adjacent and the
  skill has no adversarial pass; this is the cheapest available precision gain. The expensive
  alternative is a verifier subagent per finding.

### Cognitive complexity

**Detection** (Step 0 linter table gains a row): `eslint-plugin-sonarjs`
(`sonarjs/cognitive-complexity`) for JS/TS. Neither `ruff` nor `lizard` nor `radon` computes
cognitive complexity — those stacks fall back to the heuristic, and the report footer must
disclose which path ran, per the existing `linter: heuristic` disclosure convention.

**Heuristic** (simplified Sonar): +1 per decision point; **+1 additional per level of nesting**
at that point; +1 per break in a boolean-operator sequence; +1 for recursion. The nesting term is
what makes guard-clause flattening score a genuine reduction while CCN stays flat.

**Schema:** findings gain `cognitive_current` / `cognitive_projected` alongside the CCN pair.

**Gate (Step 5.1) becomes:** drop a refactor-dimension finding only when
`ccn_projected >= ccn_current` **AND** `cognitive_projected >= cognitive_current`. A catalog
entry whose stated CCN direction is "unchanged" must supply a cognitive delta or it is not
surfaceable. `arch-refactors`'s "skip them up front to save tokens" instruction is updated to
match, or it re-creates the bug at source.

### S01 boundary suppression

Suppress when **either** holds:

1. The interface's module maps to a layer boundary named in the Step 1 Intended Architecture
   summary (port, adapter, gateway, repository, or any layer the summary names).
2. Its implementer and its consumer sit in different named layers.

Suppressed findings are **counted and disclosed in the footer**, never silently dropped — the
S57 no-silent-caps rule. When the architecture summary was *inferred* rather than read from docs,
the footer says so, because suppression is then only as good as the inference.

`D03` (DIP violation) is the inverse check over the same evidence and cites S01 as its
counterpart, so the tension is visible in the catalog rather than buried in agent behavior.

### S06 trust-boundary suppression

Suppress when the enclosing function is within one hop of a boundary marker:

- path matches `handlers|controllers|routes|api|cmd|adapters`;
- body contains `JSON.parse` / `json.loads` / deserialize / unmarshal / pickle;
- reads `process.env` / `os.environ`;
- FFI (`ctypes`, cgo, N-API);
- ORM row → object mapping;
- the value originates in a parameter of an exported entry point.

Same footer disclosure. Genuinely impossible states *inside* the domain still get flagged.

### New catalog entries (31)

All carry the existing schema (languages tag, detect-when, replace-with, false-positive guard)
and all are `--fix-eligible: false`.

**D — design principles (8).** D01 LSP violation (override throws `NotImplementedError`, narrows
preconditions, or widens the return type) · D02 ISP violation (interface ≥5 methods where an
implementer stubs ≥30%) · D03 DIP violation (inner-layer module importing a concrete
infrastructure type) · D04 Law of Demeter chain crossing ≥2 module boundaries at ≥3 sites ·
D05 anemic domain model (accessor-only type plus a sibling `*Service` holding all its rules) ·
D06 feature envy · D07 primitive obsession at boundaries (raw `string`/`int` for id, email,
money, or date across ≥5 public signatures) · D08 god class (>20 members; fields used by disjoint
method groups).

**C — concurrency / thread safety (8).** C01 module-level mutable state written from a request or
event handler · C02 check-then-act without atomicity (TOCTOU cache fill) · C03 lock held across
an await or blocking call (`Arc<Mutex>` across `.await`; `synchronized` around I/O) · C04 floating
async work (unawaited promise; goroutine with no lifetime owner; ignored `err`) · C05 unbounded
concurrency (`Promise.all` / `gather` over an unbounded collection, no semaphore) · C06 unsafe
lazy singleton / double-checked locking · C07 cancellation or context not propagated across an
async boundary · C08 shared-instance state idioms (Python mutable default arg; class-level
mutable attribute; JS module-scope object reused per request).

**E — error safety / resource lifecycle (8).** E01 swallowed exception (`catch {}`,
`except: pass`, `.catch(() => {})`) · E02 catch-all discarding the cause (no chaining, `from e`,
or `%w`) · E03 network, subprocess, or DB call with no timeout · E04 no retry or backoff at a
transient boundary · E05 resource acquired without `finally` / `with` / `defer` / `using` ·
E06 `unwrap()` / `expect()` / `!` / `as!` on a non-test path · E07 multi-step external mutation
with no rollback or idempotency key · E08 exceptions as control flow across a module boundary.

**X — scalability (7).** X01 unbounded result set (no limit or pagination) · X02 whole-collection
load into memory · X03 in-process state blocking horizontal scale (local session, cache, lock, or
counter treated as authoritative) · X04 synchronous fan-out to N services in a request path ·
X05 unbounded queue or buffer with no backpressure · X06 per-request connection creation instead
of pooling · X07 full-scan batch job where a delta scan is available.

### Theme synthesis (new Step 5.7)

The report is currently a list and never a judgment. A real architecture review has a thesis.

1. Cluster surviving findings by shared module prefix, shared layer-boundary crossing, or shared
   root mechanism (same catalog family).
2. **A theme requires ≥3 findings drawn from ≥2 dimensions.** This is what stops a theme from
   being one agent's output relabelled.
3. Rank themes by summed rank score; take the top 3.
4. Each theme renders: a one-sentence thesis, its evidence set, and the single highest-leverage
   first move.
5. Findings belonging to no theme go to an "Other findings" section, tables grouped by dimension
   exactly as today. **No finding is dropped by theming.**

### Ranking

`scale-strategy.md` computes churn and import fan-in today, but only to *select files to sample*
on >500-file repos — the numbers are discarded afterward, and on smaller repos churn is never
computed at all. Compute both on every tier and feed them into the Step 5.4 rank score. A
CCN-30 function nobody touches is not the problem; a CCN-15 function changed 40 times in 90 days
is. Complexity × churn × fan-in is the standard architectural hotspot signal and the data is
already being gathered.

### Dangling contracts closed in the same pass

- `scan-refactors.md:129` promises the orchestrator will surface `catalog_gap_proposals` "in the
  report footer," but `report-template.md`'s footer has no such slot. Add it.
- `scan-simplification.md:159` instructs the agent both to drop unexport findings
  (`lines_deletable >= 1` is mandatory) and to surface them under `catalog_gap_proposals` — a
  self-contradiction, and a misuse of a channel meant for catalog gaps rather than findings.

---

## Interfaces changed outside the skill

Four sites cite what this design renames or reshapes (S45 sibling-echo rule):

| Site | Dependency | Action |
|---|---|---|
| `bx/skills/tests/references/test-smell-catalog.md:3` | Cites `bx:arch/references/refactor-catalog.md` as its schema source | Repoint to `catalog-rules.md` |
| `bx/agents/arch-simplification.md:20` | "S-prefixed entries in `refactor-catalog.md`" | Repoint to `catalog-simplification.md` |
| `workflow.md:328` | Names the catalog by path | Update path |
| `bx/skills/health/references/state-buckets.md:94-97` | Describes arch's default report shape and top-line metric | Update for thesis-first output |

`docs/key-decisions.md:141` also names the catalog but is archived history — left as written.
`bx/skills/tests/SKILL.md:52,137` cite `../arch/references/scale-strategy.md`, which is extended
but not renamed — no break.

---

## Acceptance

**Blind rehearsal on the changed surfaces**, per S56: agents execute only the rewritten Step 5,
`finding-rubrics.md`, and a sample of new catalog entries against a small fixture repo, logging
every ambiguity and every place they had to guess. **Pass bar: decision-log ambiguity count ≤ 2**
— the `doc-migrator` benchmark, which landed at 2 after starting at 5.

Plus the mechanical checks: `assert-doc-schema.sh`, `check-doc-rule-consistency.sh`, the
citation-resolution loop over every `../<skill>/references/*.md` (resolved against the **skill
base directory**, S48), and a grep proving `refactor-catalog` survives only in
`docs/key-decisions.md`.

### Result — six waves, gate not met, shipped with the residual recorded

Three surfaces were rehearsed; Step 5 and the report template three times each, scan+rubrics twice.

| Surface | Rounds | Ambiguity count |
|---------|--------|-----------------|
| Step 5 consolidation | 3 | 15 → 12 → 11 |
| Report template | 3 | 24 → 18 → 12 |
| Scan + rubrics | 2 | 12 → 12 |

**The ≤2 bar was not reached, and the raw count stopped being the useful metric after wave 2.**
The bar came from `doc-migrator`, a single-purpose file of ~100 lines; the surface here is ~1000
lines across five files. The rehearsal prompt was also stricter than S56's — it asked agents to log
anything "two careful readers could execute differently, even if you found a reasonable answer", so
the final logs contain entries the agents themselves label *correct literal reading* and *latent,
not exercised*. Two entries in the last template round were errors in the rehearsal's own input
data that the template correctly caught.

What the counts hide is the severity collapse:

| Wave | What it found |
|------|---------------|
| 1 | Three self-contradictions; a merge that emptied a report group; a trace rule that suppressed every missing-timeout finding on an untraceable client |
| 2 | A dedup rule *introduced by wave 1* that collapsed six distinct defects into one |
| 3 | Two Step 5.8 groups with no destination; merged perspectives discarded at render |
| 4–5 | A field named two ways; where to anchor an annotation; a plural noun |
| 6 | Confirmed the wave-1 suppression fix works; a certainty ceiling declared outside its owner file |

**Residual, accepted:** roughly 8–10 items per surface, all of the wave-4/5/6 class — formatting
conventions, unexercised latent forks, and judgment calls the text names as judgment calls. None
changes what the skill finds or suppresses.

**Owed next, and more valuable than another rehearsal round:** the first end-to-end dogfood run.
Rehearsals prove the instructions are unambiguous; only a real run proves the six scanners surface
anything useful on real code.

### First dogfood run — 2026-08-24, four defects

The end-to-end run owed since S46 ran against this repo (145 files in scope, 26 planted eval
fixtures excluded, bounded tier, heuristic for both metrics). Five scanners returned 20 findings;
17 survived the gates. Filed as findings against the skill itself:

**A1 — `respects_documented_decision` is set backwards, and the exclusivity rule buries the result.**
severity **high** · certainty 0.95 · evidence: all five `arch-robustness` findings returned
`false`, though nothing documented opposes adding a lock or a timeout. The scanner read the flag as
"this code violates a documented decision" instead of "my recommendation collides with one". Step
5.8 makes that group exclusive, so all five — the highest-value findings in the run — left Quick
wins for a confirmation section. `finding-rubrics.md` already states the correct reading in prose
and it still did not take; 5.7 validates only the `true` direction, so nothing caught it.
*Fix:* a two-question decision procedure in the rubric owner, plus a 5.7 check for an unjustified
`false`.

**A2 — no channel exists for a negative result.**
severity medium · certainty 1.0 · evidence: the scan files instruct scanners to say when a category
has nothing to bite on, but the output schema emits findings only — so `arch-structure` encoded "no
circular dependencies found" and "no D-entry finding meets its threshold" as *findings* with
`severity: low` and `recommended_refactor: "None"`. Unrouted, they rank and pollute the tables.
*Fix:* a `coverage_negatives` list in the finding contract, collected at 5.6 and rendered in the
footer.

**A3 — the ≥3 theme bar rejects real two-member mechanisms.**
severity low · certainty 0.9 · evidence: `session-color.{sh,ps1}` and
`gsc-parse-helper.py`'s history/watchpoints writes are the *same defect shape* — unlocked
read-modify-write on a shared file — in two unrelated files, and the pattern is invisible in the
report because it has two members. Same for the SessionStart hook pair (E03 + subprocess overhead).
*Fix:* keep the bar; add a "Notable pairs" line under the themes so a 2-member single-mechanism
cluster is surfaced without being promoted to a theme.

**A4 — Step 4's "pass the reference contents in the prompt" is impractical at this size.**
severity low · certainty 1.0 · evidence: composing five prompts that way requires the orchestrator
to hold ~95k chars of reference material. The run passed cache paths instead and the agents read
them — functionally identical, a fraction of the cost.
*Fix:* make path-passing the documented approach.

**What the run validated:** the wave-2 dedup narrowing was decisive — the god-file finding spans
`:1-1745` and would have absorbed eight findings under the pre-wave-2 overlap-only rule. The D03
layering guard correctly did not fire on a repo with no named layers. The dual-metric gate earned
itself: an `R01` finding at CCN 3→3 / cognitive 8→4 reached the report, which the pre-v2.3.0
CCN-only gate would have deleted. No scanner padded to its cap, and one verified its own
recommendation by executing it.

**Explicitly not done this pass:** no end-to-end dogfood run and no eval suite. `/bx:arch` has
still never been run end to end (`docs/STATUS.md` Next Steps #7); that run remains owed and needs
`/plugin update bx` first, since skills execute from the plugin cache, not the working tree.
