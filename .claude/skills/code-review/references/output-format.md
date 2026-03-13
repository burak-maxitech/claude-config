# Output Format

## Severity Summary

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

## Detailed Findings

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

## Rules for findings:
1. **Every finding MUST include a `file_path:line_number` reference** — no exceptions
2. State the problem clearly in one sentence
3. Explain *why* it matters (not just what's wrong)
4. Suggest a fix (code snippet only if it clarifies the solution)
5. Don't rewrite large sections — point to problems and trust the developer to fix them
6. For Critical/Important findings, include **git blame context** if it reveals intent (e.g., "This was introduced in commit abc123 as a workaround for X — may now be safe to remove")
7. Mark findings that are **auto-fixable** with `[fixable]` tag if `--fix` is active

## Verification Results (when --verify is active)

Append after all findings:

```markdown
## Verification Results

| Check | Status | Details |
|-------|--------|---------|
| Tests | PASS/FAIL | [N] passed, [M] failed |
| Linter | PASS/FAIL | [N] warnings, [M] errors |

**Findings cross-check:**
- [N] findings confirmed by test/lint failures
- [N] findings not caught by existing tests (coverage gap)
- [N] potential false positives (tests pass despite flagged issue)
```

## Auto-Fix Summary (when --fix is active)

Append after verification (or after findings if --verify not active):

```markdown
## Auto-Fix Applied

| # | File | What was fixed | Category |
|---|------|---------------|----------|
| 1 | `file:line` | Removed unused import `foo` | Suggestion |
| 2 | `file:line` | Added missing type annotation | Suggestion |

**[N] findings auto-fixed. [M] findings require manual review.**

Tests after fix: PASS/FAIL
```
