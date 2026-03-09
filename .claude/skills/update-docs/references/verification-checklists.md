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
- [ ] Nothing deleted, only moved
- [ ] CLAUDE.md has ALL required sections (see claude-md-sections.md)
- [ ] CLAUDE.md has "Last Updated" timestamp
- [ ] docs/ folder has specifications
- [ ] README.md links to actual files in docs/
- [ ] Existing docs/ files preserved

## Verification Checklist: CREATE Mode
- [ ] All required files generated
- [ ] Content based on actual codebase
- [ ] Tech stack accurately detected
- [ ] Project structure matches reality
- [ ] Environment variables documented
- [ ] CLAUDE.md has ALL required sections
- [ ] CLAUDE.md has "Last Updated" timestamp
- [ ] Templates ready for future updates
- [ ] Didn't overwrite existing docs/ files

## Verification Checklist: UPDATE Mode
- [ ] CLAUDE.md "Last Updated" timestamp refreshed
- [ ] CLAUDE.md session history has new entry
- [ ] CLAUDE.md status reflects current state
- [ ] CLAUDE.md links to actual docs/ files
- [ ] CLAUDE.md has all required sections intact
- [ ] README.md matches current features
- [ ] README.md links to actual docs/ files
- [ ] Relevant docs/*.md files updated
- [ ] All files consistent with each other
- [ ] No valuable context removed
- [ ] Session history archived if more than 3 entries (old sessions moved to docs/session-history.md)
- [ ] Auto-memory synced with stable project facts (if changed)
- [ ] Task list drained — completed/in-progress/pending tasks synced back to CLAUDE.md
- [ ] Project-specific files preserved
