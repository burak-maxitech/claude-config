# Expected outcome — phase 5 fixture (`--fix` pre-pass over Section 4 entries; no lane ran, so Section 2 is empty)

Five stored entries. Today 2026-10-20, session S61.

| entry | stored decision | edit stored? | re-grep | outcome |
|---|---|---|---|---|
| 9105434f `bx:save/writer-tools` | open | yes | token `Bash(wc:*)` found in bx/agents/save-writer.md (1 of 1 files) | **eligible**, gated normally |
| bf4076dd `bx:save/session-start-hook` | open | yes | token `session-start-context.ps1` absent from README.md AND bx/hooks/hooks.json (0 of 2) | **auto-closed (stale)**: decision → applied, date → 2026-10-20, note → "closed at re-grep 2026-10-20: token absent in all affected_files" |
| 57874f60 `bx:pain/plugin-cache-staleness` | open | no (legacy 9-key) | not attempted | display-only `[legacy — no stored edit]` |
| 3117b0b6 `bx:pain/bx-health-never-run` | open | prose only | no token identifiable | display-only (fails rule 3: no existing text changes; would also be `[no re-grep token]`), stays open |
| 633ecafe `bx:webdesign/stitch-design-engine` | deferred | yes | not attempted (rule 2: deferred is never offered) | display-only `[deferred 2026-07-05]` |

## Expected pre-pass summary
```
--fix pass: 1 findings eligible (0 from this run, 1 carried forward), 3 display-only (advisory/deferred/legacy/out-of-scope).
Auto-closed (stale): 1 carried-forward entries whose token is absent from every affected file — bf4076dd Hook scripts must be bash; drop the PowerShell twin from README and hooks.json
Walking eligible findings in rank order (breakage first, then best-practice, then opportunities).
Allowlist candidates to offer after the findings: 0
```
(The `Allowlist candidates` line exists only after Phase 6 lands; before that the summary has three lines.)

## Expected gate display for the one eligible finding
`[Finding 1 of 1] best_practice · M — Bash permission specifiers …`, affected files: bx/agents/save-writer.md (1), diff replaces `Bash(wc:*)` with `Bash(wc *)` on that file's `tools:` line, prompt `Apply? [y / n / skip / abort]`. The rehearsal stops here without answering.

## Default-mode closing line (if this were a report run)
`Run /bx:evolve --fix to act on up to 3 fix-eligible findings (4 open in total, 1 legacy display-only, 1 deferred). The pass re-greps …` — N=3 is the stored-field upper bound (9105434f, bf4076dd, 3117b0b6); the pre-pass then auto-closes one and sets one aside, which the line says may happen.

## Checkpoint 2 (what would be written on abort/completion before any verdict)
Only the auto-close mutation: bf4076dd → applied. Every other entry unchanged. `check-state.py` passes (one legacy warning; the missing registry is a warning, not a failure).

