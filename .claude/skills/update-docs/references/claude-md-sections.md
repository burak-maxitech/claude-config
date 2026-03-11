# CLAUDE.md Required Sections

**The `/resume-work` command depends on these exact section headers in CLAUDE.md.**

**Target size: ~17k chars, hard limit 40k chars.** If CLAUDE.md exceeds 35k chars, warn the user and suggest moving content to reference files.

CLAUDE.md **MUST** contain these sections (in this order):
1. `## Project Overview` - Name, repo, description, key docs links
2. `## Current Status` - Status table with Complete/In Progress/Not Started indicators
3. `## Completed` - Brief 1-2 line summary of completed work + link to `docs/completed-work.md` for full checklist. **NOT a full checkbox list** — the detailed list lives in the reference file.
4. `## In Progress` - Checkbox list of current work
5. `## Next Steps` - Numbered priority list
6. `## Key Decisions` - Condensed table of ~20 most important architectural decisions (API gotchas, naming conventions, critical tech choices) + link to `docs/key-decisions.md` for full history. **Do NOT include implementation details** like "removed field X" — those go only in the reference file.
7. `## Architecture Summary` - Brief architecture description
8. `## Known Issues / Blockers` - Current blockers
9. `## Environment Variables` - Required env vars
10. `## Session History` - Only the **last session** as a 3-5 bullet summary + link to `docs/session-history.md` for full archive. **NOT a chronological log** — detailed entries go in the reference file.

**Reference files (overflow docs):**
- `docs/completed-work.md` — full completed task checklist
- `docs/key-decisions.md` — full decision table with all entries
- `docs/session-history.md` — detailed session logs archive

These reference files are **optional** — if they don't exist in a project, that's fine. They are created as needed when CLAUDE.md content is offloaded.

**Do not rename, remove, or reorder these sections.**
