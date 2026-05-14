# --fix Mode (test-review)

Apply T01 (assertion-free test) deletions with per-finding diff preview. **This mode is deliberately the narrowest possible — only one smell type is fix-eligible.** Everything else routes to `--plan`.

## Why T01 only

A test with zero assertions cannot fail meaningfully. Deletion is provably safe in a way no other test rewrite is:

- T02 (weak assertion) — deletion would *remove* coverage, not fix it. Needs human-written replacement.
- T03 (mock-heavy) — the right behavior assertion depends on domain knowledge the catalog can't encode.
- T04 (mystery guest) — the fix is *adding* explicit setup, not deleting.
- T05 (redundant) — even with high similarity, boundary-value coverage is invisible to static analysis. Conservative route to `--plan`.
- snapshot_heavy — replacement assertions are domain-specific.
- coverage gaps — the fix is *writing* tests, not deleting.
- flakiness — the fix is *investigation*, not deletion (deleting a flaky test hides the underlying race).

T01 is unique: the test asserts nothing, so removing it cannot regress coverage of anything that was actually being tested. Worst case the user re-adds it with proper assertions later.

## Hard restrictions

A finding is `--fix-eligible` only if **all** are true:

1. `smell_id == "T01"`
2. `respects_documented_decision: true`
3. `certainty >= 0.7` (the T01 floor — already enforced at scan time, but re-verify)
4. The orchestrator's assertion-helper allowlist scan ran successfully (`helper_allowlist_size` is present in test-quality's footer). If for any reason it didn't, **abort the entire --fix pass** with an error — never delete T01 findings without the false-positive guard.
5. The test body contains no `console.log` / `print(...)` / `eprintln!` / `fmt.Println` immediately followed by a comment like `// TODO assert` or `# TODO`. These are in-flight tests; lower certainty to 0.5 at scan time, but defensively re-check here.

Anything failing any of these auto-routes to `--plan` instead, with a one-line note:

> Auto-routed N findings to --plan (not T01, low-certainty, or conflicts with documented posture).

## Pre-flight check

Before showing the first finding, verify:

```
1. test-quality's footer included `helper_allowlist_size: <N>` — if missing or N == 0, surface a warning:
   "WARNING: Project-defined assertion helper scan returned 0 helpers. This is unusual unless the project uses only framework matchers. Continuing anyway, but review each diff carefully."

2. Confirm with user once before starting:
   "About to walk N T01 findings for per-finding deletion gate. Continue? [y/n]"
```

Show the count of T01 findings the user will see and the count auto-routed to `--plan`.

## Per-finding gate flow

For each eligible finding, in rank order:

```
─────────────────────────────────────────────────────
[Finding 1 of 5] T01 — Assertion-free test
tests/auth/login.test.ts:142-156

Test name: "logs in valid user"

Current test body:
  it('logs in valid user', async () => {
    const user = await createUser({ email: 'a@b.com' });
    const session = await login(user.email, 'password');
    // Asserts: none found.
    // Helper allowlist scanned for these names: assertValidSession, expectAuthenticated, ...
  });

Evidence:
  - Body has 3 statements, 0 assertion calls
  - No assertion-helper names from allowlist matched
  - No after-hooks contain assertions
  - Test name does NOT match "does not throw" / "is callable" / "is defined" patterns

Proposed change (diff):
  --- tests/auth/login.test.ts
  +++ tests/auth/login.test.ts
  @@ -142,15 +142,1 @@
  -  it('logs in valid user', async () => {
  -    const user = await createUser({ email: 'a@b.com' });
  -    const session = await login(user.email, 'password');
  -  });

After this deletion:
  - Surrounding `describe('login', ...)` block still has 4 other tests → no parent prompt.
  - File still has 11 tests → no file prompt.

Apply? [y / n / skip / abort]
```

User responses:
- `y` — apply via `Edit` (delete the test block). Advance to next finding.
- `n` — record "rejected" (do not re-show this run). Advance.
- `skip` — record "skipped (revisit later)". Advance.
- `abort` — stop the whole `--fix` pass. Already-applied edits stay; use `/rewind` to undo individually.

## Cascading prompts (after each deletion)

After applying a T01 deletion, check two conditions before advancing to the next finding:

### 1. Parent block empty?

If the surrounding `describe(...)` / `context(...)` / `class Test*:` (Python) / `mod tests {...}` (Rust) block now has zero child tests, prompt separately:

```
─────────────────────────────────────────────────────
Cascade: parent block now empty

Block: describe('login', () => { ... })  at tests/auth/login.test.ts:140
Was wrapping 1 test, now wrapping 0.

Delete the empty parent block? [y / n / skip]
```

User responses are independent of the prior T01 prompt — this is a separate question.

### 2. File now has zero tests?

If the file now contains zero `it/test/def test_*/#[test]/func Test*` declarations, prompt:

```
─────────────────────────────────────────────────────
Cascade: file has zero tests

File: tests/auth/login.test.ts
After deletions, 0 tests remain. The file likely only contains imports and helpers now.

Recommendation: this is now /code-cleanup territory (orphaned test file). Do NOT delete here.
Re-run /code-cleanup after the --fix pass completes; cleanup-styles-tests will catch it.

Continue with next finding? [y/n]
```

Do not delete the file from `--fix` mode — `/code-cleanup` owns whole-file deletions. The prompt is informational + cross-skill routing.

## After all findings processed

Print a summary:

```
--fix pass complete.

Applied: 3 T01 deletions
Rejected: 1
Skipped: 1
Auto-routed to --plan: 7
Cascade-deleted empty parent blocks: 1
Files flagged for /code-cleanup follow-up: 0

Per-edit undo: press Esc Esc twice or run /rewind to step back through individual edits.
Whole-pass undo: if you did this on a branch, `git checkout main && git branch -D <fix-branch>` discards all changes.

Suggested follow-up:
- Re-run /test-review --plan to convert remaining T02/T03/T04 findings into rewrite briefs.
- Run /code-cleanup if any file-level cascades pointed there.
```

## Tool usage

- Use the `Edit` tool with exact `old_string` / `new_string` for each change. Include the full test block (from `it(...)` open through closing `});`) in `old_string`.
- Always show the diff *before* applying — never apply and ask later.
- If the same file has multiple T01 findings, process them sequentially from bottom to top (highest line number first) so earlier line numbers stay valid across edits.
- After each edit, allow the harness state to update; do not batch multiple Edits to the same file in a single tool call.

## Edge cases

- **Edit tool errors (non-unique `old_string`)**: abort that finding only, mark as "skipped (could not apply mechanically)", continue. Surface in the summary.
- **Comment lines** between the test and the previous test: include in the deletion only if the comment directly references the deleted test (`// TODO: assert against returned session`). Otherwise leave alone.
- **Test inside a `describe.each` / `it.each` loop**: T01 finding here is suspicious — the assertion may live in the iteration callback. Defensively skip with a warning, route to `--plan`.

## What this mode does NOT do

- Run tests after edits (call `/code-review --verify` separately if you want that)
- Delete other smell types (T02-T05 always route to `--plan`)
- Delete whole files (cross-skill routing to `/code-cleanup`)
- Delete imports left orphaned by the test deletion (handled by linter / formatter / future `/code-cleanup` pass)
- Update snapshot files (snapshot_heavy is `--plan`-only)
