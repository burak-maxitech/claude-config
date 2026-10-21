# Lane contract — what the three `/bx:evolve` scan lanes share

The changelog, docs and community lanes (`scan-changelog.md`, `scan-docs.md`, `scan-community.md`) take the same inputs, report `lane_status` with the same consequences, emit the same sentinel and end with the same footer keys; the two official lanes also apply the same relevance filter, populate `affected_files` the same way and emit the same finding shape (the community lane is a discovery feed since 2.12.0 and emits no findings, so §2–§6 do not bind it). Until bx 2.11.2 each scan file restated all of that, and the three copies had drifted (the S45 lesson: a restated contract drifts). **This file is the named owner of the shared text.** A scan file owns only its *method* — how it fetches, what it extracts, how it classifies — and the values in its column of the tables below. It cites a section here by number and never restates it.

`bx/skills/evolve/references/state-schema.md` owns the algorithms: `finding_id` computation, `source_url` canonicalization, `source_content_hash` normalization, the `bx:pain/<id>` convention. This file points there and restates none of them either.

**Who reads this file:** every lane agent, immediately after its own scan file (SKILL.md Step 2 names both). Where a scan file and this file disagree, this file wins for anything in §1–§10; the scan file wins for its method.

---

## §1 Shared inputs

Every lane's task prompt carries:

- `capability_inventory` — the pinned list of bx capability strings from `bx/skills/evolve/capabilities.json` (e.g. `"bx:seo/allowed-tools"`, `"bx:save-writer/model"`, `"bx:review/builtin:code-review"`, `"bx:hooks/SessionStart"`). Only produce findings that intersect this list or a pain point from the list below, and **`affected_capability` is always one of these strings, copied verbatim** (or `bx:pain/<id>`): pick the entry for the owner and area the edit touches — the frontmatter key, the `tool:<Tool>`, the `builtin:<command>`, the `idiom:<name>`, the hook event. Never compose a string that is not in the list; a freehand string fails the orchestrator's relevance check (SKILL.md Step 3.3) and the finding is dropped. When no entry fits, the finding does not intersect the inventory and is discarded unless it matches a pain point.
- `pain_point_list` — list of `{id, text}` objects naming known friction areas in the bx toolkit (e.g. `{"id": "permission-prompts-allowed-tools", "text": "permission prompts when allowed-tools misses a command"}`). Upstream content that addresses a pain point qualifies as a finding even without an exact capability match. For such findings, set `affected_capability` to `bx:pain/<id>` with the `id` copied verbatim from the list — never derived from the text, never invented (the convention and its reason are in state-schema.md's finding_id computation section).

plus the lane's own watermark field(s), defined in its scan file: `last_changelog_version` and `changelog_gap` (changelog), `docs_checked_at` and `pages_to_scan` (docs), `community_checked_at` (community). The repo root is the working directory; the Grep scope for `affected_files` is `bx/`, `README.md`, `workflow.md`.

---

## §2 Relevance filter

For each candidate delta: check whether it intersects the `capability_inventory` or addresses an item in the `pain_point_list`. If neither — discard silently. Only emit findings for candidates that match. Pain-point matches with no inventory capability produce a finding with `affected_capability` set to `bx:pain/<id>` (id copied from `pain_point_list`). The docs and community lanes run their verification gate (Read the real bx file; confirm the contradiction or absence) *before* this filter; the changelog lane has no gate because a release note states its change directly.

---

## §3 `affected_files` via Grep

For each surviving delta, identify the old/changed token (command name, flag name, frontmatter key, hook event name, settings key, pattern). Run one Grep call using `glob="{bx/**,README.md,workflow.md}"` from repo root to find every file containing that token. List every hit file in `affected_files`. This is how sibling-file echoes are found (the S45 rule: a rework isn't done until its echoes are swept from sibling files). Do not fill `affected_files` from the capability string alone — always grep first.

**When multiple deltas survive**, batch them: issue one Grep in content mode with an alternation pattern (`tok1|tok2|...`) across the same glob, then map each file→token in-context. This is the repo's batched-Grep idiom.

**Zero-hit discard rule:** for `breakage` and `best_practice` findings, zero Grep hits for the old/changed token means the plugin does not contain it — discard the finding and count it in `discarded_findings`. For `opportunity` findings there is no old token to search for; instead, set `affected_files` to the file(s) the proposed edit would touch, identified from the pain point's subject area (the relevant skill's SKILL.md or references/ file). An empty `affected_files` is never legal in an emitted finding — if you cannot identify at least one file for any class, discard.

---

## §4 Finding schema (use exactly these field names)

```json
{
  "finding_id": null,
  "class": "breakage | best_practice | opportunity",
  "tier": "<per lane — table below>",
  "severity": "<per lane — table below>",
  "certainty": "<per lane — table below>",
  "affected_files": ["<every file needing the edit, including sibling-file echoes>"],
  "upstream_delta": "<one line — per lane phrasing below>",
  "proposed_edit": "<per lane phrasing below>",
  "citation": "<per lane — table below>",
  "source_url": "<canonicalized URL — the same value used in finding_id>",
  "affected_capability": "<capability string, e.g. bx:*/allowed-tools, or bx:pain/<id>>",
  "source_excerpt": "<verbatim heading-bounded section of the source — the exact text the orchestrator will normalize and hash>"
}
```

| Field | changelog | docs | community |
|---|---|---|---|
| `tier` | `official` | `official` | *(emits no findings since 2.12.0 — `findings: []`; its output is `allowlist_candidates`, §10)* |
| `severity` | `low` / `medium` / `high` (§6) | `low` / `medium` / `high` (§6) | `low` / `medium` — never `high` (scan-community.md Step 7) |
| `certainty` | 0.0–1.0 (§6) | 0.0–1.0 (§6); an unconfirmed contradiction is capped at 0.5 or discarded | 0.3–0.6 hard band; unconfirmable claims are discarded, never capped |
| `upstream_delta` | what changed upstream | what the docs say vs what bx currently does | what the community source describes vs what bx currently does |
| `proposed_edit` | prose + concrete `old → new` where possible | prose + concrete `old → new` where possible | "consider…" phrasing — advisory, never prescriptive |
| `citation` | the release URL (`ok` path) or the raw CHANGELOG.md URL (`degraded` path) | the allowlisted doc URL — identical to `source_url` | the community page URL — identical to `source_url` |
| `source_url` | the GitHub release URL for the specific tag, e.g. `https://github.com/anthropics/claude-code/releases/tag/v2.1.170`; on the `degraded` path `https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md` for every finding, differentiated by `affected_capability` | the canonicalized allowlisted URL of the page, e.g. `https://code.claude.com/docs/en/hooks` | the canonicalized community page URL |
| finding cap | 20 | 15 | 10 |
| sentinel `finding_id` | `lane-unavailable-changelog` | `lane-unavailable-docs` | `lane-unavailable-community` |
| sentinel `severity` | `high` | `high` | `low` — a missing advisory lane is not urgent |

---

## §5 Field notes (shared)

- **`finding_id`:** set to `null` — the orchestrator computes it at consolidation from `source_url + "|" + affected_capability`. Do not attempt to compute it. Exception: the sentinel keeps its literal string id (§8).
- **`source_excerpt`:** the verbatim heading-bounded extract (release-body section, or page section from its own heading to the next same-or-higher heading) — never your own summary and never WebFetch's model-processed prose. Summaries vary between calls, so hashing one hashes noise and re-raises every rejected finding on every run (state-schema Rule 3). The orchestrator normalizes and hashes your extract per state-schema.md to produce `source_content_hash`; return the raw extract, do not hash.
- **`affected_capability`:** one of the `capability_inventory` strings verbatim (§1), or `bx:pain/<id>` with the id from `pain_point_list`, verbatim. state-schema.md's normalization section describes the form these already satisfy.
- **`source_url`:** apply state-schema.md's canonicalization before returning it; the orchestrator hashes and stores the value you return.

---

## §6 Class and severity guidance (official lanes)

The community lane's Step 7 owns its own class, severity and certainty rules under its TIER RULE; this section binds the changelog and docs lanes.

**Class:**
- `breakage` — the upstream change means existing bx config/syntax is now wrong or will stop working (a renamed flag bx uses, a removed frontmatter key bx emits, a dropped hook event). Certainty 1.0 if the removal is confirmed; 0.7–0.9 if deprecated with a migration path.
- `best_practice` — the change deprecates or explicitly recommends against a pattern bx currently uses, while the current approach still works. NOT for "a recommended pattern bx isn't using" in general — that fails §2 unless it matches a pain point. Certainty 0.7–0.9.
- `opportunity` — a new capability directly addresses a recorded pain point from `pain_point_list` and bx does not yet use it. The pain-point match is mandatory — a new capability with no pain-point match is discarded. Certainty 0.5–0.7.

**Severity:**
- `high` — breakage findings, OR opportunity findings that address a pain point the user has explicitly called out.
- `medium` — best_practice findings on heavily-used capabilities, or opportunity findings with clear benefit.
- `low` — best_practice or opportunity findings on rarely-invoked paths.

---

## §7 `lane_status`

`lane_status` is one of exactly three values, declared in the footer addendum. Each scan file's own table says what the values mean for that lane's method; the consequence is the same everywhere:

| Value | Watermark field advances? |
|---|---|
| `ok` | Yes. |
| `degraded` | Yes — everything fetched was evaluated; the partial coverage is disclosed in the footer (failed pages, coarse citations, a recorded gap). |
| `unavailable` | No. Only the sentinel (§8) was emitted; the orchestrator MUST NOT advance this lane's field, so the missed range is re-checked next run. |

The states are mutually exclusive: `ok` requires zero errors; `degraded` requires at least one success and at least one error; `unavailable` requires total failure. Silent degradation is impossible because the footer always discloses the status. (A fourth status, `current`, is set by the orchestrator in SKILL.md Step 1.5 for a lane it did not dispatch; a lane never emits it.)

---

## §8 Sentinel — the `lane_unavailable` degenerate finding

When the lane's method fails completely (its scan file defines "completely"), emit ONLY this finding and stop. Do NOT return zero findings normally — that is indistinguishable from "everything is fine" and would advance the watermark past changes that were never checked.

```json
{
  "finding_id": "lane-unavailable-<lane>",
  "class": null,
  "tier": "<lane tier, §4>",
  "severity": "<lane sentinel severity, §4>",
  "certainty": 1.0,
  "affected_files": [],
  "upstream_delta": "<the verbatim errors from every failed call, joined with ' | '>",
  "proposed_edit": "<lane-specific re-run advice, from the scan file>",
  "citation": null,
  "source_url": null,
  "affected_capability": null,
  "source_excerpt": null
}
```

The sentinel keeps its literal `finding_id` string — no hashing — and has no `source_excerpt` because there is no upstream section. Set `lane_status: unavailable` in the footer. The orchestrator removes the sentinel at consolidation (SKILL.md Step 3.1); it never reaches hashing, the decision log or fix mode.

---

## §9 Hard rules (shared)

- **Never report zero findings silently.** When the method ran but nothing matched, append `scan_note: <N> <releases|pages> evaluated; no capability or pain-point matches found`. This is different from `unavailable` — the scan ran cleanly and nothing was relevant. An empty finding list without a `scan_note` is indistinguishable from a partial run.
- **Include sibling-file echoes in `affected_files`.** Always populate via §3 Grep — never infer from the capability string alone.
- **Order findings by `severity_weight × certainty` descending** (high = 3, medium = 2, low = 1) and stop at the lane's cap (§4). Count what the cap dropped in `discarded_findings`.
- **Per-failure disclosure is explicit.** Every failed fetch, search or API call is named in the footer (`pages_failed`, `searches_failed`, or the sentinel's `upstream_delta`). A partial success is `degraded`, not `ok`.
- **Official sources belong to the official lanes.** An official page reached or needed that is not on `scan-docs.md`'s pinned allowlist goes in `allowlist_candidates` (§10) — a release note pointing at a docs page for the detail of a change, a page an allowlisted page links to, an Anthropic docs page or maintainer post met while fetching community content. The community lane never emits an official source as a finding.
- **Do not restate algorithms from state-schema.md.** Point to it for `finding_id`, canonicalization and hashing. Duplication causes drift.

---

## §10 Footer addendum — shared keys

After all findings (or after the single sentinel), every lane appends its footer. These keys appear in every lane's footer; the scan file lists the lane's additional keys (versions, pages, searches, gap fields):

```
lane_status: ok | degraded | unavailable
allowlist_candidates: [<url> — <one-line reason>, ...]   # required; [] when none — official pages reached or needed that are NOT on scan-docs.md's pinned allowlist (§9)
scan_note: <optional; several notes join with ` | ` in the order they arose — zero matches on a clean run, caps reached, anchors missing, stale sources, other non-error observations>
discarded_findings: <findings dropped by the lane's cap PLUS §3 zero-hit discards PLUS verification-gate discards, or 0>
```

**Zero-findings-but-the-method-ran case:** fill every count key with what actually happened (`pages_fetched` to the real count, `pages_failed` to its real contents — an empty list only if nothing failed), set `lane_status` to what actually happened (`ok` only if every call succeeded; `degraded` if any failed even though zero findings emerged), and use `scan_note` to say no gaps were found.

The orchestrator renders these in the report footer (`report-template.md`), uses `lane_status` for the Step 6 watermark advance, and offers each `allowlist_candidates` entry as an edit in `--fix` (`fix-mode-evolve.md`, *Allowlist candidates*).
