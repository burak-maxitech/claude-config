# Report Template — /bx:evolve

Render the final report exactly in this order. Every section appears even if empty — the output structure must be predictable across runs so users can scan a consistent shape regardless of what was found. Use imperative voice to the orchestrator throughout.

---

## Section 0 — Headline

Render this first, before anything else.

Normal case:

```
## /bx:evolve — upstream delta report

**Breakage: N · Best-practice: M · Opportunities: K · Advisory (community): J**
```

Numbers from Step 4 consolidation. All-zero special case — render instead:

```
## /bx:evolve — upstream delta report

**Toolkit is current** — no upstream deltas intersect the plugin since changelog 2.1.170 · docs 2026-06-09.
```

The watermark fields rendered in the special case are `last_changelog_version` and `docs_checked_at` from `docs/upstream/state.json`. Render as `changelog <version> · docs <date>`. If a field is null (first run), render "never" in its place.

The four counts in the normal headline are FINAL counts after decision-log suppression (rejected-unchanged findings do not appear in the headline). The footer discloses the suppression count so the math is auditable.

---

## Section 1 — Upstream Delta Digest

One line per lane. Render even if a lane was skipped or unavailable.

```
## Upstream Delta Digest

| Lane        | Status     | Range covered                          |
|-------------|------------|----------------------------------------|
| changelog   | ok         | 2.1.145 → 2.1.170 (25 releases)       |
| docs        | ok         | 2026-05-10 → 2026-06-09               |
| community   | degraded   | 2026-05-10 → 2026-06-09 (2/5 sources) |
```

**Lane statuses:** `ok` (ran fully), `degraded` (ran partially — network errors, partial results), `skipped` (user passed `--no-community`), `unavailable` (tool or auth failure prevented the lane from running).

For the changelog lane, the "Range covered" shows `<old watermark version> → <new version>` and the count of releases processed this run. If `last_changelog_version` was null (first run), render the old end as "beginning".

For docs and community lanes, the "Range covered" shows `<old *_checked_at> → today`. If the old timestamp was null (first run), render the old end as "first run".

Below the table, one line per release processed by the changelog lane:

```
**Changelog entries scanned this run:**
- v2.1.170 — 2026-06-09 — Hooks: new `PostToolUse` event added
- v2.1.169 — 2026-06-08 — MCP: `allowed-tools` now accepts glob patterns
- ...
```

If the changelog lane was skipped or unavailable, render: "Changelog entries: (lane unavailable — watermark not advanced)".

---

## Section 2 — Findings

Three subsections in order: **Breakage** first, then **Best-practice**, then **Opportunities**. Every subsection renders even when empty.

### Breakage

```
### Breakage

| Rank | Class    | Affected files | Title                               | Sev | Cert | Citation        |
|------|----------|----------------|-------------------------------------|-----|------|-----------------|
| 1    | breakage | 3              | `allowed-tools` glob syntax changed | H   | 0.95 | v2.1.169 / docs |
| 2    | breakage | 1              | Hook event `PreToolUse` renamed     | H   | 0.90 | v2.1.168        |
```

Empty state: render the header row plus one row: `| — | — | — | None — no breakage findings this run. | — | — | — |`

**Column definitions:**

- **Rank:** integer, ordered by `(sev DESC, cert DESC)` within the class.
- **Class:** `breakage`, `best_practice`, or `opportunity` — matches the finding's `class` field.
- **Affected files:** count of files in the finding's `affected_files` list.
- **Title:** the finding's short title.
- **Sev:** `H` (High), `M` (Medium), `L` (Low).
- **Cert:** certainty float 0.0–1.0 (2 decimal places).
- **Citation:** the release tag and/or lane that sourced the finding (e.g. `v2.1.169`, `docs`, `v2.1.169 / docs` when corroborated by multiple lanes).

Below each table, render a "Top finding detail" block for the #1 ranked finding:

```
**#1 — `allowed-tools` glob syntax changed** [breakage · H · cert 0.95]

Upstream delta: MCP `allowed-tools` now accepts glob patterns (v2.1.169). The old exact-string
format is still accepted but the docs state exact-string matching will be removed in a future
release. Four bx skills use exact-string `allowed-tools` entries that match the deprecated format.

Affected files (all — a partial edit leaves sibling echoes):
- bx/skills/seo/SKILL.md
- bx/skills/save/SKILL.md
- bx/skills/clean/SKILL.md
- bx/skills/arch/SKILL.md

Proposed edit: convert exact-string `allowed-tools` entries to glob patterns per the new format:
`Bash(gsc-parse-helper*)` → `Bash(gsc-parse-helper.py *)`.

Citation: https://code.claude.com/docs/en/settings#allowed-tools · v2.1.169 release notes
```

**Completeness rule (S45 doc-drift):** an entry whose `affected_files` list misses a sibling echo is an incomplete finding — all files that contain the affected pattern must be listed. The orchestrator must cross-check sibling skill files before emitting a finding. A finding that touches one SKILL.md but not its sibling references/ files is incomplete unless the pattern genuinely does not appear there.

**Hash fields:** `finding_id` and `source_content_hash` are computed by the orchestrator at consolidation (Step 4) using `Bash(python:*)`, not by lane agents. Lane agents emit `source_excerpt` (the verbatim heading-bounded extract, pre-normalization) alongside `source_url` and `affected_capability`. The orchestrator applies the `source_content_hash()` normalization from `bx/skills/evolve/references/state-schema.md` to `source_excerpt` to produce `source_content_hash`, and computes `finding_id` from `source_url + "|" + affected_capability`. By the time the report is rendered, both hash fields exist in the consolidated finding object.

### Best-practice

Same table format as Breakage, same Top finding detail block for #1. Class column value: `best_practice`.

Empty state: render the header row plus one row: `| — | — | — | None — no best-practice findings this run. | — | — | — |`

### Opportunities

Same table format. Class column value: `opportunity`.

Empty state: render the header row plus one row: `| — | — | — | None — no opportunity findings this run. | — | — | — |`

---

## Section 3 — Advisory (Community)

> **[advisory — community source, not fix-eligible]**

Advisory findings are informational only. They use "consider" phrasing. They are never offered to `--fix` mode (even if the user passes `--fix`). They never appear in Section 2's breakage/best_practice/opportunity tables.

```
## Advisory (community)

> [advisory — community source, not fix-eligible]

| Rank | Title                                              | Cert | Source                  |
|------|----------------------------------------------------|------|-------------------------|
| 1    | Consider using `--dangerously-skip-permissions`... | 0.65 | community.anthropic.com |
```

Below the table, a brief note per finding (one or two sentences, "consider" phrasing):

```
**#1 — Consider evaluating `--dangerously-skip-permissions` for CI**

Community discussion reports that CI runs using `--dangerously-skip-permissions` eliminate
permission prompts in fully-automated contexts. Consider whether your `/bx:save --silent` runs
in CI would benefit from this flag, given that `--silent` already resolves prompts to safe
defaults in interactive sessions.
```

Empty states:

- Community lane ran but found nothing: render "None — community lane found nothing relevant to the plugin this run."
- Community lane was skipped: render "None — community lane skipped via `--no-community`."
- Community lane was unavailable: render "None — community lane unavailable this run (tool or auth failure). Re-run without `--no-community` to retry."

---

## Section 4 — Carried-Forward Open Findings

All findings whose `decision` is `open` in `docs/upstream/state.json` from previous runs (i.e., `date` predates today) re-surface here.

```
## Carried-Forward Open Findings

| Finding ID (prefix) | Date first surfaced | Class        | Title                              | Badge                                        |
|---------------------|---------------------|--------------|------------------------------------|----------------------------------------------|
| a3f2c1b9            | 2026-06-05          | best_practice| Add `effort: high` to /bx:health  |                                              |
| b9c4e2f1            | 2026-06-03          | breakage     | Hook event renamed in v2.1.165     | [re-raised — source changed since rejection] |
| c1d5e9f3            | 2026-05-28          | opportunity  | Use glob in allowed-tools          | [deferred 2026-05-28]                        |
```

**Badge rules:**

- No badge: plain open finding from a prior run, neither re-raised nor deferred.
- `[re-raised — source changed since rejection]`: a finding whose `finding_id` matched a `rejected` entry but the live `source_content_hash` differs from the stored one. The entry has been transitioned back to `open`. See lifecycle Rule 3 in `bx/skills/evolve/references/state-schema.md`.
- `[deferred <original date>]`: a `deferred` entry re-surfacing per lifecycle Rule 5 in `bx/skills/evolve/references/state-schema.md`. The date shown is the original deferral date, not today.

New `open` findings written this run (from Section 2) do NOT appear in Section 4 — they are already visible in Section 2. Section 4 is exclusively for findings whose `date` predates this run.

Empty state: render the section header plus "None — no open findings carried from previous runs."

---

## Footer — Disclosure

Render as a horizontal-rule-separated block at the end of the report. The math is surfaced so the headline count cannot silently lie.

```
---

Lane status:
- changelog:   ok        (25 releases fetched, 25 processed)
- docs:        ok        (4 pages fetched, 4 processed)
- community:   degraded  (5 searches attempted, 2 sources retrieved)

Findings headline math:
  Breakage:      2 (after suppression)
  Best-practice: 3 (after suppression)
  Opportunities: 1 (after suppression)
  Advisory:      1

Decision-log filters applied this run:
  4 rejected findings suppressed (source_content_hash unchanged — source not rewritten since rejection)
  1 rejected finding re-raised (source_content_hash changed → transitioned to open)

Watermark: changelog 2.1.145 → 2.1.170 · docs 2026-05-10 → 2026-06-09 · community 2026-05-10 → 2026-06-09

Open entries written this run: 7
  (these persist in docs/upstream/state.json and re-surface until acted on)

Discarded findings (below certainty threshold or out of scope):
  changelog lane: 3 discarded
  docs lane:      1 discarded
  community lane: 0 discarded
```

The "Decision-log filters" line makes the suppression count explicit. If zero findings were suppressed, render "0 rejected findings suppressed." If a community lane was skipped, its watermark line shows the old value with a note: `community 2026-05-10 → (skipped — no advance)`.