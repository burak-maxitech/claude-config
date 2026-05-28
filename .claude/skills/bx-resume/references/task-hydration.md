# Task Hydration Rules

After presenting the summary, load CLAUDE.md tasks into the live task tracker using TaskCreate.

---

## Pre-Hydration Check

Before creating any new tasks, check for stale tasks from a previous session:

1. **Run `TaskList`** to check for existing tasks
2. **If tasks exist:**
   - These are leftover from a previous session (task state does not persist across sessions unless drained by `/bx-docs`)
   - **Warn the user:**
     > "Found [N] stale tasks from a previous session. These may contain progress not yet saved to CLAUDE.md."
   - **Show the stale tasks** with their statuses (completed, in-progress, pending)
   - **Ask the user:** "Should I drain these into CLAUDE.md first, or discard them?"
     - **Drain:** Follow the drain logic from `/bx-docs` Part 0 — completed tasks → `docs/completed-work.md`, in-progress → `## In Progress`, pending → `## Next Steps`
     - **Discard:** Proceed without saving (tasks will be overwritten by fresh hydration)
3. **If no tasks exist**, proceed directly to hydration below

---

## From "In Progress"
For each item in CLAUDE.md's `## In Progress` section:
- Create a task with `TaskCreate` (subject = the task description, status starts as `pending`)
- Include relevant file paths in the task description

## From "Next Steps"
For each item in CLAUDE.md's `## Next Steps` section:
- Create a task with `TaskCreate`
- Use the priority order to set `blockedBy` dependencies where tasks are sequential (e.g., task 2 blocked by task 1 if they depend on each other)
- Skip items that are clearly future/aspirational -- only hydrate actionable tasks

## From "Known Issues / Blockers"
For any active blockers:
- Create a task and set it as `blockedBy` on the tasks it blocks

## Rules
- **Do NOT hydrate completed items** -- those are already in `## Completed`
- **Keep task subjects concise** -- imperative form (e.g., "Add user authentication endpoint")
- **Set activeForm** on each task (e.g., "Adding user authentication endpoint")
- **Mark the recommended task as `in_progress`** once the user confirms direction
- **Limit to ~10 tasks max** -- if there are more, only hydrate the top priorities

This gives the user a live, interactive task tracker for the session instead of a static markdown list.
