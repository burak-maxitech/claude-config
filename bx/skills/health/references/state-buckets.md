# State Buckets — Routing Catalog

Each bucket maps an observable repo state to a recommended skill flow. The orchestrator (`SKILL.md` Step 2) picks **one primary** bucket and surfaces **one alternative**.

---

## A. Pre-commit cleanup

**Signal:**
- Uncommitted changes present (`git status --porcelain` non-empty)
- On a feature branch (not `main` / `master` / `develop`)
- Recent activity (last commit within ~24h, or actively editing this session)

**Mental model:** "I just finished writing a feature. I want to land it cleanly."

**Recommended flow:**
```
/simplify → /code-review → /bx:review → /bx:review --verify → commit → /bx:save
```

Why this order:
- `/simplify` (built-in, quality-only) first — auto-applies cheap clarity/altitude/dedup fixes to *what you just wrote*, so the bug-focused passes downstream read cleaner code. It does NOT hunt for bugs.
- `/code-review` (built-in, lightweight) next — scans the diff for correctness bugs at a chosen effort level. Best signal closest to the change.
- `/bx:review` next for diff-scoped correctness/security — same diff scope but more rigorous (custom skill with codebase-convention scan + git-blame context).
- `/bx:review --verify` runs your test/lint suite (parallel-backgrounded since S19) — catches regressions before commit.
- Commit, then `/bx:save` at session end so the work is captured in `CLAUDE.md`.

**Alternative:** *If the change touches auth, payments, data migrations, or anything that pages someone at 3 AM:*
```
/code-review → /bx:review --security → /bx:review --verify → commit → push → /code-review ultra <PR#> → merge → /bx:save
```

`/code-review ultra` adds 5–20 cloud subagents (10–20 min) and is overkill for routine work but the right call for high-risk code.

---

## B. Pre-merge verification

**Signal:**
- Clean working tree (`git status --porcelain` empty)
- On a feature branch with `gh pr view` returning an open PR
- Branch is N commits ahead of main

**Mental model:** "Code is committed and pushed. PR is open. Should I do anything before merging?"

**Recommended flow:**
```
/bx:review --security → /code-review ultra <PR#>
```

Why:
- `/bx:review --security` is fast in-session and surfaces OWASP-flavored issues across the diff.
- `/code-review ultra` is the deeper cloud-based pass. Worth it for any non-trivial PR that's about to merge.

**Alternative:** *If the PR is small / low-risk (docs, config, copy changes, refactors with no behavior change):*
```
/code-review (no flags)
```

Skip `/code-review ultra` for trivial PRs — the cloud cost and 10–20 min wait isn't justified.

---

## C. Post-ship audit

**Signal:**
- Clean working tree
- On `main` / `master` / `develop`
- Recent commits exist (within last few days)
- `CLAUDE.md` `In Progress` is empty or "Nothing currently in progress"

**Mental model:** "Just shipped. Calm waters. What's the technical debt situation?"

**Recommended flow** *(when `is_web: false`)*:
```
/bx:clean → /bx:arch → /bx:tests → /bx:arch --plan → /bx:plan <phase>
```

**Recommended flow** *(when `is_web: true`)*:
```
/bx:clean → /bx:arch → /bx:tests → /bx:seo → /bx:arch --plan → /bx:plan <phase>
```

Why this order:
- `/bx:clean` first deletes whole files/deps that are dead — cleaner signal for everything downstream.
- `/bx:arch` then audits the *remaining* code for structural complexity, refactor opportunities, perf suspects, and over-engineering.
- `/bx:tests` audits the test suite itself — coverage gaps in critical code AND wasteful/redundant tests. Run after the structural audits so coverage gaps are measured against post-cleanup code.
- `/bx:seo` *(web projects only)* audits SEO + Generative Engine Optimization with fresh fetched best practices. Run after structural cleanup so the SEO scan reflects the post-cleanup site. Score is tracked over time in `docs/seo-history.md`.
- `/bx:arch --plan` turns findings into phased work.
- `/bx:plan` per phase before implementing.

**Alternative:** *If you only have ~30 minutes and want one quick win, not a full audit:*
```
/bx:arch (default mode, no --plan, no --fix)
```

The default `/bx:arch` report includes a "Code we can delete: N lines" top-line metric and ranks findings by quick-wins. Pick one and act on it; come back another day for the full flow.

---

## D. Orient + audit

**Signal:**
- Clean working tree
- Long since last commit (>1 week) **OR** no `CLAUDE.md` at repo root **OR** auto-memory is empty/missing
- May be a repo the user is unfamiliar with

**Mental model:** "I don't have a clear picture of what this repo is or where it stands. Help me orient."

**Recommended flow:**
```
/bx:resume deep → /bx:clean → /bx:arch → /bx:tests → /bx:save
```

Why:
- `/bx:resume deep` reads the full reference set (`docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`) and runs the health-check ladder. If `CLAUDE.md` is missing, it surfaces the gap and recommends `/bx:save` first.
- `/bx:clean` next because it works without `CLAUDE.md` context — pure structural deletion signal.
- `/bx:arch` for the structural picture once dead code is gone.
- `/bx:tests` for the test suite picture — both coverage gaps and waste. Surfaces what to write next and what to delete. Skip if `git ls-files` shows no test files.
- `/bx:save` at the end populates `CLAUDE.md` and auto-memory so the next session starts oriented.

**Alternative:** *If `CLAUDE.md` is completely missing and the repo isn't yours:*
```
/bx:save (CREATE mode, scaffolds CLAUDE.md from the codebase) → /bx:resume → /bx:arch
```

Build the doc surface first; everything downstream is easier with it.

---

## E. Ambient improvement

**Signal:**
- Clean working tree
- `CLAUDE.md` `In Progress` is empty
- `CLAUDE.md` `Next Steps` exists and has actionable items
- Recent commits, but no urgent work right now

**Mental model:** "Nothing's broken. I have time. What should I improve?"

**Recommended flow:**
```
/bx:arch (or /bx:tests for test suite focus, or /bx:seo when is_web: true) → pick one finding → /bx:plan → implement → /code-review → /bx:save
```

Why:
- `/bx:arch` is the highest-signal entry point when nothing is on fire — it surfaces deletions, refactors, and perf wins ranked by impact. Use `/bx:tests` instead when the test suite specifically is what you want to invest in (coverage gaps in critical code + redundant/wasteful tests). When `is_web: true`, `/bx:seo` is also a strong inline option — SEO/GEO findings tend to deliver visible business impact (search ranking, AI citation) and the skill tracks scores over time in `docs/seo-history.md` so progress compounds across runs.
- When `is_web: true` and the user's improvement appetite is *visual* rather than structural — "the app works but looks dated" — route to `/bx:webdesign` instead of the audit chain. It re-skins the site's design via Google Stitch as a self-contained pipeline (extract → design → inject/verify) on a dedicated `webdesign/<date>` branch with rollback. It replaces the whole flow above (no `/bx:plan` step needed — it plans internally), and it needs a one-time Stitch MCP + `stitch-skills` setup, so flag that prerequisite when recommending it to someone who hasn't run it before.
- Pick **one** finding (don't try to do them all).
- `/bx:plan` to scope the change before writing code.
- Then the standard implement → review → docs loop.

**Alternative:** *If `CLAUDE.md` Next Steps already lists a specific item you want to tackle:*
```
/bx:plan → implement → /code-review → /bx:review --verify → /bx:save
```

Skip the audit — you already know what to work on. Go directly into the planning + implement loop.

*(In both flows above, the bare `/code-review` at the implement stage = the built-in lightweight diff scan; reach for `/bx:review` instead if you want the thorough senior-engineer treatment with `--security`/`--verify`/`--fix`.)*

---

## Tie-breaker rules

When two buckets match the signal pattern roughly equally:

1. **Uncommitted changes always wins.** A non-empty `git status` is the strongest signal. Bucket A trumps everything except an explicit user override.
2. **Open PR beats main-branch state.** If on a feature branch with an open PR and clean tree, prefer Bucket B over Bucket C.
3. **Long staleness beats recent shipping.** If last commit was >1 week ago, prefer Bucket D over Bucket C — the user likely needs orientation, not an audit.
4. **No CLAUDE.md beats everything else clean.** Always escalate to Bucket D when the doc is missing — orient before improving.
5. **C vs E (both match a clean main with empty `In Progress`):** their signals overlap by design. Prefer **C** when the recent commits just shipped something substantial — audit the new surface while it's fresh. Prefer **E** when `Next Steps` lists specific actionable items — the user already has a backlog and wants one targeted improvement, not a full audit chain.

---

## What none of these buckets cover (and why that's fine)

- **Active debugging / incident response.** This skill assumes calm-water decision-making. If something is on fire, the user reaches for grep, debugger, and `/bx:review --security` directly — not a routing advisor.
- **Greenfield / new feature work.** That's `/bx:plan` directly. The advisor will route there from Bucket E if `Next Steps` lists it, but it doesn't try to be a feature router.
- **Doc-only sessions.** That's `/bx:save` directly. The advisor will mention it as part of every flow but never as the standalone recommendation — if the user already knows it's a doc session, they don't need routing.
- **Visual redesign execution inside audit chains.** The advisor *can* route to `/bx:webdesign` (Bucket E, web projects, visual appetite) but never sequences it as a step inside an audit flow — it's a self-contained pipeline on its own branch, not a code-health pass that feeds findings downstream.

The advisor's job is the *gray zone*: "I have time, the repo is in some state, what's the best use of my next hour?" That's it.
