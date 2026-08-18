# MODE: MIGRATE (doc schema v1 -> v2)

Runs when `references/doc-schema.md`'s detection predicate returns **v1** or **partial**.
Unlike Part 0.5, this mode runs on **both** the fast path and `--full` — it is a
precondition for a correct save, not a periodic sweep.

**If `--skip-migrate` is in `$ARGUMENTS`, skip this mode entirely** and run UPDATE against
the v1 layout.

## Step 0: Eligibility pre-flight

Before anything else — including the clean-tree guard — check whether this CLAUDE.md can
actually reach a valid v2 shape. `doc-schema.md`'s v1 detection fires on **any one** of the
five state sections, but `assert-doc-schema.sh` requires **all three** of
`## Project Overview`, `## Key Decisions`, `## Known Issues / Blockers` in CLAUDE.md (plus
the five state sections, in STATUS.md — `doc-migrator` can scaffold any that are missing, see
the following bullets). Never ask permission for something that cannot succeed.

- **If CLAUDE.md lacks any of the three instruction sections** (`## Project Overview`,
  `## Key Decisions`, `## Known Issues / Blockers`) → **decline without prompting.** Emit one
  line — "CLAUDE.md does not carry the sections schema v2 requires; migration skipped." —
  and continue with a normal v1 UPDATE. No user prompt: this must not nag on every save for a
  repo that can never pass verification.
- **If those three are present**, regardless of how many of the five state sections are
  present → eligible. Continue to Step 1. `doc-migrator` scaffolds any missing state section
  as a bare header with a placeholder line, so partial state coverage does not block
  migration (see `doc-migrator.md` Step 3).

## Step 1: Clean-tree guard

Run `git status --porcelain`. If it emits **any** line:

> "This repo is on the v1 doc layout, but the working tree has [N] uncommitted files.
>  Migration needs a clean tree so it can land as one revertible commit. Commit or stash,
>  then run `/bx:save` again. Continuing with a normal save for now."

Then **skip the rest of this mode and run UPDATE against the v1 layout**. Migration is
opportunistic and must never block the work the user came to do.

## Step 2: Consent gate

Reuses the Part 5.2 / 6.2 sentinel semantics exactly. **If `--silent` is in `$ARGUMENTS`,
treat as declined without asking** — skip the mode, write no marker, and let the next
interactive run ask again.

First resolve `env_vars_disposition` from the CLAUDE.md already read in Step 0, because the
prompt has to disclose it: **`keep` if `## Environment Variables` is present in CLAUDE.md AND
its body contains a token matching `[A-Z][A-Z0-9_]{2,}` anywhere (unanchored); `drop`
otherwise, including when the section is absent from CLAUDE.md entirely.** The rule must read
identically here, in `doc-schema.md`, and in `assert-doc-schema.sh` —
`check-doc-rule-consistency.sh` is what enforces that. Step 4 passes this same value on; do
not recompute it there.

Then ask via `AskUserQuestion` (numbered fallback if unavailable). State the concrete delta,
computed from the same CLAUDE.md:

> "This repo uses doc schema v1. Migrating moves 5 state sections from CLAUDE.md into
>  `docs/STATUS.md`, and the architecture tree into `docs/architecture.md`. CLAUDE.md
>  drops from [X]k to ~[Y]k chars of always-loaded context. **Content moves rather than being
>  deleted**, and it lands as one commit you can `git revert`. Migrate now?"

**If `env_vars_disposition` is `drop` AND `## Environment Variables` is present in CLAUDE.md,
the prompt MUST also name that removal and quote the body being removed.** It is the one thing
the migration deletes rather than moves, so a bare "nothing is deleted" reassurance would be
false, and consent must attach to this specific removal rather than to a generic promise:

> "One section is removed rather than moved: `## Environment Variables`, whose body reads:
>
>      [the section's body, quoted verbatim]
>
>  It names no environment variable, so schema v2 drops it. That text is repeated in the run's
>  report, and the commit is revertible."

- **Declines** -> skip the rest of this mode, write no marker, run UPDATE on v1. Re-ask next run.
- **Accepts** -> continue.

## Step 3: Snapshot for verification

Copy the current CLAUDE.md to a scratch path (outside the repo) so Step 5 can check header
conservation against it. Use the session scratchpad, never a path inside `project_root` —
a stray file in the repo would defeat the clean-tree guard on the next run.

## Step 4: Dispatch `doc-migrator`

Dispatch one subagent via the Agent tool with `subagent_type: "bx:doc-migrator"`, passing:

- `project_root` — absolute repo path
- `today` — resolved as in `mode-update.md` Step 0.2
- `env_vars_disposition` — the value already resolved and disclosed in Step 2. Pass it
  unchanged; the rule is stated there, once.

Await its change report. Read `warnings:` as a top-level field only — a report may carry
multi-line values (`inventory:`, or a quoted dropped `## Environment Variables` body under
`notes:`), and an indented line belongs to the field above it, never a new field.

- `status: failed`, or a `warnings:` value other than the literal `none` -> go to Step 6
  (failure handling). `warnings:` is blocking-only by contract; `doc-migrator.md`'s Output
  section defines what qualifies, and this file deliberately does not restate that list —
  a restatement here would drift out of sync with it. **A report with no `warnings:` line at
  all is treated as blocking, the same as a non-`none` value** — never read a missing line as
  "nothing to report."
- `status: already-v2` -> detection was wrong; log it and fall through to UPDATE.
- `status: migrated` or `resumed-partial` -> continue to Step 5. Carry any `notes:` value
  into the session's eventual report, but it is advisory only — it never changes this
  routing or blocks the commit. `inventory:` is informational in the same way: record it with
  the run, act on nothing in it.

## Step 5: Verify invariants

Run the checker. Resolve `tests/assert-doc-schema.sh` against the base directory Claude Code
announced for this skill when it loaded, and pass it to Bash as a literal absolute path —
never let an unexpanded variable like `${CLAUDE_SKILL_DIR}` reach the shell, where it yields
an empty string and the command silently fails to resolve (the exact S33/S39 bug class):

    bash <absolute path to this skill's base dir>/tests/assert-doc-schema.sh <project_root> --expect v2 --before <snapshot>

This checks `<project_root>` — the repo being migrated. `check-doc-rule-consistency.sh` is a
**separate, development-time lint over the bx/ plugin's own source tree**, not a check on any
user's repository; it does not belong here (a plugin-authoring concern must never gate or
roll back a user's migration, especially one running after Step 4 has already touched their
files). It is exercised by the plugin's own test suite instead — never wire it into this mode.

- Exit 0 -> continue to Step 6.
- **Any non-zero exit** -> failure handling below. Do not special-case the exit code:
  `assert-doc-schema.sh` exits `2` on a usage error, and an unresolved path makes `bash
  <path>` exit `127` — the same `${CLAUDE_SKILL_DIR}`-empty-string failure warned about above.
  Neither is "1", and treating only exit `1` as failure would let an unverified migration
  commit. Any exit other than `0` means the checker did not confirm success.

## Step 6: Commit, or fail cleanly

**On success**, commit the migration **on its own**, separate from the session save, so it
stays independently revertible:

    git add CLAUDE.md docs/STATUS.md
    git add docs/architecture.md          # ONLY if doc-migrator reported creating it
    git commit -m "docs: migrate to bx doc schema v2 (CLAUDE.md -> STATUS.md split)"

The second `git add` is a separate command precisely so it can be omitted: naming a
nonexistent `docs/architecture.md` in the first one makes git fail the whole `add` on a
`pathspec did not match any files` error, leaving nothing staged. Run it only when the change
report lists `docs/architecture.md: created`. Continue to Step 7.

**On failure — no automatic rollback, and STOP the mode here.** Report what failed, name the
files left modified, and print the exact recovery command:

> "Migration failed at [step]: [what]. The working tree was clean before this ran, so
>  `git restore . && git clean -fd docs/` restores it exactly. Nothing was committed. This
>  session's save did NOT run — recover first, then run `/bx:save` again; it will proceed
>  normally against whichever layout the repo is then on."

Do NOT run those commands yourself. Auto-running `git clean -fd` is precisely the trap the
S42 `/bx:webdesign` review caught. **Do not fall through to UPDATE, Step 7, or Step 8.** A
half-migrated tree is not a safe base for a save, and running UPDATE now would write more
files on top of the unresolved failure — exactly what the recovery command above is supposed
to undo. End the run here.

## Step 7: Offer the compression pass (optional, separate)

Reached only from Step 6's success path. Migration is mechanical. Rationale compression is
authored and lossy, so it is a **separate consented pass** — never bundled, because mixing
them makes the diff unreviewable.

If CLAUDE.md's `## Key Decisions` section still exceeds 8000 chars after migration, offer:

> "CLAUDE.md is now [Y]k chars; `## Key Decisions` is [Z]k of that, and every row is already
>  duplicated in `docs/key-decisions.md`. Compressing each rationale to a one-liner would
>  bring CLAUDE.md to roughly [W]k. This rewrites prose (the only lossy step), so it lands as
>  its own commit. Run it now?"

Declining is free and re-offered next run. If `--silent`, treat as declined.

## Step 8: Fall through to UPDATE

Reached only from Step 6's success path. Continue into `mode-update.md` against the now-v2
layout. The session's actual save proceeds normally.
