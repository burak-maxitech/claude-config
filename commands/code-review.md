# /code-review - Comprehensive Code Review

Review this code like a senior engineer with 15+ years of experience. Be thorough but practical - focus on issues that matter, not pedantic style preferences.

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

## What to Review

## 1. Correctness & Bugs
- Logic errors, off-by-one mistakes, race conditions
- Null/undefined handling and edge cases
- Incorrect assumptions about data types or structures
- Error handling gaps (unhappy paths)
- State management issues

## 2. Security
- Input validation and sanitization
- Authentication/authorization flaws
- Injection vulnerabilities (SQL, XSS, command injection)
- Sensitive data exposure (logs, errors, responses)
- Insecure dependencies or configurations
- CSRF, SSRF, or other web vulnerabilities if applicable

## 3. Performance
- Unnecessary computations or redundant operations
- N+1 queries or inefficient database access patterns
- Memory leaks or excessive allocations
- Missing caching opportunities
- Blocking operations that should be async

## 4. Maintainability & Readability
- Unclear naming or confusing abstractions
- Functions/classes doing too much (SRP violations)
- Code that requires comments to understand (vs. self-documenting)
- Inconsistent patterns within the codebase
- Magic numbers or hardcoded values that should be constants

## 5. Architecture & Design
- Tight coupling or poor separation of concerns
- Missing or leaky abstractions
- **Violation of detected codebase conventions** (from Step 1)
- Scalability concerns
- Testability issues

## 6. Error Handling & Resilience
- Silent failures or swallowed exceptions
- Missing retry logic for transient failures
- Inadequate logging for debugging production issues
- Missing timeouts on external calls
- Graceful degradation gaps

## 7. Testing Considerations
- Untestable code structures
- Missing test coverage for critical paths
- Brittle test patterns if tests are included

---

## Output Format

### Severity Summary

Present this at the top of your response before any details:

```markdown
## Review Summary

| Severity | Count |
|----------|-------|
| Critical | [n] |
| Important | [n] |
| Suggestions | [n] |

**Review target:** [description — e.g., "uncommitted changes (3 files)", "PR #123 (14 files)", "src/auth.ts"]
**Conventions detected:** [brief — e.g., "TypeScript strict, Zod validation, custom AppError class, vitest"]
```

### Detailed Findings

**Critical** (must fix before merge):
- `file_path:line_number` — [Issue description]. *Why it matters:* [explanation]. *Fix:* [suggestion]

**Important** (should fix, creates technical debt if not):
- `file_path:line_number` — [Issue description]. *Why it matters:* [explanation]. *Fix:* [suggestion]

**Suggestions** (nice to have):
- `file_path:line_number` — [Issue description]. *Fix:* [suggestion]

**Convention Violations** (inconsistent with codebase patterns):
- `file_path:line_number` — [What's inconsistent]. *Project convention:* [what the rest of the codebase does]

**What's Good**:
- [Acknowledge well-written parts - be specific with `file_path:line_number` references]

### Rules for findings:
1. **Every finding MUST include a `file_path:line_number` reference** — no exceptions
2. State the problem clearly in one sentence
3. Explain *why* it matters (not just what's wrong)
4. Suggest a fix (code snippet only if it clarifies the solution)
5. Don't rewrite large sections — point to problems and trust the developer to fix them

---

$ARGUMENTS
