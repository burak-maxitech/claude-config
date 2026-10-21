# Known Issues Archive

> Issues moved out of [CLAUDE.md](../CLAUDE.md) by `/bx:save`. `Resolved` entries are
> history; `Open` entries are still live and linked from CLAUDE.md.

---

### The S37 `/bx:seo` "messed up" breakage is RESOLVED (S39) — Resolved S39 (2026-10-20)

**The S37 `/bx:seo` "messed up" breakage is RESOLVED (S39).** Root-caused to the `${CLAUDE_SKILL_DIR}` path bug (not a real Claude Code variable → the helper was never found → GSC silently fell back to heuristic-only) + an impossible "mint token once, reuse across Bash calls" auth model (shell state does not persist across Bash tool calls). Both fixed and verified against live GSC. See Session History S39 + Key Decisions.

### The unwired `bx/scripts/session-start-context.ps1` is RESOLVED by deletion (S59, 2026-09-08) — Resolved S59 (2026-10-20)

**The unwired `bx/scripts/session-start-context.ps1` is RESOLVED by deletion (S59, 2026-09-08).** The official hooks reference lists every command-hook field (`command`, `args`, `async`, `asyncRewake`, `shell`) and none selects a script per OS; the only Windows-without-Git-Bash path is a dispatcher wrapper, which cannot be verified from this machine. The `.sh` already runs on Windows via Git Bash, so `.sh`-only is now the deliberate scope (`/bx:evolve` docs-lane finding `7b54fbc1`).

### `/bx:health` reading session state from CLAUDE.md is RESOLVED (S60, v2.10.0) — Resolved S60 (2026-10-20)

**`/bx:health` reading session state from CLAUDE.md is RESOLVED (S60, v2.10.0).** Its pre-injection now reads `docs/STATUS.md` when that file exists and names the file it read; the block was executed against this repo and returned STATUS.md's sections. The skill itself has still never been run end to end.

### `start-claude.ps1` cannot be parsed by Windows PowerShell 5.1 (pre-existing, found S55) — Resolved S61 (2026-10-20), commit 7ed079a

**`start-claude.ps1` cannot be parsed by Windows PowerShell 5.1 (pre-existing, found S55).** The file is BOM-less UTF-8 containing seven non-ASCII characters (em-dashes and an arrow); WinPS 5.1 decodes a BOM-less `.ps1` as the ANSI codepage, so `—` becomes `â€"` and the trailing quote terminates a string early — 2 parse errors on 5.1, 0 on pwsh 7. Predates this branch (`git show d78105e:` confirms), and the user runs pwsh 7, but README tells teammates to install `cc` without naming a host. Fix queued in the S55 fix wave: replace the seven characters with ASCII.

### The interactive `/color` path is still unverified (S55) — Resolved S61 (2026-10-20), commit 7ed079a

**The interactive `/color` path is still unverified (S55).** `/color <c>` as a *prompt argument* is proven for `-p` (`claude -p "/color blue"` → `Session color set to: blue`, exit 0, no model turn), but the interactive path needs a TTY and could not be exercised from a tool call. The `cc` launcher now ships that argument. If the live gate shows the prompt bar is not colored, the documented fallback is a custom `statusLine` printing a per-project colored banner — a fresh design decision, NOT a launcher patch.

### `/bx:evolve` Step 3.4 has no `applied` branch (S58, found by running it) — Resolved S61 (2026-10-20), commit 8da760e

**`/bx:evolve` Step 3.4 has no `applied` branch (S58, found by running it).** The decision-log filter defines branches for `rejected`+unchanged, `rejected`+changed, `deferred`, and `open`-or-new — but not `applied`. A re-emitted applied finding matches none of them, so whether it duplicates or vanishes is undefined; it manifests whenever the watermark has not advanced past the release that produced it. Entries also store `source_content_hash` but not `source_excerpt`, so a re-check cannot compare content without re-fetching. Related: the `bx:pain/<slug>` convention derives from prose that gets reworded, so the same concern re-hashes to new IDs over time (4 entries already carry an older cache-staleness slug). **Also (S59): a follow-up `--fix` run cannot act on the previous run's findings** — fix-mode gates only findings re-emitted in the same run, and the watermark advance at the end of every run means the changelog lane never re-emits them; so the default-mode closing line "Run `/bx:evolve --fix` to act on the open Tier-1 findings" oversells a second pass. Storing `source_excerpt` (above) is the fix; until then, pass `--fix` on the same run, use `--full --fix`, or apply by hand.

### v2.10.0's first real `--full` ran S61; two run-found defects — Resolved S62 (2026-10-21)

**v2.10.0's first real `--full` ran S61 (2026-10-20); the open phase of the Known Issues shrinker is still unexecuted.** The CI workflow ran green on the merge push (run 36506759638). The resolved phase fired for real: three `RESOLVED` entries moved to the new `docs/known-issues.md`, archive-first. Two defects found by running: (1) `save-writer` writes the session entry and the state deltas BEFORE Parts 5–7, so a `--full` run's own rollup and shrinker results cannot land in the session that produced them (S61 ran the sweep first by hand); (2) the open phase would have summarized three open entries to save ~550 chars because its 300-char floor is close to the ~200–280-char replacement line, and two of those "open" entries were in fact resolved by `7ed079a` two months earlier — the status-form test cannot see resolution evidence that lives only in git. Multi-paragraph entries, tight bullet lists, the open phase and archive liveness in rotation remain text-only. Log: `docs/superpowers/plans/2026-09-28-bx-doc-tiering-phase1-rehearsals.md`.

### bx 2.11.0's first real `/bx:evolve` runs found three defects — Resolved S62 (2026-10-21)

**bx 2.11.0's first real `/bx:evolve` runs found three defects (S61, 2026-10-20).** (1) `--fix` re-dispatches all three lanes even when the watermark is minutes old — the changelog lane no-ops correctly, but the docs lane re-fetches 15 pages (~180k tokens) only to re-emit stored entries; Step 2 should be skippable when the watermark equals the lanes' current heads. (2) The fix-mode staleness re-grep misreads additive edits: an edit that *adds* text to a file shows "no token" there and the rule would narrow that file away (two entries were kept by orchestrator judgment). (3) Same concern, different release URL (`dadac845` v2.1.183 vs `6712a71e` v2.1.304) cannot be joined by the source_url rule; a pain-id match against stored open entries would. Also observed: the docs lane still reads the hooks page to ~100–200k of 270k chars (the truncation rule landed after the run), and the community lane was degraded in 5 of 6 runs before this session's clean one.
