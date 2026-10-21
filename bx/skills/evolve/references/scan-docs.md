# Scan: Official Docs (Anthropic docs pages)

Loaded by the orchestrator and passed to the `upstream-docs` subagent. You are that subagent. Detailed scanning instructions follow.

You have these tools available: Read, Grep, Glob, WebFetch. Use WebFetch for all network access. No `curl`, no shell HTTP commands.

---

## Inputs you receive in your task prompt

- `docs_checked_at` — ISO date string (YYYY-MM-DD) or null. The date the docs pages were last fetched and compared against the capability inventory. It frames the report only ("docs checked as of <date>"); it does NOT gate what you fetch — `pages_to_scan` does.
- `pages_to_scan` — the allowlisted URLs to fetch this run, chosen by the orchestrator (SKILL.md Step 1.5) from a content-hash probe of every allowlisted page: the pages whose text changed since the hash stored at the last run, pages with no stored hash, pages whose probe failed, or every page when the capability inventory changed or `--full` was passed. Fetch exactly these — no more (a page not listed is unchanged and its findings are already in the decision log) and no fewer (a listed page you do not fetch is reported in `pages_failed`, never silently dropped). The list is never empty: when nothing needs scanning the orchestrator does not dispatch this lane.
- The shared inputs — `capability_inventory`, `pain_point_list`, and the Grep scope — are defined in `bx/skills/evolve/references/lane-contract.md` §1. Read that file after this one; it owns everything this lane shares with the other two (relevance filter, `affected_files`, finding schema, sentinel, `lane_status`, hard rules, footer keys) and this file never restates it.

---

## Pinned URL allowlist

Verified 2026-06-09; `permissions` added 2026-07-22 (S50); `checkpointing` + `code-review` added 2026-08-11 (S54); `auto-mode-config` added 2026-10-20 (S61, a candidate since 2026-08-11); `code-review-local`, `ultrareview`, `plugins/manifest-reference`, `plugins/marketplace-reference`, `plugins/components`, `permission-modes`, `tools-reference` added 2026-10-20 (S61 `--fix`, from the first run's `allowlist_candidates`; `plugins/install`, `scheduled-tasks` and `settings-reference` declined 2026-10-20 — re-offer only with a new reason). For each URL: the working form confirmed by WebFetch, the capability area it covers, and any redirect note.

| URL | Capability area | Notes |
|-----|----------------|-------|
| `https://code.claude.com/docs/en/skills` | skill authoring — SKILL.md frontmatter, invocation control, subagent execution, dynamic context injection | loads directly |
| `https://code.claude.com/docs/en/plugins` | plugin creation — manifest schema, directory layout, skills/agents/hooks packaging, marketplace submission | loads directly |
| `https://code.claude.com/docs/en/plugins-reference` | plugin technical reference — complete schema specs, CLI commands, version management, monitors, LSP servers | loads directly |
| `https://code.claude.com/docs/en/plugins/loading` | plugin loading — versions and updates, the `version` field as update cache key, auto-update | added 2026-09-28; `plugins` and `plugins-reference` now return overview/manifest pages that no longer own this contract |
| `https://code.claude.com/docs/en/plugins/cli-reference` | plugin CLI — `claude plugin validate` flags, `/reload-plugins`, install/update commands | added 2026-09-28 |
| `https://code.claude.com/docs/en/plugin-evals` | plugin evals — `claude plugin eval` suite format, graders, thresholds | added 2026-09-28 |
| `https://code.claude.com/docs/en/hooks` | hook events — lifecycle points, matcher patterns, handler types, JSON schemas, exit codes, async/HTTP/MCP/prompt hooks | loads directly (page title is "Hooks reference"; the `/hooks-reference` path 404s) |
| `https://code.claude.com/docs/en/settings` | settings — scope hierarchy, settings files, permissions, allowed-tools syntax, env vars | loads directly |
| `https://code.claude.com/docs/en/permissions` | permission rules — `Tool(param:value)` parameter matching, `Agent(<name>)` subagent rules, Bash/Read/Edit specifier syntax, allow/ask/deny precedence, wildcards, working directories | loads directly |
| `https://code.claude.com/docs/en/sub-agents` | subagent configuration — system prompts, tool restrictions, model routing, persistent memory | loads directly |
| `https://code.claude.com/docs/en/memory` | memory — CLAUDE.md authoring, auto memory, .claude/rules/, path-scoped rules, import syntax | loads directly |
| `https://code.claude.com/docs/en/commands` | commands/slash-commands reference — built-in commands, bundled skills, workflow commands | candidate `/slash-commands` redirects to skills page; successor is this URL |
| `https://code.claude.com/docs/en/checkpointing` | checkpointing — per-user-prompt checkpoint capture, `/rewind` restore semantics, `Esc Esc` behavior, subagent/background-fork edits not restored, bash-command changes untracked | loads directly |
| `https://code.claude.com/docs/en/code-review` | code review — `/code-review` effort levels + remembered level, background/foreground runs, `--fix` edits outside checkpoints, `disable-model-invocation` scheduled-task caveat, `REVIEW.md`, ultra escalation | loads directly |
| `https://code.claude.com/docs/en/auto-mode-config` | auto mode — classifier-approved actions, which `allow` rules are dropped on entry (broad `Bash(*)`) and which carry over, destructive-git blocking, `PermissionDenied` retry hook | loads directly (verified 2026-10-20); owns the premise of webdesign finding `dadac845` |
| `https://code.claude.com/docs/en/code-review-local` | local `/code-review` — effort levels + remembered level, background runs, `--fix`, `REVIEW.md`, ultra escalation (the contract bx:review's ladder cites) | added 2026-10-20 (S61); the `code-review` row above now describes only the GitHub-hosted service |
| `https://code.claude.com/docs/en/ultrareview` | `/code-review ultra` — the cloud multi-agent pass bx:health and bx:review route to; `/ultrareview` alias | added 2026-10-20 (S61) |
| `https://code.claude.com/docs/en/plugins/manifest-reference` | plugin.json schema — fields, `version`, `displayName`, `userConfig`, path rules, validate | added 2026-10-20 (S61); `plugins-reference` now returns this content under another title |
| `https://code.claude.com/docs/en/plugins/marketplace-reference` | marketplace.json schema — entry fields, plugin source types, per-entry `version` and `strict` precedence, copy vs link mode | added 2026-10-20 (S61); `plugins/loading` links here for the version rule |
| `https://code.claude.com/docs/en/plugins/components` | per-component runtime — where hooks.json, `bin/`, agents and skills load from and what runs at session start | added 2026-10-20 (S61); the `plugins` row is now only an overview |
| `https://code.claude.com/docs/en/permission-modes` | permission modes, auto mode defaults, protected paths — what the classifier blocks before any rule | added 2026-10-20 (S61) |
| `https://code.claude.com/docs/en/tools-reference` | built-in tool names and behaviour (Agent, AskUserQuestion, Bash, PowerShell, WebFetch) — the vocabulary of `allowed-tools`, agent `tools` and `disallowed-tools` | added 2026-10-20 (S61) |

This lane fetches ONLY these allowlisted URLs. Following a link is allowed only to an anchor on the **same page** (one hop to a `#fragment`). Never follow links to other pages or domains. Why: unbounded link-chasing turns this pinned lane into an open-research lane and destroys the authority guarantee — findings must be traceable to a specific canonical page.

**Allowlist completeness rule (S50).** A page belongs on this list when it is the *canonical owner* of a syntax or contract the bx plugin depends on — not merely when it mentions that syntax in passing. `permissions` was absent while `settings` and `sub-agents` were present; both show only name-based `Agent(<name>)` rules, so the lane concluded `Tool(param:value)` was undocumented and proposed reverting a correct fix. **Before emitting any finding whose claim is "the docs don't document X," check whether the page that owns X is on this list at all** — if it isn't, that is an allowlist gap: put the page in `allowlist_candidates` (footer), not in a finding about the plugin. The same goes for any official page you were tempted to follow a link to: record it as a candidate instead of fetching it.

---

## Delta detection — content hashes, not a version

Docs pages are not versioned like releases, so this lane has two baselines. The **content hash** of each page (`watermark.docs_pages` in state.json, probed by the orchestrator before dispatch with `bx/skills/evolve/scripts/docs-page-hashes.py`) decides *which pages* you read: an unchanged page cannot yield a finding the decision log does not already hold — open and deferred entries carry forward, applied and rejected ones re-raise only when their source changes — unless the **capability inventory** changed, in which case every page is re-read because the comparison itself changed. Within a page you read, the baseline is the inventory: compare the guidance against what the bx plugin currently does and emit findings for any gap. Until bx 2.12.0 this lane re-read all allowlisted pages every run (~180k tokens); the probe reads none of them into context.

`docs_checked_at` only frames the report. The orchestrator advances it, and stores the hash of each page you fetched successfully, only on `ok` or `degraded` (lane-contract.md §7).

---

## Method

### Step 1 — Fetch each page in `pages_to_scan`

For each URL in `pages_to_scan` (each is a row of the allowlist above), call `WebFetch` using that row's "Capability area" column as the fetch prompt focus — ask for the full page content relevant to that specific area. Do not use a single generic prompt enumerating all areas for every URL; the per-row capability area is the fetch focus.

**Failure definition:** A fetch fails if WebFetch returns an error, a redirect to an unrelated page, or empty content where content is expected. On any failure: record the URL and error in `pages_failed` for the footer addendum and continue with the remaining URLs. Never silently skip a failed fetch — the footer must name every failure explicitly.

**One-hop rule:** you may follow a `#fragment` anchor on the same page to read a specific section. Never follow links to other pages or domains.

**Truncation rule (Claude Code 2.1.290+):** WebFetch stops at about 100,000 characters and reports how much of the page was left unread. If a fetch reports unread text, call the same URL again with `offset` set to the reported position, and repeat until the page is complete; treat the parts as one page. If the page is still incomplete when you stop, record the URL in `pages_failed` with the reason `truncated at <position> of <total>` — a half-read page is partial coverage, not a clean fetch. (The hooks and sub-agents pages exceed the limit.)

**Verbatim extract:** for each guidance item that becomes a candidate delta, capture the verbatim page text of the smallest heading-bounded section containing it, from its own heading to the next same-or-higher heading — that is the `source_excerpt`, never WebFetch's summary prose (lane-contract.md §5 says why: hash stability).

**Issue all WebFetch calls for `pages_to_scan` in a single message — they are independent; tally `lane_status` after all return.** Do not stop early on a failure — fetch all, then tally.

### Step 2 — Extract candidate deltas per page

For each successfully fetched page, extract guidance that falls into either category:

**(a) Contradiction with current bx behavior:**
- Guidance that contradicts something bx currently does (e.g. a frontmatter key bx uses has been renamed, a hook event bx uses has been removed, an `allowed-tools` pattern bx uses is now invalid)
- Guidance that recommends AGAINST a pattern bx currently uses (deprecation, anti-pattern callout)

**(b) New capability matching a recorded pain point:**
- A feature described in the docs that directly addresses a pain point in the `pain_point_list` and bx does not yet use it

Each is a candidate delta — proceed to Step 3 before emitting as a finding.

**Class assignment** is lane-contract.md §6: category (a) yields `breakage` (the current form is deprecated, removed or broken) or `best_practice` (recommended against, still works); category (b) yields `opportunity`.

### Step 3 — Verification gate

Before assigning a class or emitting any finding, Read the actual bx file(s) the candidate delta maps to and confirm the contradiction or absence in real file content.

- For a `breakage` or `best_practice` candidate: locate the specific token (frontmatter key, hook event name, settings key, flag, command) in the bx plugin files via Grep. If the token is not present in any bx file, the contradiction cannot be confirmed — cap `certainty` at 0.5 or discard the candidate.
- For an `opportunity` candidate: locate the relevant capability area in the bx plugin files. If bx already uses the new capability (the pain point is already addressed), discard the candidate.
- If you cannot confirm the contradiction or absence in a bx file, the candidate is either a false positive (bx doesn't use that token at all) or already resolved. A delta you could not confirm in a real bx file is capped at `certainty: 0.5` or discarded. **Why:** the capability inventory is a list of labels, not behavior — asserting contradictions from a label alone produces paraphrase-level junk findings that waste user attention.

Only candidates that survive the verification gate proceed to Step 4.

### Step 4 — Filter against capability inventory and pain points

Apply lane-contract.md §2 to the candidates that survived Step 3.

### Step 5 — Populate affected_files via Grep

Apply lane-contract.md §3. The token is the frontmatter key, hook event name, settings key, command name or flag the guidance contradicts; Step 3 should already have found it in a bx file, and this is the final check.

---

## lane_status definitions

`lane_status` is declared in the footer addendum; its consequence for `docs_checked_at` and the stored page hashes is lane-contract.md §7. For this lane the values mean:

| Value | Meaning |
|---|---|
| `ok` | Every page in `pages_to_scan` fetched successfully. |
| `degraded` | At least one page fetched, at least one failed. Findings are trustworthy but coverage is partial — failed pages' capability areas were NOT checked this run; the orchestrator keeps their old hash so they are re-scanned next run. |
| `unavailable` | Every fetch failed. Only the sentinel is emitted; `docs_checked_at` and the page hashes do not advance. |

**No fallback method exists for this lane.** Unlike the changelog lane (which falls back from `gh` to raw CHANGELOG.md), the docs lane has only one method: WebFetch the pages in `pages_to_scan`. If all fetches fail, the lane is `unavailable`. There is no mixed-source ambiguity.

---

## Finding schema

The schema, the per-lane field values and the shared field notes are lane-contract.md §4–§5; this lane is the **docs** column. Class, severity and certainty guidance is §6. Lane-specific values the table encodes: `citation` and `source_url` are the same allowlisted URL; a contradiction Step 3 could not confirm in a bx file is capped at `certainty: 0.5` or discarded; the cap is 15 findings.

---

## lane_unavailable degenerate finding

When every page in `pages_to_scan` fails, emit ONLY the sentinel of lane-contract.md §8 with `finding_id: "lane-unavailable-docs"`, `tier: "official"`, `severity: "high"`, `upstream_delta: "<verbatim errors from each failed WebFetch call>"` and `proposed_edit: "Re-run /bx:evolve when network is available; docs_checked_at was NOT advanced."`. Set `lane_status: unavailable`.

---

## Hard rules

lane-contract.md §9 applies in full. One rule is this lane's own: **do not follow links beyond one hop to a same-page anchor.** The pinned allowlist is the full scope of this lane, and `pages_to_scan` is this run's slice of it.

---

## Final output addendum

After all findings (or after the single sentinel), append the shared keys of lane-contract.md §10 (`lane_status`, `allowlist_candidates`, `scan_note`, `discarded_findings`) plus this lane's own:

```
pages_fetched: <n of <count of pages_to_scan> — pages that returned content successfully>
pages_failed: [<url>: <error>, ...]   # empty list [] if all succeeded; a page in pages_to_scan you did not fetch is listed here, never silently dropped
```

`allowlist_candidates` for this lane: an official `code.claude.com` or `anthropic.com` page that is the canonical owner of a contract bx depends on and is not in the table above — typically one an allowlisted page links to for the detail you needed, or one the completeness rule (above) told you was missing. Name the capability area the page would cover; the orchestrator offers it as a new allowlist row in `--fix`.

