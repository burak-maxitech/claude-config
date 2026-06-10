# Upstream Watch State — Schema + Update Mechanics

Loaded by the orchestrator at the start of every `/bx:evolve` run. Defines the canonical shape of `docs/upstream/state.json`, the lifecycle rules governing each field, and the exact procedure for reading and writing the file. **This file owns the read/write procedure — `SKILL.md` must reference this file rather than restate the mechanics.** All examples below are normative — the orchestrator compares live state against these shapes when validating a read.

All dates and timestamps in this schema are UTC ISO format: `YYYY-MM-DD`.

---

## Watermark object

The watermark records the furthest upstream point checked on the most recent completed run. A null value means "never checked" — the first run performs a full audit regardless of how far back the changelog goes.

```json
{
  "watermark": {
    "last_changelog_version": "2.1.170",
    "docs_checked_at": "2026-06-09",
    "community_checked_at": "2026-06-09"
  }
}
```

### Field definitions

| Field | Type | Meaning |
|---|---|---|
| `last_changelog_version` | string or null | The **unprefixed** claude-code version string (e.g. `"2.1.170"`) of the highest changelog entry processed in the last run. Release tags carry a leading `v` (e.g. `v2.1.170`) which is stripped before storing or comparing — the normalization rule is defined in `bx/skills/evolve/references/scan-changelog.md`. On the next run, only entries tagged AFTER this version are fetched. "After" is defined as release order returned by `gh release list` (newest-first tag order); CHANGELOG.md document order is the fallback when `gh` is unavailable. Null on first run → fetch the full changelog. |
| `docs_checked_at` | ISO date string or null | The date (YYYY-MM-DD) the Anthropic docs pages were last fetched and scanned. Advances ONLY if the docs lane ran this run (lane_status ok or degraded). A lane that was skipped or unavailable keeps its previous timestamp so the missed range is re-checked next run. Null on first run. |
| `community_checked_at` | ISO date string or null | The date (YYYY-MM-DD) the community lane (bounded WebSearch over community content) last ran. Advances ONLY if the community lane ran this run (lane_status ok or degraded). Skipped via `--no-community` or unavailable → keeps its previous timestamp. Null on first run. |

### Why the watermark matters

Without it, every run would re-evaluate the entire changelog from the beginning. Most of the time the orchestrator would reach the same "already applied" or "already rejected" verdict for each entry — wasting tokens and obscuring the genuinely new findings the user needs to act on. The watermark makes runs incremental: only changes since the last run reach the report.

The watermark advances at the END of every run (Step 5), not the beginning. Advancing at the start would mean a partial failure (network error mid-run, skill crash) marks entries as checked when they were never fully evaluated.

Each `*_checked_at` field advances ONLY if that source class was actually checked this run (lane_status ok or degraded). A lane that was skipped (`--no-community`) or unavailable keeps its previous timestamp so the missed range is re-checked next run.

---

## Decision entry schema

Each entry in the `decisions` array represents one actionable finding that has been evaluated. An entry is created when a finding is first surfaced (as `open`) and updated in-place when a verdict is reached. The `decisions` array never has duplicate `finding_id` values — every verdict (applied/rejected/deferred) overwrites the existing entry in place; a second entry for the same `finding_id` is never appended.

```json
{
  "decisions": [
    {
      "finding_id": "a3f2c1b9e4d07f8a6c2e1b3d5f7a9c0e12345678",
      "decision": "applied",
      "date": "2026-06-09",
      "source_url": "https://code.claude.com/docs/en/skills",
      "affected_capability": "bx:seo/allowed-tools",
      "source_content_hash": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1d",
      "class": "breakage",
      "title": "`allowed-tools` entry missing for Bash helper",
      "note": "Added allowed-tools entry for new Bash helper per claude-code 1.7.0 release notes."
    },
    {
      "finding_id": "b9c4e2f1a0d5b7c3e6f8a2d4b6c8e0f2a4b6c8e0",
      "decision": "rejected",
      "date": "2026-06-08",
      "source_url": "https://code.claude.com/docs/en/hooks",
      "affected_capability": "bx:save/session-start",
      "source_content_hash": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
      "class": "best_practice",
      "title": "Session-start hook pattern differs from bx approach",
      "note": "The suggested hook runs on every session-start; bx already handles this via session-start-context scripts."
    },
    {
      "finding_id": "c1d5e9f3b7a2c6d0e4f8a3b7c1d5e9f3b7a2c6d0",
      "decision": "open",
      "date": "2026-06-09",
      "source_url": "https://code.claude.com/docs/en/settings",
      "affected_capability": "bx:clean/allowed-tools",
      "source_content_hash": "9e107d9d372bb6826bd81d3542a419d6a3b1c5d2",
      "class": "best_practice",
      "title": "allowed-tools pattern syntax update for /bx:clean",
      "note": null
    },
    {
      "finding_id": "d2e6f0a4b8c2e6f0a4b8c2e6f0a4b8c2e6f0a4b8",
      "decision": "deferred",
      "date": "2026-06-09",
      "source_url": "https://code.claude.com/docs/en/hooks",
      "affected_capability": "bx:health/hooks-rework",
      "source_content_hash": "1f8ac10f23c5b5bc1167bda84b833e5c057a77d7",
      "class": "opportunity",
      "title": "Hooks rework could simplify /bx:health session orientation",
      "note": "Hooks rework is high-effort; revisit after /bx:webdesign dogfood is complete."
    }
  ]
}
```

### Field definitions

| Field | Type | Required | Meaning |
|---|---|---|---|
| `finding_id` | string (40-char hex SHA-1) | yes | Stable identifier for this finding. Computed as `sha1(source_url + "\|" + affected_capability)` where `source_url` is the canonicalized URL of the upstream source page (see canonicalization rule below) and `affected_capability` is a short normalized string identifying the bx feature area (e.g. `"bx:seo/allowed-tools"`, `"bx:save/agent-model"`). The same finding_id is produced on every run from the same source + capability pair — this is what prevents duplicates and lets the orchestrator match a live finding to its stored verdict. |
| `decision` | enum string | yes | Current verdict: `open` (surfaced, not yet acted on), `applied` (fix merged into the bx plugin), `rejected` (evaluated and deliberately skipped), or `deferred` (will apply later; re-raised on every run until changed). |
| `date` | ISO date string (YYYY-MM-DD) | yes | Date the entry was created or last transitioned to a new verdict. Set to today on creation; updated to today when any verdict (applied/rejected) overwrites `open`. Exception: deferred re-surfacing (Rule 5) keeps the original deferral date — `date` is NOT updated on re-surface, only on a subsequent verdict change. |
| `source_url` | string | yes | The canonicalized URL of the upstream source page that drove this finding (see canonicalization rule below). Makes `finding_id` recomputable from stored state and makes the log self-describing. |
| `affected_capability` | string | yes | The capability string used in the `finding_id` computation (e.g. `"bx:seo/allowed-tools"`). Makes `finding_id` recomputable from stored state without re-running the hash logic over free-text fields. |
| `source_content_hash` | string (40-char hex SHA-1) | yes | Normalized SHA-1 of the specific upstream section text that drove this finding (the cited paragraph or bullet, not the whole page). Used by the trigger-based re-raise rules for `rejected` and `deferred` entries — see Rules 3 and 5. |
| `class` | enum string or null | yes | The finding's class at its last surfacing: `breakage`, `best_practice`, or `opportunity`. Null for sentinel/degenerate entries. **Why stored:** carried-forward findings must be renderable in the report's Section 4 from state alone — without a stored class the orchestrator cannot label entries no lane re-emitted this run. |
| `title` | string or null | yes | The finding's one-line title at its last surfacing (e.g. `` "`allowed-tools` glob syntax changed" ``). Null for sentinel/degenerate entries. **Why stored:** same reason as `class` — Section 4 rendering requires it without a live lane re-emit. |
| `note` | string or null | yes (nullable) | Human-readable explanation of the verdict — a one-liner covering what was done or why it was skipped. The key must always be present; the value may be null (use null, not absent key). |

### finding_id computation (normative)

Computed by the ORCHESTRATOR at consolidation time, not by lane agents. Lane agents return `source_excerpt` (the verbatim heading-bounded extract), `source_url`, and `affected_capability`, and set `finding_id: null`. The orchestrator runs the snippet below via `Bash(python:*)` to produce the final `finding_id`.

```python
import hashlib
finding_id = hashlib.sha1(
    (source_url + "|" + affected_capability).encode("utf-8")
).hexdigest()
```

The `affected_capability` string must be normalized before hashing: lowercase, forward-slash separators, no trailing slash, no spaces. Example: `"bx:seo/allowed-tools"` not `"bx:seo / Allowed Tools"`.

**Pain-point findings — `bx:pain/<kebab-slug>` convention:** when a finding addresses a known pain point from the `pain_point_list` rather than a specific capability in the `capability_inventory`, set `affected_capability` to `bx:pain/<kebab-slug>`. The slug form is `bx:pain/` followed by the pain-point text converted to lowercase kebab-case (spaces → hyphens, punctuation stripped). Example: pain point `"permission prompts on every run"` → `bx:pain/permission-prompts-on-every-run`. The slug MUST be derived deterministically from the canonical pain-point text — never from the upstream release content — so that `finding_id` is stable across runs and re-raise checks work correctly. Apply the same normalization (lowercase, no trailing slash, no spaces) before hashing.

### source_url canonicalization (normative)

Applied to `source_url` before hashing into `finding_id` and before storing the field:

- Lowercase the scheme and host (e.g. `HTTPS://Code.Claude.com` → `https://code.claude.com`).
- Strip any `#fragment` component.
- Strip a single trailing slash from the path (e.g. `/docs/en/hooks/` → `/docs/en/hooks`).
- Drop any `utm_*` query parameters; keep all other query parameters verbatim.

### source_content_hash normalization (normative)

Computed by the ORCHESTRATOR at consolidation time by applying the function below to the lane agent's `source_excerpt` field. Lane agents return the raw verbatim extract as `source_excerpt` and do not compute hashes (they have no hashing tool). The orchestrator runs this snippet via `Bash(python:*)`.

Without normalization, CRLF/wrapping/rendering differences between fetches would spuriously re-raise every rejected finding on re-check.

```python
import hashlib, unicodedata, re

def source_content_hash(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    stripped = normalized.strip()
    collapsed = re.sub(r"[ \t\n\r]+", " ", stripped)
    return hashlib.sha1(collapsed.encode("utf-8")).hexdigest()
```

---

## Lifecycle rules

These rules are invariants — the orchestrator must not deviate from them. Each rule is stated with its reason because the reason is the guard against well-intentioned improvisation that breaks the contract.

### Rule 1: New actionable findings are written as `open` at report time

When the orchestrator identifies a finding that has no existing `finding_id` entry in `decisions`, it writes a new entry with `decision: "open"` before emitting the report. **Why:** findings survive watermark advances. Because every undecided finding persists as an `open` entry and re-surfaces in every report until the user reaches a verdict, the watermark can safely advance at the end of every run — there is no risk of a finding disappearing between runs just because the watermark moved past its source version. A secondary bonus: if the run crashes after reporting but before writing state, re-running re-surfaces the finding from state rather than re-announcing it as new.

### Rule 2: Every verdict overwrites the entry in place

Every verdict — `applied`, `rejected`, or `deferred` — overwrites the existing entry in place. The orchestrator updates `decision`, `date` (to today, except deferred re-surfacing per Rule 5), `source_content_hash` if the content was re-fetched, and `note`. It does NOT append a new entry. **Why:** one `finding_id` → one entry is a hard invariant. Appending would create duplicates that the dedup logic would have to resolve at read time, making the schema order-dependent and fragile. Overwriting in-place keeps the array flat and lookup O(n) with a simple find-by-id.

When `--fix` mode is active and the user approves a fix: `decision` → `applied`, `date` → today, `note` → description of what was changed.

When the user rejects a finding: `decision` → `rejected`, `date` → today, `note` → reason.

When the user defers a finding: `decision` → `deferred`, `date` → today (the original deferral date, preserved by Rule 5 on subsequent re-surfaces), `note` → reason.

### Rule 3: `rejected` findings use trigger-based re-raise — never proactive re-fetch

A `rejected` finding is re-raised ONLY when a current run's lane emits a finding whose `finding_id` matches the stored `rejected` entry. The orchestrator does NOT proactively fetch stored `source_url` values to check whether rejected entries have changed. Sources behind the watermark that no lane re-surfaces are never re-checked — if the source never reappears in a run's output, there is nothing to re-litigate.

**Trigger mechanics:** when a live finding matches a `rejected` entry's `finding_id`, compare the live finding's `source_content_hash` (computed from the freshly fetched content using the normalization function above) to the stored `source_content_hash`:

- **Hash unchanged:** the source section is the same as when rejected. Suppress the finding from the report; count it in the report footer as "N rejected (unchanged, suppressed)".
- **Hash changed:** the source section has been rewritten — the old rejection no longer applies. Surface the finding badged `[re-raised — source changed since rejection]`. Update the stored entry: `decision` → `open`, `source_content_hash` → new hash, `date` → today.

**Why trigger-based:** proactive re-fetching every rejected URL on every run would consume tokens and quota proportional to the decision log size, not the delta since the last run. The whole point of the decision log is to make runs incremental. A rejection is a claim about a specific piece of guidance; if the guidance never reappears in the current scan, the rejection still stands.

### Rule 4: Each watermark timestamp advances only if its lane ran this run

After all findings have been written to state (Rule 1) and any `--fix` verdicts applied (Rule 2), the orchestrator updates the watermark fields: `last_changelog_version` to the highest tag processed. `docs_checked_at` advances to today ONLY if the docs lane ran this run (lane_status ok or degraded). `community_checked_at` advances to today ONLY if the community lane ran this run. A lane that was skipped (`--no-community`) or unavailable keeps its previous timestamp, ensuring the missed range is re-checked on the next run.

**Why:** advancing at the end, not the beginning, means a failed or partial run leaves the watermark at the last fully-completed run's value. Per-lane tracking means a `--no-community` run does not falsely claim community sources were checked.

### Rule 5: `deferred` findings re-surface on every run until explicitly decided

A `deferred` entry re-surfaces in every report badged `[deferred <original date>]`. The stored `date` keeps the original deferral date and is NOT updated on re-surfacing. **Why:** deferred entries are the user's "I'll handle this later" signal; hiding them would lose track of pending work.

**Trigger mechanics for content change:** if a current run's lane emits a live finding whose `finding_id` matches a `deferred` entry AND the live finding's `source_content_hash` differs from the stored one, update the stored `source_content_hash` to the new hash and note "source changed since deferral" in the report alongside the `[deferred <original date>]` badge. The `date` field still keeps the original deferral date.

Any later verdict (applied/rejected) overwrites the `deferred` entry per Rule 2 — the entry transitions fully to the new verdict.

---

## Update mechanics

The orchestrator rewrites the entire file on every run that changes state. No appending, no shell-based in-place edits, no `jq` streaming writes that assume a particular shell environment. This file owns this procedure — `SKILL.md` must reference here rather than restate it.

**Canonical procedure:**

1. **Read** `docs/upstream/state.json` via the Read tool at the start of the run (Step 1). Deserialize into an in-context object.
2. **Modify** the in-context object as findings are evaluated and verdicts recorded throughout the run. Do not write intermediate states.
3. **Validate** the modified object before writing: confirm the `decisions` array has no duplicate `finding_id` values; confirm all required fields are present on every entry; confirm `decision` values are in the allowed enum set. **On ANY validation failure, do NOT write the file.** Report the validation failure in the run output and leave `state.json` untouched so the previous valid state is preserved.
4. **Write** the validated object back to `docs/upstream/state.json` via the Write tool at the end of the run (Step 5), serialized as pretty-printed JSON (2-space indent, keys in schema order). The Write tool is an atomic overwrite — no temp file needed.

**Why no shell-based writes:** shell state does not persist across Bash tool calls in Claude Code. A `jq` command that reads from a file in one Bash call and writes in another has no guaranteed consistency if the run interleaves tool calls. The Read-modify-in-context-Write pattern keeps the entire state transition inside a single logical unit the orchestrator controls, with no shell state assumptions.

**Why no appending:** appending a new JSON object to a `.json` file produces invalid JSON. Appending NDJSON-style would require a reader that handles both empty-array `[]` and NDJSON format. The canonical format is a single valid JSON document; rewriting the whole file keeps the format simple and the reader trivial.

**Schema order for serialization** (use this key order for readability):

```
state.json root:
  watermark:
    last_changelog_version
    docs_checked_at
    community_checked_at
  decisions: [
    finding_id
    decision
    date
    source_url
    affected_capability
    source_content_hash
    class
    title
    note
  ]
```
