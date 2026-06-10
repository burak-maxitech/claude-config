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

Numbers from Step 3 consolidation. All-zero special case — render instead:

```
## /bx:evolve — upstream delta report

**Toolkit is current** — no NEW upstream deltas intersect the plugin since changelog 2.1.170 · docs 2026-06-09.
```

If Section 4 is non-empty (there are carried-forward open or deferred entries), append a qualifier:

```
**Toolkit is current** — no NEW upstream deltas intersect the plugin since changelog 2.1.170 · docs 2026-06-09. (3 open findings carried forward — see Section 4)
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

For the changelog lane, the "Range covered" shows `<old watermark version> → <new version>` and the count of releases processed this run. If `last_changelog_version` was null (first run), render the old end as "beginning". For a skipped or unavailable lane, render `—`.

For docs and community lanes, the "Range covered" shows `<old *_checked_at> → today`. If the old timestamp was null (first run), render the old end as "first run". For a skipped or unavailable lane, render `—`.

**Unavailable lane status detail:** when a lane's status is `unavailable`, include the sentinel's `upstream_delta` field (the verbatim errors from the failed fetch/auth attempts) as the status detail in that lane's row. This is the one place sentinel content renders — the sentinel is never written to the decision log and never appears in Sections 2–4.

Below the table, one line per release processed by the changelog lane. These lines come from the changelog lane's `releases_digest` footer field (one entry per in-scope release: `<unprefixed version> — <publishedAt date> — <one-line summary>`). On the degraded path, the date is omitted from the digest entries (not available via raw CHANGELOG.md):

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
- **Citation:** the release tag and/or lane that sourced the finding (e.g. `v2.1.169`, `docs`, `v2.1.169 / docs` when two lanes emitted findings for the same `affected_capability` describing the same upstream change — the higher-authority lane's finding is kept and the other lane's citation is appended here).

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

**Re-raised findings badge:** a finding whose `finding_id` matched a `rejected` entry but the live `source_content_hash` differs from the stored one (per lifecycle Rule 3 in `bx/skills/evolve/references/state-schema.md`) is a current, live finding — it has been re-emitted this run by a lane agent and re-ranked in Section 2. Add a `[re-raised — source changed since rejection]` badge on the table row's Title column and in the detail block header. Example:

```
**#2 — Hook event `PreToolUse` renamed** [breakage · H · cert 0.90] [re-raised — source changed since rejection]
```

**Deferred findings badge:** a finding whose `finding_id` matched a `deferred` entry AND was re-emitted by a lane this run renders in Section 2 (ranked, live) — NOT in Section 4. Add a `[deferred <original date>]` badge, where the date is from the stored entry's `date` field. If the live `source_content_hash` differs from the stored one, add a note in the detail block: "source changed since deferral". Example:

```
**#3 — Hooks rework could simplify /bx:health** [opportunity · M · cert 0.65] [deferred 2026-05-28]
```

**Completeness rule (S45 doc-drift):** for the #1-ranked finding per class (the detail-block entries), confirm the `affected_files` list is complete — the lanes already populate `affected_files` via mandatory Grep; spot-check that the #1 finding's sibling files are included where the pattern appears.

**Hash fields:** both `finding_id` and `source_content_hash` exist by render time — computed at Step 3 per `bx/skills/evolve/references/state-schema.md`.

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
| 1    | Consider using `--dangerously-skip-permissions`... | 0.55 | community.anthropic.com |
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

Decision-log entries with `decision: "open"` or `decision: "deferred"` whose `finding_id` was NOT among this run's consolidated findings (i.e., no lane re-emitted them this run) re-surface here. Entries that a lane DID re-emit this run are already visible in Section 2 (including any re-raised ones) and do NOT appear here.

```
## Carried-Forward Open Findings

| Finding ID (prefix) | Date (last transition, per state-schema `date` semantics) | Class        | Title                              | Badge                     |
|---------------------|-----------------------------------------------------------|--------------|------------------------------------|-----------------------------|
| a3f2c1b9            | 2026-06-05                                                | best_practice| Add `effort: high` to /bx:health  |                             |
| c1d5e9f3            | 2026-05-28                                                | opportunity  | Use glob in allowed-tools          | [deferred 2026-05-28]       |
```

**Column values:** `Class` and `Title` are read from the `class` and `title` fields of the stored decision entry (set at the finding's last surfacing). These fields make Section 4 renderable without re-running a lane.

**Badge rules:**

- No badge: plain `open` finding from a prior run not re-emitted this run.
- `[deferred <original date>]`: a `deferred` entry re-surfacing per lifecycle Rule 5 in `bx/skills/evolve/references/state-schema.md`. The date shown is the original deferral date, not today.

Empty state: render the section header plus "None — no open findings carried from previous runs."

---

## Footer — Disclosure

Render as a horizontal-rule-separated block at the end of the report. The math is surfaced so the headline count cannot silently lie.

```
---

Lane status:
- changelog:   ok        (25 releases fetched, 25 processed)
- docs:        ok        (4 pages fetched, 4 processed)
- community:   degraded  (3 searches run, 2 pages fetched, 1 fetch failed)

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

Discarded findings (per lane — each lane reports its own composition):
  changelog lane: 3 discarded
  docs lane:      1 discarded
  community lane: 0 discarded
```

The "Decision-log filters" line makes the suppression count explicit. If zero findings were suppressed, render "0 rejected findings suppressed." If a community lane was skipped, its watermark line shows the old value with a note: `community 2026-05-10 → (skipped — no advance)`.