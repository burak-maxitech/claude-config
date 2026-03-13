# Resume Summary Template

Present this summary after completing Steps 0-3. Fill in all bracketed placeholders from your analysis.

---

```markdown
## Project Resumed: [Project Name]

### Quick Checks
- [ ] Pulled latest? (`git pull`)
- [ ] Commands synced? (`cd ~/Development/projects/claude-config && git pull`)
- [ ] Uncommitted changes? [Yes: N files / No]

### Staleness Warning (if applicable)
> ⚠ CLAUDE.md was last updated [date], but there are [N] commits since then. Documentation may be stale. Consider running `/update-docs` after reviewing.

*(Only show this section if commits are newer than CLAUDE.md's "Last Updated" date. Remove entirely if docs are fresh.)*

### Health Check (deep mode only)
- Tests: [PASS / FAIL / Skipped]
- Build: [PASS / FAIL / Skipped]

*(Only show this section when `/resume-work deep` is used. Remove entirely in default mode.)*

### Quick Overview
[One sentence: what this project does]

### Current State
| Component | Status | Notes |
|-----------|--------|-------|
| [Key area 1] | Complete/In Progress/Not Started | [Brief note] |
| [Key area 2] | Complete/In Progress/Not Started | [Brief note] |

### Last Session ([Date])
- [Key accomplishment 1]
- [Key accomplishment 2]
- [Any incomplete work]

### Ready to Continue
**Recommended next task:** [Specific task from Next Steps]

**Files likely to be modified:**
- `path/to/file1.py` - [why]
- `path/to/file2.py` - [why]

### Blockers/Issues (if any)
- [Any blockers from CLAUDE.md]

---

**Ready to continue. What would you like to work on?**
- [ ] Continue with recommended task
- [ ] Something else (please specify)
```
