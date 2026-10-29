# Architecture

> Full architecture detail, moved out of CLAUDE.md (doc schema v2). Read on demand.

---

```
claude-config/                         # marketplace repo
├── .claude-plugin/
│   └── marketplace.json               # "burak-tools" marketplace catalog
├── bx/                                # the installable `bx` plugin (S37, see Key Decisions)
│   ├── .claude-plugin/plugin.json     # manifest (explicit semver `version` = update cache key; skills → /bx:<name>)
│   ├── agents/                        # 20 subagents (Sonnet-routed) → bx:<agent>
│   ├── hooks/hooks.json               # SessionStart project-orientation injection
│   ├── scripts/                       # session-start-context.sh (bash; runs on Windows via Git Bash — the .ps1 twin was removed S59)
│   └── skills/                        # 11 skills (SKILL.md + references/) → /bx:<name>
│       ├── arch/    clean/   evolve/  health/   # evolve also: capabilities.json (pinned inventory), scripts/, tests/ (2.12.0); clean also: evals/ (3 evals, planted fixtures, 60 assertions since 2.13.0)
│       ├── plan/    resume/  review/
│       ├── save/    seo/     tests/   # save = /bx:save; save/tests/ holds the doc-schema suite
│       └── webdesign/                  # /bx:webdesign — visual re-skin via Stitch MCP
├── .claude/
│   ├── scripts/             # start-claude.{sh,ps1} launchers (not plugin components)
│   └── settings.local.json  # Local Claude Code settings
├── docs/                    # Reference files + session state
│   ├── STATUS.md            # Session state (schema v2) — read on demand by /bx:resume
│   ├── architecture.md      # This file
│   ├── completed-work.md
│   ├── key-decisions.md
│   ├── known-issues.md      # Issues moved out of CLAUDE.md (created on demand, v2.10.0)
│   ├── modernization-roadmap.md
│   ├── session-history.md
│   ├── archive/             # Rotated archive volumes (Part 7.7)
│   ├── superpowers/         # Specs + plans from brainstorm→plan workflows
│   └── upstream/            # /bx:evolve watermark, decision log, pain registry
├── .githooks/ .github/workflows/ scripts/   # version-bump guard: hook, CI, script (S60)
├── .gitignore
├── CLAUDE.md                # Always-loaded AI instructions (schema v2)
├── README.md                # Public overview
└── workflow.md              # Personal workflow guide
```

**Plugin approach (S37):** the toolkit installs as the `bx` plugin from the local `burak-tools` marketplace (`/plugin install bx@burak-tools`) — no symlinks. Skills are namespaced `/bx:<name>` and agents `bx:<agent>` by the plugin, which is the principled collision-proof fix that the S36 `bx-` prefix only worked around. `version` is explicit semver as of S54 (2026-08-11) — it is the plugin's update cache key, so every `bx/**` change must bump it (enforced by `/bx:save` Part 8; history in `CHANGELOG.md`). (Old `~/.claude/skills`+`agents` symlinks are retired on adoption — see README "Migrating from the old symlink setup".)

**Skills** are directories under `bx/skills/` containing `SKILL.md` (YAML frontmatter) + a `references/` folder. Invocable as `/bx:<name>`.

**Subagents** are the 20 markdown files under `bx/agents/`, dispatched by skills. They run on Sonnet for cost efficiency and declare scoped tool lists; command specifiers on agent `tools:` (`Bash(find:*)`) are not enforced by Claude Code (verified S61), so in-Bash discipline is prompt-enforced. (`save-writer` is dispatched by `/bx:save` to apply doc edits off the main thread; `doc-migrator` performs the one-time v1→v2 schema migration.)

**Cross-skill contract owners (S57 named-owner principle).** Where two or more skills depend on the same rule, one file owns it and the others cite it — satellites never restate. Four exist: `save/references/doc-schema.md` (the doc layout + archive set), `save/references/task-tools.md` (task-tool availability and each skill's degraded path), `arch/references/finding-rubrics.md` (severity/certainty/effort anchors and the mandatory justification fields, read by all five arch scanners), and `arch/references/scan-exclusions.md` (what a repo-wide scan must never report on — including during stack detection, which is the half that bit `/bx:tests`; since 2.13.2, references *from* an excluded tree still count as evidence, because fixture-named trees can hold real code). Cross-skill references resolve as `../<skill>/...` against the **citing skill's base directory** (S48). `bx/skills/save/tests/check-doc-rule-consistency.sh` enforces that any deliberately-duplicated block stays byte-identical.

**Scripts measure, scanners judge (S64–S65).** Where a number decides a deletion or a headline, it comes from a committed script, not from scanner prose: prose rules did not converge across reruns. `/bx:tests` runs `skills/tests/scripts/run.py` (stdlib Python, read-only on the source; writes to an OS-temp dir, and since 2.14.1 copies the run to `<repo>/.bx/tests/<date>/`, excluded via `.git/info/exclude`, so a `--plan` brief stays resumable) before dispatch — `test_bodies.py` (one row per test, assertion counts by kind), `leverage.py` (churn, path-resolved fan-in, entry points, git-history lanes), `references.py` (per-symbol references classed call/mock/mention, life support with successor detection, module ratios) and `consolidate.py` (merge clusters with a computed merge table). A failed or timed-out script becomes a `coverage_partial` entry. `references.py` also owns the test-only-symbol rule `/bx:clean` cites, so the two skills never double-count a symbol.

**Doc schema v2 (S56):** CLAUDE.md carries only always-loaded instructions; session state lives in `docs/STATUS.md`; history archives (`session-history.md`, `key-decisions.md`, `completed-work.md`, and since v2.10.0 `known-issues.md`) are append-only, read by no automatic path, and rotate into `docs/archive/` volumes past 100k chars. The contract lives at `bx/skills/save/references/doc-schema.md`; `bx/skills/save/tests/assert-doc-schema.sh` verifies it mechanically.
