---
name: code-review
description: "Reviews code like a senior engineer. Auto-detects target (uncommitted changes, staged, PR, files), scans codebase conventions, and produces severity-ranked findings with mandatory file:line references. Supports --security (OWASP deep dive), --verify (run tests/lint to validate), and --fix (auto-fix simple issues)."
disable-model-invocation: true
allowed-tools: Read, Edit, Grep, Glob, Bash(git:*), Bash(gh:*), Bash(npm:*), Bash(npx:*), Bash(cargo:*), Bash(python:*), Bash(pip:*)
argument-hint: "[file/dir/PR#/--staged/--last-commit] [--security] [--verify] [--fix]"
---

# /code-review - Comprehensive Code Review

Review this code like a senior engineer with 15+ years of experience. Be thorough but practical — focus on issues that matter, not pedantic style preferences.

> **Fresh-session tip.** For non-trivial reviews — especially of code Claude just wrote in this same session — run `/clear` first or invoke `/code-review` from a fresh `claude` session. Per the official best-practices doc's Writer/Reviewer pattern: *"a fresh context improves code review since Claude won't be biased toward code it just wrote."* Skip this for quick passes on diffs you wrote by hand or for `--last-commit` reviews where you genuinely want session context.

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
1. **Run the project's test suite** — detect test runner from package.json, Cargo.toml, pyproject.toml, etc.
2. **Run linter** if configured (eslint, ruff, clippy, etc.)
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

> **CI gating note.** This skill does not implement its own pause-for-approval flag. If you want to gate `--fix` edits in a headless run, configure a `PreToolUse` hook in `~/.claude/settings.json` that matches `Edit` (or the specific bash patterns you want to guard) and returns `"permissionDecision": "defer"`. The session exits with `stop_reason: "tool_deferred"` and can be resumed with `claude -p --resume <session-id>`. `defer` only works when the turn makes a single tool call — it guards individual edits, not the whole `--fix` run. See README "Interop with Claude Code 2.1 features" for the full recipe.

---

$ARGUMENTS
