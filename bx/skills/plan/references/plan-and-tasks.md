# After Interview Complete: Enter Plan Mode

Once the user confirms ready to proceed, transition into a formal implementation plan:

## Step 1: Enter Plan Mode
Use `EnterPlanMode` to switch into planning mode. This gives you access to explore the codebase in detail and design a concrete implementation approach.

## Step 2: Write the Implementation Plan
In plan mode, create a detailed plan that includes:
1. **Phase breakdown** — each phase from the interview summary becomes a plan section
2. **File-level changes** — for each phase, list specific files to create/modify with what changes
3. **Dependencies** — which phases depend on others
4. **Risk mitigations** — concrete steps to address each identified risk
5. **Test types per phase** — for each phase, explicitly list which test types apply:
   - **Unit tests** — isolated function/module tests (most phases)
   - **Integration tests** — tests that verify component interactions (phases with API/DB/service boundaries)
   - **E2E tests** — full user-flow tests (phases that complete a user-facing feature)
   - Not every phase needs all three — specify only what's relevant
6. **Rollback strategy** — for each phase, note how to safely undo if something goes wrong (e.g., revert commit, drop migration, feature flag off)

## Step 3: Exit Plan Mode for Approval
Use `ExitPlanMode` to present the plan to the user for approval. The user will review and either approve or request changes.

**Do NOT begin implementation until the plan is approved via ExitPlanMode.**

---

## After Plan Approved: Hydrate Task List

Once the user approves the plan, **create a live task tracker** from the implementation phases:

### Create Tasks with TaskCreate
For each implementation phase/step in the approved plan:
1. Create a task with `TaskCreate`:
   - **subject** — imperative form (e.g., "Create user authentication endpoint")
   - **description** — include specific files, changes, and acceptance criteria from the plan
   - **activeForm** — present continuous (e.g., "Creating user authentication endpoint")
2. Set `blockedBy` dependencies between sequential phases
3. Mark the first task as `in_progress` to begin

### Rules
- **One task per logical unit of work** — don't create a task per file, create a task per deliverable
- **Limit to ~10 tasks max** — group small steps if there are many phases
- **Include testing tasks** — add a task for writing tests after each major phase
- **Skip documentation tasks** — `/bx:docs` handles that at end of session

### Phase Gating — Verify Before Proceeding
Each phase is **gated**: do NOT start the next phase until the current phase passes its gate check.

**Gate check after completing each phase:**
1. Run all tests relevant to the phase (unit, integration, e2e as specified in the plan)
2. Verify all tests pass — if any fail, fix before moving on
3. **Commit the phase** with a descriptive message: `feat(<scope>): phase N — <what was delivered>`
4. Update the task status to `completed`
5. Only then mark the next task as `in_progress`

This ensures each phase is a stable, rollback-friendly checkpoint. If Phase N+1 goes wrong, you can revert to the Phase N commit cleanly.

### Then update CLAUDE.md:
1. New feature added to "In Progress"
2. Key decisions added to "Key Decisions" table
3. Any new blockers/issues identified

### Optionally update PRD with:
- New feature specifications
- Updated architecture if changed
- New API endpoints/data models

### Context Management Before Implementation
If the interview was long (many question rounds), run `/compact` before starting implementation to free up context space. The plan and tasks are persisted — you won't lose anything.

### Begin implementation following the task list, respecting phase gates.
