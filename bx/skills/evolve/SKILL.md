---
name: evolve
description: Audits the bx toolkit against upstream Anthropic changes — new Claude Code releases, official-docs best practices, and a discovery search for official pages not yet pinned — since the last run's watermark. Reports breakage/best-practice/opportunity findings with citations; --fix applies them behind a per-finding diff gate. Use when Anthropic ships a new Claude Code version, when built-ins change or collide, periodically (monthly) to keep skills current, or when asking "are my skills up to date with the latest capabilities".
disable-model-invocation: true
effort: high
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(git:*), Bash(python:*), Bash(python3:*), Agent
argument-hint: "[--full] [--fix] [--no-community]"
---

# /bx:evolve — Upstream-Watch Audit for the bx Plugin

This skill watches upstream Anthropic sources — claude-code releases, official docs, and a discovery search for official pages not yet pinned — and audits the `bx` plugin against what has changed since the last run's watermark. It surfaces breakage (upstream invalidated something bx says or does), best-practice (guidance changed for something bx does), and opportunity (new capability maps to a recorded pain point) findings with mandatory citations, then applies approved changes behind a per-finding diff gate when `--fix` is passed.

**Run-in-repo precondition.** This skill only makes sense in the claude-config repo. Before doing any other work, confirm that both `bx/` and `docs/upstream/` exist in the working directory via Glob. If either is absent, say so clearly and exit — do not attempt to recreate them or continue.

---

## Step 0 — Load State + Build Capability Inventory

### 0.1 — Load state

Read `docs/upstream/state.json`. The canonical shape, all validation rules, and the null-seed form are defined in `bx/skills/evolve/references/state-schema.md` — defer to that file entirely; do NOT restate its mechanics here. If the file is missing (first-ever run), recreate the null seed from state-schema's normative shape via Write and treat this run as `--full`.

### 0.2 — Build capability inventory

The inventory is **pinned**: `bx/skills/evolve/capabilities.json`, generated deterministically by `bx/skills/evolve/scripts/build-capabilities.py` from `bx/**`, `README.md` and `workflow.md`. It is the vocabulary of `affected_capability` — a lane may only name a string from it (or `bx:pain/<id>`), which is what keeps `finding_id` stable across runs. Until bx 2.12.0 this step rebuilt the list by Grep every run and the lanes worded strings freehand, so the same finding re-entered under new ids and the Step 3.4 `source_url` match had to forgive it.

Read the file; its `capabilities` array is the `capability_inventory` for Step 2 and its `inventory_hash` feeds Step 1.5. Then check it against the live tree:

```
python -I bx/skills/evolve/scripts/build-capabilities.py --check
```

Exit 0 means pinned equals live. Exit 1 prints `added_live_only` / `removed_pinned_only`: the file is stale — a skill, key, tool, built-in reference, idiom or hook event changed since it was written. **The run still uses the pinned file** (the lanes need one vocabulary, and a mid-run regeneration would move the baseline under the Step 3.4 match), reports the drift in the Step 0.4 line and the report footer, and under `--fix` offers the regeneration as a synthetic item (`fix-mode-evolve.md`, *Inventory drift*). Outside `--fix`, the user regenerates with `--write` and commits the file; a `bx/**` change that alters the inventory should regenerate it in the same commit.

The four categories the script derives, for the record (the script is the owner; do not re-derive by hand): **(a)** every frontmatter key in a SKILL.md or agent file → `bx:<owner>/<key>`, and every tool those keys name → `bx:<owner>/tool:<Tool>`; **(b)** backticked built-in slash commands → `bx:<owner>/builtin:<command>`; **(c)** a fixed table of harness idioms (agent dispatch, `!` injection, `bin/` helpers, no-env-persistence, allowed-tools enumeration, SessionStart, plugin-root and skill-dir variables, the model-invocation flag, rewind/checkpoints, AskUserQuestion, the task tracker) → `bx:<owner>/idiom:<name>`; **(d)** every event in `bx/hooks/hooks.json` → `bx:hooks/<Event>`. `<owner>` is the skill or agent name, `plugin` for `bx/scripts` and the manifest, `docs` for README.md and workflow.md.

**Historical archives out of scope:** `docs/key-decisions.md`, `docs/session-history.md`, and CLAUDE.md history sections are records of past state per repo convention. The script does not read them, and nothing in the inventory comes from them.

### 0.3 — Pain points (registry-backed)

Read CLAUDE.md `## Known Issues / Blockers` and `docs/STATUS.md` `## Next Steps` (doc schema v2 moved Next Steps there in S56; on a repo without `docs/STATUS.md`, read CLAUDE.md's `## Next Steps` instead). Read `docs/upstream/pain-points.json` if it exists (missing → start from an empty registry). Derive each item's lead and match it to the registry exactly as `bx/skills/evolve/references/state-schema.md`'s **Pain registry** section prescribes — that section owns the lead rule, the significant-word rule, the three-step match and the retire rule; do not improvise a slug. Keep the updated registry in context: it is written at Checkpoint 1 (Step 4), never here.

The `pain_point_list` for Step 2 is the list of active registry entries as `{id, text}`. A finding that addresses a pain point is surfaced even without a direct capability-inventory match, and its `affected_capability` is `bx:pain/<id>` with the id copied verbatim.

### 0.4 — Detection summary

End Step 0 with a one-line summary to the user, e.g.:

> Loaded state: changelog watermark 2.1.170 · docs 2026-06-09 · community 2026-06-09. Inventory: 435 pinned capabilities (no drift | drift: +3 −1, regenerate with `--write`); pain registry 6 active / 2 retired (1 new this run). 3 open findings in decision log.

---

## Step 1 — Mode Dispatch

Interpret `$ARGUMENTS`:

| Flag | Effect |
|---|---|
| *(none)* | Default delta run: research changes since the watermark, emit report, stop. |
| `--full` | Treat all watermark fields as null FOR THIS RUN only — the stored `state.json` is untouched until the end-of-run watermark advance (Step 6). Triggers a full re-audit as if running for the first time, and closes any recorded `changelog_gap` (the user asked for a fresh baseline). |
| `--fix` | Run the full report (Steps 2–4), then execute the per-finding diff gate (Step 5). |
| `--no-community` | Skip lane 3 (`upstream-community`, the official-source discovery feed). Lane 3's `community_checked_at` watermark field keeps its previous value per state-schema Rule 4 — the missed range re-checks on the next run. |

`--full --fix` is a valid combination. No other flags are recognized; if an unrecognized flag is present, say so and exit.

### 1.5 — Lane freshness check

A lane whose watermark already equals its head has nothing to scan, and dispatching it anyway costs the full read (S61: a `--fix` run minutes after a delta run re-fetched 15 docs pages, ~180k tokens, to re-emit stored entries). Before Step 2, decide per lane — skipped under `--full`, which always dispatches all three:

- **changelog** — run `git ls-remote --tags --refs https://github.com/anthropics/claude-code` and take the highest `v<semver>` tag, `v` stripped (numeric compare per component, never string order). The lane is **current** when that version equals `last_changelog_version` AND `changelog_gap` is null. A failed or empty `ls-remote` means dispatch normally — the lane has its own fallbacks and must not be skipped on a guess.
- **docs** — probe the allowlist's page hashes, from the repo root:

  ```
  python -I bx/skills/evolve/scripts/docs-page-hashes.py --state docs/upstream/state.json --allowlist bx/skills/evolve/references/scan-docs.md --inventory-file bx/skills/evolve/capabilities.json
  ```

  (add `--full` under `--full`). It reads every allowlisted page's markdown rendering into a hash — none of it into context — and prints `pages_to_scan`: changed pages, pages with no stored hash, pages whose probe failed, or every page when `inventory_changed` is true. The lane is **current** when `pages_to_scan` is empty. Keep the printed `pages`, `inventory_hash` and counts for Step 2's context block, Step 6 and the report. A probe that fails outright (non-zero exit, no JSON) means dispatch the lane with every allowlisted page — exactly as before 2.12.0.
- **community** — current when `community_checked_at` is today's date (`--no-community` still wins: that is `skipped`, not `current`). Since 2.12.0 this lane is a discovery feed (`scan-community.md`): it emits no findings, only `allowlist_candidates`.

A current lane is not dispatched. Record `lane_status: current` for it; Step 3 treats it as having returned no findings, Step 6 leaves its watermark field unchanged (it already equals the head), and the report renders it per `report-template.md`. Carried-forward entries are unaffected — `--fix` gates them from stored state, so a run with all three lanes current is a pure fix pass. State this in the Step 0.4 line when it applies, e.g. `Lanes current: docs, community (checked today); changelog head 2.1.306 = watermark.`

---

## Step 2 — Parallel Lane Dispatch

Launch all three lane agents in a single turn (three Agent calls in one message). Set `subagent_type` to the dedicated agent name for each — **never generic subagents** (the S43 rule: skill-specific agents carry the baked-in scanning instructions and the declared tool lists; a generic subagent runs on the orchestrator's model and skips both. Note that Claude Code does not enforce command specifiers such as `Bash(gh:*)` on agent `tools:` lists — verified 2026-10-20, an agent declared with `Bash(gh:*)` ran `echo` and `git` — so the lists document intent and the read-only discipline is enforced by the scan instructions, not by the harness):

- Agent call 1: `subagent_type: upstream-changelog`
- Agent call 2: `subagent_type: upstream-docs`
- Agent call 3: `subagent_type: upstream-community` (omit when `--no-community`)

Omit the Agent call for any lane Step 1.5 marked `current`.

For each Agent call, include the following shared context block verbatim, then instruct the agent as described below:

```
Watermark: last_changelog_version=<value|null> · docs_checked_at=<value|null> · community_checked_at=<value|null>
changelog_gap: <null, or {after, before} copied from state — the changelog lane paginates to `after` to close it>
capability_inventory: <the list from Step 0.2>
pain_point_list: <the active {id, text} entries from Step 0.3 — findings that address one set affected_capability to bx:pain/<id>, id verbatim>
pages_to_scan: <docs lane only — the URL list Step 1.5's probe printed, or every allowlisted URL when the probe failed or under --full>
Repo root: the working directory. Grep scope for affected_files: bx/, README.md, workflow.md.
Output: structured JSON-shaped findings per the schema in your scan instructions. finding_id: null and source_excerpt as specified — the orchestrator computes all hashes. Do NOT format a report.
```

Instruct each agent to **first Read** its own scan reference file (`upstream-changelog` → `bx/skills/evolve/references/scan-changelog.md`; `upstream-docs` → `bx/skills/evolve/references/scan-docs.md`; `upstream-community` → `bx/skills/evolve/references/scan-community.md`), **then Read `bx/skills/evolve/references/lane-contract.md` in full** (the named owner of what the lanes share — inputs, filter, `affected_files`, schema, sentinel, `lane_status`, hard rules, footer keys; the scan files cite it and do not restate it), and then Read the following named sections of `bx/skills/evolve/references/state-schema.md`: "source_url canonicalization (normative)", "affected_capability normalization" (within the finding_id computation section), and the "`bx:pain/<id>` convention" paragraph (lanes copy the id they were given; the **Pain registry** section itself is orchestrator-only and need not be read by lanes). These files live at repo-root-relative paths; the run-in-repo precondition guarantees CWD = repo root. The agent follows the scan file exactly — it is canonical. Do NOT inline the content of these files in the task prompt.

**`--no-community`:** omit the Agent call for `upstream-community` entirely. Record `lane_status: skipped` for that lane in the report footer.

**`--full`:** pass `last_changelog_version=null`, `docs_checked_at=null`, `community_checked_at=null` in the shared context block, overriding the stored values. The stored `state.json` is untouched at this point.

**Agent tool lists declare intent; they are not enforced below the tool level.** A `Bash(gh:*)` entry gives the agent all of Bash (verified 2026-10-20), so the scan instructions are the real boundary: do not ask agents to run anything beyond them. The orchestrator owns all state reads and writes; agents return raw findings only.

---

## Step 3 — Consolidate + Compute Hashes + Gate

After all lane agents return (wait for all three Agent calls to complete):

### 3.1 — Collect lane outputs

Record each lane's `lane_status` (ok / degraded / unavailable / skipped). These govern watermark advancement (Step 6) and the report footer (Step 4). Also collect every lane's `allowlist_candidates` into one de-duplicated list (by canonical URL), and add any official page the orchestrator itself fetched outside the pinned allowlist during this run — the S53 lesson was that most Tier-1 value came from exactly such pages, and a candidate that lives only in a scan note is never acted on. The list renders in the footer and feeds `--fix` (`fix-mode-evolve.md`, *Allowlist candidates*).

**Sentinels exit the pipeline here.** A `lane-unavailable-*` finding is a lane-health report, not a finding: record the lane's `lane_status: unavailable`, stash its `upstream_delta` (the verbatim errors) for the report's Section 1 lane row, and REMOVE it from the finding set. Nothing downstream of 3.1 — hashing, gating, decision log, fix mode — ever sees a sentinel; every downstream sentinel rule is entailed by this one.

### 3.2 — Same-source dedup, then compute finding_id and source_content_hash

**Dedup first, hash second.** Before hashing, collapse same-run findings that describe one upstream change under two improvised capability strings: two findings with the same `class`, whose canonical `source_url` is identical AND whose `affected_files` sets intersect, are one finding. Keep the one from the higher-authority lane (changelog > docs > community; within a lane, the higher `severity_weight × certainty`, with `severity_weight` high = 3, medium = 2, low = 1 as the scan files define it), take the union of `affected_files`, set its stored `citation` to the distinct citations joined by ` · ` (one URL when they are identical), keep the kept finding's `upstream_delta` (it becomes the entry's `title`; the other's delta is carried into the report's detail block only), and, when the absorbed finding's capability was a `bx:pain/<id>`, append `(also addresses bx:pain/<id>)` to the kept finding's `upstream_delta` so the pain coverage survives in the title and the log. Count the collapse in the footer ("N same-source collapses"). Findings that share a URL but differ in `class` or touch disjoint files stay separate — one release can legitimately rename a flag (breakage) and add a feature (opportunity), and merging them would hide the second claim. Community findings never merge into Tier-1 ones. **Apply 3.5's cross-lane corroboration rule here as well, before hashing** — 3.5 defines that rule; it is not a separate pass after 3.4, so no finding receives a 3.4 outcome and is then merged away.

For every surviving finding (all `finding_id: null` after Step 3.1's sentinel removal), compute both hashes via `Bash(python:*)`. Run the ENTIRE batch in ONE python invocation — shell state does not persist between Bash calls, so splitting across calls loses the results. Pass findings as a heredoc or inline JSON string; print computed pairs.

The normative hash snippets are defined in `bx/skills/evolve/references/state-schema.md` (finding_id computation section and source_content_hash normalization section). Use them exactly. Do not reimplement.

### 3.3 — Relevance spot-check

The relevance gate is applied lane-side. Spot-check **after 3.4's lookup** (3.4 runs first; this step keeps its number for the report's sake): drop any finding that 3.4 matched to no stored entry — neither by exact `finding_id` nor by `source_url` — and whose `affected_capability` intersects neither the capability inventory nor the pain-point list. "Intersects" means exact string equality with an inventory entry after normalization, or, for `bx:pain/<id>`, that `<id>` is in the pain-point list. A finding that 3.4 matched to a stored entry is relevant by that match: its reworded capability string is exactly what the `source_url` rule exists to forgive. This catches improvised lane output that slipped through.

### 3.4 — Decision-log filter

For each consolidated finding, look up its computed `finding_id` in the stored `decisions` array. **If there is no exact match, look for a stored entry with the same canonical `source_url` whose `affected_files` intersects the live finding's** — an entry whose `affected_files` is empty or absent (a legacy entry, or any entry stored without files) matches on `source_url` alone when the live finding's class equals the stored class. A match found this way is the same finding under a reworded capability string: adopt the stored entry's `finding_id`, `affected_capability` and `decision` for everything below, keep the stored entry (never append a second one), and count it in the footer as "N matched to a stored entry by source_url".

**Pain-id match (third lookup).** If neither matched and the live finding's `affected_capability` is `bx:pain/<id>`, look for a stored entry with that same `bx:pain/<id>` capability, any `source_url`. A pain id names one concern, so a later release that addresses it again is the same finding under a new citation, not a new finding (S61: `dadac845` v2.1.183 and `6712a71e` v2.1.304 were one edit, joined by hand). On a match: keep the stored entry's `finding_id`, `source_url` and `source_content_hash` (they key the entry; the hash comparison below is skipped — a different release is not "the source changed"), append the live `source_url` to the stored `citation` with ` · ` if not already present, and count it in the footer as "N matched to a stored entry by pain id". Then: stored `applied` or `rejected` → suppress, as the unchanged-hash branches below do; stored `open` or `deferred` → adopt the entry and surface it per its branch, refreshing the four edit fields from the live finding when the stored ones are null (Rule 6) — a non-null stored edit is kept, with the live `proposed_edit` carried into the report's detail block only. A live finding under a capability string and a stored entry under a pain id are not joined by this rule even when their files coincide; that remains orchestrator judgment, noted in the footer when exercised.

Then apply the branch for the stored decision:

- **`applied` + source_content_hash UNCHANGED (or the stored hash is the sentinel — see state-schema's sentinel rule):** suppress from the report; count in footer as "N applied (unchanged, suppressed)". An applied fix is done; the lane re-emitted it only because docs pages are re-read every run. Still refresh the stored entry from the live finding where it is incomplete: a sentinel hash becomes the live hash, a null `source_excerpt` becomes the live excerpt, and a legacy 9-key entry gains the four 2.11.0 fields (state-schema Rule 6). `decision`, `date` and `note` do not change.
- **`applied` + source_content_hash CHANGED:** the upstream guidance moved after bx adopted it. Surface with `[re-raised — source changed since application]` badge. Update the stored entry: `decision → open`, `source_content_hash → new hash`, `date → today`, `note → "was applied: " + previous note`, `title` → the live finding's one-line `upstream_delta`, and refresh the four edit fields from the live finding (per state-schema Rule 6). `class` is not changed.
- **`rejected` + source_content_hash UNCHANGED:** suppress from the report; count in footer as "N rejected (unchanged, suppressed)".
- **`rejected` + source_content_hash CHANGED:** surface with `[re-raised — source changed since rejection]` badge. Update the stored entry: `decision → open`, `source_content_hash → new hash`, `date → today` (per state-schema Rule 3).
- **`deferred`:** if re-emitted by a lane this run → surface in Section 2 (ranked, live) with `[deferred <original date>]` badge; if not re-emitted this run → carry forward in Section 4 (per state-schema Rule 5). If the live `source_content_hash` differs from stored, update stored hash and note "source changed since deferral" alongside the badge. Do NOT update the `date` field.
- **`open` or no existing entry:** surface normally.

### 3.5 — Cross-lane dedup

Cross-lane corroboration matches on `affected_capability`: when the changelog and docs lanes emit findings for the same capability describing the same upstream change, keep the higher-authority lane's finding (changelog > docs) and append the other lane's citation to the detail block. `finding_id` dedup applies only within a lane (already handled lane-side) — `finding_id` can never collide across lanes because the URL spaces are disjoint. The community lane emits no findings since 2.12.0 (its output is `allowlist_candidates`, collected at 3.1); should a `tier: community` finding ever arrive, it is advisory regardless of class and is never merged into a Tier-1 finding.

---

## Step 4 — Report

Read `bx/skills/evolve/references/report-template.md` and render exactly as specified there. Do not improvise the report structure; report-template.md owns every section, the headline format, the empty-state rows, and the footer shape.

**New actionable findings → decision log.** Before rendering the report, write new and re-raised findings to `docs/upstream/state.json`. A new entry's `title` is the lane finding's `upstream_delta` reduced to one line of at most 120 characters (lanes do not emit a separate title); the four edit fields come from the finding verbatim. "Open entries written this run" in the footer counts new `open` entries plus every entry that transitioned to `open` this run (re-raised rejected or applied). **Checkpoint 1** — write state per `bx/skills/evolve/references/state-schema.md`'s Update Mechanics (it owns the contents and procedure), and write the updated pain registry to `docs/upstream/pain-points.json` in the same turn (its shape and key order are in the schema's **Pain registry** section). Run `python -I bx/skills/evolve/tests/check-state.py .` afterwards; a non-zero exit is reported as a validation failure.

**Section 3** renders the community lane's discovery result — its `allowlist_candidates`, with reasons — not findings. Nothing from that lane is written to the decision log; a candidate that is accepted in `--fix` becomes an allowlist row, and the docs lane evaluates the page next run. (A `tier: community` finding, should one ever arrive, is likewise never written.)

---

## Step 5 — Mode Tail

### If `--fix` in $ARGUMENTS:

Read `bx/skills/evolve/references/fix-mode-evolve.md` and run the gate flow exactly as specified there. fix-mode-evolve.md owns: eligibility rules, the pre-pass summary format, the per-finding display format, verdicts (y/n/skip/abort), Edit-tool edge cases, and the post-pass summary.

**Checkpoint 2** — write state per `bx/skills/evolve/references/state-schema.md`'s Update Mechanics (it owns the contents and procedure).

### Default (no `--fix`):

End with one closing line:

> Run `/bx:evolve --fix` to act on up to N fix-eligible findings (M open in total, K legacy display-only, D deferred). The pass re-greps each carried-forward one first and reports any it closes as already done or sets aside.

Where N = `open` entries (this run's and carried-forward) with a stored `proposed_edit` and non-empty `affected_files`; M = all `open` entries; K = `open` entries without a stored edit (pre-2.11.0 legacy); D = `deferred` entries. N is an upper bound computed from stored fields alone; the `--fix` pre-pass (`fix-mode-evolve.md`) may auto-close stale entries or set aside prose-only edits, and says so. The line never claims `--fix` can reach an entry it cannot — legacy and deferred entries are named, not folded into N.

---

## Step 6 — Watermark Advance

At the end of EVERY run (default or `--fix`), advance the watermark per state-schema Rule 4:

- `last_changelog_version` ← changelog lane's `newest_version_seen` (only if changelog `lane_status` is `ok` or `degraded`).
- `changelog_gap` ← set to `{"after": <gap_after>, "before": <gap_before>, "recorded": <today>}` when the lane reports `gap_after` non-null (a fresh gap, or a recorded one that is still open — `recorded` keeps the original date in that case); set to `null` when the lane reports `gap_closed: true`; otherwise unchanged — in particular an `unavailable` or `skipped` changelog lane leaves a recorded gap exactly as it was, and the report keeps showing it. These values, like the watermark fields, are known once the lanes return (Step 3), so Step 4's report renders the values Step 6 will write. The watermark still advances past a gap — that is deliberate: the gap object, not a frozen watermark, is what keeps the unscanned range visible (a frozen watermark would re-scan the same 50 releases forever after a yanked tag). Section 1 renders the gap on every run until it is `null`.
- `docs_checked_at` ← today's date (only if docs `lane_status` is `ok` or `degraded`).
- `community_checked_at` ← today's date (only if community `lane_status` is `ok` or `degraded`). A `--no-community` run leaves this field unchanged.
- A lane marked `current` at Step 1.5 leaves its field unchanged: the stored value already equals the head, which is why it was not dispatched.
- `docs_pages` ← for each page the probe reported: `unchanged` → keep the stored entry; fetched by the lane this run and not in its `pages_failed` → `{"hash": <probe hash>, "scanned": <today>}`; in `pages_failed`, or not probed → keep the stored entry (absent stays absent), so the page is scanned again next run. When the docs lane was `current`, every probed page is `unchanged` and the map is unchanged too.
- `inventory_hash` ← the probe's `inventory_hash` when the docs lane is `ok` or `current`; otherwise unchanged. A `degraded` run keeps the old value on purpose: the pages that failed were never compared against the new inventory, and a stale inventory hash makes the next run re-read every page, which is the safe over-scan.

**Checkpoint 3** — write state per `bx/skills/evolve/references/state-schema.md`'s Update Mechanics (it owns the contents and procedure).

---

## What This Skill Is NOT

- **Not a generic web-research tool.** `deep-research` exists for that. This skill's web access is bounded (pinned URL allowlist for docs, 3-query / 5-fetch cap for the community discovery feed, `gh` + one fallback for changelog) and always filtered through the pinned capability inventory + pain-point relevance gate. The community lane evaluates no community advice: it only looks for official pages and maintainer posts the allowlist lacks.
- **Not a skill-quality reviewer.** Reviewing skill correctness, internal consistency, and step completeness is the S42 content-review treatment, invoked via skill-creator. This skill only watches upstream sources — it cannot detect skill logic bugs that have no upstream correlate.
- **Not for repos other than claude-config.** The capability inventory is built from `bx/` and the operational docs in this repo. Running it in a different repo would produce an empty inventory and zero findings.
- **Not a replacement for reading release notes when something is actively broken.** This is a periodic audit tool, not an incident response tool. If a Claude Code update broke something right now, read the release notes directly rather than waiting for a periodic run.

---

## Quick Reference

| Want... | Use... |
|---|---|
| Toolkit feels outdated — audit against upstream | `/bx:evolve` |
| Apply findings from the last report | `/bx:evolve --fix` |
| Full re-audit ignoring watermark | `/bx:evolve --full` |
| Fast pass without the discovery search | `/bx:evolve --no-community` |
| Audit skill quality and internal correctness | skill-creator content review |
| Which skill to run next in a work repo | `/bx:health` |

---

$ARGUMENTS
