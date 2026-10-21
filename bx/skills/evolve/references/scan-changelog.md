# Scan: Changelog (upstream claude-code releases)

Loaded by the orchestrator and passed to the `upstream-changelog` subagent. You are that subagent. Detailed scanning instructions follow.

You have these tools available: Read, Grep, Glob, Bash (gh commands only — pattern `gh *`), WebFetch. Use `gh` and WebFetch for all network access. No `curl`, no `git clone`, no shell HTTP commands.

---

## Inputs you receive in your task prompt

- `last_changelog_version` — string (e.g. `"2.1.170"`) or null. The highest claude-code release processed on the last run, stored as an **unprefixed version string** (no leading `v`). Null means this is the first run — scan ALL releases in the window.
- `capability_inventory` — list of bx capability strings (e.g. `"bx:seo/allowed-tools"`, `"bx:save/agent-model"`). Only produce findings that intersect this list or a pain-point from the list below.
- `pain_point_list` — list of `{id, text}` objects naming known friction areas in the bx toolkit (e.g. `{"id": "permission-prompts-allowed-tools", "text": "permission prompts when allowed-tools misses a command"}`). A release note that addresses a pain point qualifies as a finding even without an exact capability match. For such findings, set `affected_capability` to `bx:pain/<id>` with the `id` copied verbatim from the list — never derived from the text, never invented (see the schema notes below).

---

## Version normalization rule

claude-code release tags use a leading `v` (e.g. `v2.1.170`); CHANGELOG.md headings omit the `v` (e.g. `## 2.1.170`). **Strip the leading `v` for ALL comparisons and for storing the watermark.** The stored `last_changelog_version` is always the unprefixed string (e.g. `2.1.170`). Release URLs retain the `v` (e.g. `https://github.com/anthropics/claude-code/releases/tag/v2.1.170`).

---

## Method

### Step 1 — Fetch releases (primary: gh), paginating to the watermark anchor

Fetch page 1:

```
gh api "repos/anthropics/claude-code/releases?per_page=50&page=1"
```

This returns a JSON array of release objects, newest-first. Each object contains `tag_name`, `body`, and `published_at`. Parse the array in-context — no per-release follow-up calls needed.

**Failure definition:** A call fails if it exits non-zero OR returns empty/invalid JSON. A failure on page 1 falls back to the WebFetch CHANGELOG path (Step 3) with `lane_status: degraded`. A failure on a later page ends pagination: treat the pages already fetched as the window and continue with the anchor-not-found rule below (`degraded`).

**The target version.** The version you paginate toward is the **anchor**: normally `last_changelog_version`; when the context block carries a non-null `changelog_gap`, it is the gap's `after` instead (see *Closing a recorded gap*). Versions compare numerically, component by component (`2.1.420` > `2.1.99`), never as strings; a tag that does not parse as three non-negative integers is skipped with a `scan_note` naming it.

**Watermark stop rule:** Normalize each `tag_name` (strip leading `v`) before comparing. Walk the fetched releases from newest to oldest and stop at the first release whose version is **less than or equal to** the anchor; that release and everything older are excluded. Equal means the anchor tag is present. Less-than means the anchor tag itself is gone (yanked or renamed) but every release newer than it has been seen — treat the anchor as found, exclude from that release on, and emit `scan_note: watermark anchor <anchor> not present; sliced at <first older version>`. No gap exists in either case.

**Pagination rule:** if page 1 does not reach the anchor (its oldest release is still newer than the anchor), fetch `page=2`, then `page=3`, … up to **`page=10`** (500 releases), stopping as soon as a page reaches the anchor or a page returns an empty array (`[]`, the end of the release history). Concatenate pages newest-first. The anchor is almost always on page 1; every further page is one more `gh` call and nothing else. If `last_changelog_version` is null, fetch page 1 only — a null watermark is the first-run / `--full` re-audit of the recent window, not a request to read the whole history.

**Cap reached before the anchor** (10 pages fetched, the tenth non-empty, oldest release still newer than the anchor — whether history continues past page 10 is unknown and irrelevant: the cap is the cap): set `lane_status: degraded`, process every release fetched, and report the gap in the footer: `gap_after: <anchor>` and `gap_before: <normalized version of the oldest release fetched>` — the releases strictly between those two versions were never scanned. The orchestrator records this as `watermark.changelog_gap` (Step 6) and the report shows it every run until it is closed. Also emit `scan_note: watermark anchor <anchor> not reached in 10 pages (<M> releases); gap recorded`.

**End of history before the anchor** (a page returned `[]` and the oldest release fetched is still newer than the anchor): the anchor predates the whole release history, so nothing is unscanned — process everything fetched, `lane_status: ok`, no gap, `scan_note: watermark anchor <anchor> predates the release history; all <M> releases scanned`. If a gap was recorded, this closes it (`gap_closed: true`).

A null-watermark run that fills page 1 completely (50 entries) emits `scan_note: 50-release window exhausted (first run / --full)` and no gap.

**Closing a recorded gap.** When the context block carries `changelog_gap: {after, before}`, the anchor is `after` (above). Reaching it — by equality, by passing it, or by hitting the end of history — closes the gap: set `gap_closed: true`, `gap_after: null`, `gap_before: null`. Hitting the cap first leaves the gap open: `lane_status: degraded`, `gap_closed: false`, `gap_after: <after>` unchanged, `gap_before: <new oldest release fetched>`. **Input this run** is the union of two ranges: releases newer than `last_changelog_version` (the normal delta) AND releases strictly between `after` and `before` (the gap fill); releases from `before` up to and including the watermark were processed on earlier runs and are not re-processed. Report `releases_scanned` as the total and `gap_fill_scanned` as the second range's count. A `--full` run closes any gap unconditionally (`gap_closed: true`) because it re-audits the recent window by design and the user has asked for a fresh baseline.

### Step 2 — Extract release content (primary: gh)

The `gh api` call above returns `body` (markdown), `tag_name`, and `published_at` for every release in the array — no additional fetch needed. Apply the watermark slice from Step 1 to select in-scope releases, then proceed directly to Step 5 extraction.

### Step 3 — Fallback when gh fails

If the `gh api` call in Step 1 fails (non-zero exit, empty JSON, or invalid JSON), fall back to:

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

For each candidate delta: check whether it intersects the `capability_inventory` or addresses an item in the `pain_point_list`. If neither — discard silently. Only emit findings for candidates that match. Pain-point matches with no inventory capability produce a finding with `affected_capability` set to `bx:pain/<id>` (id copied from `pain_point_list` — see the schema notes below).

### Step 7 — Populate affected_files via Grep

For each surviving delta (post-filter), identify the old/changed token (command name, flag name, frontmatter key, hook event name). Run one Grep call using `glob="{bx/**,README.md,workflow.md}"` from repo root to find every file containing that token. List every hit file in `affected_files`. This is how sibling-file echoes are found (S45 rule). Do not fill `affected_files` from the capability string alone — always grep first.

**When multiple deltas survive**, batch them: issue one Grep in content mode with an alternation pattern (`tok1|tok2|...`) across `glob="{bx/**,README.md,workflow.md}"`, then map each file→token in-context. This is the repo's batched-Grep idiom.

**Zero-hit discard rule:** for `breakage` and `best_practice` findings, zero Grep hits for the old/changed token means the plugin does not contain it — discard the finding and increment `discarded_findings`. For `opportunity` findings there is no old token to search for; instead, set `affected_files` to the file(s) the proposed edit would touch, identified from the pain point's subject area. An empty `affected_files` is never legal in an emitted finding — if you cannot identify at least one file for any class, discard.

---

## Degraded-run deduplication

If two releases in a degraded run produce the same `(source_url, affected_capability)` pair, merge them into one finding. The merged finding's `upstream_delta` names both versions (e.g. `"2.1.160 + 2.1.161: ..."`), and `source_excerpt` concatenates the two verbatim sections (newest version first, separated by a blank line) for the orchestrator to normalize and hash.

---

## lane_status definitions

`lane_status` must be one of these three values. It is declared in the footer addendum and governs watermark advancement.

| Value | Meaning | Watermark advance? |
|---|---|---|
| `ok` | Primary method (`gh`) succeeded. Release bodies were fetched directly; `publishedAt` dates and release URLs are precise. | Yes — `last_changelog_version` advances to `newest_version_seen`. |
| `degraded` | Primary (`gh`) failed and the fallback (raw CHANGELOG.md fetch) succeeded — findings are trustworthy but `citation` URLs and dates are coarser (raw file URL, no `publishedAt`); OR `gh` succeeded but the watermark anchor was not found within the paginated window, so a gap exists (`gap_after`/`gap_before` set). | Yes — `last_changelog_version` still advances to `newest_version_seen` because everything fetched was evaluated; the gap, if any, is recorded in `watermark.changelog_gap` so the unscanned range is never silently forgotten. |
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

**`affected_capability` normalization:** normalize per `bx/skills/evolve/references/state-schema.md`. Example: `"bx:seo/allowed-tools"`. For pain-point-only findings (no inventory capability matched), use `bx:pain/<id>` with the id from `pain_point_list` — the convention and its reason are in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.

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
pages_fetched: <number of gh page calls made this run, 1–10 (the cap is never exceeded, so page 11 is never requested; an empty page reached within the cap counts); 0 on the CHANGELOG.md fallback>
oldest_version_seen: <unprefixed version string of the oldest release fetched — fetched, not processed — or null if unavailable>
gap_fill_scanned: <releases processed from inside a recorded gap this run, else 0>
gap_after: <the anchor version when the cap was reached before it, else null>
gap_before: <oldest_version_seen when the cap was reached before the anchor, else null>
gap_closed: <true when a recorded changelog_gap was closed this run (anchor reached or passed, end of history, or --full), else false>
lane_status: ok | degraded | unavailable
allowlist_candidates: [<url> — <one-line reason>, ...]   # official pages you reached or needed that are NOT on scan-docs.md's pinned allowlist; empty list [] when none
scan_note: <optional; several notes may apply in one run — join them with ` | ` in the order they arose (a single note may itself contain `; `). Used when the scan ran cleanly but found zero capability matches, when the 50-release window was exhausted on a null watermark, when the anchor tag was not present and the slice fell to the next older release, when the cap was reached before the anchor (gap recorded), or when the anchor predates the release history>
discarded_findings: <count of findings dropped by the 20-finding cap PLUS zero-hit affected_files discards from Step 7, or 0>
releases_digest: [<unprefixed version> — <publishedAt date> — <one-line summary>, ...]   # one entry per in-scope release processed; the summary is the body's first bullet (else its first non-heading line), trimmed to one line; on the degraded path (CHANGELOG.md fallback) the date field is omitted since publishedAt is unavailable
```

`releases_digest` feeds the report's Section 1 per-release lines. Include one entry for every release that was in scope (i.e., every release fetched and evaluated, regardless of whether it produced a finding). If `lane_status` is `unavailable`, emit an empty list `[]`.

**Zero-new-releases case:** when `last_changelog_version` equals the newest release tag in the window (i.e., no in-scope releases exist since the watermark), set `releases_scanned: 0`, `lane_status: ok`, and `newest_version_seen` to the incoming `last_changelog_version` value (a no-op advance). Never emit `null` for `newest_version_seen` on an `ok` run — the orchestrator advances the watermark to this value, and `null` would clobber the stored watermark and force a full rescan on the next run.

`allowlist_candidates` is required (an empty list is valid): when a release note points at a docs page for the detail of a change that intersects the inventory, and that page is not on `scan-docs.md`'s pinned allowlist, list it with the reason — the docs lane cannot see a page nobody pinned.

These power the report footer and the orchestrator's watermark-advance decision.
