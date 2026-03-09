# Review Checklist

Review the code against all 7 categories below. For diff-based reviews, focus on changed lines but flag issues in unchanged code if the changes introduce or expose them.

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
- **Violation of detected codebase conventions** (from convention scan)
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
