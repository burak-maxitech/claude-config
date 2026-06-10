# Scan: Official Docs (Anthropic docs pages)

Loaded by the orchestrator and passed to the `upstream-docs` subagent. You are that subagent. Detailed scanning instructions follow.

You have these tools available: Read, Grep, Glob, WebFetch. Use WebFetch for all network access. No `curl`, no shell HTTP commands.

---

## Inputs you receive in your task prompt

- `docs_checked_at` — ISO date string (YYYY-MM-DD) or null. The date the docs pages were last fetched and compared against the capability inventory. Null means this is the first run. This field frames the report ("docs checked as of <date>") but does NOT gate what you fetch — you always re-read all allowlisted pages on every run and compare against the live capability inventory (see Delta detection below).
- `capability_inventory` — list of bx capability strings (e.g. `"bx:seo/allowed-tools"`, `"bx:save/agent-model"`). Only produce findings that intersect this list or a pain point from the list below.
- `pain_point_list` — list of short strings describing known friction areas in the bx toolkit (e.g. `"permission prompts on every run"`, `"watermark drift on partial failures"`). Official guidance that addresses a pain point qualifies as a finding even without an exact capability match. For such findings, set `affected_capability` to the `bx:pain/<kebab-slug>` form — see `affected_capability` normalization under the Finding schema section and `references/scan-changelog.md`.
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

The orchestrator advances `docs_checked_at` only on `ok` or `degraded` (per `references/state-schema.md` Rule 4).

---

## Method

### Step 1 — Fetch each allowlisted page

For each URL in the pinned allowlist above, call `WebFetch` with a prompt asking for the full page content relevant to skill authoring, plugin structure, hook configuration, settings syntax, subagent definition, memory/CLAUDE.md rules, and command invocation patterns.

**Failure definition:** A fetch fails if WebFetch returns an error, a redirect to an unrelated page, or empty content where content is expected. On any failure: record `fetch_failed: <url>: <error>` for the footer addendum and continue with the remaining URLs. Never silently skip a failed fetch — the footer must name every failure explicitly.

**One-hop rule:** you may follow a `#fragment` anchor on the same page to read a specific section. Never follow links to other pages or domains.

**Order:** fetch all 8 URLs. Do not stop early on a failure — fetch all, then tally `lane_status`.

### Step 2 — Extract candidate deltas per page

For each successfully fetched page, extract guidance that falls into either category:

**(a) Contradiction with current bx behavior:**
- Guidance that contradicts something bx currently does (e.g. a frontmatter key bx uses has been renamed, a hook event bx uses has been removed, an `allowed-tools` pattern bx uses is now invalid)
- Guidance that recommends AGAINST a pattern bx currently uses (deprecation, anti-pattern callout)

**(b) New capability matching a recorded pain point:**
- A feature described in the docs that directly addresses a pain point in the `pain_point_list` and bx does not yet use it

Each is a candidate delta — proceed to Step 3 before emitting as a finding.

**Class assignment guidance:**
- `breakage` — the official docs describe the bx plugin's current form as no longer working or deprecated (e.g. a renamed key, a removed event). Certainty 1.0 if removal is confirmed; 0.7–0.9 if deprecated-with-migration-path.
- `best_practice` — the docs recommend a pattern bx isn't using, or recommend against a pattern bx uses, but the current bx approach still works. Certainty 0.7–0.9.
- `opportunity` — a new capability in the docs could simplify or replace a bx workaround, but bx's current approach still works. Certainty 0.5–0.7.

### Step 3 — Filter against capability inventory and pain points

For each candidate delta: check whether it intersects the `capability_inventory` or addresses an item in the `pain_point_list`. If neither — discard silently. Only emit findings for candidates that match. Pain-point-only findings use `affected_capability: bx:pain/<kebab-slug>` — the slug convention is defined in `references/scan-changelog.md`'s Finding schema section.

### Step 4 — Populate affected_files via Grep

For each surviving delta, identify the old/changed token (frontmatter key, hook event name, settings key, command name, flag name). Run Grep over the repo with scope `bx/`, `README.md`, and `workflow.md` to find every file that contains that token. List every hit file in `affected_files`.

This is how sibling-file echoes are found (S45 rule: a rework isn't done until its echoes are swept from sibling files). Do not fill `affected_files` from the capability string alone — always grep first.

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

The orchestrator advances `docs_checked_at` only on `ok` or `degraded`, per `references/state-schema.md` Rule 4.

---

## Finding schema (use exactly these field names)

```json
{
  "finding_id": "<sha1 of canonicalized source_url + | + affected_capability>",
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
  "source_content_hash": "<sha1 of the normalized cited section text>"
}
```

**`finding_id` computation:** `sha1(source_url + "|" + affected_capability)`. Canonicalize `source_url` and normalize `affected_capability` per `references/state-schema.md` — do not restate the algorithms here.

**`source_content_hash` computation:** normalize and hash per `references/state-schema.md`.

**`affected_capability` normalization:** normalize per `references/state-schema.md`. For pain-point-only findings (no inventory capability matched), use the `bx:pain/<kebab-slug>` form — the slug convention is defined in `references/scan-changelog.md`'s Finding schema section.

**`source_url`:** the canonicalized allowlisted URL for the page the finding comes from (e.g. `https://code.claude.com/docs/en/hooks-reference`). Apply canonicalization per `references/state-schema.md` before hashing and storing. For this lane, `citation` and `source_url` always have the same value.

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
  "source_content_hash": null
}
```

Set `lane_status: unavailable` in the footer addendum. The orchestrator MUST NOT advance `docs_checked_at` when this finding is present.

---

## Hard rules

- **Never report zero findings silently.** If all pages were fetched but none of the guidance contradicts bx or addresses a pain point, append a note in the footer: `scan_note: <N> pages evaluated; no capability or pain-point matches found`. This is different from `unavailable` — it means the scan ran cleanly but nothing was relevant.
- **Include sibling-file echoes in `affected_files`.** Always populate via Step 4 Grep — never infer from the capability string alone. If official guidance changes a key used in multiple files (e.g. a SKILL.md frontmatter key used in 7 skills + README), list every file.
- **Per-URL failure is explicit.** Every failed fetch is named in `pages_failed` in the footer. A partial success (some pages ok, some failed) → `lane_status: degraded`, not `ok`.
- **Do not restate algorithms from `references/state-schema.md`.** Point to that file for `finding_id` computation, `source_url` canonicalization, and `source_content_hash` normalization. Duplication causes drift — the S45 lesson.
- **Do not follow links beyond one hop to a same-page anchor.** The pinned allowlist is the full scope of this lane.

---

## Final output addendum

After all findings (or after the single `lane_unavailable` finding), append:

```
pages_fetched: <n — count of allowlisted URLs that returned content successfully>
pages_failed: [<url>: <error>, ...]   # empty list [] if all succeeded
lane_status: ok | degraded | unavailable
scan_note: <optional — used when scan ran cleanly but zero capability matches found, or other non-error observations>
discarded_findings: <count of findings dropped by the 15-finding cap, or 0>
```

**Zero-findings-but-all-pages-checked case:** set `pages_fetched: 8`, `pages_failed: []`, `lane_status: ok`, and use `scan_note` to explain that no gaps were found. Never return an empty finding list without a `scan_note` — that is indistinguishable from a partial run.

These power the report footer and the orchestrator's `docs_checked_at` advance decision.
