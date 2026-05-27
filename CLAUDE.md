# CLAUDE.md

Last Updated: 2026-05-26 (Session 34)

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

**`/seo-review` extended for index-coverage diagnostics (S34, 2026-05-26).** User reported declining indexed pages on burakarik.com despite SEO work; two GSC "Validation failed" emails surfaced 838 "Page with redirect" + 663 "Not found (404)" affected URLs sharing an `/article/*` + `/en/article/*` + `/tr/article/*` locale-collision pattern. The skill's impressions-only URL sampling was blind to URLs Google had deindexed (they fall out of `url_impressions_map` → never inspected). Shipped 5-area extension in 10 files (+662/-67 LOC, uncommitted): URL Inspection budget 100 → 200 with new sitemap-orphan slice; sub-dim 14 `deindex_regression` with per-run snapshot persistence + 30-day rotation + path-cluster + git-correlation evidence; sub-dim 5 severity tiering (medium/<50, high/≥50) + locale-prefix-cluster detection; sub-dim 4 ↔ sub-dim 5 cross-link via `co_occurrence_with_sub_dim_5` evidence (the "single i18n migration root cause, two symptoms" diagnosis); `.seo-data/gsc/known-bad-urls.txt` as 4th user-supplied URL source (up to 50/run, takes precedence over sitemap-orphan in shared 100-slot bucket). Burakarik.com diagnosis pending separate session — root cause is incomplete i18n canonical migration in the burakarik.com codebase, NOT in `/seo-review` or anything Claude has done. Phase 4 dogfood backlog now narrows to /test-review, /architecture-review, /code-health-advice.

## Next Steps

1. **Validate S34 extensions on burakarik.com** (separate session, separate repo). Recommended workflow: paste URLs from both GSC failing-validation emails into `.seo-data/gsc/known-bad-urls.txt` (up to 50/run, split across runs to cover full 838 + 663), then `/seo-review` should fire sub-dim 4 + sub-dim 5 with `co_occurrence_with_sub_dim_5` evidence and surface the i18n migration recommendation. Sub-dim 14 won't fire on first run (no prior snapshot); footer notes activation on next run. **Critical reframe:** burakarik.com's decreasing indexed pages is a codebase-level issue (likely incomplete i18n migration around ~4/21/26 inflection); the skill provides diagnostic tooling, not the fix. Actual fix requires investigating burakarik.com's sitemap contents, canonical tags, hreflang config, and recent git history.
2. **Dogfood `/test-review` on a real Node/Jest or Python/pytest project** — built S24 but never invoked end-to-end. Watch for: T01 false-positive rate (project-defined assertion-helper scan should be the gate), twin-headline math correctness on real subagent output, `--coverage` opt-in path against an actual jest `coverage-summary.json` / pytest `coverage.json`, scan-economics ratio thresholds (>3.0 over, <0.1 under), non-overlap with `/code-cleanup`. S30 + S34 dogfood patterns validate value here.
3. **Dogfood `/architecture-review` on a non-trivial real project** — never run end-to-end yet. Watch for linter-detection accuracy, intended-architecture summary quality, CCN-delta filter behavior, simplification false-positive rate. **S30/S34 lesson:** look for similar under-specifications in budget utilization, disk-cache boundaries, parser tool assumptions, blind-spot sampling — the patterns that surfaced in `/seo-review` likely have analogs in any data-ingestion-heavy skill.
4. **Dogfood `/code-health-advice`** — built S22 but never invoked end-to-end. Watch for: bucket misclassification rate, freshness-mismatch detection accuracy, cases where a 6th bucket would help.
5. **Address /seo-review deferred refactors** (captured in /simplify passes S25 + S27 + S29; S34 didn't add new ones — all dogfood-surfaced concerns shipped same-session): batched-Grep alternation across scan-technical/content/geo (biggest runtime win — 30 Greps → 3-6 per scan on real projects); fix-mode harness extraction from architecture-review/references/fix-mode.md; plan-mode scaffolding extraction across the 3 plan-mode-*.md files; cross-file boilerplate consolidation into a shared-rules ref file (~25-40 lines saveable). Best done after further dogfood surfaces which refactor is most needed.
6. **Part 5 session-history rollup deferred** — 4 sessions (S28-S31) eligible for compression to one-liners. Skipped this run to keep S34 update minimal; next `/update-docs` should pick them up.
7. Improve existing skill reference files based on usage patterns.
8. Consider adding hooks for automated pre-commit workflows.
9. Explore MCP server integration for external tool access.

## Key Decisions

| Decision | Rationale |
|----------|-----------|

| `/seo-review` v3.x dogfooded end-to-end on burakarik.com (S30) — 3 same-session fixes + cross-cutting "Ingestion conventions" section | First Phase 4 dogfood surfaced three under-specified areas the spec didn't anticipate: (1) `x-goog-user-project` HTTP header missing from all GSC API calls → 403 SERVICE_DISABLED despite valid auth (Google Cloud APIs called via user-credential ADC require the quota project on every call; commit `835800d`); (2) `jq` dependency for ADC `quota_project_id` extraction (not on PATH in claude-code's Bash on Windows + minimal Linux containers; replaced with `grep -oE` + `sed -E` portable to bash core; commit `bc1170a`); (3) three under-specified ingestion conventions codified into a new cross-cutting "Ingestion conventions" section in SKILL.md (commit `bc35331`): **disk-write boundary** (`.seo-data/gsc/` reserved for user config + skill-auto-generated content only; ephemeral parsing must use `mktemp`-style system temp); **JSON parser fallback chain** (`jq` → `python` → `python3` → bash regex, with Windows `python3` Microsoft-Store-stub caveat); **budget utilization expectation** (URL Inspection 100-URL + sitemap-probe 100-URL caps are ceilings not targets — orchestrator under-utilized at 40/100 + 13/100 in S30 run; spec now requires literal top-N take with no subjective trimming). Real-world value delivered: 40/100 baseline + actionable top-3 priorities including AI-citation evidence (verbatim AI-assistant system prompts in GSC queries — `"do not update memories..."` at 924+223 impressions, confirming ChatGPT/Claude/Perplexity are pulling from the smartphone-vs-mirrorless article). Phase 4 milestone complete; remaining dogfood backlog narrows to /test-review, /architecture-review, /code-health-advice. |

| `/seo-review` GSC API response cache — 24h TTL + `--no-cache` bypass flag (S31) | Motivated by the user's hesitation to consume GSC API quota during iterative `burakarik6` dogfood ("very precious to not consume usage limits of the API"). Wraps `searchanalytics.query` (Q1/Q2/Q3, 3 calls/run) + `urlInspection.index.inspect` (up to 100 calls/run, against the strict 2,000/day quota). Auth probe (sites.list) deliberately NOT cached — it's the live mode-detection check, must stay live. **TTL = 24h, settled via brief design discussion:** matches GSC's own ~2-day finalization lag (same-day reruns can't yield fresher upstream data); no `--cache-ttl <hours>` flag — single default avoids footgun configs (sub-hour defeats the point, week-long hides staleness). **`--no-cache` flag** forces fresh refetch but still writes responses to cache for next run (semantically "force refresh", not "true bypass"). **Cache layout:** `.seo-data/gsc/cache/<prefix>-<sha1-hash>.json`, already covered by existing `.gitignore` sentinel block. Per-Q-call prefixes (`sa-q1`/`sa-q2`/`sa-q3`) + per-URL prefix (`ui-`) so partial cache hits across 100-URL batches are first-class; orchestrator can list ≤5 miss-call-tags in footer when budget is mostly cached. **Wrapper invariants (5):** atomic write via `$CACHE_FILE.tmp.$$` + `mv` on HTTP 200 (no corrupted cache from interrupts); never cache non-200 (caching a 403 would lock the run into broken-auth state for 24h); TTL check via `find -mmin -$TTL_MIN` not `stat` (`stat -c %Y || stat -f %m || echo 0` had silent-cache-miss footgun on claude-code's Bash on Windows where neither flavor matches → same class of bug as S30 `jq`-missing fix); cache dir pre-created in Step 1.6.1 (Turn 1 batch, not per-call `mkdir`); first-stdout-line status marker (`CACHE_STATUS:HIT` or `CACHE_STATUS:MISS http=<code>`) for footer aggregation. **Eviction:** `find .seo-data/gsc/cache -type f -mtime +7 -delete` at Turn 1 (no `-name "*.json"` filter — also catches orphaned `.tmp.$$` files from interrupted runs). **Footer cache stats line** added — quota tracking adjusted so only `cache_misses` count toward 2,000/day. New `references/gsc-cache.md` (~200 lines: TTL policy, key strategy per endpoint, wrapper template, invariants, eviction, footer format). **Disk-write boundary updated** in Ingestion conventions to add `cache/` as a 3rd allowed entry under `.seo-data/gsc/` (alongside `config.yaml` + `README.md`). **`/simplify` pass surfaced 6 fixes, all shipped same-session** (Windows correctness top priority; per-call `mkdir` redundancy; eviction filter cruft; `age=Ns` suffix inconsistency; footer example duplication collapsed by ~15 lines; "exception" → "entry" wording). 6 files touched (1 new + 5 modified). |
| `/seo-review` — 6 spec gaps codified from burakarik6 dogfood (S31 cont.²) | 4th `/seo-review` run of the day on burakarik.com surfaced 6 distinct issues + 1 design problem the orchestrator improvised around at runtime. Categorized 2 critical bugs / 2 spec ambiguities / 1 design issue / 1 emergent capability. All 6 fixes shipped same-session in commit `7109213` (5 files / +474 / -18 LOC). **Fix #1 — UTF-8 enforcement on Python**: Windows charmap default crashes on Turkish + GSC prompt-injection queries (`"do not update memories..."`); codify `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` env vars on every invocation + `encoding='utf-8'` on every `open()`; same class as S30 `jq`-missing fix. **Fix #2 — Same-commit history dedup**: score swung 60→48→40→55 across 4 runs with last commit being docs-only (methodology variance, not codebase change); embed `<!-- commit:abc1234 -->` HTML comment on every `docs/seo-history.md` row; skip append when commit_sha already has an entry; preserves first-run data over picking winners between variant scores. **Fix #3 — Ship `references/gsc-parse-helper.py`** (~250 lines, 6 subcommands `q1`/`q2`/`q3`/`ctr`/`clusters`/`brand`): retires 5+ inline Python heredocs with different bash quoting; one heredoc failed `unexpected EOF` and forced disk-write boundary violation (`_parse_clusters.py` written into `.seo-data/gsc/cache/`); helper script is the canonical parser, no inline Python anywhere. **Fix #4 — New sub-dim 13 `brand_query_anomaly`** (catalog now 12→13 sub-dims): codifies emergent capability — orchestrator caught `"burak arık"` at pos 7.91 / 1.93% CTR as entity-recognition deficit without being told to; 3-tier brand-name resolution (Schema `Person.name` → CLAUDE.md first proper noun → repo name); trigger pos>3 OR ctr<10%; cross-links to `Person.@id` split + `Person.sameAs` Wikidata findings. **Fix #5 — CTR opportunity dual trigger**: original sub-dim 10 excluded pos<5 cases, missing smartphone-vs-mirrorless (59,679 imp / pos 4.65 / 0.28% CTR — THE most actionable finding); added high-volume override (imp>=10000 AND ctr<0.5% regardless of position) with sev=high cert=0.85. **Fix #6 — Probe-skipped redistribution rendering**: 8-pt url_health redistribution math existed in rubric.md but report only said `url_health: 0/0 (probe skipped)` without showing where pts went; "Form A" inline breakdown now mandatory (`url_health: 0/0 (probe skipped, 8pts redistributed: canonicals +2, robots_sitemap +2, ...)`). |

| Renamed custom `/code-review` → `/review-deep` after Anthropic naming collision (S32) | On 2026-05-23 Anthropic renamed built-in `/simplify` → `/code-review`, colliding with the custom code-review skill in this repo. The two skills are genuinely different — built-in is a lightweight diff scan with effort levels + `--comment` PR-comment posting; custom is a senior-engineer review with codebase-convention scanning + `--security` (OWASP) / `--verify` (run tests/lint, parallel-backgrounded since S19) / `--fix` / `--last-commit` modes. Solution: rename the custom skill to `/review-deep` and position the review tooling as a **3-tier ladder**: `/code-review` (built-in, fast, daily driver) → `/review-deep` (custom, thorough) → `/ultrareview` (built-in, cloud, 5+ verifying agents, high-risk pre-merge). Scope expanded from just the custom rename to also updating `/simplify` references throughout operational docs to `/code-review` (since `/simplify` no longer exists by that name) — partial rename would have left dead references. 16 operational files modified + 1 directory rename via `git mv`; historical files (`docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`, plus CLAUDE.md Key Decisions table rows + Last Session blocks from prior sessions) deliberately left untouched as records of past state. README "Three review tiers" blockquote restructured to lead with the rename context + 2026-05-23 date so future readers see why the collision was resolved this way. |

| 5 best-practice improvements from 2026 Claude Code docs audit (S33) | Web research across official Anthropic docs + 2026 community guides surfaced 5 high-leverage improvements, all implemented same-session in commit `5a441d1`: **(1) `${CLAUDE_SKILL_DIR}` substitution** in `/seo-review` for `gsc-parse-helper.py` invocations (CWD-independent + cross-platform — same bug-class as S30 `jq`-missing and S31 cont.² UTF-8-on-Windows). **(2) `effort: high` audit + `ultrathink` injection** — added `effort: high` to `/code-cleanup` (was missing); deliberate `effort: low` retained on `/code-health-advice`, `/resume-work`, `/update-docs` (routing/IO-bound). Added `ultrathink` keyword to the three `--plan` mode reference files. **(3) `description:` / `when_to_use:` split** on 4 verbose skills (`/seo-review` was ~1130 chars, close to the 1,536-char cap; others 500-650). Guards against silent description-truncation. **(4) Dynamic `` !`<cmd>` `` injection** in `/code-health-advice` Step 1 + `/resume-work` Step 2. Saves 1 turn per invocation + eliminates "forgot to batch" failure mode. **(5) SessionStart hook bundle** — `session-start-context.sh` + `.ps1` in `.claude/scripts/` with README install recipe. Eliminates manual `/resume-work` for routine session starts. |

| `/seo-review` S34 extension — sub-dim 14 `deindex_regression` + 200/run URL Inspection + 4-slice URL selection + known-bad-urls.txt (2026-05-26) | Triggered by user's burakarik.com indexed-page decline + two GSC validation-failed emails (838 "Page with redirect" + 663 "Not found (404)" URLs sharing `/article/*` + `/en/article/*` + `/tr/article/*` locale-collision pattern). Existing skill's impressions-only sampling was blind to URLs Google had deindexed (they fall out of `url_impressions_map` → never inspected → user only learns when Google emails). 5-area extension across 10 files (+662/-67, uncommitted): **(1) URL Inspection 100/run → 200/run**, new sitemap-orphan slice (URLs in sitemap but NOT in `url_impressions_map`, **document-order sort** — deterministic for snapshot regression diff; deliberately NOT `<lastmod>` desc since the burakarik6 failure pattern is *stable pages suddenly broken*, not *new pages*). **(2) Sub-dim 14 `deindex_regression`** — **orchestrator-emitted** (not subagent-emitted) from snapshot diff at `.seo-data/gsc/snapshots/<ts>-<sha>.json` (30-day rotation, distinct from cache's 7-day response-cache concern); path-cluster + git-correlation evidence; explicit framing to GSC's "Validation failed" emails in finding title and recommended_action. **(3) Sub-dim 5 severity tiering** medium/<50, high/≥50 (matches sub-dim 2/3 pattern; 838 URLs deserves `high`) + **locale-prefix-cluster detection** (path-prefix grouping when ≥2 locale prefixes each ≥30% of affected count). **(4) Sub-dim 4 ↔ sub-dim 5 cross-link** via `co_occurrence_with_sub_dim_5` evidence when path patterns overlap (the "single i18n migration root cause, two symptoms" diagnosis); git-changed slice now resolves BOTH `old_path` AND `new_path` from rename commits. **(5) `.seo-data/gsc/known-bad-urls.txt`** as 4th user-supplied URL source (up to 50/run, takes precedence over sitemap-orphan in shared 100-slot bucket; dedup precedence: impressions > git > user-supplied > sitemap-orphan; closes the gap for URLs Google still remembers but the codebase no longer serves — e.g., 404'd content older than git's 35-day window). `gsc-parse-helper.py` extended with `snapshot-write` + `regression` subcommands (UTF-8 preserved, atomic write via `.tmp` + `os.replace`). `score_impact:0` invariant maintained on all GSC findings — /100 score stays comparable across runs. **Burakarik.com's indexing decline itself is a codebase-level issue** (incomplete i18n canonical migration around ~4/21/26 inflection) — NOT caused by anything in the skill or by Claude; the S34 changes provide diagnostic infrastructure, not the fix. |

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
│   └── skills/              # Skills (SKILL.md + references/)
│       ├── architecture-review/
│       ├── code-cleanup/
│       ├── code-health-advice/
│       ├── plan-feature/
│       ├── resume-work/
│       ├── review-deep/
│       ├── seo-review/
│       ├── test-review/
│       └── update-docs/
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

### Last Session (Session 34) - 2026-05-26
- **`/seo-review` extended for index-coverage regression detection.** User reported declining indexed pages on burakarik.com despite ongoing SEO work; two GSC "Validation failed" emails (838 "Page with redirect" + 663 "Not found (404)") surfaced an `/article/*` + `/en/article/*` + `/tr/article/*` locale-collision pattern. Skill's impressions-only URL sampling was blind to URLs Google had deindexed.
- **5-area extension shipped (11 files modified, uncommitted):** URL Inspection budget 100 → 200 with new sitemap-orphan slice (document-order sort, deterministic for snapshot diff); sub-dim 14 `deindex_regression` orchestrator-emitted from per-run snapshot diff at `.seo-data/gsc/snapshots/` (30-day rotation, path-cluster + git-correlation evidence); sub-dim 5 severity tiering (medium/<50, high/≥50) + locale-prefix-cluster detection; sub-dim 4 ↔ sub-dim 5 `co_occurrence_with_sub_dim_5` cross-link evidence; new `.seo-data/gsc/known-bad-urls.txt` user-supplied URL source (4th slice, up to 50/run).
- **S34 cont. — API-limitation reframe in docs.** User feedback ("Doesn't the API return these reports?") surfaced that earlier docs over-emphasized `known-bad-urls.txt` as primary workflow. **The Search Console API does NOT expose the Page Indexing report** (no `pageIndexing.list` endpoint — Google product decision, not a skill limitation). `urlInspection.index.inspect` requires URL input. Rewrote `gsc-setup-readme-template.md` + `gsc-api-queries.md` to lead with the API limitation, position the file as **fallback for the gap** (not primary), and add "skill discovers reason per-URL via `coverageState` response, clusters into sub-dims 2-9 automatically — flat URL list, no tagging needed" clarification.
- **Critical reframe + validation path:** the indexed-page decline on burakarik.com is a **codebase-level issue** (likely incomplete i18n migration around ~4/21/26 inflection) — NOT caused by anything Claude has done. Skill = diagnostic infrastructure, not the fix. **Next session workflow:** run `/seo-review` on burakarik.com first; the sitemap-orphan slice catches "Page with redirect" URLs (in sitemap) automatically. If specific 404 URLs from GSC emails don't appear in the first run's inspected set, paste those (top 50 by Last crawled desc) into `known-bad-urls.txt` for run #2. User already curated a 50-URL file (404-only, redirects dropped per recommendation since sitemap-orphan covers them).
- **Part 5 session-history rollup deferred** — 5 sessions (S28-S31 + S31 cont.) eligible for compression to one-liners. Skipped this run; next `/update-docs` should pick them up FIRST before other work.

> Full session detail: [docs/session-history.md](docs/session-history.md) S34 + S34 cont.
