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
4. **Create CLAUDE.md** - With ALL required sections + moved content
5. **Create/Update docs/PRD.md** - With full specifications + moved content (use existing PRD if present)
6. **Slim down README.md** - Keep overview, add links to actual doc files
7. **Verify no content lost** - All information preserved somewhere
