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
