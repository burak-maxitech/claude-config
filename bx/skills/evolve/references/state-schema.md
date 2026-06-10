# Upstream Watch State — Schema + Update Mechanics

Loaded by the orchestrator at the start of every `/bx:evolve` run. Defines the canonical shape of `docs/upstream/state.json`, the lifecycle rules governing each field, and the exact procedure for reading and writing the file. All examples below are normative — the orchestrator compares live state against these shapes when validating a read.

For the watermark advance and decision-write procedures, see `SKILL.md` Steps 1 and 5.

---

## Watermark object

The watermark records the furthest upstream point checked on the most recent completed run. A null value means "never checked" — the first run performs a full audit regardless of how far back the changelog goes.

```json
{
  "watermark": {
    "last_changelog_version": "1.7.0",
    "docs_checked_at": "2026-06-09",
    "community_checked_at": "2026-06-09"
  }
}
```

### Field definitions

| Field | Type | Meaning |
|---|---|---|
| `last_changelog_version` | string or null | The claude-code release tag string (e.g. `"1.7.0"`) of the highest changelog entry processed in the last run. On the next run, only entries tagged AFTER this version are fetched. Null on first run → fetch the full changelog. |
| `docs_checked_at` | ISO date string or null | The date (YYYY-MM-DD) the Anthropic docs pages were last fetched and scanned. Recorded as a timestamp of the last successful check; used for the report's "delta since <date>" framing. Null on first run. |
| `community_checked_at` | ISO date string or null | The date (YYYY-MM-DD) the community sources (Claude Code GitHub issues, Anthropic community forum) were last checked. Recorded as a timestamp of the last successful check; used for the report's "delta since <date>" framing. Null on first run. |

### Why the watermark matters

Without it, every run would re-evaluate the entire changelog from the beginning. Most of the time the orchestrator would reach the same "already applied" or "already rejected" verdict for each entry — wasting tokens and obscuring the genuinely new findings the user needs to act on. The watermark makes runs incremental: only changes since the last run reach the report.

The watermark advances at the END of every run (Step 5), not the beginning. Advancing at the start would mean a partial failure (network error mid-run, skill crash) marks entries as checked when they were never fully evaluated.

---

## Decision entry schema

Each entry in the `decisions` array represents one actionable finding that has been evaluated. An entry is created when a finding is first surfaced (as `open`) and updated in-place when a verdict is reached. The `decisions` array never has duplicate `finding_id` values — a later verdict overwrites the existing entry.

```json
{
  "decisions": [
    {
      "finding_id": "a3f2c1b9e4d07f8a6c2e1b3d5f7a9c0e12345678",
      "decision": "applied",
      "date": "2026-06-09",
      "source_content_hash": "7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1d",
      "note": "Added allowed-tools entry for new Bash helper per claude-code 1.7.0 release notes."
    },
    {
      "finding_id": "b9c4e2f1a0d5b7c3e6f8a2d4b6c8e0f2a4b6c8e0",
      "decision": "rejected",
      "date": "2026-06-08",
      "source_content_hash": "da39a3ee5e6b4b0d3255bfef95601890afd80709",
      "note": "The suggested hook runs on every session-start; bx already handles this via session-start-context scripts."
    },
    {
      "finding_id": "c1d5e9f3b7a2c6d0e4f8a3b7c1d5e9f3b7a2c6d0",
      "decision": "open",
      "date": "2026-06-09",
      "source_content_hash": "9e107d9d372bb6826bd81d3542a419d6a3b1c5d2",
      "note": null
    },
    {
      "finding_id": "d2e6f0a4b8c2e6f0a4b8c2e6f0a4b8c2e6f0a4b8",
      "decision": "deferred",
      "date": "2026-06-09",
      "source_content_hash": "1f8ac10f23c5b5bc1167bda84b833e5c057a77d7",
      "note": "Hooks rework is high-effort; revisit after /bx:webdesign dogfood is complete."
    }
  ]
}
```

### Field definitions

| Field | Type | Required | Meaning |
|---|---|---|---|
| `finding_id` | string (40-char hex SHA-1) | yes | Stable identifier for this finding. Computed as `sha1(source_url + "\|" + affected_capability)` where `source_url` is the canonical URL of the upstream source page and `affected_capability` is a short normalized string identifying the bx feature area (e.g. `"bx:seo/allowed-tools"`, `"bx:save/agent-model"`). The same finding_id is produced on every run from the same source + capability pair — this is what prevents duplicates and lets the orchestrator match a live finding to its stored verdict. |
| `decision` | enum string | yes | Current verdict: `open` (surfaced, not yet acted on), `applied` (fix merged into the bx plugin), `rejected` (evaluated and deliberately skipped), or `deferred` (will apply later; re-raised on every run until changed). |
| `date` | ISO date string (YYYY-MM-DD) | yes | Date the entry was last written or updated. Set to today on creation; updated to today when a verdict overwrites `open`. |
| `source_content_hash` | string (40-char hex SHA-1) | yes | SHA-1 of the specific upstream section text that drove this finding (the cited paragraph or bullet, not the whole page). Used by the rejected-finding re-raise rule: if the source section changes, the old rejection no longer applies and the finding re-opens. |
| `note` | string or null | no | Optional human-readable explanation of the verdict — a one-liner covering what was done or why it was skipped. Set to null when absent. |

### finding_id computation (normative)

```python
import hashlib
finding_id = hashlib.sha1(
    (source_url + "|" + affected_capability).encode("utf-8")
).hexdigest()
```

The `affected_capability` string must be normalized before hashing: lowercase, forward-slash separators, no trailing slash, no spaces. Example: `"bx:seo/allowed-tools"` not `"bx:seo / Allowed Tools"`.

---

## Lifecycle rules

These rules are invariants — the orchestrator must not deviate from them. Each rule is stated with its reason because the reason is the guard against well-intentioned improvisation that breaks the contract.

### Rule 1: New actionable findings are written as `open` at report time

When the orchestrator identifies a finding that has no existing `finding_id` entry in `decisions`, it writes a new entry with `decision: "open"` before emitting the report. **Why:** findings survive watermark advances. Because every undecided finding persists as an `open` entry and re-surfaces in every report until the user reaches a verdict, the watermark can safely advance at the end of every run — there is no risk of a finding disappearing between runs just because the watermark moved past its source version. A secondary bonus: if the run crashes after reporting but before writing state, re-running re-surfaces the finding from state rather than re-announcing it as new.

### Rule 2: `--fix` verdicts overwrite the `open` entry in-place

When the user approves a fix and `--fix` mode is active, the orchestrator updates the existing entry: sets `decision` to `applied`, `date` to today, and `note` to a description of what was changed. It does NOT append a new entry. **Why:** one `finding_id` → one entry is a hard invariant. Appending would create duplicates that the dedup logic would have to resolve at read time, making the schema order-dependent and fragile. Overwriting in-place keeps the array flat and lookup O(n) with a simple find-by-id.

### Rule 3: A `rejected` finding is re-raised only when its `source_content_hash` no longer matches the live source

On each run, the orchestrator fetches the source section for every `rejected` entry and recomputes its SHA-1. If the hash matches the stored `source_content_hash`, the rejection stands and the finding is suppressed from the report. If the hash differs, the source has changed — the old rejection no longer applies — so the orchestrator resets `decision` to `open` and updates `source_content_hash` to the new hash. **Why:** a "rejected" verdict is a claim that a specific piece of upstream guidance was evaluated and found inapplicable to bx. If Anthropic rewrites that guidance, the old verdict is stale. Re-raising on hash change ensures the user re-evaluates changed guidance without being spammed by unchanged rejected findings.

### Rule 4: The watermark advances at the end of EVERY run

After all findings have been written to state (Rule 1) and any `--fix` verdicts applied (Rule 2), the orchestrator updates the watermark fields to reflect the current run's reach: `last_changelog_version` to the highest tag processed, `docs_checked_at` and `community_checked_at` to today's date. **Why:** advancing at the end, not the beginning, means a failed or partial run leaves the watermark at the last fully-completed run's value. The next run will re-check the same range rather than skipping it. This is the safe failure mode — slightly redundant work on retry, never missing entries.

---

## Update mechanics

The orchestrator rewrites the entire file on every run that changes state. No appending, no shell-based in-place edits, no `jq` streaming writes that assume a particular shell environment.

**Canonical procedure:**

1. **Read** `docs/upstream/state.json` via the Read tool at the start of the run (Step 1). Deserialize into an in-context object.
2. **Modify** the in-context object as findings are evaluated and verdicts recorded throughout the run. Do not write intermediate states.
3. **Validate** the modified object before writing: confirm the `decisions` array has no duplicate `finding_id` values; confirm all required fields are present; confirm `decision` values are in the allowed enum set.
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
    source_content_hash
    note
  ]
```
