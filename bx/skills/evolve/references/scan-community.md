# Scan: Community Sources (WebSearch + curated fetches)

Loaded by the orchestrator and passed to the `upstream-community` subagent. You are that subagent. Detailed scanning instructions follow.

You have these tools available: Read, Grep, Glob, WebSearch, WebFetch. Use WebSearch and WebFetch for all network access. No `curl`, no shell HTTP commands.

---

## TIER RULE — READ FIRST

**Every finding from this lane carries `tier: community`. Community findings are advisory-only:**

- They are NEVER `--fix`-eligible (the orchestrator must not offer to apply them automatically).
- `proposed_edit` must be phrased as "consider…" not "change X to Y".
- **Severity caps at `medium` for all community findings** — community claims are uncorroborated by an official source; high severity is reserved for Tier-1 lanes where provenance is verified.
- **Certainty band: 0.3–0.6** — never above 0.6 for any community finding, regardless of how confident the source sounds. Exception: the `lane-unavailable-community` sentinel is exempt (certainty 1.0, empty affected_files) — it reports lane health, not a community claim.

A community pattern becomes actionable (and `--fix`-eligible) ONLY when a Tier-1 source (Anthropic docs or the claude-code changelog) independently corroborates it. In that case, the docs/changelog lane **owns** the finding — not this one. If you encounter an official Anthropic source while fetching community content, do NOT emit a `tier: community` finding for it — record it in `scan_note` so the orchestrator knows the docs or changelog lane should own it.

---

## Inputs you receive in your task prompt

- `community_checked_at` — ISO date string (YYYY-MM-DD) or null. The date the community lane last ran successfully. Null means this is the first run. Used only to frame the report ("community checked as of <date>"); it does NOT gate what you search — you always search with fresh queries.
- `capability_inventory` — list of bx capability strings (e.g. `"bx:seo/allowed-tools"`, `"bx:save/agent-model"`). Only produce findings that intersect this list or a pain point from the list below.
- `pain_point_list` — list of short strings describing known friction areas in the bx toolkit (e.g. `"permission prompts on every run"`, `"watermark drift on partial failures"`). Community guidance that addresses a pain point qualifies as a finding even without an exact capability match. For such findings, set `affected_capability` to the `bx:pain/<kebab-slug>` form — see the `bx:pain/<kebab-slug>` convention in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.
- `tier_definitions` — the tier table from the orchestrator (currently only one tier for this lane: `tier: community`). You only emit `tier: community`; the definitions are context for correctly NOT emitting official-tier findings.

---

## Method

### Step 1 — Formulate queries (at most 3)

Derive at most **3** WebSearch queries per run. Use exactly this allocation — do not improvise additional slots:

1. **Fixed slot 1:** `Claude Code skills best practices <current year>` — scans for general skill-authoring patterns and anti-patterns.
2. **Fixed slot 2:** `Claude Code plugin <capability> pattern` — replace `<capability>` with the capability from `capability_inventory` that has the most entries/files in the inventory (a proxy for surface area, derivable from the input itself; ties broken by pain-point count). If `capability_inventory` is empty, use the most prominent concept from `pain_point_list`. If both `capability_inventory` and `pain_point_list` are empty, run slot 1 only and record the omission in `scan_note`.
3. **Variable slot 3:** Derived from the **highest-severity pain point** in `pain_point_list` — formulate a targeted query for that specific friction. If `pain_point_list` is empty, omit this query.

**Why 3 is the hard cap:** this lane has the worst signal-to-noise ratio of the three lanes. Community posts mix outdated advice, paraphrased official docs, and SEO-shaped listicles. Beyond 3 queries the marginal finding quality drops sharply and the noise-filtering cost (Steps 3–5 below) exceeds the value. The cap is a quality gate, not a time constraint.

### Step 2 — Run WebSearch queries

For each query from Step 1, call WebSearch. Collect all returned URLs and their snippet text.

**Failure definition:** A WebSearch call fails if it returns an error or zero results. Record each failed query in the footer.

**Recency filter (apply immediately):** discard any result whose publish or "last updated" date is older than 6 months before the current date. Exception: if a result is the ONLY source covering a claim that matches a pain point, retain it but flag it in `scan_note` as `stale_source` — cap certainty at 0.3 and use it only for `best_practice`/`breakage` context. A stale-only source cannot support an `opportunity` finding (whose band floor is 0.4); discard `opportunity` candidates sourced exclusively from stale results.

**Authority heuristics (apply before fetching):** from the search results, prefer:
- Named engineering blogs from companies or individuals with Claude Code production experience
- Conference talks or session write-ups
- High-engagement community posts (significant upvotes/stars/reactions visible in the snippet)
- GitHub Discussions, Issues, or Pull Requests on `anthropics/claude-code`

**GitHub boundary rule:** posts by Anthropic maintainers in `anthropics/*` repos (Issues, PRs, Discussions, release notes) count as OFFICIAL sources — never emit them as `tier: community` findings. Hand them off via `scan_note` using the `official_source_found:` format, exactly as you would for any other Tier-1 source encountered during community fetching. Apply shortlist ranking in order: named engineering blog > maintainer/conference content > high-engagement community post; use recency as the tiebreaker. The 5-fetch budget is spent on the global top 5 across all queries.

**Discard before fetching:**
- SEO-shaped listicles ("10 best practices for…", "top X tips…") with no identifiable author
- Results that clearly paraphrase the official Anthropic docs (they carry no independent signal — they are reproductions of Tier-1 content with unknown freshness and accuracy)
- Pages that require sign-in to view content

Apply both filters to produce a ranked shortlist for Step 3. Never fetch a result you have already discarded.

### Step 3 — Fetch shortlisted pages (at most 5 total)

**Hard cap: 5 WebFetch calls for this entire run.** This is the worst-signal-to-noise lane; unbounded fetching is how blogspam and outdated advice get in. The cap forces pre-fetch triage (Step 2 filters) to do its job.

For each shortlisted URL (in rank order, up to 5):
- Call WebFetch using the bx capability area most relevant to that URL as the fetch focus.
- **Verbatim-extract requirement (hash stability):** for each claim that becomes a candidate finding, capture the **verbatim page text** of the smallest heading-bounded section containing that claim — from its own heading to the next same-or-higher-level heading. That verbatim extract (NOT WebFetch's summary prose) is what gets returned as `source_excerpt`. Hashing WebFetch's model-processed summary would produce an unstable hash that changes between calls even when the underlying content is unchanged — which re-raises every rejected finding on every run (state-schema Rule 3). The verbatim extract is the only stable hash input; the orchestrator normalizes and hashes it.
- **Failure definition:** A fetch fails if WebFetch returns an error, a redirect to an unrelated page, or empty content where content is expected. Record each failed URL in `pages_failed` for the footer. Continue with remaining URLs.

If 5 fetches have been used and shortlisted URLs remain, stop fetching and record the count of unfetched URLs in `scan_note` as `cap_reached`.

### Step 4 — Verification gate

**Before assigning a class or emitting any finding, Read the actual bx file(s)** the candidate claim maps to and confirm the claim is about something bx actually does.

- For a `best_practice` candidate (source recommends against a pattern): locate the specific token or pattern in bx plugin files via Grep (scope `bx/`, `README.md`, `workflow.md`). If the token is absent from all bx files, the claim is not about bx's behavior — discard.
- For an `opportunity` candidate (source suggests a pattern addressing a pain point): locate the relevant capability area in bx plugin files. If bx already implements the suggested approach, discard.
- **Unconfirmable claims are discarded entirely** — do not emit even at certainty 0.3. This rule is **stricter than the docs lane** (which caps at 0.5 for unconfirmable claims). The reason: community sources have a higher noise floor — claims are often vague, paraphrased, or inapplicable to bx's specific architecture. Emitting an unconfirmable community finding at any certainty level trains the user to ignore this lane.

Only candidates that survive the verification gate proceed to Step 5.

### Step 5 — Filter against capability inventory and pain points

For each verified candidate: check whether it intersects the `capability_inventory` or addresses an item in the `pain_point_list`. If neither — discard silently. Only emit findings for candidates that match. Pain-point-only findings use `affected_capability: bx:pain/<kebab-slug>` — the slug convention and normalization rule are defined in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.

### Step 6 — Populate affected_files via Grep

For each surviving candidate, identify the token, pattern, or capability area it claims bx uses. Run Grep over the repo with scope `bx/`, `README.md`, and `workflow.md` to find every file that contains that token. List every hit file in `affected_files`.

**Zero-hit Grep rule:** zero Grep hits for a `breakage` or `best_practice` finding → discard (the verification gate in Step 4 should have caught this; Step 6 is the final check). For `opportunity` findings there is no old token to grep for — set `affected_files` to the file(s) the proposed "consider" edit would touch, identified from the pain point's subject (e.g. the relevant skill's SKILL.md or references/ file). The zero-hit discard applies only to `breakage`/`best_practice` claims about existing bx behavior. An empty `affected_files` is never legal in any emitted finding — if you cannot identify at least one file for any class, discard.

**Why Grep is mandatory:** the S45 rule — a rework isn't done until its echoes are swept from sibling files. `affected_files` must name every file the proposed edit would touch, including sibling-file echoes, not just the primary skill file.

### Step 7 — Assign class and certainty

**Class assignment:**
- `breakage` — community source claims a pattern bx uses is broken or incompatible. Class assignment is a guess from community content; certainty 0.3–0.5 (unverified by an official source). A community `breakage` finding is still advisory-only.
- `best_practice` — community source recommends AGAINST a pattern bx currently uses. NOT for "a pattern bx isn't using" in general — only for guidance that calls out bx's existing behavior as not recommended. Certainty 0.3–0.5.
- `opportunity` — community source describes an approach that directly addresses a recorded pain point from `pain_point_list` and bx does not yet use it. The pain-point match is **mandatory** — a community suggestion with no pain-point match is discarded. Certainty 0.4–0.6 (pain-point match provides marginal corroboration).

**Certainty band reminder:** 0.3–0.6 always. Never above 0.6 for any community finding.

**Severity cap reminder:** never `high` for community findings. The maximum is `medium`. Assign:
- `medium` — `breakage` claims from community sources (the cap; an uncorroborated breakage claim is exactly what the Tier-1 corroboration handoff exists for — also record it as a candidate for the changelog/docs lane via `scan_note: changelog_candidate:` or `scan_note: docs_candidate:` when the breakage is plausibly upstream-caused), OR `best_practice`/`opportunity` findings on heavily-used bx capabilities or high-priority pain points.
- `low` — findings on rarely-invoked paths or low-priority pain points.

**Cap: max 10 findings** (the lowest cap of the three lanes). Why: this lane's advisory-only, uncorroborated findings warrant a lower cap than Tier-1 lanes. Surfacing 15–20 advisory items would bury the actionable Tier-1 findings. Order by `severity_weight × certainty` descending. Severity weights: medium=2, low=1. If more than 10 qualify, include the 10 highest-weighted and record the discarded count in the footer.

---

## lane_status definitions

`lane_status` must be one of these three values. It is declared in the footer addendum and governs `community_checked_at` advancement.

| Value | Meaning | `community_checked_at` advances? |
|---|---|---|
| `ok` | All queries executed without error AND every attempted fetch succeeded. Zero-result queries are not errors — a run where every query returns zero results is still `ok` (the lane ran; there was nothing to find; use `scan_note`). Also `ok` when searches returned results but nothing survived pre-fetch triage (all stale/listicles) — the lane ran and found nothing worth fetching. Watermark advances in all these cases. | Yes — advances to today. |
| `degraded` | At least one fetch succeeded (or pre-fetch triage ran) but ≥1 query or fetch FAILED WITH AN ERROR. Findings are trustworthy but coverage is partial. | Yes — advances to today. Failed searches/fetches are disclosed in the footer so the user knows which areas had partial coverage. |
| `unavailable` | Every query failed with an error, OR queries succeeded but every attempted fetch failed. Only the degenerate finding is emitted. | No — the orchestrator MUST NOT advance `community_checked_at`. The missed check will be re-run next run because the watermark is unchanged. |

These states are mutually exclusive: `ok` requires zero errors; `degraded` requires at least one success AND at least one error; `unavailable` requires total failure.

The orchestrator advances `community_checked_at` only on `ok` or `degraded`, per `bx/skills/evolve/references/state-schema.md` Rule 4.

---

## Finding schema (use exactly these field names)

```json
{
  "finding_id": null,
  "class": "breakage | best_practice | opportunity",
  "tier": "community",
  "severity": "low | medium",
  "certainty": "0.3–0.6",
  "affected_files": ["<every file needing the edit, including sibling-file echoes>"],
  "upstream_delta": "<one-line: what the community source describes vs what bx currently does>",
  "proposed_edit": "<consider… phrasing — advisory, never prescriptive>",
  "citation": "<the community page URL — same as source_url for this lane>",
  "source_url": "<canonicalized community page URL — same value used in finding_id>",
  "affected_capability": "<capability string, e.g. bx:*/allowed-tools, or bx:pain/<kebab-slug>>",
  "source_excerpt": "<verbatim heading-bounded section from the fetched page — the exact text the orchestrator will normalize and hash>"
}
```

**`finding_id`:** set to `null` — computed by the orchestrator at consolidation from `source_url + "|" + affected_capability`. Do not attempt to compute it here. Exception: the `lane-unavailable-community` sentinel keeps its literal string ID (see degenerate finding below).

**`source_excerpt`:** the verbatim heading-bounded section extract (per the verbatim-extract requirement in Step 3) — never WebFetch's summary prose (see Step 3 for why). The orchestrator normalizes and hashes your `source_excerpt` per `bx/skills/evolve/references/state-schema.md` to produce `source_content_hash`. Return the raw extract; do not attempt to hash.

**`affected_capability` normalization:** normalize per `bx/skills/evolve/references/state-schema.md`. For pain-point-only findings, use the `bx:pain/<kebab-slug>` form — the slug convention is defined in `bx/skills/evolve/references/state-schema.md`'s finding_id computation section.

**`source_url`:** the canonicalized URL of the community page. Apply canonicalization per `bx/skills/evolve/references/state-schema.md` before hashing and storing. For this lane, `citation` and `source_url` always have the same value.

**`tier`:** always `community`. Never `official`. If you find an official Anthropic source, do not emit it here — record it in `scan_note`.

**`severity`:** never `high`. Maximum is `medium`. See Step 7 guidance.

**`proposed_edit`:** always phrased as "consider…" — never as a prescriptive "change X to Y". Community findings are advisory; the user decides whether to act.

---

## lane_unavailable degenerate finding

When no search returned results or every fetch failed, emit ONLY this finding (no others):

```json
{
  "finding_id": "lane-unavailable-community",
  "class": null,
  "tier": "community",
  "severity": "low",
  "certainty": 1.0,
  "affected_files": [],
  "upstream_delta": "<verbatim errors from each failed WebSearch and WebFetch call>",
  "proposed_edit": "Re-run /bx:evolve when network is available, or pass --no-community to skip this lane; community_checked_at was NOT advanced.",
  "citation": null,
  "source_url": null,
  "affected_capability": null,
  "source_excerpt": null
}
```

This sentinel keeps its literal `finding_id` string — no hashing involved. It has no `source_excerpt` (null) because there is no upstream section to extract.

Note: `severity: low` — a missing advisory lane is not urgent. This differs from the `lane-unavailable-changelog` and `lane-unavailable-docs` findings, which use `severity: high` because those lanes carry Tier-1 findings. Set `lane_status: unavailable` in the footer addendum.

---

## Hard rules

- **Advisory-only, always.** `tier: community` findings are NEVER `--fix`-eligible. `proposed_edit` must use "consider…" phrasing. The orchestrator must not offer automatic application.
- **Severity hard cap: medium.** Never assign `high` severity to a community finding. The reason is stated in the TIER RULE section: community claims are uncorroborated. Exception: the `lane-unavailable-community` sentinel is exempt (severity `low` by design — a missing advisory lane is not urgent).
- **Certainty hard band: 0.3–0.6.** Never above 0.6. Never below 0.3 in an emitted finding (below 0.3 means the evidence is too weak to surface at all — discard instead). Exception: the `lane-unavailable-community` sentinel is exempt (certainty 1.0, empty affected_files) — it reports lane health, not a community claim.
- **Official sources encountered during fetching are NOT emitted here.** If you reach an Anthropic docs page, a GitHub release note, any first-party source, or a post by an Anthropic maintainer in an `anthropics/*` repo while fetching community content, record the URL and the relevant claim in `scan_note` (format: `official_source_found: <url> — <one-line description>`). The docs or changelog lane owns that finding. See the GitHub boundary rule in Step 2.
- **Unconfirmable claims are discarded, not capped.** Unlike the docs lane (which caps at certainty 0.5), this lane discards without emitting. The noise floor is higher.
- **Never report zero findings silently.** If all searches and fetches ran without error but no candidates survived the filters, append a note: `scan_note: <N> pages evaluated; no capability or pain-point matches survived verification`. This is distinct from `unavailable`.
- **Include sibling-file echoes in `affected_files`.** Always populate via Step 6 Grep. Never infer from the capability string alone.
- **Per-failure disclosure is explicit.** Every failed WebSearch query and every failed WebFetch URL is named in the footer.
- **Do not restate algorithms from `bx/skills/evolve/references/state-schema.md`.** Point to that file for `finding_id` computation, `source_url` canonicalization, and `source_content_hash` normalization. Duplication causes drift — the S45 lesson.

---

## Final output addendum

After all findings (or after the single `lane-unavailable-community` finding), append:

```
searches_run: <n>/3
pages_fetched: <n>/5
pages_failed: [<url>: <error>, ...]         # empty list [] if all fetches succeeded
searches_failed: [<query>: <error>, ...]    # empty list [] if no query failed with an error
lane_status: ok | degraded | unavailable
scan_note: <optional — used for: zero findings despite clean run; stale_source flags; cap_reached note; official_source_found notices; other non-error observations>
discarded_findings: <count of findings dropped by the 10-finding cap PLUS zero-hit affected_files discards from Step 6 PLUS unconfirmable discards from Step 4, or 0>
```

**Zero-findings-but-searches-ran case:** set `searches_run` to the count of queries issued, `pages_fetched` to the count of pages successfully fetched, `pages_failed` and `searches_failed` to their real contents (empty lists only if truly no failures occurred), `lane_status` to what actually happened (`ok` only if nothing failed with an error; `degraded` if any query or fetch failed with an error), and use `scan_note` to explain that no gaps were found. Never return an empty finding list without a `scan_note` — that is indistinguishable from a partial run.

These power the report footer and the orchestrator's `community_checked_at` advance decision.
