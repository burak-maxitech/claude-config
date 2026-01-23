# /resume-work - Resume Development Session

Get up to speed on this project and continue development from where we left off.

---

## Your Task

You are resuming work on this project after a break (hours, days, or weeks). Your goal is to:

1. **Understand the project** - What it does, how it works
2. **Know current state** - What's done, what's in progress, what's next
3. **Be ready to code** - Have full context to continue immediately

---

## Step 1: Read Documentation (In This Order)

### 1.1 CLAUDE.md (Start Here - Required)
**Location:** `CLAUDE.md` in project root

This is your **primary context file**. Read it completely to understand:
- Project overview and purpose
- Current status (what's complete, in progress, not started)
- Recent session history (what happened last time)
- Next steps (prioritized task list)
- Key decisions made (and why)
- Known issues and blockers
- Architecture summary

### 1.2 README.md (Required)
**Location:** `README.md` in project root

Understand:
- Project purpose and features
- Tech stack
- Project structure
- How to run/test locally
- Links to other documentation

### 1.3 docs/*.md Files (As Needed)
**Location:** `docs/` folder

Scan for PRD and specification files:
- Full architecture details
- API specifications
- Data models
- Configuration details
- Any project-specific documentation

**Prioritize reading:**
- Files referenced in CLAUDE.md "Key Documentation" section
- PRD files (contain detailed requirements)
- Skip sample/example data files unless needed

---

## Step 2: Analyze Current Codebase

After reading documentation, quickly scan:

### 2.1 Project Structure
```bash
# Get folder overview
ls -la
ls -la */
```

Verify structure matches what's documented.

### 2.2 Recent Changes (If Git Available)
```bash
# Recent commits
git log --oneline -10

# What files changed recently
git diff --stat HEAD~5

# Any uncommitted changes
git status
```

### 2.3 Key Files
Based on CLAUDE.md "In Progress" and "Next Steps," identify and briefly review:
- Files currently being worked on
- Files that need modification next
- Entry points (main.py, index.js, etc.)

---

## Step 3: Identify Continuation Point

Based on your analysis, determine:

### 3.1 What Was Last Worked On
From CLAUDE.md session history:
- Last session's accomplishments
- Files that were modified
- Any incomplete work

### 3.2 What's Next
From CLAUDE.md "Next Steps":
- Priority 1 task (immediate)
- Priority 2-3 tasks (upcoming)
- Any blockers to address first

### 3.3 Current State Assessment
- Is there incomplete work to finish first?
- Are there any failing tests or broken code?
- Any blockers that need resolution?

---

## Step 4: Present Summary to User

After analysis, present a **concise summary**:

```markdown
## Project Resumed: [Project Name]

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

---

## Guidelines

### Be Concise
- Don't dump entire documentation back at user
- Summarize key points only
- Focus on actionable information

### Be Accurate
- Only state what's actually in the documentation
- If something is unclear, say so
- Don't assume - verify from docs/code

### Be Proactive
- Identify the most logical next step
- Flag any issues or blockers upfront
- Suggest files that will likely need changes

### Handle Missing Documentation
If CLAUDE.md or other docs are missing/incomplete:
```markdown
## Documentation Gap Detected

**Missing:** CLAUDE.md (session context file)

**Recommendation:** Run `/update-docs` first to establish documentation structure, then `/resume-work` again.

**Or:** I can analyze the codebase directly and create a status summary. Would you like me to proceed?
```

---

## Optional: Deep Dive Mode

If user runs `/resume-work deep` or `/resume-work --verbose`:

Provide additional details:
- Full architecture diagram
- Complete file tree
- All environment variables needed
- Detailed breakdown of each component's state
- Full session history (not just last session)

---

## After Resuming

Once you've presented the summary and user confirms direction:

1. **Start working** on the agreed task
2. **Reference docs** as needed during development
3. **At end of session**, remind user: "Run `/update-docs` to save progress"

---

## Quick Reference

| If... | Then... |
|-------|---------|
| CLAUDE.md exists | Read it first, it has everything you need |
| CLAUDE.md missing | Suggest running `/update-docs` first |
| Last session was recent | Focus on "In Progress" and "Next Steps" |
| Last session was weeks ago | Read more thoroughly, verify code state |
| User specifies task | Skip recommendation, focus on their request |
| Blockers exist | Surface them immediately before starting work |

---

## Scope

$ARGUMENTS
