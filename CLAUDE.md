# CLAUDE.md

Last Updated: 2026-08-11 (Session 54)

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
| Plugin packaging (`bx`) | Core complete (S37); explicit semver **v1.0.0** + CHANGELOG.md (S54) — pending install smoke-test + symlink retirement |
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

1. **Smoke-test batch (quick):** `/loop /bx:review` (docs now confirm the disable-model-invocation plain-text behavior for *scheduled tasks*; whether `/loop` shares it is the open half — workflow.md caveat is now "partially confirmed"); `/plugin update bx` without `/reload-plugins` (v2.1.221 "when safe", finding `fab78c6a`); a few `2>/dev/null` commands watching for new prompts (v2.1.214 fail-closed, finding `093df977`); `CLAUDE_ENV_FILE` UTF-8 persistence.
2. **Design session: a verification pass for `/bx:review`** — still single-pass at `effort: high` with no false-positive filter; Anthropic's reviewer runs parallel agents + verification. Brainstorm → spec → skill-creator eval (finding `d1480670`, deliberately half-fixed in S53).
3. **Resume the `/bx:webdesign` kaanarik run past review** — `/plugin update bx` first (picks up v1.0.0), re-run `/bx:webdesign` (resumes at `review_pending`), push through **Phase 3 inject+verify**. While there, VERIFY open finding `dadac845`: auto-mode blocks destructive git and Phase-3's rollback is exactly `git restore .` + `git clean -fd` — S54's community lane surfaced Anthropic's official auto-mode post confirming the premise.
4. **Real `/bx:seo` run against burakarik.com** — auth fixed S39, content-review-hardened S45.
5. **Dogfood `/bx:tests`, `/bx:arch`, `/bx:health`** — all content-review-hardened in S46, never run end-to-end.
6. **S37 plugin-packaging leftovers** — install smoke-test, retire `~/.claude` symlinks, `settings.local.json` `Skill(bx-*)` → `Skill(bx:*)`, launcher-script symlink-check retirement.
7. **`/bx:evolve` follow-ups** — evaluate adding `auto-mode-config` to the scan-docs allowlist (owns the auto-mode classifier contract; flagged S54); act on the 14 `open` findings (top: the skills-dir/activation-gap cluster, now 5 distinct sources); v2 ideas: extract shared `references/lane-contract.md` (three scan files share ~50% mass), treat lane digest one-liners as non-citation-grade.
8. **`/bx:seo` deferred items** — code-review leftovers (#5 redundant per-call token mints; #6 `_read_skill_config` CWD assumption; #7 `fetch-sa` subcommand) plus the S25/S27/S29 refactors (batched-Grep alternation; fix-mode + plan-mode scaffolding extraction).

## Key Decisions

| Decision | Rationale |
|----------|-----------|
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
| Explicit semver plugin versioning replaces commit-SHA versioning (S54) | `version` in plugin.json is the plugin's **update cache key**: users receive an update only when it changes, so a `bx/**` push without a bump is invisible (`/plugin update` reports "already at the latest version"). Set v1.0.0 + `displayName`; `CHANGELOG.md` started; `/bx:save` Part 8 enforces bump-on-bx-change (PATCH fixes / MINOR new skill-agent-flag / MAJOR breaking; `--silent` defaults PATCH). Old "omitted version = every commit is a version" claims swept from README + CLAUDE.md. |

> Full decision log: [docs/key-decisions.md](docs/key-decisions.md)

## Architecture Summary

```
claude-config/                         # marketplace repo
├── .claude-plugin/
│   └── marketplace.json               # "burak-tools" marketplace catalog
├── bx/                                # the installable `bx` plugin (S37, see Key Decisions)
│   ├── .claude-plugin/plugin.json     # manifest (explicit semver `version` = update cache key; skills → /bx:<name>)
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

**Plugin approach (S37):** the toolkit installs as the `bx` plugin from the local `burak-tools` marketplace (`/plugin install bx@burak-tools`) — no symlinks. Skills are namespaced `/bx:<name>` and agents `bx:<agent>` by the plugin, which is the principled collision-proof fix that the S36 `bx-` prefix only worked around. `version` is explicit semver as of S54 (2026-08-11) — it is the plugin's update cache key, so every `bx/**` change must bump it (enforced by `/bx:save` Part 8; history in `CHANGELOG.md`). (Old `~/.claude/skills`+`agents` symlinks are retired on adoption — see README "Migrating from the old symlink setup".)

**Skills** are directories under `bx/skills/` containing `SKILL.md` (YAML frontmatter) + a `references/` folder. Invocable as `/bx:<name>`.

**Subagents** are the 18 markdown files under `bx/agents/`, dispatched by skills. They run on Sonnet for cost efficiency and have scoped tool permissions. (`save-writer` is dispatched by `/bx:save` to apply doc edits off the main thread.)

## Known Issues / Blockers

**The S37 `/bx:seo` "messed up" breakage is RESOLVED (S39).** Root-caused to the `${CLAUDE_SKILL_DIR}` path bug (not a real Claude Code variable → the helper was never found → GSC silently fell back to heuristic-only) + an impossible "mint token once, reuse across Bash calls" auth model (shell state does not persist across Bash tool calls). Both fixed and verified against live GSC. See Session History S39 + Key Decisions.

**Plugin-versioning sharp edge (S54):** `version` in `bx/.claude-plugin/plugin.json` is the plugin's update cache key — a push that changes `bx/**` without bumping it is never offered to users (`/plugin update` reports "already at the latest version"). `/bx:save` Part 8 enforces the bump; manual committers follow the README contributors note. History in `CHANGELOG.md`.

**14 open upstream findings** live in `docs/upstream/state.json`; the watermark is current again (changelog 2.1.228 · docs/community 2026-08-11 — S54's full run released the S53 freeze). Correction from resume: the S53 "5 uncommitted files" claim was stale — they were committed in `e1bd066` and pushed before this session, and the plugin cache already carried them.

## Environment Variables

None required. This is a pure configuration repo — no runtime dependencies or secrets.

## Session History

> Full history: [docs/session-history.md](docs/session-history.md)

### Last Session (Session 54) - 2026-08-11
- **Full `/bx:evolve` released the S53 watermark freeze** after growing the docs-lane allowlist 9 → 11 (`checkpointing` + `code-review` pinned — the S50 completeness rule's 3rd firing): 11 releases scanned (2.1.218 → 2.1.228), all 3 lanes ok, 4 Tier-1 findings + 3 advisories; watermark now 2.1.228 / 2026-08-11.
- **`--fix` applied 4/4.** Top catch: the S53 per-edit checkpoint-undo error survived at **9 sites across 8 files** in every other `--fix` skill (clean/arch/tests/seo/evolve + workflow.md) — all swept to the per-user-prompt framing. Also: README's v2.1.223 `/review`-alias disambiguation; v2.1.221 activation signal (hedged); `/loop` caveat upgraded to "partially confirmed".
- **Explicit plugin versioning shipped (user request):** `plugin.json` `version: 1.0.0` + `displayName`, `CHANGELOG.md` started, `/bx:save` Part 8 now mandates the bump (version = update cache key — a push without a bump reaches nobody), echo sweep over README/CLAUDE.md's old commit-SHA-versioning claims.
- Community lane handed off Anthropic's **official** auto-mode sources confirming destructive-git blocking — addendum recorded on open webdesign finding `dadac845`; `auto-mode-config` flagged as the next allowlist candidate.
- Resume-time corrections: S53's "5 uncommitted files" were actually committed (`e1bd066`) and pushed; stray empty Key Decisions table header removed.

> Full session detail: [docs/session-history.md](docs/session-history.md) S54
