# Task-Tracker Tool Availability

**Canonical owner** for one platform fact that every bx skill touching the live task tracker
depends on. Satellites cite this file; they do NOT restate the version, the model list, or the
env-var name. If any of those change, they change here only.

Cited by: `/bx:resume` (Step 5), `/bx:save` (Part 0 drain), `/bx:plan` (Step 6),
`/bx:arch --plan`, `/bx:tests --plan`.

---

## The fact

As of claude-code **v2.1.233**, the task-tracker tools — `TaskCreate`, `TaskGet`,
`TaskUpdate`, `TaskList`, `TodoWrite` — are **not in the default toolset** on Opus 4.8,
Sonnet 5, Fable 5, Mythos 5 and newer models. `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` restores them.
Older models still carry them by default.

Listing these tools in a skill's `allowed-tools` does **not** make them appear —
`allowed-tools` grants permission, not existence. The frontmatter entries stay: they are what
permits the tools on the sessions that do have them.

## The check

Before the first task-tool call in a run, check whether the tool is actually present in your
toolset. Do not call it hopefully and react to the failure.

- **Present** → take the skill's tracker path, exactly as written.
- **Absent** → take the skill's degraded path below, and tell the user **once per run** (not
  once per task), in one line:
  > Task tools aren't available in this session (`CLAUDE_CODE_ENABLE_TODO_TOOLS=1` enables
  > them) — <what I am doing instead>.

## Degraded paths

| Skill | Tracker path | Degraded path |
|-------|--------------|---------------|
| `/bx:resume` Step 5 | Hydrate `## In Progress` / `## Next Steps` / blockers into live tasks | Skip the pre-hydration stale check (no tracker ⇒ no stale tasks) and present the same items as a numbered list in the Step 4 summary, with the recommended item marked. Same selection rules, same ~10 cap. |
| `/bx:save` Part 0 | Drain `TaskList` into the docs | Behave exactly as `--skip-tasks`: no drain. Derive the In Progress / Next Steps deltas from the conversation instead — the orchestrator has that context either way. Say so in the drain summary line. |
| `/bx:plan` Step 6 | Hydrate approved plan phases into tasks | The approved plan document **is** the tracker: keep the phase list visible in the response, work phases in order, and keep the per-phase gate (tests pass → commit → next phase). |
| `/bx:arch --plan`, `/bx:tests --plan` | n/a — these hand briefs off, they never hydrate | Unchanged: hand the phased brief to `/bx:plan` or paste it into a fresh session. `/bx:plan` owns the availability decision. |

The tracker path is never deleted from a skill — it is what runs whenever the tools are
present. Degraded paths are fallbacks, not replacements.
