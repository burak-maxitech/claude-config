# --fix Mode

Apply mechanical refactors with per-finding diff preview. **Architectural refactors cascade**, so this mode is deliberately restrictive.

## Hard restrictions

A finding is `--fix-eligible` only if **all** are true:

1. The catalog entry has `--fix-eligible: true`
2. The refactor is **single-file** (no edits outside the finding's location's file)
3. The refactor is **non-API-breaking** (no exported symbol rename, signature change, or removal of an exported symbol with importers)
4. `respects_documented_decision: true`
5. `certainty >= 0.7`

**Simplification findings (S-prefix)** that *are* fix-eligible:

- **S04** when the unread config key lives in a single file (typical for ad-hoc constants in `config.ts`); auto-routes to `--plan` when key spans multiple env files.
- **S06** defensive-code removal — always single-file by definition.
- **S09** unused-export deletion when symbol body lives in one file AND has no importers (zero cross-file impact).

All other S-findings (S01, S02, S03, S05, S07, S08) auto-route to `--plan` because they require coordinated cross-file edits.

Anything failing any of these auto-routes to `--plan` mode instead, with a one-line note:

> Auto-routed N findings to --plan (cross-file, API-breaking, low-certainty, or conflicts with documented decisions).

## Per-finding gate flow

For each eligible finding, in rank order:

```
─────────────────────────────────────────────────────
[Finding 1 of 5] R03 — Replace flag arg with two fns
src/util/parse.ts:12-40

Current snippet:
  <30-line excerpt around the function>

Proposed change (diff):
  <unified diff showing exact edits>

Estimated CCN delta: 8 → 4 (Δ -4)

Apply? [y / n / skip / abort]
```

- `y` — apply via `Edit` tool, advance to next finding
- `n` — record "rejected" (do not re-show this run), advance
- `skip` — record "skipped (revisit later)", advance
- `abort` — stop the whole `--fix` pass; nothing already-applied is reverted (use `/rewind` if needed)

## After all findings processed

Print a summary:

```
--fix pass complete.

Applied: 3 refactors across 3 files
Rejected: 1
Skipped: 1
Auto-routed to --plan: 4

Per-edit undo: press Esc Esc twice or run /rewind to step back through individual edits.
Whole-pass undo: this was probably done on a branch — `git checkout main && git branch -D <fix-branch>` discards all changes.
```

## Tool usage

- Use the `Edit` tool with exact `old_string` / `new_string` for each change
- Always show the diff *before* applying — never apply and ask later
- If the same file has multiple findings, group them and show one combined diff if practical (still gated as one approval); if conflicts, do them sequentially
- Re-read the file after each edit (the harness tracks state, but be defensive about overlapping edits)

## Edge cases

- **Test file with the same refactor pattern** — apply if it's in the same file as the finding's location; do not chase tests in sibling files (that's cross-file).
- **Refactor invalidates a comment in the file** — update the comment in the same diff if it directly references removed code; otherwise leave alone.
- **Edit tool errors (e.g. non-unique old_string)** — abort that finding, mark as "skipped (could not apply mechanically)", continue with the next.

## What this mode does NOT do

- Run tests after edits (call `/code-review --verify` afterward if you want that)
- Update imports across the codebase (single-file restriction)
- Rename exported symbols
- Reorganize directory structure
- Add or remove dependencies
