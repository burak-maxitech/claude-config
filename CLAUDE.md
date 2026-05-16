# CLAUDE.md

Last Updated: 2026-05-15 (Session 31 cont.²)

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
│       ├── code-review/
│       ├── plan-feature/
│       ├── resume-work/
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

### Last Session (Session 31 cont.²) - 2026-05-15
- **`/seo-review` GSC API response cache shipped (24h TTL + `--no-cache` flag).** Wraps Search Analytics (Q1/Q2/Q3) + URL Inspection (≤100/run); auth probe NOT cached. Motivated by user hesitation to consume GSC quota on iterative `burakarik6` dogfood. `/simplify` pass surfaced 6 fixes shipped same-session (priority: Windows correctness `stat` chain → `find -mmin`). Commit `87e2edf`.
- **`/update-docs` Part 7 — Size-Pressure Rollup shipped + dogfooded same-session.** Closes 3 design gaps that left `burakarik6` CLAUDE.md at 47k (rollups trigger on row count not size; Architecture Summary has no enforcement; In Progress/Next Steps caps are warn-only). Part 7 fires after Parts 5/6 with section-by-section size diagnostic + 6 section-specific shrinkers + per-section consent gate. First dogfood (this CLAUDE.md): **40,030 → ~14,000 chars (~65% reduction)** — Key Decisions shrunk 27k → 4.7k (17 oldest rows moved to `docs/key-decisions.md`); Last Session block 5.5k → 2.2k (7 bullets → top 3). Commit `5fba06a`.
- **2nd burakarik6 dogfood: 6 spec gaps caught + fixed same-session.** User ran `/seo-review --no-cache` on burakarik.com (4th `/seo-review` of the day). Surfaced 6 distinct issues categorized as 2 critical bugs / 2 spec ambiguities / 1 design problem / 1 emergent capability. All 6 shipped in commit `7109213` (5 files / +474/-18): UTF-8 enforcement on Python (Windows charmap crash on Turkish + prompt-injection queries); same-commit history dedup (score swung 60→48→40→55 across 4 runs with last commit docs-only — pure methodology variance); new `references/gsc-parse-helper.py` (retires 5+ inline Python heredocs + disk-write boundary violation); new sub-dim 13 `brand_query_anomaly` (codifies emergent capability — orchestrator caught `"burak arık"` at pos 7.91 / 1.93% CTR); CTR opportunity dual trigger (high-volume override catches smartphone article at pos 4.65); probe-skipped rendering Form A inline breakdown.

> Full session detail: [docs/session-history.md](docs/session-history.md) S31 + S31 cont. + S31 cont.²
