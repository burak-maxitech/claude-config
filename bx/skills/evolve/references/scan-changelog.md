# Scan: Changelog (upstream claude-code releases)

Loaded by the orchestrator and passed to the `upstream-changelog` subagent. You are that subagent. Detailed scanning instructions follow.

You have these tools available: Read, Grep, Glob, Bash (gh commands only — pattern `gh *`), WebFetch. Use `gh` and WebFetch for all network access. No `curl`, no `git clone`, no shell HTTP commands.

---

## Inputs you receive in your task prompt

- `last_changelog_version` — string (e.g. `"2.1.170"`) or null. The highest claude-code release processed on the last run, stored as an **unprefixed version string** (no leading `v`). Null means this is the first run — scan ALL releases in the window.
- `capability_inventory` — list of bx capability strings (e.g. `"bx:seo/allowed-tools"`, `"bx:save/agent-model"`). Only produce findings that intersect this list or a pain-point from the list below.
- `pain_point_list` — list of short strings describing known friction areas in the bx toolkit (e.g. `"permission prompts on every run"`, `"watermark drift on partial failures"`). A release note addressing a pain point qualifies as a finding even without an exact capability match. For such findings, set `affected_capability` to the `bx:pain/<kebab-slug>` form — see the `bx:pain/<kebab-slug>` convention in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.
- `tier_definitions` — the tier table from the orchestrator (currently only one tier for this lane: `tier: official`). You only emit `tier: official`; the definitions are context for correctly NOT emitting community-style advisory findings.

---

## Version normalization rule

claude-code release tags use a leading `v` (e.g. `v2.1.170`); CHANGELOG.md headings omit the `v` (e.g. `## 2.1.170`). **Strip the leading `v` for ALL comparisons and for storing the watermark.** The stored `last_changelog_version` is always the unprefixed string (e.g. `2.1.170`). Release URLs retain the `v` (e.g. `https://github.com/anthropics/claude-code/releases/tag/v2.1.170`).

---

## Method

### Step 1 — Enumerate releases (primary: gh)

Run:

```
gh release list --repo anthropics/claude-code --limit 50
```

This returns releases newest-first. Collect the tag names in that order.

**Watermark stop rule:** Normalize each tag (strip leading `v`) before comparing. Iterate from newest to oldest. Stop when you reach the release whose normalized version **exactly equals** `last_changelog_version`. Do not fetch or evaluate that release or any older ones. If no exact match is found within the 50-release window (the watermark tag was yanked, or more than 50 releases have shipped since the last run — claude-code ships near-daily so this is realistic), process the entire window AND emit a `scan_note: watermark anchor <last_changelog_version> not found in the 50-release window; window may be incomplete — consider re-running with a larger limit`.

If `last_changelog_version` is null, process ALL releases returned in the 50-release window and emit a `scan_note` if the window was exhausted (i.e., you hit the `--limit 50` cap without finding a stopping point).

### Step 2 — Fetch each in-scope release body (primary: gh)

For each in-scope tag, run:

```
gh release view <tag> --repo anthropics/claude-code --json body,tagName,publishedAt
```

Parse `body` (markdown), `tagName` (the tag string), and `publishedAt` (ISO timestamp).

**Failure definition:** A call fails if it exits non-zero OR returns an empty body where content is expected. If `gh release list` succeeds but ANY `gh release view` call fails, do not mix sources — fall back to the WebFetch CHANGELOG path for the entire window (Step 3) and set `lane_status: degraded`. There are no mixed-source runs; the lane is all-or-nothing by design.

### Step 3 — Fallback when gh fails

If `gh release list` or any `gh release view` call fails (no auth, network error, rate limit, or empty body), fall back to:

```
WebFetch https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md
```

Slice the fetched markdown to include only sections whose normalized heading (strip leading `v`) appears **above** the watermark's heading in document order (document order, top = newest). If `last_changelog_version` is null, use the entire fetched document. If the watermark heading is absent from the document (version was yanked or predates the CHANGELOG), process the whole document AND emit a `scan_note: watermark anchor <last_changelog_version> not found in CHANGELOG.md; entire document processed — window may be incomplete`.

In the fallback path, `citation` and `source_url` for each finding use the CHANGELOG.md raw URL (`https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`), and `publishedAt` is not available — omit the date from citation prose.

### Step 4 — Both paths fail: emit lane_unavailable

If BOTH the primary (`gh`) and fallback (WebFetch) fail, emit a single `lane_unavailable` finding (degenerate form — see below) and stop. Do NOT report zero findings and return normally — that is indistinguishable from "everything is fine" and would silently advance the watermark past changes that were never checked. The S30/S35 rule: every fetch failure is explicit, named, and blocks the watermark advance.

### Step 5 — Extract candidate deltas per release

For each in-scope release body, extract these categories of change. Each is a candidate delta — proceed to Step 6 before emitting as a finding.

- **Renames or deprecations** of commands, flags, or slash-command names (e.g. a built-in skill renamed, a flag removed or renamed).
- **New or changed frontmatter keys** in skill YAML (e.g. a new required field, a renamed field, a changed allowed-values enum).
- **New or changed hook events** (e.g. a new hook lifecycle point, a renamed event name, changed hook payload shape).
- **Tool-permission syntax changes** (e.g. `allowed-tools` pattern syntax change, new permission categories, changed glob rules).
- **New capabilities** that could replace existing bx workarounds (e.g. a new built-in command that does what a bx skill currently hand-implements).

### Step 6 — Filter against capability inventory and pain points

For each candidate delta: check whether it intersects the `capability_inventory` or addresses an item in the `pain_point_list`. If neither — discard silently. Only emit findings for candidates that match. Pain-point matches with no inventory capability produce a finding with `affected_capability` set to the `bx:pain/<kebab-slug>` form (see the `bx:pain/<kebab-slug>` convention in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section).

### Step 7 — Populate affected_files via Grep

For each surviving delta (post-filter), identify the old/changed token (command name, flag name, frontmatter key, hook event name). Run Grep over the repo with scope `bx/`, `README.md`, and `workflow.md` to find every file that contains that token. List every hit file in `affected_files`. This is how sibling-file echoes are found (S45 rule). Do not fill `affected_files` from the capability string alone — always grep first.

Example: if a flag `--allowed-tools` is renamed, run `Grep pattern="--allowed-tools" path="bx/"` and also check `README.md` and `workflow.md` individually. Every returned file path goes into `affected_files`.

---

## Degraded-run deduplication

If two releases in a degraded run produce the same `(source_url, affected_capability)` pair, merge them into one finding. The merged finding's `upstream_delta` names both versions (e.g. `"2.1.160 + 2.1.161: ..."`), and `source_excerpt` concatenates the two verbatim sections (newest version first, separated by a blank line) for the orchestrator to normalize and hash.

---

## lane_status definitions

`lane_status` must be one of these three values. It is declared in the footer addendum and governs watermark advancement.

| Value | Meaning | Watermark advance? |
|---|---|---|
| `ok` | Primary method (`gh`) succeeded. Release bodies were fetched directly; `publishedAt` dates and release URLs are precise. | Yes — `last_changelog_version` advances to `newest_version_seen`. |
| `degraded` | Primary (`gh`) failed; fallback (raw CHANGELOG.md fetch) succeeded. Findings are still trustworthy but `citation` URLs and dates are coarser (raw file URL instead of per-release URL; no `publishedAt`). | Yes — `last_changelog_version` still advances because the changelog content was successfully evaluated; the user is informed of the coarser citation quality via the `lane_status: degraded` disclosure. |
| `unavailable` | Both primary and fallback failed. Only the `lane_unavailable` degenerate finding was emitted. | No — the orchestrator MUST NOT advance `last_changelog_version` when `lane_status` is `unavailable`. The missed range will be re-checked on the next run because the watermark is unchanged. |

**Why this matters:** the orchestrator advances the watermark only on `ok` or `degraded`. Silent degradation is impossible — the report footer always discloses `lane_status`, so the user knows whether citations are precise or coarse, and knows when no advance occurred.

---

## Finding schema (use exactly these field names)

```json
{
  "finding_id": null,
  "class": "breakage | best_practice | opportunity",
  "tier": "official",
  "severity": "low | medium | high",
  "certainty": "0.0–1.0",
  "affected_files": ["<every file needing the edit, including sibling-file echoes>"],
  "upstream_delta": "<one-line: what changed upstream>",
  "proposed_edit": "<prose + concrete old→new where possible>",
  "citation": "<the release URL>",
  "source_url": "<canonicalized release URL — same value used in finding_id>",
  "affected_capability": "<capability string, e.g. bx:*/allowed-tools>",
  "source_excerpt": "<verbatim heading-bounded section from the release body — the exact text the orchestrator will normalize and hash>"
}
```

**`finding_id`:** set to `null` — computed by the orchestrator at consolidation from `source_url + "|" + affected_capability`. Do not attempt to compute it here. Exception: the `lane-unavailable-changelog` sentinel keeps its literal string ID (see degenerate finding below).

**`source_excerpt`:** the verbatim heading-bounded extract (or release-body section) that is the hash input — not your own summary prose. The orchestrator normalizes and hashes your `source_excerpt` per `bx/skills/evolve/references/state-schema.md` to produce `source_content_hash`. Return the raw extract; do not attempt to hash.

**`affected_capability` normalization:** normalize per `bx/skills/evolve/references/state-schema.md`. Example: `"bx:seo/allowed-tools"`. For pain-point-only findings (no inventory capability matched), use the `bx:pain/<kebab-slug>` form — the slug derivation convention (form, example, stability requirement) is defined in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.

**`source_url` for the `ok` path:** the GitHub release URL for the specific tag, e.g. `https://github.com/anthropics/claude-code/releases/tag/v2.1.170`. Apply canonicalization per `bx/skills/evolve/references/state-schema.md` before hashing and storing.

**`source_url` for the `degraded` path:** `https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md` (canonicalized). All findings in a degraded run share this URL; `finding_id` differentiation comes from `affected_capability`.

**`class` assignment guidance:**

- `breakage` — the upstream change means existing bx config/syntax is now wrong or will stop working (e.g. a renamed flag bx currently uses, a removed frontmatter key bx emits).
- `best_practice` — the change deprecates or explicitly recommends against a pattern bx currently uses, while the current approach still works. NOT for "a recommended pattern bx isn't using" in general — that fails the relevance gate unless it matches a pain point.
- `opportunity` — a new capability directly addresses a recorded pain point from `pain_point_list` and bx does not yet use it. The pain-point match is mandatory — a new capability with no pain-point match is discarded (same rule as the docs lane).

**`severity` guidance:**

- `high` — breakage findings, OR opportunity findings that address a pain point the user has explicitly called out.
- `medium` — best_practice findings on heavily-used capabilities, or opportunity findings with clear benefit.
- `low` — best_practice or opportunity findings on rarely-invoked paths.

**`certainty` guidance:** 1.0 for breakages where the old syntax is confirmed removed; 0.7–0.9 for deprecations with a migration path; 0.5–0.7 for opportunity findings where the new capability MAY cover the use case but needs verification.

---

## lane_unavailable degenerate finding

When both primary and fallback fail, emit ONLY this finding (no others):

```json
{
  "finding_id": "lane-unavailable-changelog",
  "class": null,
  "tier": "official",
  "severity": "high",
  "certainty": 1.0,
  "affected_files": [],
  "upstream_delta": "<verbatim error from gh> | <verbatim error from the fallback WebFetch>",
  "proposed_edit": "Re-run /bx:evolve when network/gh auth is available. The changelog watermark was NOT advanced.",
  "citation": null,
  "source_url": null,
  "affected_capability": null,
  "source_excerpt": null
}
```

This sentinel keeps its literal `finding_id` string — no hashing involved. It has no `source_excerpt` (null) because there is no upstream section to extract.

The orchestrator MUST NOT advance `last_changelog_version` when this finding is present. Set `lane_status: unavailable` in the footer addendum.

---

## Hard rules

- **Never report zero findings silently.** If in-scope releases exist but none match the capability inventory or pain points, append a note in the footer: `scan_note: <N> releases evaluated; no capability or pain-point matches found`. This is different from `unavailable` — it means the scan ran cleanly but nothing was relevant.
- **Include sibling-file echoes in `affected_files`.** Always populate via Step 7 Grep — never infer from the capability string alone. If a rename or syntax change requires edits in multiple files (e.g. the skill SKILL.md AND a references/ file AND CLAUDE.md), list every file.
- **Order findings by `severity_weight × certainty` descending.** Severity weights: high=3, medium=2, low=1. Cap at 20 findings. If more than 20 qualify, include the 20 highest-weighted and note the count of discarded findings in the footer.
- **Do not restate algorithms from `bx/skills/evolve/references/state-schema.md`.** Point to that file for `finding_id` computation, `source_url` canonicalization, and `source_content_hash` normalization. Duplication causes drift — the S45 lesson.

---

## Final output addendum

After all findings (or after the single `lane_unavailable` finding), append:

```
releases_scanned: <n — 0 if lane_status is unavailable, since nothing was successfully evaluated>
newest_version_seen: <unprefixed version string, or null if unavailable>
lane_status: ok | degraded | unavailable
scan_note: <optional — used when scan ran cleanly but zero capability matches found, when the --limit 50 window was exhausted, or when the watermark anchor was not found>
discarded_findings: <count of findings dropped by the 20-finding cap PLUS zero-hit affected_files discards from Step 7, or 0>   # same semantics in all three lanes
```

**Zero-new-releases case:** when `last_changelog_version` equals the newest release tag in the window (i.e., no in-scope releases exist since the watermark), set `releases_scanned: 0`, `lane_status: ok`, and `newest_version_seen` to the incoming `last_changelog_version` value (a no-op advance). Never emit `null` for `newest_version_seen` on an `ok` run — the orchestrator advances the watermark to this value, and `null` would clobber the stored watermark and force a full rescan on the next run.

These power the report footer and the orchestrator's watermark-advance decision.
