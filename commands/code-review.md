# /code-review - Comprehensive Code Review

Review this code like a senior engineer with 15+ years of experience. Be thorough but practical - focus on issues that matter, not pedantic style preferences.

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
- Violation of established patterns in the codebase
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

**Critical** (must fix before merge):
- [List blocking issues with file:line references]

**Important** (should fix, creates technical debt if not):
- [List significant issues]

**Suggestions** (nice to have):
- [List improvements]

**What's Good**:
- [Acknowledge well-written parts - be specific]

For each issue:
1. State the problem clearly
2. Explain *why* it matters
3. Suggest a fix (code snippet only if it clarifies the solution)

Don't rewrite large sections - point to problems and trust the developer to fix them.

---

## Files to Review

$ARGUMENTS
