# Design: bx doc tiering — the rules tier, and the section with no governor

**Date:** 2026-08-24
**Status:** Draft — problem evidenced, **decisions open** (no user decision pass yet)
**Author:** Session 59 with Claude
**Ships as:** bx plugin v2.4.0 (proposed — MINOR: new behavior, no breaking schema change)
**Supersedes:** the twice-parked `.claude/rules/` item (`docs/key-decisions.md:60`; deferred
again in `plans/2026-08-17-bx-doc-schema-v2.md:1865` and
`specs/2026-08-17-bx-doc-schema-v2-design.md:324`)

---

## Problem

Schema v2 shipped in S56 on a clear thesis: always-loaded instructions stay in CLAUDE.md,
session state moves to `docs/STATUS.md`, and the always-loaded file is held near ~7k chars.
Field evidence says the thesis is right and the enforcement is incomplete.

### Evidence

A `/doctor` run on an external repo that uses `/bx:save` and `/bx:resume` every session:

| Measure | Value | Against bx's own numbers |
|---|---|---|
| CLAUDE.md | 31.1k chars (~7,775 est. tokens) | **2.6× the 12k soft cap, 4.4× the ~7k target** |
| `## Known Issues / Blockers` | 14.9k chars | **48% of the file** — the dominant bloat source |
| Doctor's largest fix | 4 path-scoped `.claude/rules/` files, ~8,619 chars (~2,155 tokens) | a file tier the schema does not have |
| Doctor's derivable-content trim | ~1,300 chars (~311 tokens) | a cut bx's preservation clause forbids |
| Net proposed | 31.1k → ~21.2k chars; Known Issues 14.9k → ~6.2k | still above bx's soft cap afterward |

The repo was saving diligently. The machinery ran and did not hold the line.

**Source caveat.** The `/doctor` transcript reached us partially garbled (~15 truncated
spans). Figures are used only where internally consistent: 31,100/7,775 = 4.0 chars/token
before and 21,200/5,300 = 4.0 after. Section-level counts taken from the transcript are
marked *(reported)*; counts taken from this repo are marked *(measured)*.

### 1. `## Known Issues / Blockers` is a required section with no cap, no shrinker, and no archive

It is the only required CLAUDE.md section with zero size governance anywhere in the skill:

- `references/claude-md-sections.md:14` requires it.
- `mode-update.md:339-344` (Part 1.7) is its entire lifecycle rule — "add new issues, remove
  resolved ones." No size awareness.
- Part 1.10 (`mode-update.md:394`) enforces per-section caps on three `docs/STATUS.md`
  sections and defers Key Decisions to Part 6. Known Issues is not mentioned.
- Part 7.3's shrinker table (`mode-update.md:694-700`) has **no row for it**. Exactly one
  CLAUDE.md shrinker exists, and it is Key Decisions at an 8000-char threshold.
- `references/doc-schema.md`'s canonical archive set is session-history / key-decisions /
  completed-work / next-steps-backlog. There is no `docs/known-issues.md`, so there is no
  destination even if a shrinker existed.

On `--full`, Part 7.2 renders a top-5 section table with an **"Over threshold?"** column. For
Known Issues that cell is unanswerable — 7.2 renders it, 7.3 defines no threshold. Then 7.3's
escape clause, written for *project-specific* sections (`## Quick Commands`, `## Don't
Modify`, `## Environment Variables`), silently absorbs a **required schema section**:
*"reports it but takes no action, deferring to user judgment."*

Corroborated locally *(measured, this repo)*:

```
  6250  ## Key Decisions             (threshold 8000 — will not fire)
  2947  ## Known Issues / Blockers   (no threshold exists at any size)
   531  ## Project Overview
        CLAUDE.md total: 9,870
```

Already the #2 section here, growing, and unreachable by any shrinker.

### 2. Resolved blockers are deleted, not relocated

Part 1.7 says *"Remove resolved issues."* This is the single place bx contradicts its own
rule. `references/doc-structure-rules.md` is unambiguous — *"content moves, it does not
disappear"* — and every other section has a named destination. A resolved blocker carries
exactly the kind of why-it-was-this-way knowledge the Pruning Is Preservation clause exists to
protect, and today it is dropped on the floor.

### 3. The schema has no path-scoped tier

Schema v2 defines two tiers: **always-loaded** (CLAUDE.md) and **on-demand by `/bx:resume`**
(`docs/STATUS.md` + archives). `.claude/rules/*.md` with `paths:` frontmatter is a third:
**auto-loaded, but only when Claude touches a matching path.** bx has no vocabulary for it.

This is not a new discovery for this repo — it is a re-discovery with a use case attached. S13
verified the feature is real against the official memory page and recorded
(`docs/key-decisions.md:60`):

> *"real documented feature in the memory page… Not shipped this session because there's
> nothing urgent to put in it; revisit if a cross-project repo-convention file becomes
> useful."*

The doctor supplied the missing use case, with measurements. Note where its 8,619 chars came
from: Known Issues 14.9k → 6.2k *(reported)*. **Problems 1 and 3 are one gap seen from two
sides** — path-scoped operational knowledge accretes in Known Issues precisely because the
schema offers it no other home.

The constraint the doctor got right, and the hard part of automating this:

> *"Never move a 'never do X' into a lazily-loaded file."*

bx's existing shrinkers select by **age** (Part 6 FIFO) and **size** (Part 7 thresholds).
Neither can distinguish a prod-DB warning from a cold-cache note. A rules-tier shrinker needs a
**criticality predicate** — a genuinely new kind of judgment for this skill, and the one most
capable of causing real damage when wrong.

### 4. Adopting the tier today would go unsupervised

If a user follows the doctor's advice against a bx-managed repo right now:

- **Invariants 1 and 2 go blind.** `doc-schema.md`'s invariants account for CLAUDE.md +
  `docs/STATUS.md` only, and `tests/assert-doc-schema.sh:78` checks those two files. Bytes
  moved into `.claude/rules/` leave the accounted set: the checker either trips Invariant 2
  (byte conservation) or — worse — passes while content silently exits supervision.
- **`/bx:resume` never sees it.** Step 0 declares CLAUDE.md and `MEMORY.md` already-in-context
  and reads `docs/STATUS.md`. Rules files load when Claude reads a matching path; during a
  resume (STATUS.md, `docs/`, git) that may never fire. The summary is then produced without
  operational constraints that used to be always-loaded, and neither the skill nor the user is
  told anything is missing.

### 5. The preservation rule actively protects derivable content

Doctor check 3 proposed cutting a Stack row (`package.json` states it), a Repo row (`git
remote -v`), a local-dev-path row (it is the cwd), and a justification paragraph. Only ~311
tokens — the smallest win — but it is a **rule tension**, not a size problem.

`doc-structure-rules.md` says *"NEVER remove existing information unless it's factually
incorrect or obsolete"* and *"when in doubt, keep it."* Derivable content is neither incorrect
nor obsolete, so bx protects it permanently.

bx already holds the counter-principle, scoped to exactly one section:

> *"Compressing a session history block to a one-liner with commit hashes is preservation —
> the full prose is recoverable via `git show <hash>`."*

Identical argument: recoverable elsewhere ⇒ safe to drop from the always-loaded file. It is
applied to session history and nowhere else.

### 6. The ~7k target is unenforced

Nothing acts between the ~7k target and the 12k soft cap. This repo sits at **9,870
*(measured)*** — 41% over target, with nothing due to fire. Either the target or the cap is
the wrong number, and today the target is decoration.

---

## Open decisions

**Not locked.** These are recommendations for a decision pass, not settled choices.

| # | Question | Recommendation | Why |
|---|---|---|---|
| 1 | Scope of this pass | **Problems 1, 2, 5, 6 now; 3 + 4 behind a second gate** | 1/2/5/6 are bounded edits to owned files with existing precedent. 3 introduces a new file tier *and* a new judgment class; it should not ride along. |
| 2 | Known Issues destination | **New archive `docs/known-issues.md`**, joining the canonical set in `doc-schema.md` | Every other required section has one; the archive access rules (append-only, anchored tail reads, rotation) then apply unchanged. |
| 3 | Known Issues threshold | **4000 chars → shrink to under 2500** | Key Decisions sits at 8000/6000 and is meant to be the largest section. Known Issues at 14.9k *(reported)* must not be able to recur. |
| 4 | Known Issues shrinker | **Resolved-first, then oldest-unresolved FIFO** | Resolved entries are pure history; unresolved ones may still be load-bearing. Never move an unresolved blocker while a resolved one remains. |
| 5 | Rules-tier automation | **Advisory only in v2.4.0 — detect and report, never write `.claude/rules/`** | The criticality predicate is unproven. An advisory pass earns evidence at zero blast radius. |
| 6 | Criticality predicate | **Prohibition-shaped content is ineligible, permanently** | Direct encoding of the doctor's rule. Cheap to state, cheap to check, and the failure it prevents is the expensive one. |
| 7 | Derivable-content rule | **Generalize the existing `git show` clause; apply to Project Overview only** | It is a one-line extension of a rule bx already holds, not a new policy. Scoping it to Project Overview keeps it away from Key Decisions and Known Issues. |
| 8 | Target vs cap | **Keep ~7k as the stated design target; add a 9k advisory rung** | Closes the dead band without moving the soft cap, which existing repos are calibrated against. |

Rationale for the close calls:

- **(1) Split the pass.** Problem 3 is the larger win and the larger risk. Problems 1/2/5/6
  make the always-loaded file governable using machinery that already exists and has already
  been blind-rehearsed. Shipping them first also *reduces* the pressure that makes 3 urgent,
  which is the right order.
- **(5) Advisory, not automatic.** Every other Part 7 shrinker moves content between files bx
  owns, under a consent gate, with an invariant checker watching. A rules migration moves
  content **out of the schema entirely**, into a file whose load semantics bx cannot observe
  and whose failure mode is silent (§4). Detect-and-report first.
- **(6) Prohibition-shaped, not "safety-critical."** "Safety-critical" is a judgment call an
  agent will get wrong at the margin. "Contains a prohibition" is closer to a syntactic
  property — never, don't, must not, always, before you — and errs toward keeping content
  always-loaded, which is the safe direction.

---

## Architecture (proposed)

### The tier model, named

The schema gains explicit vocabulary. `doc-schema.md` becomes the owner; satellites reference
it rather than restating it (S57 convention).

| Tier | Loading | Files | Cost |
|---|---|---|---|
| **T1 — always** | every request, every session | `CLAUDE.md` | paid always |
| **T2 — on demand** | when `/bx:resume` or a person reads it | `docs/STATUS.md`, archives, `docs/archive/` volumes | paid on read |
| **T3 — path-scoped** | when Claude touches a matching path | `.claude/rules/*.md` | paid on relevance |

The **placement rule**, stated once: *content whose relevance is bounded by a path belongs in
T3; content that is a prohibition, or that applies with no path in mind, stays T1; content that
is state or history is T2.*

### D1 — `docs/known-issues.md` joins the canonical archive set

Added to `doc-schema.md`'s Archives section as a fifth auto-managed archive, inheriting the
existing access rule verbatim: append-only, anchored tail reads, never read in full by any
automatic path, rotation at 100k via Part 7.7. Extended in the three dependent places the
Archives section already names as followers: `mode-update.md` Steps 0.3/3.0 exclusion lists,
and the `/bx:resume` do-not-read list.

### D2 — Part 1.7 relocates instead of deleting

Replaces *"Remove resolved issues"*:

> Move each resolved issue to `docs/known-issues.md` under a `## Resolved` heading with its
> resolution session and, where one exists, the commit hash. Append via anchored tail read. Do
> not delete. An issue is resolved when the session that resolved it says so — never inferred
> from absence of mention.

The last clause matters: a blocker not discussed this session is not resolved, and an inference
rule here would quietly destroy exactly the content D1 exists to keep.

### D3 — Known Issues enters the Part 7.3 shrinker table

New row, matching the existing format:

| Section | Threshold | Shrinker action |
|---|---|---|
| CLAUDE.md `## Known Issues / Blockers` | 4000 chars | **Resolved-first rollup** — move resolved entries to `docs/known-issues.md` (oldest first) until the section is under 2500 chars. If still over with no resolved entries left, move oldest *unresolved* entries, keeping a one-line summary + link in CLAUDE.md. Never leave an unresolved blocker with no T1 trace. |

Also closes the unanswerable-cell defect: 7.2's "Over threshold?" column now resolves for every
required section, and 7.3's tolerated-as-is clause is narrowed to say explicitly that it covers
project-specific sections only — a *required* section falling through it is a bug.

### D4 — the rules tier, advisory (gated behind decision 1)

A new Part 7.9, sibling to 7.7 rather than nested inside Part 7 (consistent with the pending
S57 finding about Part 7's carve-outs). Runs on `--full` only, and **writes nothing**:

1. If CLAUDE.md is over its soft cap *and* `## Known Issues / Blockers` is over its 7.3
   threshold, scan T1 content for path-scoped candidates: entries naming a concrete directory
   or path glob that exists in the repo.
2. Apply the **eligibility filter**: an entry is ineligible if it is prohibition-shaped, if it
   names no path, or if it applies to more than three top-level directories.
3. Report only:

   > *"[N] entries in `## Known Issues / Blockers` are scoped to specific paths (~[C] chars).
   > These are candidates for `.claude/rules/` path-scoped files, which load only when you
   > touch those directories. [M] further entries were excluded as prohibitions and must stay
   > always-loaded. `/bx:save` does not write these files — see `doc-schema.md` T3."*

No consent prompt, because nothing is applied. Promotion to an applying shrinker is a follow-up
decision that requires the report to have been right in practice first.

### D5 — invariants extended before the tier is usable

Whether or not D4 ships, `doc-schema.md` Invariants 1 and 2 and `tests/assert-doc-schema.sh`
must learn that `.claude/rules/*.md` exists — otherwise the first user who hand-follows a
`/doctor` report gets a false pass or a false failure:

- **Invariant 2** counts `.claude/rules/*.md` bytes in the conserved total when the directory
  is present.
- **New Invariant 5:** no file under `.claude/rules/` may contain a prohibition-shaped line.
  This is the criticality rule made mechanically checkable, and it holds for hand-written rules
  files too.
- `--before` snapshot comparison extends to the same set.

### D6 — `/bx:resume` learns the tier exists

`/bx:resume` still never writes. Step 6 (Validate Structure) gains one check: if
`.claude/rules/*.md` exists, name the files and their `paths:` globs in the summary, so the
operator knows which constraints are *not* currently loaded. One line, no reads of the rule
bodies:

> *"3 path-scoped rule files exist (`src/lib/scrape/**`, …). They load when you touch those
> paths — not now."*

### D7 — derivable-content clause generalized

`doc-structure-rules.md` gains, adjacent to the existing `git show` sentence:

> **Derivable facts are recoverable, and recoverable content may leave T1.** A fact a session
> can obtain in one command — the stack from `package.json`, the remote from `git remote -v`,
> the project path from the cwd — is preserved by that command, not by CLAUDE.md. This is the
> same rule as the session-history one-liner, applied to `## Project Overview`. It does **not**
> extend to `## Key Decisions` or `## Known Issues / Blockers`, whose content is *why*, and is
> derivable from nothing.

### D8 — the dead band gets a rung

Part 1.9 gains a middle advisory at 9k: warn, name the section most likely responsible, take no
action. The 12k soft cap and every Part 7 trigger are unchanged.

---

## Non-goals

- **Automating `.claude/rules/` writes.** Explicitly deferred (decision 5).
- **Touching the T1/T2 split.** Schema v2's core split is validated by this evidence, not
  challenged by it. No marker bump; this is v2 machinery, not v3.
- **Plugin/MCP curation.** The doctor's checks 1 and 9 are `/doctor`'s job, not `/bx:save`'s.
- **A `/bx:doctor`.** Tempting, and out of scope.
- **Retro-fixing the external repo.** It is not this repo; findings only.

---

## Risks

| Risk | Mitigation |
|---|---|
| The `paths:` frontmatter schema was verified in S13 (2026-04-11) and not since | **Re-verify against the official memory page before D4/D5 ship.** This repo's own standing rule — *verify every external claim before shipping* (`docs/archive/key-decisions-1.md:132`) — was written after a near-miss on this exact feature. |
| The prohibition-shaped filter has false negatives | It only gates an advisory report in v2.4.0. Invariant 5 is the durable backstop, and it checks the file that actually exists rather than the intent behind it. |
| Resolved-first shrinking removes a blocker still being worked | D2 forbids inferring resolution from silence; D3 forbids leaving an unresolved blocker with no T1 trace. |
| Another required section is discovered ungoverned later | D3's narrowing of the tolerated-as-is clause makes that a reportable bug class rather than a silent pass. |
| `docs/known-issues.md` becomes a dumping ground | It inherits 100k rotation via Part 7.7 like every other archive. |

---

## Acceptance

Per the S56 instrument, restated in the S58 spec: **blind rehearsals on changed surfaces,
decision-log ambiguity ≤ 2.** The surfaces here are small and mostly extend existing formats,
so the bar should be reachable — unlike S58, where it was not met and shipped on the severity
curve instead.

1. `assert-doc-schema.sh` passes on all existing fixtures, with unchanged behavior for repos
   that have no `.claude/rules/` directory.
2. New fixture: a repo *with* `.claude/rules/`, one file containing a prohibition → Invariant 5
   must fail it.
3. New fixture: Known Issues at 6k with three resolved entries → D3 shrinks it under 2500 by
   moving resolved entries only.
4. Blind rehearsal of D2 + D3 + D4's report text.
5. **Field check, not a fixture:** re-run `/doctor` on the external repo after a `--full` save
   and confirm CLAUDE.md moved toward the target. Fixtures prove the instructions are
   unambiguous; only that repo proves the numbers changed.

---

## Open questions

1. **Does a rules file's `paths:` glob match on read, on edit, or both?** Determines whether
   D6's "not currently loaded" line is accurate. Needs the memory page.
2. **Should `docs/known-issues.md` carry resolved entries only, or both?** D2/D3 currently let
   both land there. Resolved-only is cleaner to read; both is simpler to implement.
3. **Was the external repo's CLAUDE.md ever edited outside `save-writer`?** Its
   `settings.local.json` permanently carries `Bash(sed -i '113,116d' CLAUDE.md)`, `Bash(sed -i
   's|+ vintage Chrono24…')`, and `Bash(perl -0pi -e '…')`. `/bx:save` writes CLAUDE.md through
   `save-writer`'s Read/Edit/Write and its `allowed-tools` grants no `sed` or `perl`. If those
   are hand-edits, this is only permission hygiene. If a save run fell back to shell editing,
   `save-writer` is being bypassed and the invariant checker never saw those edits — which
   would change the priority of this whole spec.
4. **Does the 4000-char threshold hold for repos with genuinely many blockers?** This repo has
   five and sits at 2,947. Sample of two.

---

## What the evidence also validated

Recorded because it is evidence the design works where it is specified:

- **Auto-memory discipline held.** 29 lines / 6.9k against the 200-line / 25KB limits, with no
  duplicate `~/.claude/CLAUDE.md` or `CLAUDE.local.md`. `mode-update.md` Part 4.3's
  what-NOT-to-write rules are doing their job in a repo that saves every session.
- **SessionStart hooks cost nothing measurable.** Max 2.8s against a 10s guideline, zero
  timeouts, across the same window.
- **The T1/T2 split is not what failed.** CLAUDE.md at 31.1k with state correctly absent is a
  *section-governance* failure, not a schema failure. Schema v2's thesis survives its first
  adverse field measurement; only its enforcement surface needs work.
