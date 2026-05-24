---
name: review-deep
description: "Senior-engineer code review (thorough tier). Auto-detects target (uncommitted, staged, PR, files), scans codebase conventions, and produces severity-ranked findings with mandatory file:line references. Supports `--security` (OWASP deep dive), `--verify` (run tests/lint to validate), and `--fix` (auto-fix simple issues)."
when_to_use: "When user wants more rigor than the lightweight built-in `/code-review` but doesn't need `/ultrareview`'s cloud fleet. Slots between the built-in `/code-review` (fast diff scan, daily default) and `/ultrareview` (cloud, 5+ verifying subagents, high-risk pre-merge). Trigger phrases: 'review this carefully', 'security review', 'thorough review', 'check this PR for bugs', or passing `--security`/`--verify`/`--fix` flags."
disable-model-invocation: true
effort: high
allowed-tools: Read, Edit, Grep, Glob, Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(npx:*), Bash(cargo:*), Bash(python:*), Bash(pip:*)
argument-hint: "[file/dir/PR#/--staged/--last-commit] [--security] [--verify] [--fix]"
---

# /review-deep - Comprehensive Code Review

Review this code like a senior engineer with 15+ years of experience. Be thorough but practical — focus on issues that matter, not pedantic style preferences.

> **Fresh-session tip.** For non-trivial reviews — especially of code Claude just wrote in this same session — run `/clear` first or invoke `/review-deep` from a fresh `claude` session. Per the official best-practices doc's Writer/Reviewer pattern: *"a fresh context improves code review since Claude won't be biased toward code it just wrote."* Skip this for quick passes on diffs you wrote by hand or for `--last-commit` reviews where you genuinely want session context.

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
| `--security` | Deep security-focused review against OWASP Top 10 (see checklist) |
| `--verify` | After review, run tests and linters to validate findings are real |
| `--fix` | Auto-fix simple findings (unused imports, missing types, formatting) after review |

Flags can be combined (e.g., `src/api/ --security --verify`).

For diff-based reviews (empty args, PR, --staged, --last-commit): focus on the **changed lines** but read enough surrounding context to understand the full picture. Flag issues in unchanged code only if the changes introduce or expose them.

### Large Diff Guard

Before starting the review, check the diff size:
1. Count changed lines: `git diff --stat` (or `gh pr diff --stat` for PRs)
2. If **>500 changed lines**: warn the user and suggest reviewing by directory or file group to avoid context exhaustion
3. If **>1000 changed lines**: strongly recommend splitting the review — offer to generate a file-group plan:
   > "This PR touches [N] files with [M] changed lines. I recommend reviewing in chunks. Want me to group the files by module and review each group separately?"
4. For chunked reviews, present a combined summary at the end

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

> If a large file is being sampled via an MCP-backed reader and the default result size truncates it, the MCP server can set `_meta["anthropic/maxResultSizeChars"]` per tool (up to 500K chars, added in Claude Code 2.1.91) to return the full file in one call. No skill-side change required; this is a server-side knob to be aware of.

---

## Step 1.5: Kick Off Verification Early (when `--verify` is in $ARGUMENTS)

If `--verify` is in `$ARGUMENTS`, start the test runner and linter **now**, in background, so they complete in parallel with the review work in Steps 2–4.

1. Detect test/lint commands from project config (`package.json` scripts, `pyproject.toml`, `Cargo.toml`, `Makefile`, plugin `bin/test` on `$PATH`)
2. Launch each as a Bash call with `run_in_background: true` — you'll be notified when each completes
3. Note the commands and expected output locations; Step 5 collects results

This parallelizes ~10–60s of test/lint time with the review itself. If no runnable test/lint command is obvious, skip — Step 5 will fall back to running synchronously.

Skip Step 1.5 entirely when `--verify` is not set, or for diff-based reviews where the user is reviewing code they haven't checked out (PR reviews via `gh pr diff`).

---

## Step 2: Review Against Checklist

Read `references/review-checklist.md` and review the code against all applicable categories.

If `--security` is in `$ARGUMENTS`, also read `references/security-deep-dive.md` and run the OWASP-focused review.

---

## Step 3: Git Blame Context (for Critical/Important findings)

For each **Critical** or **Important** finding, run `git blame -L <start>,<end> <file>` on the relevant lines to understand:
- **Who** wrote the code and **when**
- **Why** it was written that way (check the commit message with `git log -1 <commit-hash> --format="%s"`)
- Whether the pattern was **intentional** (e.g., a known workaround, a deliberate tradeoff)

Include this context in the finding if it changes the severity or recommendation. If git blame reveals a deliberate decision with a clear rationale, downgrade the finding or note the context.

Skip git blame for trivial suggestions and for files with no git history (new files).

---

## Step 4: Present Findings

Read `references/output-format.md` and present findings in the required format.

---

## Step 5: Verification (when `--verify` is in $ARGUMENTS)

After presenting findings, validate them:
1. **Collect test output** from the background task started in Step 1.5 (or run the test command synchronously now if Step 1.5 was skipped)
2. **Collect linter output** from the background task started in Step 1.5 (or run synchronously now)
3. **Cross-check findings**: if a finding claims "this will break X" but tests pass, note the discrepancy — the finding may be a false positive or tests may be insufficient
4. Append a **Verification Results** section to the output:
   ```
   ## Verification Results
   - Tests: [PASS/FAIL] ([N] passed, [M] failed)
   - Linter: [PASS/FAIL] ([N] warnings, [M] errors)
   - Findings validated: [N]/[total] confirmed by test/lint results
   ```

---

## Step 6: Auto-Fix (when `--fix` is in $ARGUMENTS)

After review (and verification if `--verify` also present), auto-fix **only simple, safe findings**:

**Safe to auto-fix:**
- Unused imports / dead requires
- Missing type annotations where types are obvious
- Formatting issues (trailing whitespace, missing semicolons per project style)
- Simple null checks where the fix pattern is clear from codebase conventions

**Never auto-fix:**
- Logic changes, architectural issues, or anything requiring design decisions
- Security vulnerabilities (these need human judgment on the right fix)
- Performance optimizations (tradeoffs involved)
- Anything marked Critical

After fixing, show a summary of what was changed and run tests again to confirm nothing broke. End the summary with this line:

> **If anything looks wrong, press `Esc Esc` or run `/rewind` to undo these edits.** Checkpoints are created automatically before each edit and persist across sessions.

> **CI gating.** Not self-gating. To pause for approval in headless `claude -p` runs, configure a `PreToolUse` `defer` hook scoped (via the `if` field) to `Edit` or specific Bash patterns. Full recipe in README "Interop with Claude Code 2.1 features".

---

$ARGUMENTS
