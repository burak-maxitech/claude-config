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
/code-review → /review-deep → /review-deep --verify → commit → /update-docs
```

Why this order:
- `/code-review` (built-in, lightweight) first because it works on *what you just wrote* — best signal closest to the change. Fix obvious quality issues before a structured review sees them.
- `/review-deep` next for diff-scoped correctness/security — same diff scope but more rigorous (custom skill with codebase-convention scan + git-blame context).
- `/review-deep --verify` runs your test/lint suite (parallel-backgrounded since S19) — catches regressions before commit.
- Commit, then `/update-docs` at session end so the work is captured in `CLAUDE.md`.

**Alternative:** *If the change touches auth, payments, data migrations, or anything that pages someone at 3 AM:*
```
/code-review → /review-deep --security → /review-deep --verify → commit → push → /ultrareview <PR#> → merge → /update-docs
```

`/ultrareview` adds 5–20 cloud subagents (10–20 min) and is overkill for routine work but the right call for high-risk code.

---

## B. Pre-merge verification

**Signal:**
- Clean working tree (`git status --porcelain` empty)
- On a feature branch with `gh pr view` returning an open PR
- Branch is N commits ahead of main

**Mental model:** "Code is committed and pushed. PR is open. Should I do anything before merging?"

**Recommended flow:**
```
/review-deep --security → /ultrareview <PR#>
```

Why:
- `/review-deep --security` is fast in-session and surfaces OWASP-flavored issues across the diff.
- `/ultrareview` is the deeper cloud-based pass. Worth it for any non-trivial PR that's about to merge.

**Alternative:** *If the PR is small / low-risk (docs, config, copy changes, refactors with no behavior change):*
```
/code-review (no flags)
```

Skip `/ultrareview` for trivial PRs — the cloud cost and 10–20 min wait isn't justified.

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
/code-cleanup → /architecture-review → /test-review → /architecture-review --plan → /plan-feature <phase>
```

**Recommended flow** *(when `is_web: true`)*:
```
/code-cleanup → /architecture-review → /test-review → /seo-review → /architecture-review --plan → /plan-feature <phase>
```

Why this order:
- `/code-cleanup` first deletes whole files/deps that are dead — cleaner signal for everything downstream.
- `/architecture-review` then audits the *remaining* code for structural complexity, refactor opportunities, perf suspects, and over-engineering.
- `/test-review` audits the test suite itself — coverage gaps in critical code AND wasteful/redundant tests. Run after the structural audits so coverage gaps are measured against post-cleanup code.
- `/seo-review` *(web projects only)* audits SEO + Generative Engine Optimization with fresh fetched best practices. Run after structural cleanup so the SEO scan reflects the post-cleanup site. Score is tracked over time in `docs/seo-history.md`.
- `/architecture-review --plan` turns findings into phased work.
- `/plan-feature` per phase before implementing.

**Alternative:** *If you only have ~30 minutes and want one quick win, not a full audit:*
```
/architecture-review (default mode, no --plan, no --fix)
```

The default `/architecture-review` report includes a "Code we can delete: N lines" top-line metric and ranks findings by quick-wins. Pick one and act on it; come back another day for the full flow.

---

## D. Orient + audit

**Signal:**
- Clean working tree
- Long since last commit (>1 week) **OR** no `CLAUDE.md` at repo root **OR** auto-memory is empty/missing
- May be a repo the user is unfamiliar with

**Mental model:** "I don't have a clear picture of what this repo is or where it stands. Help me orient."

**Recommended flow:**
```
/resume-work deep → /code-cleanup → /architecture-review → /test-review → /update-docs
```

Why:
- `/resume-work deep` reads the full reference set (`docs/session-history.md`, `docs/completed-work.md`, `docs/key-decisions.md`) and runs the health-check ladder. If `CLAUDE.md` is missing, it surfaces the gap and recommends `/update-docs` first.
- `/code-cleanup` next because it works without `CLAUDE.md` context — pure structural deletion signal.
- `/architecture-review` for the structural picture once dead code is gone.
- `/test-review` for the test suite picture — both coverage gaps and waste. Surfaces what to write next and what to delete. Skip if `git ls-files` shows no test files.
- `/update-docs` at the end populates `CLAUDE.md` and auto-memory so the next session starts oriented.

**Alternative:** *If `CLAUDE.md` is completely missing and the repo isn't yours:*
```
/update-docs (CREATE mode, scaffolds CLAUDE.md from the codebase) → /resume-work → /architecture-review
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
/architecture-review (or /test-review for test suite focus, or /seo-review when is_web: true) → pick one finding → /plan-feature → implement → /code-review → /update-docs
```

Why:
- `/architecture-review` is the highest-signal entry point when nothing is on fire — it surfaces deletions, refactors, and perf wins ranked by impact. Use `/test-review` instead when the test suite specifically is what you want to invest in (coverage gaps in critical code + redundant/wasteful tests). When `is_web: true`, `/seo-review` is also a strong inline option — SEO/GEO findings tend to deliver visible business impact (search ranking, AI citation) and the skill tracks scores over time in `docs/seo-history.md` so progress compounds across runs.
- Pick **one** finding (don't try to do them all).
- `/plan-feature` to scope the change before writing code.
- Then the standard implement → review → docs loop.

**Alternative:** *If `CLAUDE.md` Next Steps already lists a specific item you want to tackle:*
```
/plan-feature → implement → /code-review → /review-deep --verify → /update-docs
```

Skip the audit — you already know what to work on. Go directly into the planning + implement loop.

*(In both flows above, the bare `/code-review` at the implement stage = the built-in lightweight diff scan; reach for `/review-deep` instead if you want the thorough senior-engineer treatment with `--security`/`--verify`/`--fix`.)*

---

## Tie-breaker rules

When two buckets match the signal pattern roughly equally:

1. **Uncommitted changes always wins.** A non-empty `git status` is the strongest signal. Bucket A trumps everything except an explicit user override.
2. **Open PR beats main-branch state.** If on a feature branch with an open PR and clean tree, prefer Bucket B over Bucket C.
3. **Long staleness beats recent shipping.** If last commit was >1 week ago, prefer Bucket D over Bucket C — the user likely needs orientation, not an audit.
4. **No CLAUDE.md beats everything else clean.** Always escalate to Bucket D when the doc is missing — orient before improving.

---

## What none of these buckets cover (and why that's fine)

- **Active debugging / incident response.** This skill assumes calm-water decision-making. If something is on fire, the user reaches for grep, debugger, and `/review-deep --security` directly — not a routing advisor.
- **Greenfield / new feature work.** That's `/plan-feature` directly. The advisor will route there from Bucket E if `Next Steps` lists it, but it doesn't try to be a feature router.
- **Doc-only sessions.** That's `/update-docs` directly. The advisor will mention it as part of every flow but never as the standalone recommendation — if the user already knows it's a doc session, they don't need routing.

The advisor's job is the *gray zone*: "I have time, the repo is in some state, what's the best use of my next hour?" That's it.
