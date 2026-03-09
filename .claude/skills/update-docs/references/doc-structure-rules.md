# Documentation Structure Rules

## Target State

All projects should have this documentation system:

| File | Location | Purpose | Audience |
|------|----------|---------|----------|
| **README.md** | Root | Public overview, setup guide, quick reference | Developers, new team members |
| **CLAUDE.md** | Root | Session context, progress tracking, working notes | AI coding assistants |
| **docs/*.md** | docs/ | PRD, specifications, detailed documentation | Detailed implementation reference |

## Handling docs/ Folder

The `docs/` folder may contain **one or more** documentation files:
- `docs/PRD.md` - Single PRD file
- `docs/[project-name]-prd.md` - Project-specific PRD
- `docs/architecture.md`, `docs/api.md`, etc. - Multiple spec files
- `docs/sample-*.md`, `docs/examples-*.md` - Supporting documents

**Rules for docs/ folder:**
1. **Scan all .md files** in docs/ folder
2. **Identify PRD files** (contain "PRD", "requirements", "specifications" in name or content)
3. **Update relevant files** based on what changed in codebase
4. **Preserve project-specific files** - don't rename or restructure existing docs
5. **Reference by actual filename** in README.md and CLAUDE.md links

---

## CRITICAL: Context Preservation Rule

**These files serve as the primary context source for AI coding assistants in future sessions.**

Therefore:
- **NEVER remove existing information unless it's factually incorrect or obsolete**
- **ALWAYS preserve context that helps an AI understand the project**
- **ADD new information, don't replace unless necessary**
- **When in doubt, keep it - more context is better than less**
- **Expand and enrich existing sections rather than condensing them**
- **During REFACTOR: Move content to appropriate files, don't delete it**
- **Preserve existing file names in docs/ - don't rename project-specific files**
