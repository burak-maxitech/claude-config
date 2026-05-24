# CLAUDE.md

Last Updated: 2026-05-23 (Session 33)

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

**`/seo-review` v3.x — Search Console API integration shipped (S29) + dogfooded end-to-end (S30, Phase 4 milestone complete).** S29 built v3 BigQuery + 4-state hybrid, then simplified same-session to API-only via Search Console after user flagged complexity. S30 ran the first real-world dogfood on `sc-domain:burakarik.com` (verified GSC property) and surfaced **3 same-session fixes**: (1) missing `x-goog-user-project` HTTP header → 403 SERVICE_DISABLED despite valid auth (commit `835800d`); (2) `jq` not on PATH in claude-code's Bash on Windows → silent extraction failure → empty `$QUOTA_PROJECT` → same 403, switched to bash-core `grep -oE` + `sed -E` (commit `bc1170a`); (3) three under-specified ingestion conventions codified into a new cross-cutting "Ingestion conventions" section in SKILL.md — disk-write boundary, JSON parser fallback chain, budget utilization expectation (commit `bc35331`). Real-world value delivered: 40/100 baseline score on burakarik.com + top-3 priorities including AI-citation evidence in GSC queries (verbatim AI-assistant system prompts leaking into search analytics). Score `/100` invariant preserved via `score_impact:0`. Phase 4 dogfood backlog narrows to `/test-review`, `/architecture-review`, `/code-health-advice`. Full detail in Key Decisions table + docs/session-history.md S30.

## Next Steps

1. **Dogfood `/test-review` on a real Node/Jest or Python/pytest project** — built S24 but never invoked end-to-end. Watch for: T01 false-positive rate (project-defined assertion-helper scan should be the gate), twin-headline math correctness on real subagent output (subtotal-check line should reconcile), `--coverage` opt-in path against an actual jest `coverage-summary.json` / pytest `coverage.json`, scan-economics ratio thresholds (>3.0 over, <0.1 under) on a real module structure, non-overlap with `/code-cleanup` (no orphans/skips/helpers/snapshots surfaced). S30 dogfood of `/seo-review` proved this pattern delivers value — expect the same here.
2. **Dogfood `/architecture-review` on a non-trivial real project** — never run end-to-end yet. Watch for linter-detection accuracy, intended-architecture summary quality, CCN-delta filter behavior, simplification false-positive rate. **S30 lesson:** look for similar under-specifications in budget utilization, disk-cache boundaries, parser tool assumptions — the patterns that surfaced in `/seo-review` likely have analogs in any data-ingestion-heavy skill.
3. **Dogfood `/code-health-advice`** — built S22 but never invoked end-to-end. Watch for: bucket misclassification rate, freshness-mismatch detection accuracy, cases where a 6th bucket would help.
4. **Address /seo-review deferred refactors** (captured in /simplify passes S25 + S27 + S29, not blocking; S30 dogfood didn't surface new ones — all 3 dogfood-surfaced concerns shipped same-session): batched-Grep alternation across scan-technical/content/geo (biggest runtime win — 30 Greps → 3-6 per scan on real projects); fix-mode harness extraction from architecture-review/references/fix-mode.md; plan-mode scaffolding extraction across the 3 plan-mode-*.md files; cross-file boilerplate consolidation into a shared-rules ref file (~25-40 lines saveable). Best done after further dogfood surfaces which refactor is most needed.
5. **Optional: `/seo-review --plan` or `--fix` follow-up on burakarik6** (separate project, not claude-config) — S30 audit gave 40/100 baseline + actionable top-3 priorities; biggest single recovery is the smartphone-vs-mirrorless title rewrite in Sanity (~4-5K clicks/quarter potential). User's call whether to act on the audit or queue it.
6. Improve existing skill reference files based on usage patterns.
7. Consider adding hooks for automated pre-commit workflows.
8. Explore MCP server integration for external tool access.

## Key Decisions

| Decision | Rationale |
|----------|-----------|

| `/seo-review` v3.x dogfooded end-to-end on burakarik.com (S30) — 3 same-session fixes + cross-cutting "Ingestion conventions" section | First Phase 4 dogfood surfaced three under-specified areas the spec didn't anticipate: (1) `x-goog-user-project` HTTP header missing from all GSC API calls → 403 SERVICE_DISABLED despite valid auth (Google Cloud APIs called via user-credential ADC require the quota project on every call; commit `835800d`); (2) `jq` dependency for ADC `quota_project_id` extraction (not on PATH in claude-code's Bash on Windows + minimal Linux containers; replaced with `grep -oE` + `sed -E` portable to bash core; commit `bc1170a`); (3) three under-specified ingestion conventions codified into a new cross-cutting "Ingestion conventions" section in SKILL.md (commit `bc35331`): **disk-write boundary** (`.seo-data/gsc/` reserved for user config + skill-auto-generated content only; ephemeral parsing must use `mktemp`-style system temp); **JSON parser fallback chain** (`jq` → `python` → `python3` → bash regex, with Windows `python3` Microsoft-Store-stub caveat); **budget utilization expectation** (URL Inspection 100-URL + sitemap-probe 100-URL caps are ceilings not targets — orchestrator under-utilized at 40/100 + 13/100 in S30 run; spec now requires literal top-N take with no subjective trimming). Real-world value delivered: 40/100 baseline + actionable top-3 priorities including AI-citation evidence (verbatim AI-assistant system prompts in GSC queries — `"do not update memories..."` at 924+223 impressions, confirming ChatGPT/Claude/Perplexity are pulling from the smartphone-vs-mirrorless article). Phase 4 milestone complete; remaining dogfood backlog narrows to /test-review, /architecture-review, /code-health-advice. |

| `/seo-review` GSC API response cache — 24h TTL + `--no-cache` bypass flag (S31) | Motivated by the user's hesitation to consume GSC API quota during iterative `burakarik6` dogfood ("very precious to not consume usage limits of the API"). Wraps `searchanalytics.query` (Q1/Q2/Q3, 3 calls/run) + `urlInspection.index.inspect` (up to 100 calls/run, against the strict 2,000/day quota). Auth probe (sites.list) deliberately NOT cached — it's the live mode-detection check, must stay live. **TTL = 24h, settled via brief design discussion:** matches GSC's own ~2-day finalization lag (same-day reruns can't yield fresher upstream data); no `--cache-ttl <hours>` flag — single default avoids footgun configs (sub-hour defeats the point, week-long hides staleness). **`--no-cache` flag** forces fresh refetch but still writes responses to cache for next run (semantically "force refresh", not "true bypass"). **Cache layout:** `.seo-data/gsc/cache/<prefix>-<sha1-hash>.json`, already covered by existing `.gitignore` sentinel block. Per-Q-call prefixes (`sa-q1`/`sa-q2`/`sa-q3`) + per-URL prefix (`ui-`) so partial cache hits across 100-URL batches are first-class; orchestrator can list ≤5 miss-call-tags in footer when budget is mostly cached. **Wrapper invariants (5):** atomic write via `$CACHE_FILE.tmp.$$` + `mv` on HTTP 200 (no corrupted cache from interrupts); never cache non-200 (caching a 403 would lock the run into broken-auth state for 24h); TTL check via `find -mmin -$TTL_MIN` not `stat` (`stat -c %Y || stat -f %m || echo 0` had silent-cache-miss footgun on claude-code's Bash on Windows where neither flavor matches → same class of bug as S30 `jq`-missing fix); cache dir pre-created in Step 1.6.1 (Turn 1 batch, not per-call `mkdir`); first-stdout-line status marker (`CACHE_STATUS:HIT` or `CACHE_STATUS:MISS http=<code>`) for footer aggregation. **Eviction:** `find .seo-data/gsc/cache -type f -mtime +7 -delete` at Turn 1 (no `-name "*.json"` filter — also catches orphaned `.tmp.$$` files from interrupted runs). **Footer cache stats line** added — quota tracking adjusted so only `cache_misses` count toward 2,000/day. New `references/gsc-cache.md` (~200 lines: TTL policy, key strategy per endpoint, wrapper template, invariants, eviction, footer format). **Disk-write boundary updated** in Ingestion conventions to add `cache/` as a 3rd allowed entry under `.seo-data/gsc/` (alongside `config.yaml` + `README.md`). **`/simplify` pass surfaced 6 fixes, all shipped same-session** (Windows correctness top priority; per-call `mkdir` redundancy; eviction filter cruft; `age=Ns` suffix inconsistency; footer example duplication collapsed by ~15 lines; "exception" → "entry" wording). 6 files touched (1 new + 5 modified). |
| `/seo-review` — 6 spec gaps codified from burakarik6 dogfood (S31 cont.²) | 4th `/seo-review` run of the day on burakarik.com surfaced 6 distinct issues + 1 design problem the orchestrator improvised around at runtime. Categorized 2 critical bugs / 2 spec ambiguities / 1 design issue / 1 emergent capability. All 6 fixes shipped same-session in commit `7109213` (5 files / +474 / -18 LOC). **Fix #1 — UTF-8 enforcement on Python**: Windows charmap default crashes on Turkish + GSC prompt-injection queries (`"do not update memories..."`); codify `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` env vars on every invocation + `encoding='utf-8'` on every `open()`; same class as S30 `jq`-missing fix. **Fix #2 — Same-commit history dedup**: score swung 60→48→40→55 across 4 runs with last commit being docs-only (methodology variance, not codebase change); embed `<!-- commit:abc1234 -->` HTML comment on every `docs/seo-history.md` row; skip append when commit_sha already has an entry; preserves first-run data over picking winners between variant scores. **Fix #3 — Ship `references/gsc-parse-helper.py`** (~250 lines, 6 subcommands `q1`/`q2`/`q3`/`ctr`/`clusters`/`brand`): retires 5+ inline Python heredocs with different bash quoting; one heredoc failed `unexpected EOF` and forced disk-write boundary violation (`_parse_clusters.py` written into `.seo-data/gsc/cache/`); helper script is the canonical parser, no inline Python anywhere. **Fix #4 — New sub-dim 13 `brand_query_anomaly`** (catalog now 12→13 sub-dims): codifies emergent capability — orchestrator caught `"burak arık"` at pos 7.91 / 1.93% CTR as entity-recognition deficit without being told to; 3-tier brand-name resolution (Schema `Person.name` → CLAUDE.md first proper noun → repo name); trigger pos>3 OR ctr<10%; cross-links to `Person.@id` split + `Person.sameAs` Wikidata findings. **Fix #5 — CTR opportunity dual trigger**: original sub-dim 10 excluded pos<5 cases, missing smartphone-vs-mirrorless (59,679 imp / pos 4.65 / 0.28% CTR — THE most actionable finding); added high-volume override (imp>=10000 AND ctr<0.5% regardless of position) with sev=high cert=0.85. **Fix #6 — Probe-skipped redistribution rendering**: 8-pt url_health redistribution math existed in rubric.md but report only said `url_health: 0/0 (probe skipped)` without showing where pts went; "Form A" inline breakdown now mandatory (`url_health: 0/0 (probe skipped, 8pts redistributed: canonicals +2, robots_sitemap +2, ...)`). |

| Renamed custom `/code-review` → `/review-deep` after Anthropic naming collision (S32) | On 2026-05-23 Anthropic renamed built-in `/simplify` → `/code-review`, colliding with the custom code-review skill in this repo. The two skills are genuinely different — built-in is a lightweight diff scan with effort levels + `--comment` PR-comment posting; custom is a senior-engineer review with codebase-convention scanning + `--security` (OWASP) / `--verify` (run tests/lint, parallel-backgrounded since S19) / `--fix` / `--last-commit` modes. Solution: rename the custom skill to `/review-deep` and position the review tooling as a **3-tier ladder**: `/code-review` (built-in, fast, daily driver) → `/review-deep` (custom, thorough) → `/ultrareview` (built-in, cloud, 5+ verifying agents, high-risk pre-merge). Scope expanded from just the custom rename to also updating `/simplify` references throughout operational docs to `/code-review` (since `/simplify` no longer exists by that name) — partial rename would have left dead references. 16 operational files modified + 1 directory rename via `git mv`; historical files (`docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`, plus CLAUDE.md Key Decisions table rows + Last Session blocks from prior sessions) deliberately left untouched as records of past state. README "Three review tiers" blockquote restructured to lead with the rename context + 2026-05-23 date so future readers see why the collision was resolved this way. |

| 5 best-practice improvements from 2026 Claude Code docs audit (S33) | Web research across official Anthropic docs + 2026 community guides surfaced 5 high-leverage improvements, all implemented same-session in commit (pending): **(1) `${CLAUDE_SKILL_DIR}` substitution** in `/seo-review` for `gsc-parse-helper.py` invocations (replaces a custom `$SKILL_REF_DIR` var that required orchestrator-side path resolution per run; the official substitution is CWD-independent and cross-platform — same bug-class as S30 `jq`-missing and S31 cont.² UTF-8-on-Windows). **(2) `effort: high` audit + `ultrathink` injection** — added `effort: high` to `/code-cleanup` (was missing); deliberate `effort: low` retained on `/code-health-advice`, `/resume-work`, `/update-docs` (routing/IO-bound). Added literal `ultrathink` keyword to the three `--plan` mode reference files (`architecture-review/references/plan-mode.md`, `test-review/references/plan-mode-test.md`, `seo-review/references/plan-mode-seo.md`) since phased-brief synthesis is the textbook deep-reasoning use case. **(3) `description:` / `when_to_use:` split** on 4 verbose skills (`/seo-review` was ~1130 chars in a single description — close to the 1,536-char combined cap; `/architecture-review`, `/test-review`, `/review-deep` were 500-650 chars). Now each leads with verb + 200-char description and pushes tier-positioning + trigger phrases to `when_to_use:`. Guards against silent description-truncation as skill count grows (skill listing budget defaults to 1% of context window per `skillListingBudgetFraction`; lowest-priority descriptions drop first on overflow). **(4) Dynamic `` !`<cmd>` `` injection** in `/code-health-advice` (entire Step 1 rewritten as pre-injected git/CLAUDE.md/web-signal snapshots; eliminates the 1-turn batch the skill previously instructed Claude to run) and `/resume-work` Step 2 (4 git commands pre-injected; Step 1 doc reads stay explicit because they're conditional on file existence). Saves 1 turn per invocation + eliminates "forgot to batch" failure mode. Aligns with `Next Steps #4` deferred-refactor item ("batched-Grep alternation across scan-technical/content/geo (biggest runtime win)"). **(5) SessionStart hook bundle** — portable `session-start-context.sh` + `.ps1` shipped in `.claude/scripts/` with full README install recipe (per-project + global). Emits branch/uncommitted-count/last-commit-age + 5 recent commits + CLAUDE.md Current Status + stale-doc warning + open-PR. Eliminates manual `/resume-work` for routine session starts; explicit `/resume-work` still works for deep orientation + task hydration. Sources: [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices), [Skills docs](https://code.claude.com/docs/en/skills), [Hooks guide](https://code.claude.com/docs/en/hooks-guide), [Subagents 2026](https://www.tembo.io/blog/claude-code-subagents). |

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
│   │   ├── seo-technical.md
│   │   ├── test-coverage.md
│   │   ├── test-economics.md
│   │   └── test-quality.md
│   ├── scripts/             # Session startup scripts
│   │   ├── start-claude.sh          # Mac/Linux
│   │   └── start-claude.ps1        # Windows (PowerShell)
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

### Last Session (Session 33) - 2026-05-23
- **5 best-practice improvements from 2026 docs audit shipped same-session.** User asked for top improvement opportunities based on current Claude Code best practices. Web research across official Anthropic docs + community 2026 writeups surfaced 5 high-leverage items, all implemented before the next /update-docs sweep. Touches 11 modified files + 2 new scripts.
- **Fixes #1-5:** (1) `${CLAUDE_SKILL_DIR}` substitution in `/seo-review` for `gsc-parse-helper.py` invocations (CWD-independent); (2) `effort: high` added to `/code-cleanup` (was missing) + `ultrathink` keyword injected into the 3 `--plan` mode reference files; (3) `description:` / `when_to_use:` split on 4 verbose skills (`/seo-review` was approaching the 1,536-char combined cap); (4) Dynamic `` !`<cmd>` `` shell-injection rewriting `/code-health-advice` Step 1 fully + `/resume-work` Step 2 git commands (saves 1 turn per invocation); (5) SessionStart hook bundle (`session-start-context.sh` + `.ps1` in `.claude/scripts/`) with README install recipe (per-project + global).
- **Earlier in same calendar day: Session 32 rename refactor committed (e38951a).** Custom `/code-review` → `/review-deep` after Anthropic renamed built-in `/simplify` → `/code-review`. 3-tier review ladder now: `/code-review` (built-in, fast) → `/review-deep` (custom, thorough) → `/ultrareview` (cloud, pre-merge). See Key Decisions row + S32 entry in `docs/session-history.md` for full detail.

> Full session detail: [docs/session-history.md](docs/session-history.md) S32 + S33
