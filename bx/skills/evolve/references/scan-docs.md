# Scan: Official Docs (Anthropic docs pages)

Loaded by the orchestrator and passed to the `upstream-docs` subagent. You are that subagent. Detailed scanning instructions follow.

You have these tools available: Read, Grep, Glob, WebFetch. Use WebFetch for all network access. No `curl`, no shell HTTP commands.

---

## Inputs you receive in your task prompt

- `docs_checked_at` — ISO date string (YYYY-MM-DD) or null. The date the docs pages were last fetched and compared against the capability inventory. Null means this is the first run. This field frames the report ("docs checked as of <date>") but does NOT gate what you fetch — you always re-read all allowlisted pages on every run and compare against the live capability inventory (see Delta detection below).
- `capability_inventory` — list of bx capability strings (e.g. `"bx:seo/allowed-tools"`, `"bx:save/agent-model"`). Only produce findings that intersect this list or a pain point from the list below.
- `pain_point_list` — list of short strings describing known friction areas in the bx toolkit (e.g. `"permission prompts on every run"`, `"watermark drift on partial failures"`). Official guidance that addresses a pain point qualifies as a finding even without an exact capability match. For such findings, set `affected_capability` to the `bx:pain/<kebab-slug>` form — see the `bx:pain/<kebab-slug>` convention in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.
- `tier_definitions` — the tier table from the orchestrator (currently only one tier for this lane: `tier: official`). You only emit `tier: official`.

---

## Pinned URL allowlist

Verified 2026-06-09. For each URL: the working form confirmed by WebFetch, the capability area it covers, and any redirect note.

| URL | Capability area | Notes |
|-----|----------------|-------|
| `https://code.claude.com/docs/en/skills` | skill authoring — SKILL.md frontmatter, invocation control, subagent execution, dynamic context injection | loads directly |
| `https://code.claude.com/docs/en/plugins` | plugin creation — manifest schema, directory layout, skills/agents/hooks packaging, marketplace submission | loads directly |
| `https://code.claude.com/docs/en/plugins-reference` | plugin technical reference — complete schema specs, CLI commands, version management, monitors, LSP servers | loads directly |
| `https://code.claude.com/docs/en/hooks` | hook events — lifecycle points, matcher patterns, handler types, JSON schemas, exit codes, async/HTTP/MCP/prompt hooks | loads directly (page title is "Hooks reference"; the `/hooks-reference` path 404s) |
| `https://code.claude.com/docs/en/settings` | settings — scope hierarchy, settings files, permissions, allowed-tools syntax, env vars | loads directly |
| `https://code.claude.com/docs/en/sub-agents` | subagent configuration — system prompts, tool restrictions, model routing, persistent memory | loads directly |
| `https://code.claude.com/docs/en/memory` | memory — CLAUDE.md authoring, auto memory, .claude/rules/, path-scoped rules, import syntax | loads directly |
| `https://code.claude.com/docs/en/commands` | commands/slash-commands reference — built-in commands, bundled skills, workflow commands | candidate `/slash-commands` redirects to skills page; successor is this URL |

This lane fetches ONLY these allowlisted URLs. Following a link is allowed only to an anchor on the **same page** (one hop to a `#fragment`). Never follow links to other pages or domains. Why: unbounded link-chasing turns this pinned lane into an open-research lane and destroys the authority guarantee — findings must be traceable to a specific canonical page.

---

## Delta detection — no version watermark

Docs pages are not versioned like releases. The comparison baseline is the **capability inventory** (what the bx plugin currently does), NOT memory of past page content. `docs_checked_at` only frames the report ("docs checked as of <date>"); it does NOT define what to check.

Every run: re-read all allowlisted pages, compare guidance against the inventory, and emit findings for any gap. This is why the lane stays cheap and stateless — there is no stored "last seen" page content to diff against.

The orchestrator advances `docs_checked_at` only on `ok` or `degraded` (per `bx/skills/evolve/references/state-schema.md` Rule 4).

---

## Method

### Step 1 — Fetch each allowlisted page

For each URL in the pinned allowlist above, call `WebFetch` using that URL's "Capability area" column (from the allowlist table) as the fetch prompt focus — ask for the full page content relevant to that specific area. Do not use a single generic prompt enumerating all areas for every URL; the per-row capability area is the fetch focus.

**Failure definition:** A fetch fails if WebFetch returns an error, a redirect to an unrelated page, or empty content where content is expected. On any failure: record the URL and error in `pages_failed` for the footer addendum and continue with the remaining URLs. Never silently skip a failed fetch — the footer must name every failure explicitly.

**One-hop rule:** you may follow a `#fragment` anchor on the same page to read a specific section. Never follow links to other pages or domains.

**Verbatim-extract requirement (hash stability):** for each guidance item that becomes a candidate delta, capture the **verbatim page text** of the smallest heading-bounded section containing that guidance — from its own heading to the next same-or-higher-level heading. That verbatim extract (not WebFetch's summary prose) is what gets returned as `source_excerpt`. Hashing a summary hashes noise: WebFetch's model-processed output varies between calls, causing the hash to change even when the underlying guidance is unchanged — which re-raises every rejected finding on every run (state-schema Rule 3). The verbatim extract is the only stable hash input; the orchestrator normalizes and hashes it.

**Order:** fetch every allowlisted URL. Do not stop early on a failure — fetch all, then tally `lane_status`.

### Step 2 — Extract candidate deltas per page

For each successfully fetched page, extract guidance that falls into either category:

**(a) Contradiction with current bx behavior:**
- Guidance that contradicts something bx currently does (e.g. a frontmatter key bx uses has been renamed, a hook event bx uses has been removed, an `allowed-tools` pattern bx uses is now invalid)
- Guidance that recommends AGAINST a pattern bx currently uses (deprecation, anti-pattern callout)

**(b) New capability matching a recorded pain point:**
- A feature described in the docs that directly addresses a pain point in the `pain_point_list` and bx does not yet use it

Each is a candidate delta — proceed to Step 3 before emitting as a finding.

**Class assignment guidance** (derives directly from Step 2's extraction categories):
- `breakage` — category (a): guidance says the plugin's current form is deprecated, removed, or broken (e.g. a frontmatter key bx uses has been renamed or removed, a hook event has been dropped). Certainty 1.0 if removal is confirmed; 0.7–0.9 if deprecated-with-migration-path.
- `best_practice` — category (a) only: guidance explicitly recommends AGAINST a pattern bx currently uses (deprecation callout, anti-pattern warning) but the current approach still works. NOT for "a pattern bx isn't using" in general — only for guidance that calls out bx's existing behavior as not recommended. Certainty 0.7–0.9.
- `opportunity` — category (b) only: a new capability in the docs directly addresses a recorded pain point from `pain_point_list` and bx does not yet use it. The pain-point match is mandatory — a new capability with no pain-point match is discarded. Certainty 0.5–0.7.

### Step 3 — Verification gate

Before assigning a class or emitting any finding, Read the actual bx file(s) the candidate delta maps to and confirm the contradiction or absence in real file content.

- For a `breakage` or `best_practice` candidate: locate the specific token (frontmatter key, hook event name, settings key, flag, command) in the bx plugin files via Grep. If the token is not present in any bx file, the contradiction cannot be confirmed — cap `certainty` at 0.5 or discard the candidate.
- For an `opportunity` candidate: locate the relevant capability area in the bx plugin files. If bx already uses the new capability (the pain point is already addressed), discard the candidate.
- If you cannot confirm the contradiction or absence in a bx file, the candidate is either a false positive (bx doesn't use that token at all) or already resolved. A delta you could not confirm in a real bx file is capped at `certainty: 0.5` or discarded. **Why:** the capability inventory is a list of labels, not behavior — asserting contradictions from a label alone produces paraphrase-level junk findings that waste user attention.

Only candidates that survive the verification gate proceed to Step 4.

### Step 4 — Filter against capability inventory and pain points

For each verified candidate delta: check whether it intersects the `capability_inventory` or addresses an item in the `pain_point_list`. If neither — discard silently. Only emit findings for candidates that match. Pain-point-only findings use `affected_capability: bx:pain/<kebab-slug>` — the slug convention and normalization rule are defined in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.

### Step 5 — Populate affected_files via Grep

For each surviving delta, identify the old/changed token (frontmatter key, hook event name, settings key, command name, flag name). Run Grep over the repo with scope `bx/`, `README.md`, and `workflow.md` to find every file that contains that token. List every hit file in `affected_files`.

This is how sibling-file echoes are found (S45 rule: a rework isn't done until its echoes are swept from sibling files). Do not fill `affected_files` from the capability string alone — always grep first.

**Zero-hit grep rule:** for `breakage` and `best_practice` findings, zero Grep hits for the old/changed token means the plugin does not contain it — discard the finding and increment the discarded count in the footer. (The verification gate in Step 3 should have caught this; Step 5 is the final check.) For `opportunity` findings, there is no old token to search for; instead, set `affected_files` to the file(s) the proposed edit would touch, identified from the pain point's subject area. An empty `affected_files` is never legal in an emitted finding — if you cannot identify at least one file, discard the finding.

Example: if a frontmatter key `when_to_use` is described differently in the docs, run `Grep pattern="when_to_use" path="bx/"` and also check `README.md` and `workflow.md` individually. Every returned file path goes into `affected_files`.

---

## lane_status definitions

`lane_status` must be one of these three values. It is declared in the footer addendum and governs `docs_checked_at` advancement.

| Value | Meaning | `docs_checked_at` advances? |
|---|---|---|
| `ok` | Every allowlisted page fetched successfully. | Yes — advances to today. |
| `degraded` | At least one page fetched, at least one failed. Findings are trustworthy but coverage is partial — failed pages' capability areas were NOT checked this run. | Yes — advances to today. The failed URLs are disclosed in the footer so the user knows which areas had partial coverage. |
| `unavailable` | Every fetch failed. Only the degenerate `lane_unavailable` finding is emitted. | No — the orchestrator MUST NOT advance `docs_checked_at`. The missed check will be re-run next run because the watermark is unchanged. |

**No fallback method exists for this lane.** Unlike the changelog lane (which falls back from `gh` to raw CHANGELOG.md), the docs lane has only one method: WebFetch the allowlisted URLs. If all fetches fail, the lane is `unavailable`. There is no mixed-source ambiguity.

The orchestrator advances `docs_checked_at` only on `ok` or `degraded`, per `bx/skills/evolve/references/state-schema.md` Rule 4.

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
  "upstream_delta": "<one-line: what the docs say vs what bx currently does>",
  "proposed_edit": "<prose + concrete old→new where possible>",
  "citation": "<the allowlisted doc URL — same as source_url for this lane>",
  "source_url": "<canonicalized allowlisted URL — same value used in finding_id>",
  "affected_capability": "<capability string, e.g. bx:*/allowed-tools>",
  "source_excerpt": "<verbatim heading-bounded section from the fetched page — the exact text the orchestrator will normalize and hash>"
}
```

**`finding_id`:** set to `null` — computed by the orchestrator at consolidation from `source_url + "|" + affected_capability`. Do not attempt to compute it here. Exception: the `lane-unavailable-docs` sentinel keeps its literal string ID (see degenerate finding below).

**`source_excerpt`:** the verbatim heading-bounded section extract (per the verbatim-extract requirement in Step 1) — never WebFetch's summary prose (summaries are unstable across calls; see Step 1 for why). The orchestrator normalizes and hashes your `source_excerpt` per `bx/skills/evolve/references/state-schema.md` to produce `source_content_hash`. Return the raw extract; do not attempt to hash.

**`affected_capability` normalization:** normalize per `bx/skills/evolve/references/state-schema.md`. For pain-point-only findings (no inventory capability matched), use the `bx:pain/<kebab-slug>` form — the slug convention is defined in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.

**`source_url`:** the canonicalized allowlisted URL for the page the finding comes from (e.g. `https://code.claude.com/docs/en/hooks`). Apply canonicalization per `bx/skills/evolve/references/state-schema.md` before hashing and storing. For this lane, `citation` and `source_url` always have the same value.

**`severity` guidance:**
- `high` — breakage findings, OR opportunity findings that directly address a pain point the user has explicitly called out.
- `medium` — best_practice findings on heavily-used capabilities, or opportunity findings with clear benefit.
- `low` — best_practice or opportunity findings on rarely-invoked paths.

**Cap:** max 15 findings, ordered `severity_weight × certainty` descending. Severity weights: high=3, medium=2, low=1 (same as changelog lane). If more than 15 qualify, include the 15 highest-weighted and note the count of discarded findings in the footer.

---

## lane_unavailable degenerate finding

When every allowlisted URL fails, emit ONLY this finding (no others):

```json
{
  "finding_id": "lane-unavailable-docs",
  "class": null,
  "tier": "official",
  "severity": "high",
  "certainty": 1.0,
  "affected_files": [],
  "upstream_delta": "<verbatim errors from each failed WebFetch call>",
  "proposed_edit": "Re-run /bx:evolve when network is available; docs_checked_at was NOT advanced.",
  "citation": null,
  "source_url": null,
  "affected_capability": null,
  "source_excerpt": null
}
```

This sentinel keeps its literal `finding_id` string — no hashing involved. It has no `source_excerpt` (null) because there is no upstream section to extract.

Set `lane_status: unavailable` in the footer addendum. The orchestrator MUST NOT advance `docs_checked_at` when this finding is present.

---

## Hard rules

- **Never report zero findings silently.** If all pages were fetched but none of the guidance contradicts bx or addresses a pain point, append a note in the footer: `scan_note: <N> pages evaluated; no capability or pain-point matches found`. This is different from `unavailable` — it means the scan ran cleanly but nothing was relevant.
- **Include sibling-file echoes in `affected_files`.** Always populate via Step 5 Grep — never infer from the capability string alone. If official guidance changes a key used in multiple files (e.g. a SKILL.md frontmatter key used in 7 skills + README), list every file.
- **Per-URL failure is explicit.** Every failed fetch is named in `pages_failed` in the footer. A partial success (some pages ok, some failed) → `lane_status: degraded`, not `ok`.
- **Do not restate algorithms from `bx/skills/evolve/references/state-schema.md`.** Point to that file for `finding_id` computation, `source_url` canonicalization, and `source_content_hash` normalization. Duplication causes drift — the S45 lesson.
- **Do not follow links beyond one hop to a same-page anchor.** The pinned allowlist is the full scope of this lane.

---

## Final output addendum

After all findings (or after the single `lane_unavailable` finding), append:

```
pages_fetched: <n — count of allowlisted URLs that returned content successfully>
pages_failed: [<url>: <error>, ...]   # empty list [] if all succeeded
lane_status: ok | degraded | unavailable
scan_note: <optional — used when scan ran cleanly but zero capability matches found, or other non-error observations>
discarded_findings: <count of findings dropped by the 15-finding cap PLUS zero-hit affected_files discards from Step 5, or 0>   # same semantics in all three lanes
```

**Zero-findings-but-all-pages-checked case:** set `pages_fetched` to the count of allowlist rows successfully fetched, `pages_failed` to its real contents (empty list only if truly no fetches failed), `lane_status` to what actually happened (`ok` only if every allowlisted page fetched successfully; `degraded` if any page failed even though zero findings emerged from the pages that did succeed), and use `scan_note` to explain that no gaps were found. Never return an empty finding list without a `scan_note` — that is indistinguishable from a partial run.

These power the report footer and the orchestrator's `docs_checked_at` advance decision.
