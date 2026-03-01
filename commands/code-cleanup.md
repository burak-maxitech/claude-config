# /code-cleanup - Codebase Cleanup Analysis

Analyze this codebase like a senior engineer performing a cleanup audit. Identify dead code, unused files, and technical debt that can be safely removed.

---

## Execution Strategy: Parallel Scanning

To analyze efficiently, **scan multiple categories in parallel using subagents:**

### Turn 1 — Launch parallel scans:
- **Agent 1 (Files & Code):** Scan for unused files (Section 1), dead code (Section 2), and commented-out blocks
- **Agent 2 (Dependencies & Config):** Scan for unused dependencies (Section 4), configuration cruft (Section 6), and obsolete patterns (Section 5)
- **Agent 3 (Styles & Tests):** Scan for unused CSS (Section 3) and test cleanup (Section 7) — skip if project has no CSS or tests

### Turn 2 — Consolidate:
- Merge results from all agents
- Cross-reference findings (e.g., an unused file may also contain dead code — deduplicate)
- Classify each finding into the output categories

Do NOT scan categories one by one sequentially. Use the Agent tool to parallelize.

---

## What to Scan

## 1. Unused Files
- Script files that were one-time use (migrations, setup scripts, data fixes)
- Orphaned files not imported/referenced anywhere
- Duplicate files or old versions (file.old.js, file.backup.py, file_v2.ts)
- Empty or placeholder files
- Leftover test data files

## 2. Dead Code
- Functions/methods never called
- Classes never instantiated
- Unreachable code (after return, inside always-false conditions)
- Commented-out code blocks
- Unused imports/dependencies

## 3. Unused CSS
- CSS classes not referenced in any HTML, JSX, TSX, or template files
- Unused ID selectors
- Duplicate CSS rules (same selector defined multiple times)
- Overridden styles that have no effect
- Vendor prefixes no longer needed for supported browsers
- Empty rulesets
- CSS variables (custom properties) never used
- Dead media queries for breakpoints not used in the app
- Leftover styles for deleted components

## 4. Unused Dependencies
- Packages in package.json/requirements.txt/etc. not actually imported
- Dev dependencies that are no longer needed
- Duplicate packages serving same purpose

## 5. Obsolete Patterns
- Deprecated API usage that should be updated
- Old workarounds for bugs that are now fixed
- Feature flags for features fully rolled out
- TODO/FIXME comments for issues already resolved

## 6. Configuration Cruft
- Unused environment variables
- Dead configuration options
- Orphaned database migrations that were never run
- Stale CI/CD pipeline stages

## 7. Test Cleanup
- Tests for deleted features
- Skipped tests that have been skipped for too long
- Test utilities no longer used
- Snapshot files for deleted components

---

## Output Format

### Summary Dashboard

Present this at the top of your response before any details:

```markdown
## Cleanup Audit Summary

| Category | Items Found | Lines Removable | Risk Level |
|----------|------------|-----------------|------------|
| Unused Files | [count] | [est. lines] | Safe/Caution |
| Dead Code | [count] | [est. lines] | Safe/Caution |
| Unused CSS | [count] | [est. lines] | Safe/Caution |
| Unused Dependencies | [count] | — | Safe/Caution |
| Obsolete Patterns | [count] | [est. lines] | Safe/Caution |
| Configuration Cruft | [count] | — | Safe/Caution |
| Test Cleanup | [count] | [est. lines] | Safe/Caution |
| **Total** | **[total]** | **[total lines]** | |
```

### Quick Wins

List zero-risk deletions the user can approve in bulk without individual review:
- Empty files
- `.backup`, `.old`, `_v2` files
- Commented-out code blocks (>5 lines)
- Unused imports

Format as a single actionable list:
```markdown
### Quick Wins (zero-risk, bulk-approvable)
- [ ] Delete `path/to/file.backup.js` (empty/backup file)
- [ ] Remove 12 unused imports across 5 files
- [ ] Remove 3 commented-out blocks (47 lines total)
```

### Detailed Findings

**Safe to Delete** (no references found, safe to remove):
- [List files/code with confidence level]

**Likely Safe** (verify before deleting):
- [List items that appear unused but need confirmation]

**Needs Investigation** (potentially unused but risky):
- [List items that require deeper analysis]

**Recommended Dependency Cleanup**:
- [List packages to remove]

For each item:
1. State what it is and where it's located (`file_path:line_number`)
2. Explain why it appears unused
3. Note any risks or things to verify before deletion

Be conservative - when in doubt, flag for investigation rather than deletion.

---

## Scope Handling

`$ARGUMENTS` determines what to scan:

| Arguments | Behavior |
|-----------|----------|
| *(empty)* | Full codebase scan — all 7 categories |
| `src/` or `app/` (directory path) | Scope scan to that directory only |
| `--files` | Only scan Section 1 (Unused Files) |
| `--code` | Only scan Section 2 (Dead Code) |
| `--css` | Only scan Section 3 (Unused CSS) |
| `--deps` | Only scan Section 4 (Unused Dependencies) |
| `--tests` | Only scan Section 7 (Test Cleanup) |
| `--aggressive` | Move "Likely Safe" items into "Safe to Delete" — for codebases with good test coverage |
| Combined (e.g., `src/ --code --deps`) | Scoped + filtered |

When a filter is active, skip the parallel agent strategy and scan the single category directly.

---

$ARGUMENTS
