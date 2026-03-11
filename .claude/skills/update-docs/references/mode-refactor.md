# MODE: REFACTOR (Split Existing README.md)

When README.md contains everything, split it intelligently:

## What Goes Where

### -> Move to CLAUDE.md (Session Context)
- Current status / progress tracking
- TODO lists and next steps
- Work in progress notes
- Session history (if any)
- Known issues and blockers
- Recent decisions and their rationale
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
4. **Create CLAUDE.md** - With ALL required sections (see `claude-md-sections.md`), using the **lean format:**
   - `## Completed` — brief summary line + link to `docs/completed-work.md`
   - `## Key Decisions` — condensed top ~20 architectural decisions + link to `docs/key-decisions.md`
   - `## Session History` — only last session as 3-5 bullets + link to `docs/session-history.md`
5. **Create reference files** from the content that doesn't fit in lean CLAUDE.md:
   - `docs/completed-work.md` — full completed task checklist (if there are completed items)
   - `docs/key-decisions.md` — full decision table (if there are more than ~20 decisions, or to start the log)
   - `docs/session-history.md` — detailed session entry for this refactor session
6. **Create/Update docs/PRD.md** - With full specifications + moved content (use existing PRD if present)
7. **Slim down README.md** - Keep overview, add links to actual doc files
8. **Verify no content lost** - All information preserved somewhere (CLAUDE.md + reference files + docs/)
9. **Size check** - Verify CLAUDE.md is under 35k chars (target ~17k)
