# Output Format & Verification Checklists

## Output Format (All Modes)

### 1. Summary (in response, not in docs)

```markdown
## Documentation Mode: [REFACTOR/CREATE/UPDATE]

### Documentation Structure Detected

**docs/ folder contents:**
- [List all files found in docs/]

### Actions Taken

**[REFACTOR only] Content Migration:**
| Section | From | To |
|---------|------|-----|
| ... | ... | ... |

**Files Created:**
- [List new files]

**Files Modified:**
- [List modified files with change summary]

**Files Preserved (unchanged):**
- [List files that didn't need changes]

**Discrepancies Found:**
- [Any mismatches between docs and code]

**Verification:**
- [ ] All content preserved (REFACTOR)
- [ ] All files created (CREATE)
- [ ] All files consistent (UPDATE)
- [ ] Links in README.md point to actual files
- [ ] Links in CLAUDE.md point to actual files
- [ ] CLAUDE.md has all required sections for /resume-work
```

### 2. Full File Contents

Provide complete content for each file created or significantly modified.

---

## Verification Checklist: REFACTOR Mode
- [ ] All README.md content accounted for
- [ ] Nothing deleted, only moved (content may move to reference files — that counts as preserved)
- [ ] CLAUDE.md has ALL required sections (see claude-md-sections.md) in lean format
- [ ] CLAUDE.md Completed section is a summary + link (NOT full checklist)
- [ ] CLAUDE.md Key Decisions has ~20 max rows + link to full log
- [ ] CLAUDE.md Session History has only last session (3-5 bullets) + link
- [ ] Reference files created as needed (docs/completed-work.md, docs/key-decisions.md, docs/session-history.md)
- [ ] CLAUDE.md has "Last Updated" timestamp
- [ ] CLAUDE.md is under 35k chars (target ~17k)
- [ ] docs/ folder has specifications
- [ ] README.md links to actual files in docs/
- [ ] Existing docs/ files preserved

## Verification Checklist: CREATE Mode
- [ ] All required files generated
- [ ] Content based on actual codebase
- [ ] Tech stack accurately detected
- [ ] Project structure matches reality
- [ ] Environment variables documented
- [ ] CLAUDE.md has ALL required sections in lean format
- [ ] CLAUDE.md has "Last Updated" timestamp
- [ ] CLAUDE.md does NOT reference files that don't exist yet (reference files created on demand by /update-docs)
- [ ] Templates ready for future updates
- [ ] Didn't overwrite existing docs/ files

## Verification Checklist: UPDATE Mode
- [ ] CLAUDE.md "Last Updated" timestamp refreshed
- [ ] CLAUDE.md session history has brief last-session summary (3-5 bullets, NOT full log)
- [ ] Detailed session log appended to docs/session-history.md
- [ ] CLAUDE.md Completed section is a summary line + link (NOT a full checklist)
- [ ] Completed items appended to docs/completed-work.md
- [ ] New key decisions appended to docs/key-decisions.md
- [ ] CLAUDE.md Key Decisions table has only important architectural decisions (~20 max)
- [ ] CLAUDE.md status reflects current state
- [ ] CLAUDE.md links to actual docs/ files (including reference files)
- [ ] CLAUDE.md has all required sections intact
- [ ] CLAUDE.md is under 35k chars (warn if exceeded, target ~17k)
- [ ] Cap enforcement (Part 1.10) ran — Current Status ≤10, Next Steps ≤10, In Progress ≤5 (or warnings issued)
- [ ] Size-pressure rollup (Part 7) ran when CLAUDE.md exceeded 35k post-Parts 5/6, or skipped silently when under threshold
- [ ] README.md matches current features
- [ ] README.md links to actual docs/ files
- [ ] Relevant docs/*.md files updated
- [ ] All files consistent with each other
- [ ] No valuable context removed
- [ ] Auto-memory synced with stable project facts (if changed)
- [ ] Task list drained — completed/in-progress/pending tasks synced back
- [ ] Session-history rollup considered (unless --skip-rollup) — older entries compressed when count > 5
- [ ] Key Decisions rollup considered (unless --skip-decisions-rollup) — oldest rows moved to docs/key-decisions.md when CLAUDE.md table > 20
- [ ] Commit checkpoint offered LAST (unless --skip-commit) — runs after both rollups so their changes land in the same commit
- [ ] Project-specific files preserved

## Post-Verification Note

If the user plans to continue working after `/update-docs`, suggest:
> "To free up context consumed by the docs update, consider running `/compact` before continuing work."
