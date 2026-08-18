# MODE: REFACTOR (Split Existing README.md)

When README.md contains everything, split it intelligently:

## What Goes Where

### -> Move to CLAUDE.md (Instructions)
- Project overview (name, repository, description) and key documentation links
- Recent decisions and their rationale
- Known issues and blockers

### -> Move to docs/STATUS.md (Session State)
- Current status / progress tracking
- Completed work and finished tasks
- Work in progress notes
- TODO lists and next steps
- Session history (if any)
- "Current state" sections
- Development notes
- Anything that changes frequently

### -> Move to docs/PRD.md (Full Specifications)
- Detailed architecture documentation
- Complete API specifications
- Data models and schemas
- Sequence diagrams
- Detailed configuration specs
- Integration details
- Security specifications
- Detailed technical decisions (ADRs)
- Anything comprehensive/reference-like

### -> Keep in README.md (Public Overview)
- Project description (concise)
- Feature list (bullet points)
- Quick start / installation
- Basic usage examples
- Project structure (brief)
- Tech stack summary
- Links to other docs
- Contributing guidelines
- License

## Refactor Process

1. **Analyze existing README.md** - Identify all sections
2. **Check if docs/ exists** - Scan for existing documentation files
3. **Categorize each section** - Determine which file it belongs to
4. **Create CLAUDE.md** - With ALL required instruction sections (see `claude-md-sections.md`):
   - `## Project Overview`
   - `## Key Decisions` — condensed top ~20 architectural decisions + link to `docs/key-decisions.md`
   - `## Known Issues / Blockers`
   - `## Environment Variables` — only when populated
   - `> Session state: [docs/STATUS.md](docs/STATUS.md)` pointer line
5. **Create `docs/STATUS.md`** - With ALL required state sections, in order (see `claude-md-sections.md`):
   - `## Current Status`
   - `## Completed` — brief summary line + link to `docs/completed-work.md`
   - `## In Progress`
   - `## Next Steps`
   - `## Session History` — only last session as 3-5 bullets + link to `docs/session-history.md`
6. **Create reference files** from the content that doesn't fit in lean CLAUDE.md / STATUS.md:
   - `docs/completed-work.md` — full completed task checklist (if there are completed items)
   - `docs/key-decisions.md` — full decision table (if there are more than ~20 decisions, or to start the log)
   - `docs/session-history.md` — detailed session entry for this refactor session
7. **Create/Update docs/PRD.md** - With full specifications + moved content (use existing PRD if present)
8. **Slim down README.md** - Keep overview, add links to actual doc files
9. **Verify no content lost** - All information preserved somewhere (CLAUDE.md + docs/STATUS.md + reference files + docs/)
10. **Size check** - Verify CLAUDE.md is ~7k chars and docs/STATUS.md is ~10k chars
11. **Write the schema marker last** - Prepend `<!-- bx-doc-schema: 2 -->` as CLAUDE.md's first line only once everything above is written, matching `doc-schema.md`'s invariant 4 (the marker is written last)
