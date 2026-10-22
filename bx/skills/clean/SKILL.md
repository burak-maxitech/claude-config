---
name: clean
description: Codebase-wide cleanup audit that finds dead code, unused files, stale dependencies, unused CSS, and technical debt that's safe to remove. Use whenever the user wants to find what can be deleted — dead code, unused files or components, a dependency audit, leftover CSS, stale imports, backup/old files, or general pruning — whether whole-repo or scoped to a module ("any dead code in src/payments?"), phrased formally or casually ("this repo is messy", "let's clean things up"), or by motivation (shrinking the bundle, clearing leftovers after a migration or rewrite). Different from /code-review (which reviews recent changes for quality) — this audits the entire existing codebase for things that can be removed. Not for trivial one-offs like deleting a couple of known lines, fixing broken imports, or configuring a linter.
disable-model-invocation: true
effort: high
allowed-tools: Read, Grep, Glob, Edit, Bash(find:*), Bash(grep:*), Bash(wc:*), Bash(cat:*), Bash(head:*), Bash(tail:*), Bash(sort:*), Bash(uniq:*), Bash(sed:*), Bash(awk:*), Bash(md5sum:*), Bash(git:*), Bash(jq:*), Bash(npm:*), Bash(yarn:*), Bash(pnpm:*), Bash(pip:*), Bash(pip-audit:*), Bash(safety:*), Bash(cargo:*), Bash(composer:*), Bash(govulncheck:*), Bash(bundle:*), Bash(gh:*), Agent
---

# Code Cleanup — Codebase Cleanup Audit

Analyze this codebase like a senior engineer performing a cleanup audit. Identify dead code, unused files, and technical debt that can be safely removed.

## Step 0 — Detect Project Context and Compute Scope

Before scanning anything, gather project context to determine which categories are relevant. This avoids wasting time scanning for CSS in a Python backend or npm dependencies in a Rust project.

### 0.1 — Exclusions first

Read `../arch/references/scan-exclusions.md` (resolve against this skill's base directory). It is the canonical owner of the paths every repo-wide `bx` scanner skips — planted fixture trees (`**/fixtures/**`, `**/testdata/**`, `**/evals/fixtures/**`), vendored and generated output, immutable history archives. Compute the excluded path set **once**, here, and hand it to every agent; agents never re-derive or widen it. This matters most for this skill: a fixture tree holds files that are unused *on purpose*, and a scan that reports them produces true-shaped findings that are false by construction — the run looks successful, which is what makes the omission dangerous.

### 0.2 — Stack detection

**Auto-detect stack from manifests outside the excluded trees only** (skip silently if missing). A manifest inside a fixture tree carries the fixture's stack, not the repo's; if the only manifest sits inside an excluded tree, the conclusion is "no stack detected", not the fixture's stack.

- `package.json` → Node/JS project (scan npm deps, CSS, JSX/TSX). Also check for monorepo: a `workspaces` field, or a sibling `pnpm-workspace.yaml`, means scan each child manifest as its own target.
- `requirements.txt` / `pyproject.toml` / `Pipfile` → Python project (scan pip deps)
- `Cargo.toml` → Rust project (scan cargo deps). If root has `[workspace]` with `members = [...]`, scan each member crate separately.
- `go.mod` → Go project
- `composer.json` → PHP project
- `Gemfile` → Ruby project

**Auto-detect features** (again outside the excluded trees):

- Any `.css`, `.scss`, `.less`, `.module.css` files → enable CSS scan
- Any `__tests__`, `*.test.*`, `*.spec.*`, `tests/`, `pytest.ini`, `jest.config.*` → enable test scan
- `.env*` files, `docker-compose*`, `.github/workflows/` → enable config scan
- `tsconfig.json` → TypeScript project (adjust import scanning)
- `public/`, `assets/`, `static/`, `fonts/` or image/font files anywhere → enable the orphaned-assets check
- `locales/`, `i18n/`, `lang/`, `translations/` → enable the dead-i18n-keys check; `config/*.{yaml,json,toml}`, `settings.py`, `appsettings*.json` → dead-config-keys check
- A lockfile (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`, `Pipfile.lock`) → lockfile-drift check; two of them for different managers is itself a finding
- Not a git repository (`git rev-parse --git-dir` fails) → note it: the agents fall back from `git ls-files` to `find`, and every age-based check (one-off scripts, stale skips) becomes **unavailable** rather than clean (see Step 3).

### 0.3 — Scope

`$ARGUMENTS` may name a directory (`src/`, `app/payments/`). That directory is the **scope**: the file-level categories (unused files, dead code, unused CSS, obsolete patterns, test cleanup) only report items *inside* it, but reference searches still run across the whole repo — a file in `src/payments/` that is imported from `src/billing/` is used, and a scan that only greps inside the scope would call it dead.

The manifest-level categories — unused dependencies (§4), vulnerable dependencies (§4.5) and configuration cruft (§6) — are declared at the repo or workspace root, not inside a directory. Under a directory scope they run only when the scoped directory is itself a workspace root (its own `package.json` / `Cargo.toml` with the workspace's source beneath it); otherwise they are **skipped** and the dashboard says so ("skipped — scoped run; dependencies are declared at the manifest, not in `src/payments/`"). Grepping `src/payments/` for every dependency in the root manifest would flag everything the rest of the app uses.

Store the detected stack, the scope, and the excluded set. Tell the user what you detected in one line, e.g. "Detected: TypeScript/React project with Jest tests. Scanning all 7 categories; excluded 2 fixture trees (26 files)." or "Detected: pnpm monorepo with 5 workspaces. Scope: `packages/api/` (a workspace root — deps scanned for that manifest only)."

## Step 1 — Parallel Scan

Launch the three dedicated scanner subagents in parallel using the Agent tool. They run on **Sonnet** for cost efficiency; the detailed scan instructions live in this skill's `references/` files. The agents' `tools:` lists document the intent of a read-only scan, but Claude Code does not enforce command specifiers such as `Bash(git:*)` (verified 2026-10-20: an agent declared with `Bash(gh:*)` ran `echo` and `git` unblocked), so the scan instructions are the real boundary — never ask an agent to run anything beyond them.

**Pass reference files by absolute path, not by contents.** Each agent has `Read`; tell it to read its scan file in full before scanning, giving the absolute path resolved against this skill's base directory (`<skill base dir>/references/scan-files-code.md`, and so on). Inlining the three files would put ~640 lines into this context to compose three prompts, for no gain — the agent ends up with the same text either way.

**Shared context block** — include verbatim in every Agent call, then the agent-specific lines below:

```
Detected stack: <from Step 0.2, incl. package manager and workspaces>
Scope: <directory from Step 0.3, or "repo root">
Excluded paths: <the set from Step 0.1 — never read or report inside these; never widen the scope>
Scan file: <absolute path> — Read it in full first and follow it exactly.
Filters: <the --files/--code/--css/--deps/--tests flags present, or "none">
--vulns: <enabled|disabled>
Output: structured findings per your scan file's output format, plus its "Unavailable checks" block. Do NOT format a report.
```

**Important orchestration rules:**
- Launch ALL agents in a single turn (one Agent call per agent), setting each call's `subagent_type` to the agent named in its section below (`cleanup-files-code` / `cleanup-deps-config` / `cleanup-styles-tests`) — never a generic subagent, which would skip the baked-in scanning rules and run on the orchestrator's model
- Each agent returns structured findings — do NOT ask agents to format final output
- **Filter flags select agents.** `--files` and `--code` belong to `cleanup-files-code`, `--deps` to `cleanup-deps-config`, `--css` and `--tests` to `cleanup-styles-tests`. With exactly one filter flag, skip the dispatch and scan that single category directly in the main context (read the scan file yourself). With two or more, dispatch only the agents that own them and tell each which of its sections to run. **`--vulns` is NOT a filter flag** — it *adds* Section 4.5 on top of whatever else runs; on its own it means full parallel scan + vuln scan (see Scope Handling)
- If a category is irrelevant to the detected stack (e.g., CSS for a Python CLI tool) or skipped by the scope rule in Step 0.3, skip it entirely
- **Vulnerability scanning is opt-in only.** Section 4.5 (Vulnerable Dependencies) runs ONLY if `$ARGUMENTS` contains `--vulns` or the user explicitly asks for it. Default scans never call `npm audit`, `pip-audit`, etc. — those hit network registries and slow the audit. Tell the user once that a vuln scan is available via `/bx:clean --vulns` if they want it.

### Agent 1: Files & Dead Code Scanner
Dispatch the `cleanup-files-code` subagent with the shared block, `Scan file: <skill base dir>/references/scan-files-code.md`, and the file extensions that matter for the detected stack.

### Agent 2: Dependencies & Config Scanner
Dispatch the `cleanup-deps-config` subagent with the shared block, `Scan file: <skill base dir>/references/scan-deps-config.md`, the detected package manager(s) and the config file paths. **If `--vulns` is in `$ARGUMENTS`, set `--vulns: enabled` so the agent runs Section 4.5 with the audit command for the detected stack.** Otherwise the agent skips that section silently. Skip this agent entirely when Step 0.3 skipped the manifest-level categories.

### Agent 3: Styles & Tests Scanner
**Only spawn if the project has CSS files AND/OR test files.** Dispatch the `cleanup-styles-tests` subagent with the shared block, `Scan file: <skill base dir>/references/scan-styles-tests.md`, and which of the two sections apply. If neither CSS nor tests exist, skip this agent entirely.

## Step 2 — Consolidate & Deduplicate

After all agents return:

1. **Deduplicate** — An unused file containing dead code should appear once (in "Unused Files", not also in "Dead Code")
2. **Cross-reference** — If a dependency is unused AND the only file importing it is also unused, group them together
3. **Normalize risk** — the agents already tag each finding `safe`/`likely_safe`/`needs_investigation`; don't re-derive from scratch, but spot-check against these definitions and downgrade anything that doesn't meet the bar:
   - **Safe** — No references found anywhere in codebase (grep confirms zero hits)
   - **Likely Safe** — Appears unused but has indirect reference patterns (dynamic imports, reflection, string-based lookups)
   - **Needs Investigation** — Used in ways that are hard to statically analyze (metaprogramming, plugin systems, config-driven loading)
4. **Reconcile `quick_win` tags** — the Quick Wins set is closed (empty files, backup-suffixed files, commented-out blocks of 5 or more lines, carve-out-clean unused imports). An agent that tags a whole module or a dead function `quick_win: true` is expressing certainty, not eligibility: downgrade it to `quick_win: false` and keep its `risk`. `--fix` auto-applies what carries the tag, so this reconciliation is what stands between a confident scanner and an unconfirmed deletion.
5. **Collect unavailable checks** — every agent returns an `## Unavailable checks` block naming checks it could not perform (no git history for age-based rules, `gh` absent for TODO issue lookups, an audit tool not installed). These are not findings: they never rank. Carry them to the dashboard so a reader can tell a clean category from one that was never checked.

## Step 3 — Output

The eight dashboard rows are stable; the finer `type:` values the agents return roll into them. Unused Files takes unused sources, backup/empty/duplicate files, one-off scripts, **orphaned assets** and **trivial directories**. Dead Code takes dead functions, **unused exports**, **unused type definitions**, commented-out blocks, unreachable code and unused imports. Unused Dependencies takes unused, misplaced and duplicate packages and **lockfile drift**. Obsolete Patterns takes deprecated APIs, workarounds, **stale feature flags** and resolved TODOs. Config Cruft takes unused env vars, dead CI stages, orphaned tool configs, Docker cruft, **dead i18n keys** and **dead config keys**. Mention the sub-types present in each row's detail section so a reader can see which checks produced the count.

### Summary Dashboard

```
## Cleanup Audit Summary

| Category           | Items Found | Lines Removable | Risk   |
|--------------------|-------------|-----------------|--------|
| Unused Files       | [count]     | [est. lines]    | [risk] |
| Dead Code          | [count]     | [est. lines]    | [risk] |
| Unused CSS         | [count]     | [est. lines]    | [risk] |
| Unused Dependencies| [count]     | —               | [risk] |
| Vulnerable Deps    | [count]     | —               | [severity-mix] |
| Obsolete Patterns  | [count]     | [est. lines]    | [risk] |
| Config Cruft       | [count]     | —               | [risk] |
| Test Cleanup       | [count]     | [est. lines]    | [risk] |
| **Total**          | **[total]** | **[total]**     |        |

Scope: <repo root | directory> · Excluded: <N paths in M fixture/vendored trees> · Unavailable: <none | list>
```

A row has one of three states, and the distinction is the whole point — a reader cannot tell a healthy codebase from an unscanned one unless the dashboard says which:

- **A count** (including 0) — the category applies and was genuinely checked.
- **"— (skipped — not applicable)"** — irrelevant to the stack, or skipped by the scope rule; say which. The "Vulnerable Deps" row shows "(not scanned — pass `--vulns` to enable)" by default.
- **"(unavailable — <reason>)"** on the trailer line — the category ran, but a check inside it could not be performed (no git history, `gh` missing, audit tool not installed). Never let a 0 stand in for a check that did not happen.

### Quick Wins (zero-risk, bulk-approvable)

List items that can be deleted without any review:
- Empty files
- `.backup`, `.old`, `_v2`, `.bak` files
- Commented-out code blocks (5 or more consecutive lines)
- Unused imports — only those the scanner tagged `quick_win: true`; it withholds the tag from side-effect imports, re-export (barrel) files and lint-suppressed lines, where "no reference in this file" is not "unused"

This list is closed. Nothing else is a Quick Win, whatever the scanner tagged (Step 2.4) — not an orphaned asset, not an unused export, not a dead i18n key. Those are one confirmation each under `--fix`.

Format as a checklist:
```
- [ ] Delete `path/to/file.backup.js` (empty/backup file)
- [ ] Remove 12 unused imports across 5 files
- [ ] Remove 3 commented-out blocks (47 lines total)
```

### Detailed Findings

Group into four sections (plus a fifth when `--vulns` was passed):

**Safe to Delete** — Zero references, safe to remove. Include file path and line numbers. For an unused export or type, name the symbol and say the file stays (only the symbol goes) unless the file is otherwise empty; for an orphaned asset give its size; for a trivial directory list what it contains; for a dead i18n or config key give the dotted key and the file.

**Likely Safe** — Appears unused but verify before deleting. Explain what to check.

**Needs Investigation** — Potentially unused but risky. Explain the concern.

**Dependency Cleanup** — Packages to remove, with uninstall commands for the detected package manager.

**Vulnerable Dependencies** *(only present when `--vulns` was passed)* — Packages with known CVEs, grouped by severity (critical → high → moderate → low). Each entry shows the installed version, the vulnerable range, the fixed version (if known), and a fix command. **Never auto-applied** — see the Fix Mode carve-out below.

For each item, state:
1. What it is and where (`file_path:line_number`)
2. Why it appears unused (what was searched, what wasn't found)
3. Any risks or things to verify

Be conservative — when in doubt, flag for investigation rather than deletion.

## Fix Mode (when `--fix` is in $ARGUMENTS)

If the user passes `--fix`, apply Quick Wins automatically:

1. **Check the working tree first.** If it's dirty (uncommitted changes), warn the user and ask whether to stash before doing anything else — never create the branch on top of unrelated changes
2. **Record the starting branch** (`git rev-parse --abbrev-ref HEAD`) — call it `<start>` below; the repo's default branch is not always `main`. Then create a cleanup branch: `git checkout -b cleanup/YYYYMMDD`
3. **Auto-apply Quick Wins only** — delete empty files, remove unused imports, delete `.backup`/`.old` files, remove commented-out blocks of 5 or more lines. Delete files with `git rm` (not bare `rm`) so every removal is staged and trivially reversible; in-file removals use Edit
4. For each "Safe to Delete" item, show it and ask for confirmation before removing
5. If `--aggressive` is also present, include "Likely Safe" items in step 4 (show and ask for confirmation before removing each one) — never auto-delete "Likely Safe" items
6. Skip "Needs Investigation" entirely (report only)
7. **Skip "Vulnerable Dependencies" entirely.** `--fix` never auto-runs `npm audit fix` / `pip-audit --fix` / `cargo audit fix` / equivalents — version bumps can break the app, transitive constraints get rewritten, and lockfile churn is project-policy. Vulnerable deps are report-only; the user runs the suggested `fix_command` themselves after reviewing.
8. Stage all changes and commit: `chore: automated cleanup — [count] items removed`
9. Show a summary diff with `git diff --stat HEAD~1`
10. Tell the user: "Review the changes on the `cleanup/YYYYMMDD` branch. Merge when satisfied, or `git checkout <start> && git branch -D cleanup/YYYYMMDD` to discard the whole branch. To undo in-file edits, run `/rewind` (or press `Esc Esc` on an empty prompt) — checkpoints are captured before each user prompt, not each edit, so one rewind reverts the whole batch of Edit-tool removals applied in a turn. Checkpoints do NOT track files removed with `git rm` (a Bash command): undo deletions by discarding the branch, or with `git restore --staged --worktree <paths>` before the step 8 commit / `git reset --hard HEAD~1` after it. Checkpoints survive a session resume and are deleted after 30 days." Under auto mode, `git restore` and `git reset --hard` are destructive-git forms the classifier may deny unless the user's own message states the intent — say so if the user asks you to run them, and print the exact command.

> **CI gating.** Not self-gating. To pause for approval in headless `claude -p` runs, configure a `PreToolUse` `defer` hook scoped (via the `if` field) to destructive Bash patterns. Full recipe in README "Interop with Claude Code 2.1 features".

## Dry-Run Mode (when `--dry-run` is in $ARGUMENTS)

If the user passes `--dry-run`, show the impact of `--fix` without touching the working tree, the index, or the branch list. Earlier versions staged the removals on a throwaway branch and then reset it, which depended on `git reset --hard` (a command auto mode may deny) and once carried staged deletions back onto the user's branch. Nothing here mutates anything:

1. Run the full scan as normal
2. For every Quick Win and "Safe to Delete" **file** removal, confirm git would remove it with `git rm -n --quiet -- <paths>` (the dry-run flag lists, never removes; a non-zero exit names paths git does not track, which `--fix` would have to `rm` instead — report those separately)
3. For every **in-file** removal (unused imports, commented-out blocks, dead functions), take the removable line count from the finding's `lines:` field — do not edit the file to measure it
4. Render the impact as a `git diff --stat`-shaped table — one row per file (`path | lines removed | whole file?`), a total row, and the count of items that `--fix` would defer for confirmation — so the user sees exactly what `--fix` would stage
5. Tell the user: "This was a dry run — nothing was changed. Run with `--fix` to apply."

## Scope Handling

`$ARGUMENTS` controls scope:

| Argument | Behavior |
|---|---|
| *(empty)* | Full codebase scan, all applicable categories |
| `src/` or `app/` (directory) | Scope the file-level categories to that directory (references still searched repo-wide). Manifest-level categories (§4 deps, §4.5 vulns, §6 config) run only if the directory is a workspace root; otherwise skipped and said so — see Step 0.3 |
| `--files` | Only Section 1 (Unused Files) |
| `--code` | Only Section 2 (Dead Code) |
| `--css` | Only Section 3 (Unused CSS) |
| `--deps` | Only Section 4 (Unused Dependencies) |
| `--vulns` | Adds Section 4.5 (Vulnerable Dependencies) — runs the stack-appropriate audit command (`npm audit`, `pip-audit`, `cargo audit`, etc.). Combinable with anything; on its own, runs the full scan + vuln scan. Network-dependent; never auto-fixed by `--fix`. |
| `--tests` | Only Section 7 (Test Cleanup) |
| `--fix` | Full scan + auto-apply Quick Wins |
| `--dry-run` | Full scan + the impact table `--fix` would produce, computed without changing the tree — nothing is staged, branched or deleted |
| `--aggressive` | In report mode: move "Likely Safe" → "Safe to Delete" in the output. Only actually deletes them if combined with `--fix` (i.e., `--aggressive --fix`). Without `--fix`, it's cosmetic reclassification only |
| Combined (e.g., `src/ --code --deps`) | Scoped + filtered: one filter runs inline, two or more dispatch only the agents that own them (Step 1) |

$ARGUMENTS
