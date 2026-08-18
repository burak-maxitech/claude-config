# Architecture

> Full architecture detail, moved out of CLAUDE.md (doc schema v2). Read on demand.

---

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
