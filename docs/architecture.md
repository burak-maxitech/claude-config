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
│   ├── scripts/                       # session-start-context.{sh,ps1}
│   └── skills/                        # 11 skills (SKILL.md + references/) → /bx:<name>
│       ├── arch/    clean/   evolve/  health/
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
│   ├── modernization-roadmap.md
│   ├── session-history.md
│   ├── superpowers/         # Specs + plans from brainstorm→plan workflows
│   └── upstream/            # /bx:evolve watermark + decision log
├── .gitignore
├── CLAUDE.md                # Always-loaded AI instructions (schema v2)
├── README.md                # Public overview
└── workflow.md              # Personal workflow guide
```

**Plugin approach (S37):** the toolkit installs as the `bx` plugin from the local `burak-tools` marketplace (`/plugin install bx@burak-tools`) — no symlinks. Skills are namespaced `/bx:<name>` and agents `bx:<agent>` by the plugin, which is the principled collision-proof fix that the S36 `bx-` prefix only worked around. `version` is explicit semver as of S54 (2026-08-11) — it is the plugin's update cache key, so every `bx/**` change must bump it (enforced by `/bx:save` Part 8; history in `CHANGELOG.md`). (Old `~/.claude/skills`+`agents` symlinks are retired on adoption — see README "Migrating from the old symlink setup".)

**Skills** are directories under `bx/skills/` containing `SKILL.md` (YAML frontmatter) + a `references/` folder. Invocable as `/bx:<name>`.

**Subagents** are the 19 markdown files under `bx/agents/`, dispatched by skills. They run on Sonnet for cost efficiency and have scoped tool permissions. (`save-writer` is dispatched by `/bx:save` to apply doc edits off the main thread; `doc-migrator` performs the one-time v1→v2 schema migration.)

**Cross-skill contract owners (S57 named-owner principle).** Where two or more skills depend on the same rule, one file owns it and the others cite it — satellites never restate. Four exist: `save/references/doc-schema.md` (the doc layout + archive set), `save/references/task-tools.md` (task-tool availability and each skill's degraded path), `arch/references/finding-rubrics.md` (severity/certainty/effort anchors and the mandatory justification fields, read by all five arch scanners), and `arch/references/scan-exclusions.md` (what a repo-wide scan must never read — including during stack detection, which is the half that bit `/bx:tests`). Cross-skill references resolve as `../<skill>/...` against the **citing skill's base directory** (S48). `bx/skills/save/tests/check-doc-rule-consistency.sh` enforces that any deliberately-duplicated block stays byte-identical.

**Doc schema v2 (S56):** CLAUDE.md carries only always-loaded instructions; session state lives in `docs/STATUS.md`; history archives (`session-history.md`, `key-decisions.md`, `completed-work.md`) are append-only, read by no automatic path, and rotate into `docs/archive/` volumes past 100k chars. The contract lives at `bx/skills/save/references/doc-schema.md`; `bx/skills/save/tests/assert-doc-schema.sh` verifies it mechanically.
