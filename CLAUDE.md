# CLAUDE.md

Last Updated: 2026-07-30 (Session 53)

## Project Overview

**claude-config** — Personal Claude Code configuration repo containing custom skills, subagents, and workflow documentation.

- **Repo:** [burak-maxitech/claude-config](https://github.com/burak-maxitech/claude-config) (public — went public S49 for easier teammate plugin install)
- **README.md** — Public overview, setup instructions, command reference
- **Workflow.md** — Detailed personal workflow guide (daily workflow, scenarios, tips)
- **docs/** — Reference files (session history, key decisions, completed work)

## Current Status

| Area | Status |
|------|--------|
| Skills (11) | Complete |
| Subagents (18) | Complete |
| Plugin packaging (`bx`) | Core complete (S37) — pending install smoke-test + symlink retirement |
| Startup scripts | Complete |
| Cross-platform setup | Complete |
| GitHub sync | Complete |
| Documentation | Complete |

## Completed

All 11 skills, 18 subagents, cross-platform setup, and documentation system are complete.

See [docs/completed-work.md](docs/completed-work.md) for full checklist.

**`/seo-review` hardened across 4 improvement groups + 15 code-review fixes (S35, 2026-05-26).** Same-day continuation of S34 burakarik.com dogfood. User ran the skill with new `known-bad-urls.txt`; orchestrator wrote a 396-line `_inspect_batch.py` into `.seo-data/gsc/` (third disk-write boundary violation across S31 cont.² + S34 + S35) + only inspected 50 of 100 pasted URLs. Shipped 4 groups + ran `/code-review` extra-high effort surfacing 15 findings, then fixed all 15 same-session (+1105/-71 LOC across 7 files, uncommitted). **Group A:** new `inspect-batch` helper subcommand (parallel HTTP via ThreadPoolExecutor + per-URL cache + atomic write + 429/5xx retry); broader disk-write boundary rule forbidding ALL orchestrator-written scripts under `.seo-data/gsc/`. **Group B:** subagent-skip rule codified (new Step 4.5) with 4 gating conditions + audit-trail marking + `--force-dispatch` escape hatch. **Group C:** cache TTL split — sa-* stays 24h, ui-* becomes 7d (coverageState is weeks-stable; fixes the 0/197 cache-hit problem from S34). **Group D:** finding lifecycle infrastructure — `finding-history.json` (run_count tracker with same-commit guard + ESCALATE marker at run_count>=3) + `watchpoints.json` (auto-emitted on `code_changed_since_gsc_window=true` + 21-day recheck + 90-day evict). Three new helper subcommands. **Top correctness fixes:** `head -1 sa-q2-*.json` race → deterministic hash recomputation; DST off-by-one via `time.mktime` → `datetime.date.fromisoformat()`; null-metric TypeError; operator precedence in `classify_transition`; bare `.tmp` race → PID suffix; 20-worker rate-limit burst → 6 workers + retries.

## In Progress

**`/bx:webdesign` first dogfood + third hardening pass (S52), pending re-run.** The 10th skill had its **first real end-to-end run** (on `kaanarik`): the whole pipeline ran — setup → detection → branch → inventory → before-shots → Stitch seeding → direction interview → quota pre-flight → 3-screen generation → mandatory review → palette iteration — and **paused cleanly at `review_pending`** on `webdesign/2026-07-23`, **no app code touched**. The safety architecture held; every failure was in the delegation surface (Google's skills + Stitch platform + Windows env). The run surfaced **15 findings, all applied S52** across 7 files: `stitch::`→`stitch-design:` naming; latent Phase-3 clean-tree traps (`.gitignore` now committed, `.playwright-mcp/` gitignored); Tailwind-v4 detection + `@theme` merge; setup-doc rewrite; Stitch platform gotchas + lossy-palette "verify-one-then-batch" pass. Then self-reviewed the fixes: `/bx:review` caught 2 more (`allowed-tools` `mv`/`cp`; a 2.1a↔2.2 double-generation) and a 4-agent `/simplify` pass applied 11 dedup/altitude refinements (incl. the missed Phase-3 after-shot site and a Step-4 self-contradiction). Earlier hardening: S42 (16) + S48 (13/12, `9b9c703`). **The 15-fix batch is pushed (`62d3461`); the review+simplify fixes land in the S52 re-save — `/plugin update bx` to pick everything up.** Kickoff prompt: `docs/webdesign-first-run-prompt.md`; dogfood checklist: `docs/superpowers/plans/2026-06-06-bx-webdesign-dogfood.md`.

**S37 plugin packaging — remaining:** install smoke-test, retire `~/.claude` symlinks, `settings.local.json` `Skill(bx-*)` → `Skill(bx:*)`, launcher-script symlink-check retirement. (GSC MCP migration #1 declined; Playwright #2 deferred.)

## Next Steps

1. **Commit + push the S53 `/bx:review` fixes**, then `/plugin update bx` + `/reload-plugins` — 5 files uncommitted (`bx/skills/review/SKILL.md`, `bx/skills/review/references/output-format.md`, `README.md`, `workflow.md`, `docs/upstream/state.json`).
2. **`/bx:evolve` follow-ups** — **add the `checkpointing` and `code-review` doc pages to `scan-docs.md`'s allowlist (9 → 11)**: S53 proved the gap, with orchestrator direct-fetches of those two pages producing 5 of 7 findings including the only factually-wrong one (2nd consecutive run the S50 allowlist-completeness rule fired). Then run a **full** `/bx:evolve` — the watermark is frozen at 2.1.217 by S53's scoped run, so releases 2.1.218–2.1.220 are unaudited for the other 10 skills. Also still pending: smoke-check open finding `093df977` (v2.1.214 fail-closed FD-redirects vs bx's pervasive `2>/dev/null`) together with the `CLAUDE_ENV_FILE` UTF-8 check; give the skill the S42 content-review treatment; act on the 14 `open` findings (top: `.claude/skills` / `@skills-dir` auto-load, 4 sources converging); v2 ideas: re-arm carried-forward findings for `--fix` from state, treat lane digest one-liners as non-citation-grade.
3. **Smoke-test `/loop /bx:review`** — S53 added a *hedged* caveat to `workflow.md` because Anthropic documents `disable-model-invocation` commands being read as plain text when used as a **scheduled task's** prompt, and every bx skill sets that flag. `/loop` and `/schedule` are different mechanisms, so this is unverified. Confirm, then replace the hedge with a definitive statement (or drop the examples).
4. **Design session: a verification pass for `/bx:review`** — S53 finding `d1480670` applied only its cheap half (output-format Rule 8, the "verification bar"). The skill is still single-pass with no independent false-positive filter, while running at `effort: high`, which Anthropic documents as casting a wider net. Anthropic's own reviewer runs parallel agents *plus* a verification step. Needs brainstorm → spec → skill-creator eval, not a `--fix` bolt-on.
5. **Resume the `/bx:webdesign` kaanarik run past review** — refresh the plugin cache, re-run `/bx:webdesign` (resumes at `review_pending`), push through **Phase 3 inject+verify** to exercise the latent fixes the paused first run never reached (Tailwind-v4 `@theme` merge, `.gitignore`/`.playwright-mcp` clean-tree guards). Stitch MCP + `stitch-skills` already installed in the target repo.
6. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45.
7. **Dogfood `/bx:tests`, `/bx:arch`, `/bx:health`** — all content-review-hardened in S46, never run end-to-end.
8. **S37 plugin-packaging leftovers** — install smoke-test, retire `~/.claude` symlinks, `settings.local.json` `Skill(bx-*)` → `Skill(bx:*)`, launcher-script symlink-check retirement.
9. **`/bx:evolve` v2: extract shared `references/lane-contract.md`** — the three scan files share ~50% of their mass (inputs, filter, affected_files discipline, schema, addendum); flagged by all four `/simplify` agents, deferred for a fresh review cycle.
10. **`/bx:seo` deferred items** — code-review leftovers (#5 redundant per-call token mints; #6 `_read_skill_config` CWD assumption; #7 `fetch-sa` subcommand) plus the S25/S27/S29 refactors (batched-Grep alternation; fix-mode + plan-mode scaffolding extraction).

## Key Decisions

| Decision | Rationale |
|----------|-----------|

| GSC MCP migration (roadmap #1) evaluated and declined (S37, 2026-05-28) | `mcp-search-console` (the `gsc` MCP server) has **no response caching** + caps `batch_url_inspection` at **10 URLs/call** — a full migration would regress the quota economics the S31/S35 cache layer protects (the skill inspects up to 200 URLs in parallel with a 7-day `ui-*` cache via `gsc-parse-helper.py`). **`/bx:seo` stays on gcloud ADC + the helper.** The `gsc` MCP server stays configured machine-local (`~/.config/bx-seo/`, portable OAuth `token.json`) for *ad-hoc interactive* GSC queries only — NOT wired into the skill. Git history across all branches/remotes/reflog confirms the skill was **never** on MCP; only the roadmap doc mentions it. `get_advanced_search_analytics` (clean JSON, 25k-row pagination) is the one tool worth revisiting if ever rebuilt — Performance queries only, never URL Inspection. Full: [docs/key-decisions.md](docs/key-decisions.md). |
| `/bx:docs` → `/bx:save` rework — fast-by-default + Sonnet offload (S38, 2026-05-29) | The end-of-session save (paired with `/bx:resume`) routinely took >10 min so the user abandoned it. Root causes: Step 0 read all docs every run (~60k tokens incl. the 70k+53k append-only archives the update never reads *from*) even on `--fast`; the verification step echoed full file contents back; verbose prose. Fix: the lean session-save is now the **default** (drain tasks → CLAUDE.md session block → session-history append → commit), with README/docs sync + rollups moved to `--full`; a new `save-writer` Sonnet subagent does the big reads + all file writes off the main thread while the Opus orchestrator composes a small "update packet" + dispatches; full-file output dump → compact change report; prose caps on new entries; scoped Step-0 reads. Skill renamed `/bx:docs` → `/bx:save` (collision-proof pair-name with `/bx:resume`). Subagents 14 → 15. Built via superpowers brainstorm→spec→writing-plans→subagent-driven flow; specs in [docs/superpowers/](docs/superpowers/). Full: [docs/key-decisions.md](docs/key-decisions.md). |
| `/bx:seo` GSC path+auth+sitemap repair (S39, 2026-05-29) | The skill's entire GSC path was dead since plugin packaging: `${CLAUDE_SKILL_DIR}` isn't a real Claude Code variable (→ helper file-not-found, silent heuristic-only), and the token-passing assumed shell state persists across Bash calls (it doesn't). Fixed with a `bin/` launcher on PATH + in-call stdlib refresh-token minting — ADC **as the user, NOT a service account** (open Google bug blocks adding SAs to GSC; multi-machine via `adc_credentials_path` in config.yaml). Also closed the sitemap-discovery gap: fetch the LIVE sitemap (GSC `sitemaps.list` → robots.txt → conventional) instead of globbing a repo-local file that's empty for generated sitemaps — which had silently starved sub-dim 14 deindex detection. Verified against live GSC (sites.list 200) + burakarik.com (2,892-URL sitemap). Full: [docs/key-decisions.md](docs/key-decisions.md). |
| PowerShell `try/catch` can't gate native-exe failures — `cc` launcher git-pull fix (S40) | `start-claude.ps1` printed "Project synced." even when `git pull` failed: `try/catch` only catches terminating PowerShell errors, but native exes (git) signal failure via `$LASTEXITCODE`, so the `catch` was dead code (proved empirically). Fixed by gating the message on `$LASTEXITCODE` in all 3 spots + swapping `--quiet`/`2>/dev/null` for `--stat` so pulls are observable. Rule for future `.ps1`: never expect `try/catch` to catch a native command's exit code — check `$LASTEXITCODE`. |
| `/bx:webdesign` — Stitch-driven web design refactor skill (S41, 2026-06-06) | New 10th skill: re-skins an existing web project's visual design via Google Stitch, driven through the **Stitch MCP + Google's official `google-labs-code/stitch-skills`** (Model A: reuse their skills + detect-and-guide one-time setup, NOT re-implement). Web-only, refactor-only v1 (greenfield/non-web exit cleanly). Thin orchestrator owning what Google's kit lacks: web/styling/runnability detection, preserve-aware page briefs, **tokens-first + per-page safe restyle** (preserve logic/content/assets, restyle within existing responsive breakpoints, `git restore .`+`git clean -fd` rollback on failure), and build/test + Playwright + before/after verification. 3 resumable phases (Extract & Stage → Design & Review → Inject & Verify) on a dedicated `webdesign/<date>` branch; state in `.webdesign/state.json`; canonical Stitch formats from Google's repo bundled + runtime fresh-fetch. Built brainstorm→spec→plan→subagent-driven (two-stage review per task); merged `d5e98ab`. Full: [docs/key-decisions.md](docs/key-decisions.md). |
| Pre-dogfood review-hardening of `/bx:webdesign` + `/bx:save` (S42, 2026-06-06) | Both freshly-built skills were content-reviewed (skill-creator's quantitative eval loop is infeasible for them — MCP/session-state-dependent inputs + subjective outputs) and hardened before any real run. **`/bx:webdesign`** (16 fixes, `d6681e8`): closed the S41 `app_runnable:false` Phase-2 dead-end (capture+persist a user-supplied `stitch_project_id`); Phase-3 git-safety as a **general invariant** — *every root artifact the skill or Google's `stitch-skills` create must be gitignored (`.stitch/`, `.webdesign/SITE.md`) or staged (`DESIGN.md`) before `git add -A`/`git clean -fd`*, else the clean-tree guard self-trips and `clean -fd` can delete files; the top `/code-review` catch was a literal `git add … DESIGN.md` that aborts the token commit when no root file exists. **`/bx:save`**: plugin skills must declare every Bash helper in `allowed-tools` (the fast path called `wc`/`awk` unpermitted → a prompt every run); the packet now carries multiple `decision_rows` + `## Known Issues`/`## Completed` deltas; `save-writer` skips+`warnings:` on a non-matching delta (no silent partial save); and `disable-model-invocation` flipped to `true` (explicit-only, matching `/bx:resume` and 9/10 `bx` skills). |
| `/bx:clean` Step 1 dispatches dedicated Sonnet `cleanup-*` agents (S43) | Step 1 said "spawn a Task subagent" → a generic subagent on the orchestrator's Opus model, so the `cleanup-files-code`/`-deps-config`/`-styles-tests` agents (`model: sonnet`, least-privilege tools) were dead code and every scan ran on Opus. Now dispatches them by name, matching the `/bx:arch` + `/bx:tests` idiom — restoring Sonnet routing + tool scoping. (commit 65179cd) |
| `/bx:clean` eval suite + measured skill value (S43) | skill-creator full eval loop (with-skill vs no-skill baseline, 2 iterations): the skill is 100% but raw Claude **ties it on report-mode detection** even with precision traps (dynamic import, config-only dep, obscure PyPI name mismatch); the skill's measurable edge is **fix-mode discipline** (defers Safe-to-Delete, never auto-removes deps) + **prompt-independent category coverage**. Committed `bx/skills/clean/evals/` as a regression suite. (commit 65179cd) |
| `/bx:save --silent` — zero-prompt runs (S44) | The Part 8 commit ask was the only unavoidable prompt; end-of-session saves want zero questions. `--silent` auto-commits with the suggested message (no push) and resolves every `--full` consent prompt to its safe default: first-run rollup consents (5.2/6.2) decline without writing the sentinel, the 7.4 shrinker gate is skip-all. Named over `--yes` because the flag never answers "yes" on the user's behalf except the commit itself. (commit b82162d) |
| `/bx:seo` content-review hardening — doc-drift sweep rule (S45) | skill-creator qualitative review of all 15 skill files before the first real burakarik.com run found 3 high + 9 medium findings, all fixed in `1d6698a`. Pattern: every rework generation (CSV→API S29, helper-dispatch S35, auth S39) left stale echoes in sibling files that bait orchestrator improvisation — the canonical-paths table still mandated N-parallel-curl after S35 shipped `inspect-batch`, and Step 1.6.14 assumed env vars persist across Bash calls (same class as the pre-S39 token bug). Rules: a rework isn't done until its echoes are swept from sibling files; `allowed-tools` must enumerate every command a skill invokes, including plugin `bin/` helpers (2nd instance of the S42 lesson). |
| `/bx:evolve` upstream-watch skill — design contract (S46) | 11th skill: audits the bx toolkit against upstream Anthropic changes. Two-tier authority (official = actionable with mandatory citations; community = advisory-only, never fix-eligible). Committed watermark + decision log at `docs/upstream/state.json` (open/applied/rejected/deferred; trigger-based re-raise only when a re-emitted finding's source hash changed). Capability-inventory relevance gate: "new capability exists" alone is never a finding. Orchestrator computes ALL hashes — lane agents return `source_excerpt` (LLMs can't SHA-1; centralizing the algorithm prevents per-lane drift). Spec: `docs/superpowers/specs/2026-06-09-bx-evolve-design.md`. |
| Sentinel exit-point principle for /bx:evolve (S46) | `lane-unavailable-*` sentinels are lane-health reports, not findings: they exit the pipeline at consolidation Step 3.1 (lane_status set, errors stashed for the report's Section 1, removed from the finding set). All downstream exemptions (hashing, decision log, fix eligibility, certainty bands) are entailed by the single principle instead of 7 scattered carve-outs — the /simplify pass (`21b41bb`) collapsed the scatter the review iterations had accumulated. |
| `/bx:evolve` relevance gate confirmed + user-directed registration path (S47) | First dogfood validated the S46 gate: opportunity findings require a pain-point match, so per-skill "new capability" items are filtered by design. When the user wants them anyway, the orchestrator registers them as proper `open` findings with re-fetched verbatim excerpts + caveat notes. Lane digest one-liners are NOT citation-grade — verify against release bodies (wildcard fix: v2.1.139, not v2.1.145; v2.1.143 dependency enforcement: enable/disable-time only). |
| `CLAUDE_ENV_FILE` session env persistence (S47) | SessionStart scripts now write `PYTHONIOENCODING=utf-8` + `PYTHONUTF8=1` exports to the harness-provided `$CLAUDE_ENV_FILE` (CC 2.1.152+), persisting to every Bash call in the session — the principled fix for the recurring Windows-charmap class (S31/S33). Per-call prefixes in /bx:seo stay until a smoke-check passes. |
| Cross-skill references must resolve against the skill base directory, not repo-rooted paths (S48) | /bx:webdesign phase1 pointed at `bx/skills/seo/SKILL.md` for the route-enumeration table — a path that exists in neither the installed plugin-cache layout (no `bx/` prefix) nor the target project's CWD where the skill actually runs; same class as the S39 `${CLAUDE_SKILL_DIR}` bug. Rule: sibling-skill reads use `../<skill>/...` resolved against the base directory Claude Code announces at skill load. Corollary from the same review: every background process a skill starts needs its stop mechanism named and permitted (`KillShell`), or orchestrators improvise `kill`/`taskkill`. |
| `Agent(model:…)` deny rules do NOT guard omitted-model dispatch (S50) | The permissions docs confirm `Tool(param:value)` is real, but also that "a parameter the model omits is never matched" — so `Agent(model:opus)` catches an *explicit* Opus request and never fires on a generic dispatch that sends no `model` param, which is exactly the S43 bug it was added to guard. Two further limits: the value is compared against literal input before normalization (alias `opus` matches, a full model ID does not), and parameter rules are valid in `deny`/`ask` only, never `allow`. The durable guard remains frontmatter `model: sonnet` + dispatching agents by name. |
| `${CLAUDE_SKILL_DIR}` is real, but text-substitution — not a shell variable (S50) | Corrects a repo-wide claim (in `bx/bin/gsc-parse-helper` and `bx/skills/seo/SKILL.md`) that it "is NOT a real Claude Code substitution". It is real and documented, expanded in a skill's rendered markdown and in `allowed-tools` Bash rules (v2.1.129+) — but never by the shell, so anything reaching the shell unexpanded still yields an empty string. That distinction is what the S33 bug actually was; the `bin/`-launcher-on-PATH remedy stays correct, and `${CLAUDE_PLUGIN_ROOT}` genuinely is unavailable to Bash. |
| `/bx:webdesign` first dogfood + 15-fix hardening (S52) | First real end-to-end run (kaanarik) paused clean at `review_pending`; the safety architecture held and all 15 findings were in the delegation surface, not orchestration. Durable gotchas now encoded: `stitch-skills` install as `stitch-design:<name>` (NOT `stitch::`); Tailwind v4 has no config file (tokens in `@theme`, not `tailwind.config.js`); the init wizard prints its own `claude mcp add` (API-key `http` path, not a fixed `proxy`/`GOOGLE_CLOUD_PROJECT` command); Stitch color control is lossy (a light seed never resolves bright, overrides silently drop) → verify the palette via `get_project` before batch-generating. |
| Scoped `/bx:evolve` runs must freeze the watermark (S53) | `/bx:evolve` has no per-skill scoping; its inventory spans all of `bx/`. When a run is deliberately narrowed to one skill, advancing `last_changelog_version` / `docs_checked_at` would record the *unexamined* skills as audited through that version, and those releases would never be re-scanned. A scoped run therefore suppresses Step 6 entirely and reports the frozen watermark, leaving a full run still owed. |
| Checkpoints are per-user-prompt, not per-edit — and subagent edits aren't checkpointed at all (S53) | Any bx skill telling users how to undo its `--fix` edits must not promise per-edit granularity: Claude Code captures one checkpoint **before each user prompt**, so a batch fixing N findings in one turn has a single checkpoint and `/rewind` reverts all of it. Two riders: `Esc Esc` opens the menu only when the prompt input is empty, and edits applied by a *subagent* (or a background forked skill) land outside session checkpoints entirely — git is the only undo for those. Corrected in `/bx:review`; audit the other `--fix` skills for the same claim. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
claude-config/                         # marketplace repo
├── .claude-plugin/
│   └── marketplace.json               # "burak-tools" marketplace catalog
├── bx/                                # the installable `bx` plugin (S37, see Key Decisions)
│   ├── .claude-plugin/plugin.json     # manifest (commit-SHA versioned; skills → /bx:<name>)
│   ├── agents/                        # 18 subagents (Sonnet-routed) → bx:<agent>
│   ├── hooks/hooks.json               # SessionStart project-orientation injection
│   ├── scripts/                       # session-start-context.{sh,ps1}
│   └── skills/                        # 11 skills (SKILL.md + references/) → /bx:<name>
│       ├── arch/    clean/   evolve/  health/
│       ├── plan/    resume/  review/
│       ├── save/    seo/     tests/   # save = /bx:save (was docs)
│       └── webdesign/                  # /bx:webdesign — visual re-skin via Stitch MCP
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

**Subagents** are the 18 markdown files under `bx/agents/`, dispatched by skills. They run on Sonnet for cost efficiency and have scoped tool permissions. (`save-writer` is dispatched by `/bx:save` to apply doc edits off the main thread.)

## Known Issues / Blockers

**The S37 `/bx:seo` "messed up" breakage is RESOLVED (S39).** Root-caused to the `${CLAUDE_SKILL_DIR}` path bug (not a real Claude Code variable → the helper was never found → GSC silently fell back to heuristic-only) + an impossible "mint token once, reuse across Bash calls" auth model (shell state does not persist across Bash tool calls). Both fixed and verified against live GSC. See Session History S39 + Key Decisions.

**Uncommitted S53 work:** the `/bx:review` edits from this session's scoped `/bx:evolve --fix` pass (5 files) are uncommitted — `/plugin update bx` + `/reload-plugins` won't carry them until they are committed and pushed. (The S52 `/bx:webdesign` hardening previously flagged here as unpushed **is** pushed, as of `4931ee7`.) The Stitch MCP + `stitch-skills` are already installed in the `kaanarik` target repo (S52 dogfood). **14 open upstream findings** live in `docs/upstream/state.json`, and the `/bx:evolve` watermark is deliberately frozen at changelog 2.1.217 / docs 2026-07-22 because S53's run was skill-scoped — a full run is still owed.

## Environment Variables

None required. This is a pure configuration repo — no runtime dependencies or secrets.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 53) - 2026-07-30
- Ran **`/bx:evolve` scoped to a single skill (`/bx:review`)** — a first. The skill has no per-skill scoping, so the capability inventory was narrowed to `bx/skills/review/` (23 entries) and the **watermark deliberately frozen**, since advancing it would have falsely recorded the other 10 skills as audited.
- **The docs lane returned zero findings while correctly reporting two allowlist gaps.** Orchestrator direct-fetches of the unpinned `checkpointing` and `code-review` pages produced **5 of the 7 findings**, including the only factually-wrong claim in the skill — the 2nd consecutive run the S50 allowlist-completeness rule has fired.
- **7 findings registered; `--fix` applied 5, rejected 1, skipped 1.** Top catch: `/bx:review` told users checkpoints are created "before each edit" when they are created **before each user prompt**, so one `/rewind` reverts a whole `--fix` batch, not a single edit.
- Deliberately **half-fixed** the run's most valuable finding: `/bx:review` has no false-positive verification pass while Anthropic's own reviewer does. Only the cheap "verification bar" rule landed; the architecture is queued for a proper design session rather than a `--fix` bolt-on.
- Corrected a stale CLAUDE.md claim — the S52 `/bx:webdesign` hardening was recorded as unpushed but is pushed at `4931ee7`.

> Full session detail: [docs/session-history.md](docs/session-history.md) S53
