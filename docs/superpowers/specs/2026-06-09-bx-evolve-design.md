# /bx:evolve — Upstream-Watch & Skill-Modernization Design

**Date:** 2026-06-09 (Session 46)
**Status:** Approved (brainstorm complete)
**Approach:** A — purpose-built scan skill in the bx house idiom (report + gated apply)

## Problem

The AI tooling space moves fast: Anthropic ships new Claude Code versions, renames built-ins, deprecates commands, and evolves best practices continuously. The `bx` toolkit has already been bitten three times by upstream drift it learned about late: S32 (built-in `/code-review` collided with the custom skill), S36 (`/simplify` reinstated + `/ultrareview` deprecated, invalidating documented review ladders), S39 (`${CLAUDE_SKILL_DIR}` turned out not to be a real variable). S33 proved the countermeasure works — a manual web audit of official docs + community guides yielded 5 shipped improvements — but it was a one-off. This skill makes that audit repeatable, cheap, and disciplined.

## Goals

1. Detect upstream changes (Claude Code releases, official docs, community practice) that affect this plugin — *before* they break a run.
2. Propose skill/agent/doc updates as a findings report with mandatory citations.
3. Apply approved changes behind a per-finding diff gate (`--fix`), never automatically.
4. Never re-litigate a rejected proposal; never propose churn for churn's sake.

## Non-goals (v1)

- Auditing anything outside this repo (the skill is specific to claude-config's `bx` plugin + operational docs).
- Auto-applying edits without the per-finding gate.
- A `--plan` mode (proposed edits are doc-file edits; report + `--fix` covers the loop).
- Watching non-Anthropic ecosystems (MCP servers, third-party plugins) — possible v2.

## Shape

- **Skill:** `bx/skills/evolve/` → `/bx:evolve` (11th skill)
- **Frontmatter:** `disable-model-invocation: true`, `effort: high`, `argument-hint: "[--full] [--fix] [--no-community]"`
- **Modes:**
  - default — research delta since watermark → report
  - `--full` — ignore watermark, from-scratch audit (the S33 treatment)
  - `--fix` — after report, walk findings with per-finding diff preview (the `/bx:arch --fix` gate flow)
  - `--no-community` — official-only fast pass (skips the Tier-2 lane)
- **New agents (15 → 18), all Sonnet, least-privilege tools, every invoked command enumerated:**
  - `bx/agents/upstream-changelog.md` — releases/CHANGELOG delta via `gh` against the public `anthropics/claude-code` repo (WebFetch fallback). Tools: `Read, Grep, Glob, Bash(gh:*), WebFetch`. Catches the **breakage class** (renames, deprecations, new flags). Most trusted lane.
  - `bx/agents/upstream-docs.md` — WebFetch over a **pinned allowlist** of official doc pages (skills authoring, plugin reference, hooks, settings, subagents, memory). Tools: `Read, Grep, Glob, WebFetch`. Catches the **best-practice class**.
  - `bx/agents/upstream-community.md` — bounded WebSearch (hard cap on fetches per run), emits **advisory-only** findings. Tools: `Read, Grep, Glob, WebSearch, WebFetch`. Catches the **emergent-pattern class**.
- **References:** `references/scan-changelog.md`, `references/scan-docs.md` (includes the pinned URL allowlist), `references/scan-community.md`, `references/report-template.md`, `references/fix-mode-evolve.md`, `references/state-schema.md`.

## Authority model (two-tier)

- **Tier 1 (actionable):** official Anthropic surfaces only — claude-code CHANGELOG/releases and the pinned official Claude Code docs allowlist. (Other official surfaces like the Anthropic engineering blog reach the report only via the community lane's `official_source_found` handoff — no lane fetches them directly.) Every actionable finding carries a mandatory Tier-1 citation URL.
- **Tier 2 (advisory):** community content via bounded WebSearch. Advisory findings are clearly badged, never actionable on their own, and never eligible for `--fix`. A Tier-2 pattern becomes actionable only when a Tier-1 source corroborates it.

## Step flow (orchestrator)

0. **Load state + build capability inventory.** Read `docs/upstream/state.json` (watermark + decision log). Grep/Read `bx/` + operational docs (README.md, workflow.md, CLAUDE.md review-ladder references) to inventory: every frontmatter key in use, every built-in skill referenced (`/code-review`, `/simplify`, `/code-review ultra`…), every harness idiom relied on (Task dispatch + `subagent_type`, `!` injection, plugin `bin/` PATH helpers, no-env-var-persistence assumption, allowed-tools enumeration), model routing, hook events. Pain points come from CLAUDE.md Known Issues / Next Steps / deferred decision items. Historical archives (docs/*.md records of past state) are out of scope per repo convention.
1. **Parallel dispatch** of the three lanes (single turn, one Task call per agent, dedicated agents by name — the S43 rule). Each gets: the watermark, the capability inventory, the pain-point list, and its scan reference content. `--no-community` skips lane 3.
2. **Relevance gate (churn discipline).** A finding exists ONLY if an upstream delta (a) intersects the capability inventory, or (b) solves a recorded pain point. "New capability exists" alone is never a finding. Classification:
   - `breakage` — upstream invalidated something the plugin says or does (S32/S36/S39 class). Highest severity.
   - `best_practice` — official guidance changed for something the plugin does.
   - `opportunity` — new capability that maps to a recorded pain point.
   - Tier-2 findings are always `advisory` regardless of class.
3. **Decision-log filter.** Drop findings whose `finding_id` has a `rejected` decision AND whose source content hash is unchanged since that decision. Cross-lane corroboration matches on `affected_capability` (not `finding_id` — URL spaces are disjoint across lanes so `finding_id` can never collide cross-lane): when two lanes emit findings for the same capability, keep the higher-authority lane's finding and append the other's citation. Surface previously-`deferred` findings that were re-emitted this run with a `[deferred <date>]` badge in Section 2; entries not re-emitted carry forward to Section 4.
4. **Report.** Headline: `Breakage: N · Best-practice: M · Opportunities: K · Advisory: J`. Per finding: classification, severity, certainty, **all affected files** (the S45 doc-drift rule is baked into the finding schema — a proposed edit that doesn't enumerate every sibling-file echo is incomplete), proposed edit, Tier-1 citation. Footer disclosure: sources fetched + versions, watermark old → new, decision-log filters applied, community fetch count vs cap. **Every new actionable finding is written to the decision log as `open`** — findings survive the watermark advance until explicitly decided.
5. **`--fix` tail.** Per-finding diff preview gate (y / n / skip / abort). Every verdict overwrites the finding's `open` entry in the decision log. Advisory findings are never offered. After the pass: remind `/plugin update bx` + `/reload-plugins`, and recommend the S42 content-review treatment for any skill that received non-trivial edits.
6. **Closing + watermark.** The watermark advances at the end of **every** run (default or `--fix`) — safe because undecided findings persist as `open` in the decision log and re-surface in every report until decided. Default-mode closing line: how to apply (`--fix`) and the count of `open` findings carried forward.

## Finding schema

```
finding_id: null                      (set by lane agents; orchestrator computes finding_id + source_content_hash at consolidation)
class: breakage | best_practice | opportunity
tier: official | community            (community ⇒ advisory, never fix-eligible)
severity: low | medium | high
certainty: 0.0–1.0
affected_files: [<every file needing the edit, including sibling-file echoes>]
upstream_delta: <one-line: what changed upstream>
proposed_edit: <prose + concrete old→new where possible>
citation: <Tier-1 URL>                (mandatory for official tier)
source_url: <canonicalized source URL — finding_id input>
affected_capability: <normalized capability string — finding_id input>
source_excerpt: <verbatim extract — orchestrator computes finding_id + source_content_hash at consolidation>
```

## State: `docs/upstream/state.json` (committed)

```json
{
  "watermark": {
    "last_changelog_version": "2.1.170",
    "docs_checked_at": "2026-06-09",
    "community_checked_at": "2026-06-09"
  },
  "decisions": [
    {
      "finding_id": "<hash>",
      "decision": "open | applied | rejected | deferred",
      "date": "2026-06-09",
      "source_url": "<canonicalized URL of the upstream source page>",
      "affected_capability": "<e.g. bx:seo/allowed-tools>",
      "source_content_hash": "<hash>",
      "class": "breakage | best_practice | opportunity",
      "title": "<one-line finding title at last surfacing>",
      "note": "<optional one-liner>"
    }
  ]
}
```

Committed to the repo (multi-machine sync, like everything else here). Rejected findings re-raise only when a current run re-surfaces the same `finding_id` with a changed `source_content_hash` (trigger-based — the orchestrator never proactively re-fetches stored URLs). This mirrors the proven `/bx:seo` finding-history pattern (S35), minus the run-count escalation (not needed — decisions are explicit here).

## Orchestrator allowed-tools

`Read, Grep, Glob, Edit, Write, Bash(git:*), Bash(python:*), Bash(python3:*), Task`
(Write is for state.json; Edit for `--fix`; gh/WebFetch/wc/jq/cat/head are lane tools — lanes carry their own network/CLI tools and jq is forbidden for state writes; orchestrator needs only python for hashing.)

## Validation plan

- skill-creator's quantitative eval loop is infeasible (network- and time-dependent inputs, subjective outputs) — same verdict as `/bx:webdesign` and `/bx:save` in S42.
- **Pre-dogfood:** qualitative content review (the S42/S45 treatment) of all files.
- **Dogfood = first real run.** Smoke checks it must pass:
  1. Already-applied S33/S39-era changes produce **zero findings** (the inventory check recognizes current state as current).
  2. The S36-class scenario, simulated: a known past rename (e.g., `/ultrareview` → `/code-review ultra`) would have produced a `breakage` finding listing every operational file that referenced it.
  3. Re-run immediately after: zero NEW findings (watermark advanced); only carried-forward `open` findings re-surface, and the run is fast.
  4. A rejected finding stays rejected on the next run.

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Blogspam / stale community content | Two-tier authority; Tier 2 advisory-only + fetch cap |
| Churn proposals ("use shiny new X") | Relevance gate: inventory intersection or recorded pain point, else no finding |
| Breaking working skills via misread source | Per-finding diff gate; mandatory citations; content-review treatment after non-trivial edits |
| Re-litigating rejected ideas every run | Decision log keyed by finding_id + source hash |
| Doc-drift from applied fixes (S45 lesson) | `affected_files` must enumerate all sibling echoes; incomplete enumeration = incomplete finding |
| Docs URLs rot | Pinned allowlist lives in one reference file; lane reports fetch failures explicitly (never silently skips — the S30/S35 "ship the canonical primitive" lesson) |

## Naming

`/bx:evolve` (approved working name). Alternatives considered: `/bx:upstream`, `/bx:refresh`.
