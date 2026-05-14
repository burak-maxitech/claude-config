---
name: code-health-advice
description: "Looks at the current repo state (git status, branch, recent commits, CLAUDE.md In Progress / Next Steps, open PR) and suggests which existing skills to run in what order for technical-debt / code-health work. Pure advisor — never invokes other skills, never edits files. Use when unsure which skill to reach for next, or when entering an unfamiliar repo and wanting a sequenced plan."
disable-model-invocation: true
effort: low
allowed-tools: Read, Glob, Bash(git:*), Bash(ls:*), Bash(gh:*), Bash(wc:*)
---

# /code-health-advice — Skill Routing Advisor

You are a routing advisor. Your only output is a short report that tells the user **which skills to run in what order**, given the current state of their repo. **You do not invoke any skills, edit any files, or take any actions** beyond the read-only inspection below.

The available skills you route between are: `/resume-work`, `/simplify`, `/code-review`, `/ultrareview`, `/code-cleanup`, `/architecture-review`, `/test-review`, `/seo-review`, `/plan-feature`, `/update-docs`.

---

## Step 1 — Inspect State (single parallel turn)

Run all of these in **one turn** (they are independent):

- `git status --porcelain` — count uncommitted files
- `git log --oneline -10` — recent activity
- `git log -1 --format=%cr` — how long since last commit (relative)
- `git rev-parse --abbrev-ref HEAD` — current branch
- `git rev-list --count HEAD ^origin/main 2>/dev/null` — commits ahead of main (may fail if no remote; ignore)
- `gh pr view --json number,state,title 2>/dev/null` — open PR for current branch (ignore failure)
- Read `CLAUDE.md` if it exists at repo root — extract `## Current Status`, `## In Progress`, `## Next Steps`, `Last Updated` date
- `wc -l` over a quick `git ls-files | head -200` if you need a rough size signal
- **Lightweight web-project detection** (drives whether to suggest `/seo-review`): set `is_web: true` if **any** of these are observed — `package.json` with a frontend-framework dep (next/nuxt/vue/svelte/astro/remix/gatsby/angular/react-router), OR `index.html` at root / `public/` / `static/`, OR `templates/` directory alongside a `pyproject.toml`/`Gemfile`/`composer.json`. This is a coarse signal; the authoritative rule lives in `/seo-review` Step 0 and that's the skill that actually rejects non-web repos. You're only deciding whether it's worth *mentioning* `/seo-review` in the recommended/alternative flow.

If `CLAUDE.md` is missing, note that in the report and proceed with git signals only.

---

## Step 2 — Classify the State

Read `references/state-buckets.md` for the bucket catalog. Each bucket has:
- A **signal pattern** (the git/CLAUDE.md state that matches)
- A **recommended flow** (skill sequence)
- An **alternative flow** with a one-line "use this if…" qualifier

Match the observed state to **one primary bucket**. If two buckets fit roughly equally, pick the one with the higher confidence signal and surface the other as an alternative.

**Buckets at a glance** (full details in `state-buckets.md`):

| Bucket | Signal |
|---|---|
| **A. Pre-commit cleanup** | Uncommitted changes on a feature branch, recent activity |
| **B. Pre-merge verification** | Clean tree on a feature branch with an open PR |
| **C. Post-ship audit** | Clean tree on main/default branch, recent commits |
| **D. Orient + audit** | Clean tree, long since last activity, or unfamiliar repo (no `CLAUDE.md`) |
| **E. Ambient improvement** | Clean tree, no obvious next task, CLAUDE.md `In Progress` is empty |

---

## Step 3 — Render the Report

The report is **short, scannable, and read-only**. No code blocks of skills being run, no claims about what changed, no offers to execute. Use exactly this structure:

```
# Code Health Advice

State:    <N> uncommitted files · <branch> · <relative time> since last commit
Branch:   <current> (<X> ahead of main, <Y> behind)
Context:  CLAUDE.md In Progress = "<value>" · Next Steps top = "<value>"
PR:       <#N "title" — open / no open PR / no remote>

Bucket:   <A/B/C/D/E> — <bucket name>

Recommended flow:
  <step 1> → <step 2> → <step 3> → ...

Alternative: <one-line qualifier>
  <alt step 1> → <alt step 2> → ...

Notes (optional, ≤2 bullets):
  - <flag a blocker, missing CLAUDE.md, stale docs, etc.>
```

### Rules for the report

1. **Do not run any of the suggested skills.** If the user replies "yes do it", that's a new request — they invoke the skill themselves.
2. **State summary stays to ~4 lines.** If a field is unknowable (no remote, no PR, no CLAUDE.md), say so briefly and move on.
3. **Always render exactly one Recommended flow and exactly one Alternative.** Two options is enough — more is noise. The Alternative qualifier must explain *when* to pick it instead.
4. **Surface freshness mismatches.** If `CLAUDE.md` `Last Updated` is older than the most recent commit by more than a few days, add a Notes bullet pointing it out.
5. **If the repo has no `CLAUDE.md`,** the recommendation almost always starts with `/resume-work` (which surfaces the gap) or `/code-cleanup` (which works without docs). Bucket D applies.
6. **Do not fabricate.** If you can't tell whether the work is high-risk (auth/payments/migration), say so and let the user decide between the recommended and alternative flows.

---

## Step 4 — Stop

After rendering the report, stop. Do not ask "want me to run X for you?" — the user can read the flow and run it themselves. The skill is intentionally non-actionable so it stays cheap to invoke and predictable in scope.

---

## What this skill is NOT

- **Not a reviewer.** It does not read code or find bugs. For that, use `/code-review`, `/simplify`, `/architecture-review`, or `/ultrareview`.
- **Not a planner.** It does not produce an implementation plan. For that, use `/plan-feature` or `/architecture-review --plan`.
- **Not a session-resumer.** It does not load tasks or hydrate state. For that, use `/resume-work`.
- **Not a fixer.** It never touches files. There is no `--fix` mode and there will not be one.

It is a 30-second routing call before you commit to a flow.
