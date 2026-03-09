---
name: code-cleanup
description: Codebase cleanup audit that finds dead code, unused files, stale dependencies, and technical debt. Use when user mentions dead code, unused files, cleanup, technical debt, code hygiene, dependency audit, removing unused CSS, stale imports, or any form of codebase pruning — even casually like "this repo is messy" or "let's clean things up."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(find:*), Bash(grep:*), Bash(wc:*), Bash(cat:*), Bash(head:*), Bash(tail:*), Bash(sort:*), Bash(uniq:*), Bash(sed:*), Bash(awk:*), Bash(git:*), Bash(jq:*), Bash(npm:*), Bash(pip:*), Bash(cargo:*), Task
---

# Code Cleanup — Codebase Cleanup Audit

Analyze this codebase like a senior engineer performing a cleanup audit. Identify dead code, unused files, and technical debt that can be safely removed.

## Step 0 — Detect Project Context

Before scanning anything, gather project context to determine which categories are relevant. This avoids wasting time scanning for CSS in a Python backend or npm dependencies in a Rust project.

**Auto-detect stack by reading these (skip silently if missing):**

- `package.json` → Node/JS project (scan npm deps, CSS, JSX/TSX)
- `requirements.txt` / `pyproject.toml` / `Pipfile` → Python project (scan pip deps)
- `Cargo.toml` → Rust project (scan cargo deps)
- `go.mod` → Go project
- `composer.json` → PHP project
- `Gemfile` → Ruby project

**Auto-detect features:**

- Any `.css`, `.scss`, `.less`, `.module.css` files → enable CSS scan
- Any `__tests__`, `*.test.*`, `*.spec.*`, `tests/`, `pytest.ini`, `jest.config.*` → enable test scan
- `.env*` files, `docker-compose*`, `.github/workflows/` → enable config scan
- `tsconfig.json` → TypeScript project (adjust import scanning)

Store the detected stack info and use it to skip irrelevant scan categories automatically. Tell the user what you detected and what you're scanning (one line, e.g., "Detected: TypeScript/React project with Jest tests. Scanning all 7 categories.").

## Step 1 — Parallel Scan

Launch subagents in parallel using the Task tool. Each agent handles an independent domain.

**Important orchestration rules:**
- Launch ALL agents in a single turn (one Task call per agent)
- Each agent returns structured findings — do NOT ask agents to format final output
- If `$ARGUMENTS` contains a filter flag (`--files`, `--code`, `--css`, `--deps`, `--tests`), skip parallelization and scan that single category directly in the main context
- If a category is irrelevant to the detected stack (e.g., CSS for a Python CLI tool), skip it entirely

### Agent 1: Files & Dead Code Scanner
Read the `references/scan-files-code.md` file from this skill's directory, then spawn a Task subagent with those instructions. Pass it the detected project stack info so it knows what file extensions matter.

### Agent 2: Dependencies & Config Scanner
Read the `references/scan-deps-config.md` file from this skill's directory, then spawn a Task subagent with those instructions. Pass it the detected package manager and config file paths.

### Agent 3: Styles & Tests Scanner
**Only spawn if the project has CSS files AND/OR test files.** Read the `references/scan-styles-tests.md` file from this skill's directory, then spawn a Task subagent with those instructions. If neither CSS nor tests exist, skip this agent entirely.

## Step 2 — Consolidate & Deduplicate

After all agents return:

1. **Deduplicate** — An unused file containing dead code should appear once (in "Unused Files", not also in "Dead Code")
2. **Cross-reference** — If a dependency is unused AND the only file importing it is also unused, group them together
3. **Classify risk** for each finding:
   - **Safe** — No references found anywhere in codebase (grep confirms zero hits)
   - **Likely Safe** — Appears unused but has indirect reference patterns (dynamic imports, reflection, string-based lookups)
   - **Needs Investigation** — Used in ways that are hard to statically analyze (metaprogramming, plugin systems, config-driven loading)

## Step 3 — Output

### Summary Dashboard

```
## Cleanup Audit Summary

| Category           | Items Found | Lines Removable | Risk   |
|--------------------|-------------|-----------------|--------|
| Unused Files       | [count]     | [est. lines]    | [risk] |
| Dead Code          | [count]     | [est. lines]    | [risk] |
| Unused CSS         | [count]     | [est. lines]    | [risk] |
| Unused Dependencies| [count]     | —               | [risk] |
| Obsolete Patterns  | [count]     | [est. lines]    | [risk] |
| Config Cruft       | [count]     | —               | [risk] |
| Test Cleanup       | [count]     | [est. lines]    | [risk] |
| **Total**          | **[total]** | **[total]**     |        |
```

If a category was skipped (irrelevant to project), show "—" across the row and note "(skipped — not applicable)" instead of a risk level.

### Quick Wins (zero-risk, bulk-approvable)

List items that can be deleted without any review:
- Empty files
- `.backup`, `.old`, `_v2`, `.bak` files
- Commented-out code blocks (>5 lines)
- Unused imports

Format as a checklist:
```
- [ ] Delete `path/to/file.backup.js` (empty/backup file)
- [ ] Remove 12 unused imports across 5 files
- [ ] Remove 3 commented-out blocks (47 lines total)
```

### Detailed Findings

Group into four sections:

**Safe to Delete** — Zero references, safe to remove. Include file path and line numbers.

**Likely Safe** — Appears unused but verify before deleting. Explain what to check.

**Needs Investigation** — Potentially unused but risky. Explain the concern.

**Dependency Cleanup** — Packages to remove, with uninstall commands for the detected package manager.

For each item, state:
1. What it is and where (`file_path:line_number`)
2. Why it appears unused (what was searched, what wasn't found)
3. Any risks or things to verify

Be conservative — when in doubt, flag for investigation rather than deletion.

## Fix Mode (when `--fix` is in $ARGUMENTS)

If the user passes `--fix`, apply Quick Wins automatically:

1. Create a cleanup branch: `git checkout -b cleanup/YYYYMMDD`
2. **Auto-apply Quick Wins only** — delete empty files, remove unused imports, delete `.backup`/`.old` files, remove commented-out blocks >5 lines
3. For each "Safe to Delete" item, show it and ask for confirmation before removing
4. Skip "Likely Safe" and "Needs Investigation" entirely (report only)
5. Stage all changes and commit: `chore: automated cleanup — [count] items removed`
6. Show a summary diff with `git diff --stat HEAD~1`
7. Tell the user: "Review the changes on the `cleanup/YYYYMMDD` branch. Merge when satisfied, or `git checkout main && git branch -D cleanup/YYYYMMDD` to discard."

If the working tree is dirty (uncommitted changes), warn the user and ask whether to stash first.

## Scope Handling

`$ARGUMENTS` controls scope:

| Argument | Behavior |
|---|---|
| *(empty)* | Full codebase scan, all applicable categories |
| `src/` or `app/` (directory) | Scope to that directory only |
| `--files` | Only Section 1 (Unused Files) |
| `--code` | Only Section 2 (Dead Code) |
| `--css` | Only Section 3 (Unused CSS) |
| `--deps` | Only Section 4 (Unused Dependencies) |
| `--tests` | Only Section 7 (Test Cleanup) |
| `--fix` | Full scan + auto-apply Quick Wins |
| `--aggressive` | Move "Likely Safe" → "Safe to Delete" (for well-tested codebases) |
| Combined (e.g., `src/ --code --deps`) | Scoped + filtered |

When a single filter is active, skip subagent parallelization and scan directly.

$ARGUMENTS
