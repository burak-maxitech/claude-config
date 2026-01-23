# /code-cleanup - Codebase Cleanup Analysis

Analyze this codebase like a senior engineer performing a cleanup audit. Identify dead code, unused files, and technical debt that can be safely removed.

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

**Safe to Delete** (no references found, safe to remove):
- [List files/code with confidence level]

**Likely Safe** (verify before deleting):
- [List items that appear unused but need confirmation]

**Needs Investigation** (potentially unused but risky):
- [List items that require deeper analysis]

**Recommended Dependency Cleanup**:
- [List packages to remove]

For each item:
1. State what it is and where it's located
2. Explain why it appears unused
3. Note any risks or things to verify before deletion

Be conservative - when in doubt, flag for investigation rather than deletion.

---

## Scope

$ARGUMENTS
