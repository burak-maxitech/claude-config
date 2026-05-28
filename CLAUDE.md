# CLAUDE.md

Last Updated: 2026-05-28 (Session 36)

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
| Subagents (13) | Complete |
| Startup scripts | Complete |
| Cross-platform setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 9 skills, 13 subagents, cross-platform setup, and documentation system are complete.

See [docs/completed-work.md](docs/completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

None — working tree clean at the start of this rename work. Next session picks up the validation/dogfood backlog from Next Steps (now #1: validate the SEO skill, now `/bx-seo`, on a real burakarik.com run).

## Next Steps

1. **Validate S35 on a real burakarik.com run.** Infrastructure now backs the S34 validation step: 100 user-supplied URL cap (was 50), helper-driven Turn 2b dispatch, split TTL (ui-* 7d means S34 cache entries now hit), finding-history infrastructure ready to track all current findings as run_count=1. Sub-dim 14 will fire since S34 wrote the baseline snapshot. Skip-mode (`dispatch_mode == "skip_codebase_subagents"`) likely fires on subsequent same-property reruns if no code commits intervene.
2. **Dogfood `/bx-tests` on a real Node/Jest or Python/pytest project** — built S24 but never invoked end-to-end. Watch for: T01 false-positive rate (project-defined assertion-helper scan should be the gate), twin-headline math correctness on real subagent output, `--coverage` opt-in path against an actual jest `coverage-summary.json` / pytest `coverage.json`, scan-economics ratio thresholds (>3.0 over, <0.1 under), non-overlap with `/bx-clean`. S30 + S34 + S35 dogfood patterns validate value here.
3. **Dogfood `/bx-arch` on a non-trivial real project** — never run end-to-end yet. Watch for linter-detection accuracy, intended-architecture summary quality, CCN-delta filter behavior, simplification false-positive rate. **S30/S34/S35 lesson:** look for similar under-specifications in budget utilization, disk-cache boundaries, parser tool assumptions, blind-spot sampling — the patterns that surfaced in `/bx-seo` likely have analogs in any data-ingestion-heavy skill.
4. **Dogfood `/bx-health`** — built S22 but never invoked end-to-end. Watch for: bucket misclassification rate, freshness-mismatch detection accuracy, cases where a 6th bucket would help.
5. **Address `/bx-seo` deferred refactors** (captured in `/simplify` passes S25 + S27 + S29; S34/S35 didn't add new ones — all dogfood-surfaced concerns shipped same-session): batched-Grep alternation across scan-technical/content/geo (biggest runtime win — 30 Greps → 3-6 per scan on real projects); fix-mode harness extraction from bx-arch/references/fix-mode.md; plan-mode scaffolding extraction across the 3 plan-mode-*.md files; cross-file boilerplate consolidation into a shared-rules ref file (~25-40 lines saveable). Best done after further dogfood surfaces which refactor is most needed.
6. Improve existing skill reference files based on usage patterns.
7. Consider adding hooks for automated pre-commit workflows.
8. Explore MCP server integration for external tool access.

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

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
claude-config/
├── .claude/
│   ├── agents/              # Subagent definitions (Sonnet-routed)
│   │   ├── arch-performance.md
│   │   ├── arch-refactors.md
│   │   ├── arch-simplification.md
│   │   ├── arch-structure.md
│   │   ├── cleanup-deps-config.md
│   │   ├── cleanup-files-code.md
│   │   ├── cleanup-styles-tests.md
│   │   ├── geo-generative.md
│   │   ├── seo-content.md
│   │   ├── seo-gsc-insights.md
│   │   ├── seo-technical.md
│   │   ├── test-coverage.md
│   │   ├── test-economics.md
│   │   └── test-quality.md
│   ├── scripts/             # Session startup scripts
│   │   ├── session-start-context.sh    # SessionStart hook (Bash/Mac/Linux)
│   │   ├── session-start-context.ps1   # SessionStart hook (Windows)
│   │   ├── start-claude.sh             # Mac/Linux launcher
│   │   └── start-claude.ps1            # Windows (PowerShell) launcher
│   ├── settings.local.json  # Shared Claude Code settings
│   └── skills/              # Skills (SKILL.md + references/) — all under `bx-` prefix (S36, see Key Decisions)
│       ├── bx-arch/         # was architecture-review
│       ├── bx-clean/        # was code-cleanup
│       ├── bx-docs/         # was update-docs
│       ├── bx-health/       # was code-health-advice
│       ├── bx-plan/         # was plan-feature
│       ├── bx-resume/       # was resume-work
│       ├── bx-review/       # was review-deep
│       ├── bx-seo/          # was seo-review
│       └── bx-tests/        # was test-review
├── docs/                    # Reference files (overflow from CLAUDE.md)
│   ├── completed-work.md
│   ├── key-decisions.md
│   └── session-history.md
├── .gitignore
├── CLAUDE.md                # This file — AI session context
├── README.md                # Public overview
└── Workflow.md              # Personal workflow guide
```

**Symlink approach:** Only `.claude/skills/` and `.claude/agents/` are symlinked into `~/.claude/` on each machine. This preserves local credentials and settings while sharing skills and agents across machines via Git.

**Skills** are directories containing `SKILL.md` (main logic with YAML frontmatter) and a `references/` folder with supporting documents. They are user-invocable via `/skill-name`.

**Subagents** are markdown files in `.claude/agents/` dispatched by skills (not user-invocable). They run on Sonnet for cost efficiency and have scoped tool permissions.

## Known Issues / Blockers

None currently.

## Environment Variables

None required. This is a pure configuration repo — no runtime dependencies or secrets.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 36) - 2026-05-28
- **Renamed all 9 custom skills under the `bx-` prefix** — `bx-review`, `bx-arch`, `bx-tests`, `bx-seo`, `bx-clean`, `bx-health`, `bx-plan`, `bx-resume`, `bx-docs`. Root-cause fix for recurring name collisions/confusion with built-ins. `git mv` + token-sweep across 76 files via `find -exec perl` (the system `grep` is **ugrep** where `-Z`≠null-delimit, which silently broke two `xargs -0` attempts first). Commit `c5e654a`.
- **Plugin overlap analysis** of 4 newly-installed plugins (superpowers, code-simplifier, playwright, claude-code-setup). **Uninstalled `code-simplifier`** (redundant with built-in `/simplify` + the `arch-simplification` subagent; JS/React-tuned, irrelevant here).
- **Review-tooling freshness fixes** (commit `385c248`): `/ultrareview` → `/code-review ultra` (deprecated alias) everywhere; reinstated built-in `/simplify` re-added to the review ladder + Bucket A routing — corrects S32's now-stale "/simplify gone" premise.
- **Phase-0 doc reconcile** (commit `a60c006`): S35 was already committed (`548bdee`); fixed the stale "uncommitted" note, resynced MEMORY.md to 9 skills / 13 subagents, rolled up S32 in session-history.
- **Heads-up:** `superpowers` ships an aggressive every-session skill-mandate SessionStart hook — flagged, left enabled (it defers to CLAUDE.md). Disable if it fights quick edits.

> Full session detail: [docs/session-history.md](docs/session-history.md) S36
