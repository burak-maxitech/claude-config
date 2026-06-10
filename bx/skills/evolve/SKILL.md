---
name: evolve
description: Audits the bx toolkit against upstream Anthropic changes — new Claude Code releases, official-docs best practices, and community patterns — since the last run's watermark. Reports breakage/best-practice/opportunity findings with citations; --fix applies them behind a per-finding diff gate. Use when Anthropic ships a new Claude Code version, when built-ins change or collide, periodically (monthly) to keep skills current, or when asking "are my skills up to date with the latest capabilities".
disable-model-invocation: true
effort: high
allowed-tools: Read, Grep, Glob, Edit, Write, Bash(git:*), Bash(gh:*), Bash(wc:*), Bash(jq:*), Bash(cat:*), Bash(head:*), Bash(python:*), Bash(python3:*), WebFetch, Task
argument-hint: "[--full] [--fix] [--no-community]"
---

# /bx:evolve — Upstream-Watch Audit for the bx Plugin

This skill watches upstream Anthropic sources — claude-code releases, official docs, and community patterns — and audits the `bx` plugin against what has changed since the last run's watermark. It surfaces breakage (upstream invalidated something bx says or does), best-practice (guidance changed for something bx does), and opportunity (new capability maps to a recorded pain point) findings with mandatory citations, then applies approved changes behind a per-finding diff gate when `--fix` is passed.

This skill is distinct from related tooling in this repo:

- **`/bx:health`** — routing advisor; answers "which skill should I run next on this project". It reads your codebase, not upstream sources.
- **S42 content-review treatment via skill-creator** — audits skill quality (correctness, completeness, internal consistency). It reads `bx/` files against themselves, not against upstream.
- **`deep-research`** — generic multi-source web research. It has no concept of the bx plugin, no watermark, no decision log, and no relevance gate tied to the capability inventory.

**Run-in-repo precondition.** This skill only makes sense in the claude-config repo. Before doing any other work, confirm that both `bx/` and `docs/upstream/` exist in the working directory via Glob. If either is absent, say so clearly and exit — do not attempt to recreate them or continue.

---

## Step 0 — Load State + Build Capability Inventory

### 0.1 — Load state

Read `docs/upstream/state.json`. The canonical shape, all validation rules, and the null-seed form are defined in `bx/skills/evolve/references/state-schema.md` — defer to that file entirely; do NOT restate its mechanics here. If the file is missing (first-ever run), recreate the null seed from state-schema's normative shape via Write and treat this run as `--full`.

### 0.2 — Build capability inventory

Enumerate current bx capabilities by reading across `bx/**`, `README.md`, and `workflow.md`. Gather these four categories in parallel (multiple Read/Grep/Glob calls in one turn):

**(a) Frontmatter keys in use across all skills and agents.** Glob `bx/skills/*/SKILL.md` and `bx/agents/*.md`; for each file, read the YAML frontmatter block and note every key present (e.g. `allowed-tools`, `effort`, `disable-model-invocation`, `argument-hint`, `when_to_use`, `model`, `tools`, `user-invocable`).

**(b) Built-in skill references.** Grep `bx/` + `README.md` + `workflow.md` for `/code-review`, `/simplify`, `/code-review ultra`, and any other slash-commands that are not bx-namespaced. These are the built-in surface area the repo depends on — changes here are breakage candidates.

**(c) Harness idioms relied on.** Grep for: Task dispatch + `subagent_type`, `!` dynamic injection syntax, plugin `bin/` PATH helpers, the no-env-var-persistence assumption (documented in CLAUDE.md), allowed-tools enumeration discipline (the S42/S45 lesson), SessionStart hook invocations.

**(d) Hook events.** Read `bx/hooks/hooks.json`; enumerate every event name registered.

Render inventory entries as capability strings in `bx:<skill>/<area>` form (e.g. `bx:seo/allowed-tools`, `bx:save/agent-model`). These feed `finding_id` computation — the format matters. For normalization rules, see state-schema.md's `affected_capability` normalization section.

**Historical archives out of scope:** `docs/key-decisions.md`, `docs/session-history.md`, and CLAUDE.md history sections are records of past state per repo convention. Do not include them in the inventory.

### 0.3 — Pain points

Read CLAUDE.md `## Known Issues / Blockers` and `## Next Steps`. Extract each item as a short pain-point string (e.g. `"permission prompts on every run"`, `"watermark drift on partial failures"`). These feed the relevance gate — a finding that addresses a pain point is surfaced even without a direct capability-inventory match.

### 0.4 — Detection summary

End Step 0 with a one-line summary to the user, e.g.:

> Loaded state: changelog watermark 2.1.170 · docs 2026-06-09 · community 2026-06-09. Inventory: 47 capability entries, 6 pain points. 3 open findings in decision log.

---

## Step 1 — Mode Dispatch

Interpret `$ARGUMENTS`:

| Flag | Effect |
|---|---|
| *(none)* | Default delta run: research changes since the watermark, emit report, stop. |
| `--full` | Treat all watermark fields as null FOR THIS RUN only — the stored `state.json` is untouched until the end-of-run watermark advance (Step 6). Triggers a full re-audit as if running for the first time. |
| `--fix` | Run the full report (Steps 2–4), then execute the per-finding diff gate (Step 5). |
| `--no-community` | Skip lane 3 (`upstream-community`). Lane 3's `community_checked_at` watermark field keeps its previous value per state-schema Rule 4 — the missed range re-checks on the next run. |

`--full --fix` is a valid combination. No other flags are recognized; if an unrecognized flag is present, say so and exit.

---

## Step 2 — Parallel Lane Dispatch

Launch all three lane agents in a single turn (three Task calls in one message). Set `subagent_type` to the dedicated agent name for each — **never generic subagents** (the S43 rule: skill-specific agents carry the least-privilege tool lists and baked-in scanning instructions; a generic subagent runs on the orchestrator's model and bypasses tool scoping):

- Task 1: `subagent_type: upstream-changelog`
- Task 2: `subagent_type: upstream-docs`
- Task 3: `subagent_type: upstream-community` (omit when `--no-community`)

For each Task call:

1. Read the agent's scan reference file (`upstream-changelog` → `bx/skills/evolve/references/scan-changelog.md`; `upstream-docs` → `bx/skills/evolve/references/scan-docs.md`; `upstream-community` → `bx/skills/evolve/references/scan-community.md`) and pass its **full content** in the task prompt.

2. Also pass the full content of `bx/skills/evolve/references/state-schema.md` (agents point to it for canonicalization conventions and cannot reliably read sibling paths from their own CWD — inline it).

3. Include the following shared context block verbatim:

```
Watermark: last_changelog_version=<value|null> · docs_checked_at=<value|null> · community_checked_at=<value|null>
Capability inventory: <the list from Step 0.2>
Pain points: <the list from Step 0.3>
Tier definitions: official = actionable with citation; community = advisory-only, never fix-eligible
Repo root: the working directory. Grep scope for affected_files: bx/, README.md, workflow.md.
Output: structured JSON-shaped findings per the schema in your scan instructions. finding_id: null and source_excerpt as specified — the orchestrator computes all hashes. Do NOT format a report.
```

**`--no-community`:** omit the Task call for `upstream-community` entirely. Record `lane_status: skipped` for that lane in the report footer.

**`--full`:** pass `last_changelog_version=null`, `docs_checked_at=null`, `community_checked_at=null` in the shared context block, overriding the stored values. The stored `state.json` is untouched at this point.

**Agent tool lists are least-privilege.** Do not ask agents to run anything beyond their scan instructions. The orchestrator owns all state reads and writes; agents return raw findings only.

---

## Step 3 — Consolidate + Compute Hashes + Gate

After all lane agents return (wait for all three Task calls to complete):

### 3.1 — Collect lane outputs

Record each lane's `lane_status` (ok / degraded / unavailable / skipped). These govern watermark advancement (Step 6) and the report footer (Step 4).

### 3.2 — Compute finding_id and source_content_hash

For every non-sentinel finding (i.e., every finding whose `finding_id` is null), compute both hashes via `Bash(python:*)`. Run the ENTIRE batch in ONE python invocation — shell state does not persist between Bash calls, so splitting across calls loses the results. Pass findings as a heredoc or inline JSON string; print computed pairs.

The normative hash snippets are defined in `bx/skills/evolve/references/state-schema.md` (finding_id computation section and source_content_hash normalization section). Use them exactly. Do not reimplement.

Sentinel findings (`lane-unavailable-changelog`, `lane-unavailable-docs`, `lane-unavailable-community`) keep their literal string IDs — do not hash them.

### 3.3 — Relevance spot-check

The relevance gate is applied lane-side. Spot-check: drop any finding whose `affected_capability` intersects neither the capability inventory nor the pain-point list. This catches improvised lane output that slipped through.

### 3.4 — Decision-log filter

For each consolidated finding, look up its computed `finding_id` in the stored `decisions` array:

- **`rejected` + source_content_hash UNCHANGED:** suppress from the report; count in footer as "N rejected (unchanged, suppressed)".
- **`rejected` + source_content_hash CHANGED:** surface with `[re-raised — source changed since rejection]` badge. Update the stored entry: `decision → open`, `source_content_hash → new hash`, `date → today` (per state-schema Rule 3).
- **`deferred`:** surface in Section 4 of the report with `[deferred <original date>]` badge (per state-schema Rule 5). If the live `source_content_hash` differs from stored, update stored hash and note "source changed since deferral" alongside the badge. Do NOT update the `date` field.
- **`open` or no existing entry:** surface normally.

### 3.5 — Cross-lane dedup

Same `finding_id` from two lanes → keep the higher-authority lane's version (changelog > docs > community); merge citations into a single `citation` string (e.g. `"v2.1.169 / docs"`). Tier-2 (community) findings are advisory regardless of class — never promote a community finding to actionable by merging it with a Tier-1 finding that shares a `finding_id`.

---

## Step 4 — Report

Read `bx/skills/evolve/references/report-template.md` and render exactly as specified there. Do not improvise the report structure; report-template.md owns every section, the headline format, the empty-state rows, and the footer shape.

**New actionable findings → decision log.** Before rendering the report, write every NEW finding (no existing `finding_id` entry in `decisions`) to `docs/upstream/state.json` as `decision: "open"` per state-schema Rule 1. Use the Read-modify-in-context-Write procedure from state-schema.md's Update Mechanics section.

**Advisory findings are NOT written to the decision log.** Community-sourced (`tier: community`) findings are advisory-only and never actionable on their own. There is nothing to track in `decisions` for them — they appear in Section 3 of the report and are gone when the run ends. The decision log tracks only actionable findings that require a verdict.

---

## Step 5 — Mode Tail

### If `--fix` in $ARGUMENTS:

Read `bx/skills/evolve/references/fix-mode-evolve.md` and run the gate flow exactly as specified there. fix-mode-evolve.md owns: eligibility rules, the pre-pass summary format, the per-finding display format, verdicts (y/n/skip/abort), Edit-tool edge cases, and the post-pass summary.

Apply verdicts to `docs/upstream/state.json` per state-schema Rule 2 (overwrite in place, never append).

### Default (no `--fix`):

End with one closing line:

> Run `/bx:evolve --fix` to apply N eligible findings. M open findings carried forward in `docs/upstream/state.json`.

Where N = count of Tier-1 open findings in this run's report (fix-eligible), and M = total `open` + `deferred` entries in the decision log after this run.

---

## Step 6 — Watermark Advance

At the end of EVERY run (default or `--fix`), advance the watermark per state-schema Rule 4:

- `last_changelog_version` ← changelog lane's `newest_version_seen` (only if changelog `lane_status` is `ok` or `degraded`).
- `docs_checked_at` ← today's date (only if docs `lane_status` is `ok` or `degraded`).
- `community_checked_at` ← today's date (only if community `lane_status` is `ok` or `degraded`). A `--no-community` run leaves this field unchanged.

Rewrite `docs/upstream/state.json` using the canonical Read-modify-in-context-Write procedure from state-schema.md's Update Mechanics section. Validate before writing; on any validation failure, do NOT write and report the failure explicitly — leave `state.json` at its previous valid state.

---

## What This Skill Is NOT

- **Not a generic web-research tool.** `deep-research` exists for that. This skill's web access is bounded (pinned URL allowlist for docs, 3-query / 5-fetch cap for community, `gh` + one fallback for changelog) and always filtered through the capability inventory + pain-point relevance gate.
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
| Fast official-only pass (no community search) | `/bx:evolve --no-community` |
| Audit skill quality and internal correctness | skill-creator content review |
| Which skill to run next in a work repo | `/bx:health` |

---

$ARGUMENTS
