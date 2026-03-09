---
name: code-review
description: "Reviews code like a senior engineer. Auto-detects target (uncommitted changes, staged, PR, files), scans codebase conventions, and produces severity-ranked findings with mandatory file:line references."
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(git:*), Bash(gh:*)
argument-hint: "[file/dir/PR#/--staged/--last-commit]"
---

# /code-review - Comprehensive Code Review

Review this code like a senior engineer with 15+ years of experience. Be thorough but practical — focus on issues that matter, not pedantic style preferences.

---

## Step 0: Determine Review Target

Interpret `$ARGUMENTS` to decide what to review:

| Arguments | Behavior |
|-----------|----------|
| *(empty)* | Review **uncommitted changes** — run `git diff` and `git diff --staged` to get the working diff, then review only the changed lines and their surrounding context |
| File path(s) (e.g., `src/auth.ts`) | Review the specified file(s) in full |
| Directory (e.g., `src/api/`) | Review all source files in that directory |
| PR number (e.g., `123` or `#123`) | Fetch PR diff with `gh pr diff 123` and review the PR changes |
| `--staged` | Review only staged changes (`git diff --staged`) |
| `--last-commit` | Review the last commit (`git diff HEAD~1`) |

For diff-based reviews (empty args, PR, --staged, --last-commit): focus on the **changed lines** but read enough surrounding context to understand the full picture. Flag issues in unchanged code only if the changes introduce or expose them.

---

## Step 1: Detect Codebase Conventions

Before reviewing, **quickly scan the codebase for established patterns** so you can review against project conventions, not just general best practices.

**In a single parallel call**, sample 2-3 representative files to detect:
- **Error handling pattern** — do they throw, return Result types, use error codes, or use a custom error class?
- **Naming conventions** — camelCase vs snake_case, prefix conventions (e.g., `I` for interfaces, `use` for hooks)
- **Import style** — absolute vs relative, barrel files, path aliases
- **Test patterns** — testing library, describe/it vs test, mock patterns
- **Logging approach** — console, structured logger, custom wrapper
- **Type patterns** — strict TypeScript, Zod validation, runtime checks

Do NOT spend more than one turn on this. Sample quickly, note the patterns, and move on. If the codebase is small (<10 files), you'll naturally see conventions while reviewing — skip this step.

---

## Step 2: Review Against Checklist

Read `references/review-checklist.md` and review the code against all 7 categories.

---

## Step 3: Present Findings

Read `references/output-format.md` and present findings in the required format.

---

$ARGUMENTS
