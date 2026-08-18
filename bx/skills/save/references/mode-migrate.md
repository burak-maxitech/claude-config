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
the state sections, in STATUS.md, which Step 4 below can now scaffold if some are missing —
see Step 4). Never ask permission for something that cannot succeed.

- **If CLAUDE.md lacks any of the three instruction sections** (`## Project Overview`,
  `## Key Decisions`, `## Known Issues / Blockers`) → **decline without prompting.** Emit one
  line — "CLAUDE.md does not carry the sections schema v2 requires; migration skipped." —
  and continue with a normal v1 UPDATE. No user prompt: this must not nag on every save for a
  repo that can never pass verification.
- **If those three are present**, regardless of how many of the five state sections are
  present → eligible. Continue to Step 1. `doc-migrator` scaffolds any missing state section
  as a bare header with a placeholder line, so partial state coverage does not block
  migration (see `doc-migrator.md` Step 2).

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

Otherwise ask via `AskUserQuestion` (numbered fallback if unavailable). State the concrete
delta, computed from the CLAUDE.md already read in Step 0:

> "This repo uses doc schema v1. Migrating moves 5 state sections from CLAUDE.md into
>  `docs/STATUS.md`, and the architecture tree into `docs/architecture.md`. CLAUDE.md
>  drops from [X]k to ~[Y]k chars of always-loaded context. **Nothing is deleted — content
>  moves**, and it lands as one commit you can `git revert`. Migrate now?"

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
- `env_vars_disposition` — `keep` if `## Environment Variables` is present in CLAUDE.md AND
  its body contains a token matching `[A-Z][A-Z0-9_]{2,}` anywhere (unanchored); `drop`
  otherwise, **including when the section is absent from CLAUDE.md entirely**. See Global
  Constraints; the rule must read identically here, in `doc-schema.md`, and in
  `assert-doc-schema.sh`.

Await its change report.

- `status: failed`, or a `warnings:` value other than the literal `none` -> go to Step 6
  (failure handling).
- `status: already-v2` -> detection was wrong; log it and fall through to UPDATE.
- `status: migrated` or `resumed-partial` -> continue to Step 5.

## Step 5: Verify invariants

Run the target-repo checker. Resolve `tests/assert-doc-schema.sh` against the base directory
Claude Code announced for this skill when it loaded, and pass it to Bash as a literal
absolute path — never let an unexpanded variable like `${CLAUDE_SKILL_DIR}` reach the shell,
where it yields an empty string and the command silently fails to resolve (the exact
S33/S39 bug class):

    bash <absolute path to this skill's base dir>/tests/assert-doc-schema.sh <project_root> --expect v2 --before <snapshot>

Also run the plugin's own self-consistency check. This is a **separate, second check** — it
scans the bx/ plugin's own source tree, not `<project_root>`, and takes no arguments (it
resolves its own tree from its own location). Run it because a drifted plugin source (the
populated-rule regex or the schema marker stated differently in two of its own files) would
make the check above untrustworthy too, even if it happens to pass:

    bash <absolute path to this skill's base dir>/tests/check-doc-rule-consistency.sh

- Both exit 0 -> continue to Step 6.
- Either exits non-zero -> failure handling below. If it was the self-consistency check that
  failed, say so explicitly in the report — that is a bx plugin defect independent of this
  repo, worth reporting upstream, in addition to (not instead of) the recovery below, since
  Step 4 may already have modified this repo regardless of which check caught the problem.

## Step 6: Commit, or fail cleanly

**On success**, commit the migration **on its own**, separate from the session save, so it
stays independently revertible:

    git add CLAUDE.md docs/STATUS.md docs/architecture.md
    git commit -m "docs: migrate to bx doc schema v2 (CLAUDE.md -> STATUS.md split)"

(Include `docs/architecture.md` only if it was created.) Continue to Step 7.

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
