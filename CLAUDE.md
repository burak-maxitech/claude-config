# CLAUDE.md

Last Updated: 2026-05-29 (Session 38)

## Project Overview

**claude-config** — Personal Claude Code configuration repo containing custom skills, subagents, and workflow documentation.

- **Repo:** [burak-maxitech/claude-config](https://github.com/burak-maxitech/claude-config) (private)
- **README.md** — Public overview, setup instructions, command reference
- **Workflow.md** — Detailed personal workflow guide (daily workflow, scenarios, tips)
- **docs/** — Reference files (session history, key decisions, completed work)

## Current Status

| Area | Status |
|------|--------|
| Skills (9) | Complete |
| Subagents (15) | Complete |
| Plugin packaging (`bx`) | Core complete (S37) — pending install smoke-test + symlink retirement |
| Startup scripts | Complete |
| Cross-platform setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 9 skills, 13 subagents, cross-platform setup, and documentation system are complete.

See [docs/completed-work.md](docs/completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**`/bx:save` rework shipped (S38) — merged to `main`, pending push + plugin refresh to activate.** `/bx:docs` was reworked into the faster, renamed `/bx:save` (fast-by-default UPDATE + `save-writer` Sonnet offload; see Key Decisions). Merged to `main` with `--no-ff` (8 commits), **not yet pushed**. Until `main` is pushed and `/plugin update bx` runs, the installed plugin still serves the old slow `/bx:docs`.

**S37 plugin packaging (#4) — remaining:** install smoke-test (`/plugin install bx@burak-tools`), verify agent-dispatch naming (`bx:seo-technical` vs bare), retire `~/.claude` symlinks, `settings.local.json` `Skill(bx-*)` → `Skill(bx:*)`, SessionEnd→`/bx:save` nudge, launcher-script symlink-check retirement. (GSC MCP migration #1 declined; Playwright #2 deferred — see Key Decisions.)

## Next Steps

1. **Activate `/bx:save`:** push `main` to origin, then `/plugin marketplace update burak-tools` → `/plugin update bx` (or run `cc`). Then **dogfood `/bx:save`** as the real session-save — first end-to-end test of the speedup, the packet round-trip to `save-writer`, the `bx:save-writer` dispatch naming, and the key-decisions anchor rule. (This session's save ran on the old slow `/bx:docs`.)
2. **⚠️ Revisit + fix `/bx:seo` — user flagged the skill as messed up (S37).** First diagnose *what* is actually wrong before touching code: the repo skill is at its committed state (git confirms `bx/skills/seo/` untouched, working tree clean), so the issue is either an expectation-vs-reality gap, the GSC auth/MCP confusion (gcloud+helper vs the separate interactive MCP server), or uncommitted/unpushed changes on a Windows PC. Pin down the concrete symptom (run it, or check the PC's `git status`) first. Do NOT reopen the GSC→MCP migration (declined — see Key Decisions). See Known Issues / Blockers.
3. **Validate S35 on a real burakarik.com run.** Infrastructure now backs the S34 validation step: 100 user-supplied URL cap (was 50), helper-driven Turn 2b dispatch, split TTL (ui-* 7d means S34 cache entries now hit), finding-history infrastructure ready. Sub-dim 14 will fire since S34 wrote the baseline snapshot.
4. **Dogfood `/bx:tests` on a real Node/Jest or Python/pytest project** — built S24 but never invoked end-to-end. Watch for: T01 false-positive rate, twin-headline math correctness, `--coverage` opt-in path, scan-economics ratio thresholds (>3.0 over, <0.1 under), non-overlap with `/bx:clean`.
5. **Dogfood `/bx:arch` on a non-trivial real project** — never run end-to-end. Watch for linter-detection accuracy, intended-architecture summary quality, CCN-delta filter behavior, simplification false-positive rate.
6. **Dogfood `/bx:health`** — built S22 but never invoked end-to-end. Watch for bucket misclassification + freshness-mismatch detection accuracy.
7. **Address `/bx:seo` deferred refactors** (captured in `/simplify` passes S25 + S27 + S29): batched-Grep alternation across scan-technical/content/geo (biggest runtime win); fix-mode harness extraction; plan-mode scaffolding extraction; cross-file boilerplate consolidation. Best done after further dogfood surfaces which is most needed.
8. Improve existing skill reference files based on usage patterns; consider pre-commit hooks.

## Key Decisions

| Decision | Rationale |
|----------|-----------|

| `/seo-review` GSC API response cache — 24h TTL + `--no-cache` bypass flag (S31) | Motivated by the user's hesitation to consume GSC API quota during iterative `burakarik6` dogfood ("very precious to not consume usage limits of the API"). Wraps `searchanalytics.query` (Q1/Q2/Q3, 3 calls/run) + `urlInspection.index.inspect` (up to 100 calls/run, against the strict 2,000/day quota). Auth probe (sites.list) deliberately NOT cached — it's the live mode-detection check, must stay live. **TTL = 24h**, settled via brief design discussion: matches GSC's own ~2-day finalization lag. **`--no-cache` flag** forces fresh refetch but still writes responses to cache for next run. **Cache layout:** `.seo-data/gsc/cache/<prefix>-<sha1-hash>.json`. Per-Q-call prefixes (`sa-q1`/`sa-q2`/`sa-q3`) + per-URL prefix (`ui-`). **Wrapper invariants (5):** atomic write via `$CACHE_FILE.tmp.$$` + `mv` on HTTP 200; never cache non-200; TTL check via `find -mmin -$TTL_MIN`; cache dir pre-created in Step 1.6.1; first-stdout-line status marker. **Eviction:** `find -mtime +7 -delete` at Turn 1. **Disk-write boundary updated** to add `cache/` as a 3rd allowed entry under `.seo-data/gsc/`. **S35 update:** TTL split by call-type — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable). |

| `/seo-review` — 6 spec gaps codified from burakarik6 dogfood (S31 cont.²) | 4th `/seo-review` run of the day on burakarik.com surfaced 6 distinct issues + 1 design problem the orchestrator improvised around at runtime. Categorized 2 critical bugs / 2 spec ambiguities / 1 design issue / 1 emergent capability. All 6 fixes shipped same-session in commit `7109213` (5 files / +474 / -18 LOC). **Fix #1 — UTF-8 enforcement on Python**: Windows charmap default crashes on Turkish + GSC prompt-injection queries; codify `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` env vars on every invocation + `encoding='utf-8'` on every `open()`. **Fix #2 — Same-commit history dedup**: score swung 60→48→40→55 across 4 runs with last commit being docs-only (methodology variance, not codebase change); embed `<!-- commit:abc1234 -->` HTML comment + skip append when commit_sha already has an entry. **Fix #3 — Ship `references/gsc-parse-helper.py`** (~250 lines, 6 subcommands `q1`/`q2`/`q3`/`ctr`/`clusters`/`brand`): retires inline Python heredocs; helper script is the canonical parser. **Fix #4 — New sub-dim 13 `brand_query_anomaly`** (catalog now 12→13): codifies emergent capability — orchestrator caught `"burak arık"` at pos 7.91 / 1.93% CTR as entity-recognition deficit. **Fix #5 — CTR opportunity dual trigger**: high-volume override (imp>=10000 AND ctr<0.5% regardless of position). **Fix #6 — Probe-skipped redistribution rendering** mandatory in report footer. |

| Renamed custom `/code-review` → `/review-deep` after Anthropic naming collision (S32) | On 2026-05-23 Anthropic renamed built-in `/simplify` → `/code-review`, colliding with the custom code-review skill in this repo. The two skills are genuinely different — built-in is a lightweight diff scan with effort levels + `--comment` PR-comment posting; custom is a senior-engineer review with codebase-convention scanning + `--security` (OWASP) / `--verify` (run tests/lint, parallel-backgrounded since S19) / `--fix` / `--last-commit` modes. Solution: rename the custom skill to `/review-deep` and position the review tooling as a **3-tier ladder**: `/code-review` (built-in, fast, daily driver) → `/review-deep` (custom, thorough) → `/ultrareview` (built-in, cloud, 5+ verifying agents, high-risk pre-merge). Scope expanded to also updating `/simplify` references throughout operational docs to `/code-review` (since `/simplify` no longer exists by that name). 16 operational files modified + 1 directory rename via `git mv`; historical files deliberately left untouched as records of past state. README "Three review tiers" blockquote restructured to lead with the rename context + 2026-05-23 date. |

| 5 best-practice improvements from 2026 Claude Code docs audit (S33) | Web research across official Anthropic docs + 2026 community guides surfaced 5 high-leverage improvements, all implemented same-session in commit `5a441d1`: **(1) `${CLAUDE_SKILL_DIR}` substitution** in `/seo-review` for `gsc-parse-helper.py` invocations (CWD-independent + cross-platform). **(2) `effort: high` audit + `ultrathink` injection** — added `effort: high` to `/code-cleanup`; deliberate `effort: low` retained on `/code-health-advice`, `/resume-work`, `/update-docs` (routing/IO-bound). Added `ultrathink` keyword to the three `--plan` mode reference files. **(3) `description:` / `when_to_use:` split** on 4 verbose skills. Guards against silent description-truncation. **(4) Dynamic `` !`<cmd>` `` injection** in `/code-health-advice` Step 1 + `/resume-work` Step 2. Saves 1 turn per invocation. **(5) SessionStart hook bundle** — `session-start-context.sh` + `.ps1` in `.claude/scripts/`. Eliminates manual `/resume-work` for routine session starts. |

| `/seo-review` S34 extension — sub-dim 14 `deindex_regression` + 200/run URL Inspection + 4-slice URL selection + known-bad-urls.txt (2026-05-26) | Triggered by user's burakarik.com indexed-page decline + two GSC validation-failed emails (838 "Page with redirect" + 663 "Not found (404)" URLs sharing `/article/*` + `/en/article/*` + `/tr/article/*` locale-collision pattern). Existing skill's impressions-only sampling was blind to URLs Google had deindexed (they fall out of `url_impressions_map` → never inspected → user only learns when Google emails). 5-area extension across 10 files (+662/-67): **(1) URL Inspection 100/run → 200/run**, new sitemap-orphan slice (document-order sort — deterministic for snapshot regression diff). **(2) Sub-dim 14 `deindex_regression`** — orchestrator-emitted from snapshot diff at `.seo-data/gsc/snapshots/<ts>-<sha>.json` (30-day rotation, path-cluster + git-correlation evidence). **(3) Sub-dim 5 severity tiering** medium/<50, high/≥50 + locale-prefix-cluster detection. **(4) Sub-dim 4 ↔ sub-dim 5 cross-link** via `co_occurrence_with_sub_dim_5` evidence (the "single i18n migration root cause, two symptoms" diagnosis); git-changed slice now resolves BOTH `old_path` AND `new_path` from rename commits. **(5) `.seo-data/gsc/known-bad-urls.txt`** as 4th user-supplied URL source (S35 raised cap 50→100/run). `score_impact:0` invariant maintained on all GSC findings. **Burakarik.com's indexing decline is a codebase-level issue** (incomplete i18n canonical migration around ~4/21/26 inflection) — NOT caused by anything Claude has done. |

| `/seo-review` S35 hardening — 4 improvement groups + 15 code-review fixes (2026-05-26) | Same-day continuation of S34 dogfood. User ran the skill on burakarik6 with the new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (3rd disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high surfacing 15 findings + fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (~200 LOC: ThreadPoolExecutor parallel HTTP + per-URL 7d ui-* TTL + atomic write via `.tmp.<pid>` + os.replace + never-cache-non-200 + 3-retry exponential backoff on 429/5xx + 6 workers). Broader disk-write boundary rule: NO orchestrator-written Python/JS/shell anywhere under `.seo-data/gsc/`. Canonical-paths table forbids the next improvisation by name. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marker `(inherited from <sha> [<date>])` + `inherited_from:<sha>` HTML comment on history rows + new `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d after S34 scored 0/197 cache hits despite 85 prior cache entries (3 days old, past 24h TTL). Two-tier eviction (sa- at 7d, ui- at 14d = TTL + slack). **Group D:** finding lifecycle = `finding-history.json` (run_count tracker with same-commit guard so methodology-variance reruns don't inflate, `ESCALATE` at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true`, 21-day recheck, 90-day evict). Three new helper subcommands: `history-update`, `watchpoint-emit`, `watchpoint-check` (4 banner formats: improved/regressed/unchanged/no_data). **15 code-review fixes — top correctness bugs:** `head -1 sa-q2-*.json` picked random old Q2 file → deterministic hash recomputation from cache-key inputs; `time.mktime`/`localtime` had DST off-by-one on UTC dates → `datetime.date.fromisoformat() + timedelta()`; `_watchpoint_status` crashed on None metrics → filter upstream; "3-slice" docs-spec drift across 5 files → bulk to "4-slice"; operator precedence in `classify_transition` for `'soft 404 (not found)'` → parens; bare `.tmp` race → PID suffix; 20-worker burst rate → 6 + retries; `sys.exit(1)` before stdout flush → return bool + print-before-write; missing `\|\| skip` error trap between Step 6.8 sub-steps; null-title TypeError → `(f.get('title') or '')`; dangling "Pre-Turn-2 watchpoint check" reference → Step 1.6.14; per-call CACHE_STATUS spec drift → split Turn 2a (per-call) vs Turn 2b (aggregate); 24h-TTL back-references in 3 places; `_atomic_write_json` duplicated `snapshot_write` → refactored. **Altitude lesson:** every new dispatch shape that lives in spec-prose-only ("N parallel bash curl calls") gets improvised by the orchestrator into `.seo-data/gsc/` until shipped as a canonical helper subcommand. Same pattern as S30 `jq`-missing + S31 cont.² UTF-8-on-Windows. The fix is always "ship the canonical primitive," not "tell the orchestrator harder." |

| All 9 custom skills renamed under `bx-` prefix + shortened (S36, 2026-05-28) | Root-cause fix for recurring namespace collisions/confusion with built-ins. S32 was the first symptom (built-in `/code-review` shadowed the custom one → renamed custom → `/review-deep`); then two more shifts landed: Anthropic **reinstated `/simplify`** as a separate built-in (quality-only, applies fixes — invalidating S32's "/simplify no longer exists" premise), and **`/ultrareview` was deprecated → `/code-review ultra`**. The word "review" alone now maps to 5 built-ins/skills. Flat-namespace sharing is the root cause, so the fix is a personal prefix that can never collide with any present/future built-in + groups the whole toolkit under one tab-complete. **Mapping:** review-deep→`bx-review`, architecture-review→`bx-arch`, test-review→`bx-tests`, seo-review→`bx-seo`, code-cleanup→`bx-clean`, code-health-advice→`bx-health`, plan-feature→`bx-plan`, resume-work→`bx-resume`, update-docs→`bx-docs`. **Sweep:** 9 `git mv` + literal token-replace across 76 operational files (skills/agents/scripts/settings.local.json/README/workflow.md) via `find -exec perl` (the system `grep` is **ugrep** — `-Z` means fuzzy-match, not null-delimit, which silently no-op'd two earlier `xargs -0` attempts). Built-in refs (`/code-review`, `/simplify`, `/ultrareview`) deliberately preserved. Historical archives (`docs/*.md`, CLAUDE.md Key Decisions/Session History/Completed narrative) left untouched per the S32 records-of-past-state convention — this row + the file-tree comments are the old→new map. **Also this session:** uninstalled the `code-simplifier` plugin (redundant with built-in `/simplify` + the `arch-simplification` subagent; its baked-in standards are JS/React-specific, irrelevant to this markdown/Python repo). Review-tooling doc-freshness fixes also applied same session (separate commit): `/ultrareview`→`/code-review ultra` everywhere (deprecated alias → live command), and the reinstated built-in `/simplify` re-introduced into the review ladder + Bucket A routing. |
| GSC MCP migration (roadmap #1) evaluated and declined (S37, 2026-05-28) | `mcp-search-console` (the `gsc` MCP server) has **no response caching** + caps `batch_url_inspection` at **10 URLs/call** — a full migration would regress the quota economics the S31/S35 cache layer protects (the skill inspects up to 200 URLs in parallel with a 7-day `ui-*` cache via `gsc-parse-helper.py`). **`/bx:seo` stays on gcloud ADC + the helper.** The `gsc` MCP server stays configured machine-local (`~/.config/bx-seo/`, portable OAuth `token.json`) for *ad-hoc interactive* GSC queries only — NOT wired into the skill. Git history across all branches/remotes/reflog confirms the skill was **never** on MCP; only the roadmap doc mentions it. `get_advanced_search_analytics` (clean JSON, 25k-row pagination) is the one tool worth revisiting if ever rebuilt — Performance queries only, never URL Inspection. Full: [docs/key-decisions.md](docs/key-decisions.md). |
| `/bx:docs` → `/bx:save` rework — fast-by-default + Sonnet offload (S38, 2026-05-29) | The end-of-session save (paired with `/bx:resume`) routinely took >10 min so the user abandoned it. Root causes: Step 0 read all docs every run (~60k tokens incl. the 70k+53k append-only archives the update never reads *from*) even on `--fast`; the verification step echoed full file contents back; verbose prose. Fix: the lean session-save is now the **default** (drain tasks → CLAUDE.md session block → session-history append → commit), with README/docs sync + rollups moved to `--full`; a new `save-writer` Sonnet subagent does the big reads + all file writes off the main thread while the Opus orchestrator composes a small "update packet" + dispatches; full-file output dump → compact change report; prose caps on new entries; scoped Step-0 reads. Skill renamed `/bx:docs` → `/bx:save` (collision-proof pair-name with `/bx:resume`). Subagents 14 → 15. Built via superpowers brainstorm→spec→writing-plans→subagent-driven flow; specs in [docs/superpowers/](docs/superpowers/). Full: [docs/key-decisions.md](docs/key-decisions.md). |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
claude-config/                         # marketplace repo
├── .claude-plugin/
│   └── marketplace.json               # "burak-tools" marketplace catalog
├── bx/                                # the installable `bx` plugin (S37, see Key Decisions)
│   ├── .claude-plugin/plugin.json     # manifest (commit-SHA versioned; skills → /bx:<name>)
│   ├── agents/                        # 15 subagents (Sonnet-routed) → bx:<agent>
│   ├── hooks/hooks.json               # SessionStart project-orientation injection
│   ├── scripts/                       # session-start-context.{sh,ps1}
│   └── skills/                        # 9 skills (SKILL.md + references/) → /bx:<name>
│       ├── arch/    clean/   health/
│       ├── plan/    resume/  review/
│       ├── save/    seo/     tests/   # save = /bx:save (was docs)
├── .claude/
│   ├── scripts/             # start-claude.{sh,ps1} launchers (not plugin components)
│   └── settings.local.json  # Local Claude Code settings
├── docs/                    # Reference files (overflow from CLAUDE.md)
│   ├── completed-work.md
│   ├── key-decisions.md
│   ├── modernization-roadmap.md
│   └── session-history.md
├── .gitignore
├── CLAUDE.md                # This file — AI session context
├── README.md                # Public overview
└── workflow.md              # Personal workflow guide
```

**Plugin approach (S37):** the toolkit installs as the `bx` plugin from the local `burak-tools` marketplace (`/plugin install bx@burak-tools`) — no symlinks. Skills are namespaced `/bx:<name>` and agents `bx:<agent>` by the plugin, which is the principled collision-proof fix that the S36 `bx-` prefix only worked around. `version` is omitted so each commit is a new version. (Old `~/.claude/skills`+`agents` symlinks are retired on adoption — see README "Migrating from the old symlink setup".)

**Skills** are directories under `bx/skills/` containing `SKILL.md` (YAML frontmatter) + a `references/` folder. Invocable as `/bx:<name>`.

**Subagents** are the 15 markdown files under `bx/agents/`, dispatched by skills. They run on Sonnet for cost efficiency and have scoped tool permissions. (`save-writer` is dispatched by `/bx:save` to apply doc edits off the main thread.)

## Known Issues / Blockers

**`/bx:seo` flagged for revisit + fix (S37, 2026-05-28).** The user flagged the SEO skill as "messed up" and wants it fixed next session. **Verified baseline:** the repo skill files (`bx/skills/seo/`) were NOT modified in S37 — git shows them at their committed state and the working tree is clean, so whatever is wrong was not introduced this session. Likely candidates: the GSC auth/MCP confusion that consumed S37 (the skill uses gcloud + `gsc-parse-helper.py`; the `gsc` MCP server is separate/interactive-only — see Key Decisions + the `gsc-auth-model` memory), an expectation-vs-reality mismatch, or uncommitted/unpushed work on one of the Windows PCs. **Next session: first establish the concrete symptom** (run the skill, or check the PC's `git status`/`git log`) before changing anything. Do NOT reopen the GSC→MCP migration (evaluated and declined).

## Environment Variables

None required. This is a pure configuration repo — no runtime dependencies or secrets.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 38) - 2026-05-29
- **Reworked `/bx:docs` → `/bx:save`** (pairs with `/bx:resume`): the end-of-session save was taking >10 min and the user had stopped using it.
- **Fast by default**: bare `/bx:save` does the lean session-save (drain tasks → CLAUDE.md session block → session-history append → commit); the heavy README/docs sweep + rollups are now opt-in via `--full`. `--fast` kept as a no-op alias.
- **Sonnet offload**: new `save-writer` subagent (15th) absorbs the big `session-history.md` read + all file writes off the main thread; the Opus orchestrator only composes a small "update packet" + dispatches. Scoped Step-0 reads (~−30k tokens/run); full-file output dump removed; prose caps added.
- **Built via superpowers** brainstorm → spec → writing-plans → subagent-driven execution; final holistic review caught a runtime blocker (missing `Task` in `allowed-tools`) — fixed. 8 commits merged to `main` (not yet pushed). Spec/plan in `docs/superpowers/`.
- **To activate**: push `main` + `/plugin update bx` (the cache still runs the old slow `/bx:docs` — this very save ran on it).

> Full session detail: [docs/session-history.md](docs/session-history.md) S38
