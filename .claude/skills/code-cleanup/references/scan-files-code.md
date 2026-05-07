# Files & Dead Code Scanner

You are a subagent scanning for unused files and dead code. Be thorough but conservative — false positives waste the user's time, false negatives are acceptable since this is an audit, not an auto-delete.

## Input

You will receive project stack info (language, framework, file extensions). Use it to focus your search.

## 1. Unused Files

Scan for files that are never imported, required, or referenced anywhere else in the codebase.

**Method:**
- List source files with `git ls-files` (honors `.gitignore` automatically — no need to maintain a hardcoded skip list — and is much faster than `find` on large repos). Fall back to `find` only if the project isn't a git repo.
- **Batch the reference search.** Do not loop one-grep-per-file. With hundreds of files that's hundreds of Grep calls. Make a single `Grep` call with a regex alternating across all candidate basenames, e.g. pattern `\b(userProfile|authMiddleware|dateUtils|...)\b` with `output_mode: count` so each file's match count comes back in one shot. Then bucket: any basename with zero hits across all files (excluding self-matches in the basename's own file) is a "potentially unused" candidate. For ~50–100 candidates per call, this collapses 50–100 Grep runs into one.
- A file is "unused" if zero other files reference it AND it's not an entry point (like `index.*`, `main.*`, `app.*`, `server.*`, `manage.py`, `setup.py`, `__init__.py`)

**Also flag:**
- Files with backup/old suffixes: `.old`, `.bak`, `.backup`, `_v2`, `_old`, `_backup`, `.orig`, `Copy of *`
- Empty files (0 bytes or only whitespace/comments)
- One-time scripts: files in `scripts/`, `migrations/`, or `tools/` that look like one-offs. Batch-check with a single command: `git log --format="%H %ai" --diff-filter=A -- scripts/ tools/ migrations/` to get creation dates for all files in those directories, then filter for files with only one commit touching them that are >6 months old. Avoid running `git log` per-file — it's too slow on large repos.
- Duplicate files: same content, different names (compare with `md5sum` on a sample)

**Do NOT flag:**
- Config files (`.env*`, `*.config.*`, `tsconfig.json`, `jest.config.*`, etc.)
- Entry points and framework-required files
- Files referenced in config files (webpack, vite, etc.)
- Type declaration files (`.d.ts`) unless truly orphaned

## 2. Dead Code

Scan for code that exists but is never executed.

**Method — Functions/Methods:**
- Extract all function/method definitions using grep patterns appropriate for the project language
- **Batch the call-site search.** Make a single `Grep` call alternating across all extracted function names: pattern `\b(funcA|funcB|funcC|...)\b` with `output_mode: count`. Bucket matches by name; any name whose only match is its own definition line is a "dead" candidate.
- A function is "dead" if it has zero call sites AND is not exported from a public API

**Method — Commented-out code:**
- Find blocks of 5+ consecutive commented lines that look like code (contain `=`, `{`, `(`, `function`, `class`, `def`, `import`, `return`)
- Report the file, line range, and a short preview

**Method — Unreachable code:**
- Look for code after unconditional `return`, `throw`, `exit`, `break`, `continue` statements
- Look for branches that are always false (e.g., `if (false)`, `if 0:`, `#if 0`)

**Method — Unused imports:**
- For each import/require statement, check if the imported name is used anywhere in that file
- This is a Quick Win category — high confidence, safe to auto-remove

**Output format (return as structured text):**

```
## Unused Files
- path: <file_path>
  reason: <why it's unused>
  lines: <line count>
  risk: safe|likely_safe|needs_investigation
  quick_win: true|false

## Dead Code
- path: <file_path>
  location: <start_line>-<end_line>
  type: function|commented_block|unreachable|unused_import
  name: <function name or description>
  reason: <why it appears dead>
  lines: <removable line count>
  risk: safe|likely_safe|needs_investigation
  quick_win: true|false
```

Limit to top 50 findings per category. If there are more, note the count and say "showing top 50 by confidence."