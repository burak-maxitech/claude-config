# Documentation Structure Rules

## Target State

All projects should have this documentation system:

| File | Location | Purpose | Audience |
|------|----------|---------|----------|
| **README.md** | Root | Public overview, setup guide, quick reference | Developers, new team members |
| **CLAUDE.md** | Root | Lean session context (~17k chars), active status, working notes | AI coding assistants |
| **docs/*.md** | docs/ | PRD, specifications, detailed documentation | Detailed implementation reference |
| **docs/completed-work.md** | docs/ | Full completed task checklist (overflow from CLAUDE.md) | Reference |
| **docs/key-decisions.md** | docs/ | Full decision log (overflow from CLAUDE.md) | Reference |
| **docs/session-history.md** | docs/ | Detailed session logs archive (overflow from CLAUDE.md) | Reference |

**Size targets:** CLAUDE.md should be ~17k chars, hard limit 40k chars. When sections grow large, offload detail to the reference files above and keep only summaries + links in CLAUDE.md.

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
- **Context preservation applies to the WHOLE documentation system** (CLAUDE.md + reference files + docs/), not to CLAUDE.md alone. Moving content from CLAUDE.md to a reference file (e.g., `docs/completed-work.md`) is preservation, not removal.
- **During REFACTOR: Move content to appropriate files, don't delete it**
- **Preserve existing file names in docs/ - don't rename project-specific files**
