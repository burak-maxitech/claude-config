# /plan-feature - Feature Planning Interview

Interview me exhaustively about a feature before any implementation begins.

**Companion commands:**
- `/resume-work` - Start of session context
- `/update-docs` - End of session documentation

---

## Step 1: Detect Project State

First, analyze the current project state:

| State | Condition | Interview Mode |
|-------|-----------|----------------|
| **GREENFIELD** | No code exists, or CLAUDE.md shows "Not Started" for most components | Full architecture interview |
| **EXISTING** | Working codebase exists, CLAUDE.md shows progress | Integration-focused interview |

**Detection logic:**
```
IF no source code files exist (only docs):
    -> GREENFIELD mode
ELSE IF CLAUDE.md exists AND shows completed components:
    -> EXISTING mode (integration focus)
ELSE:
    -> GREENFIELD mode
```

**Announce the mode:**
> "Planning Mode: [GREENFIELD/EXISTING PROJECT]"

---

## Step 2: Read Project Context

### If CLAUDE.md exists, read it for:
- Current project status
- Completed components
- Architecture decisions already made
- Tech stack already chosen
- Known issues/blockers

### If docs/*.md (PRD files) exist, read them for:
- Existing architecture
- Data models
- API specifications
- Configuration patterns
- Integration details

### Use this context to:
- Skip questions already answered by existing docs
- Reference existing patterns in questions
- Identify integration points
- Understand constraints

---

## Step 3: Identify Feature Scope

If `$ARGUMENTS` provided:
- Read the specified plan file
- Identify NEW FEATURE sections vs existing documentation
- Focus interview on the new/changed parts

If no arguments:
- Ask: "What feature are you planning? Describe it briefly."
- Then proceed with interview

---

## Interview Process

1. Read all available context (CLAUDE.md, PRD, plan file)
2. Analyze what's specified vs what's ambiguous or missing
3. **Ask questions in batches of 3-5 at a time**
4. **Wait for my answers before continuing**
5. Probe deeper on vague answers
6. Continue until all relevant categories are covered
7. Summarize understanding and confirm before proceeding

**Do NOT start coding until the interview is complete.**

---

# MODE: GREENFIELD (New Project / Major Feature)

Cover ALL categories systematically:

## Technical Implementation
- Tech stack, framework, architecture pattern
- Data flow, API contracts, database schema
- Auth approach, state management
- External dependencies, performance requirements
- Caching, error handling, logging, testing strategy

## UI & UX (if applicable)
- User journey, screens/views needed
- Key interactions, responsive design
- Accessibility requirements
- Loading/empty/error states
- Navigation, visual hierarchy

## Edge Cases & Error Handling
- What happens when X fails?
- Offline behavior, timeouts, rate limiting
- Concurrent users, data validation failures
- Partial success scenarios, recovery mechanisms

## Concerns & Risks
- What's hardest? What worries you most?
- Security, scalability, maintainability concerns
- Blockers, dependencies on others, unknowns

## Tradeoffs & Decisions
- Speed vs quality, build vs buy
- Simplicity vs flexibility
- What's negotiable vs non-negotiable
- Technical debt tolerance

## Scope & Boundaries
- What's IN vs OUT of scope
- MVP vs full vision, what can be deferred
- What must ship together

## Business Context
- Stakeholders, timeline, success metrics
- Who maintains this, who uses it

---

# MODE: EXISTING PROJECT (Feature Addition)

Focus on integration, skip architecture already decided:

## Integration & Compatibility
- Which existing modules/files will this touch?
- What existing patterns should we follow?
- Are there breaking changes to existing APIs/schemas?
- What existing utilities/helpers can we reuse?
- How does this affect existing tests?

## New Technical Implementation
- What NEW data structures or schemas are needed?
- What NEW external APIs or services?
- What NEW configuration options?
- Performance impact on existing flows?

## Edge Cases & Migration
- How do we handle existing data?
- Backward compatibility requirements?
- Rollback strategy if something goes wrong?
- Feature flag or gradual rollout needed?

## Scope Boundaries
- What's the minimum viable addition?
- What can be deferred to a follow-up?
- Dependencies on other planned work?

## Testing Strategy
- New test cases needed?
- Which existing tests might break?
- Integration test considerations?

---

## Interview Rules

1. **Ask 3-5 numbered questions at a time**
2. Be specific to the plan/feature content - no generic questions
3. **Reference existing code/docs** when relevant (EXISTING mode)
4. **Skip questions already answered** by CLAUDE.md or PRD
5. Probe deeper on vague answers: "Can you be more specific about...?"
6. Note open questions when I say "I don't know"
7. Circle back if new answers affect earlier topics
8. After each category: "Anything else on [category] before we move on?"

## Question Types

- **Gap questions**: What's missing from the plan?
- **Ambiguity questions**: What could be interpreted multiple ways?
- **Assumption questions**: What unstated assumptions exist?
- **Implication questions**: What does X imply about Y?
- **Extreme questions**: Edge cases, scale limits, failure modes
- **Integration questions**: How does this fit with existing X? (EXISTING mode)

---

## Finishing Up

After all relevant categories are covered, provide:

### For GREENFIELD:
1. **Summary** of key decisions/requirements by category
2. **Architecture overview** based on decisions
3. **Open questions** still to resolve
4. **Risks identified**
5. **Suggested phases** for implementation

### For EXISTING PROJECT:
1. **Summary** of new feature requirements
2. **Integration points** with existing code
3. **Files to modify** vs new files to create
4. **Risks** specific to integration
5. **Impact on existing functionality**

### Then ask:
> "Ready to proceed with implementation, or dig deeper on anything?"

**Only after I confirm -> begin implementation.**

---

## After Interview Complete

Once I confirm ready to proceed:

1. **Update CLAUDE.md** with:
   - New feature added to "In Progress" or "Next Steps"
   - Key decisions added to "Key Decisions" table
   - Any new blockers/issues identified

2. **Optionally update PRD** with:
   - New feature specifications
   - Updated architecture if changed
   - New API endpoints/data models

3. **Begin implementation** following the plan

---

## Quick Reference

| Project State | Focus | Skip |
|---------------|-------|------|
| GREENFIELD | Full architecture, all categories | Nothing |
| EXISTING | Integration, compatibility, migration | Already-decided architecture |

| If I say... | Then... |
|-------------|---------|
| "I don't know" | Note as open question, move on |
| "Let's skip that" | Mark as out of scope, move on |
| "Good question..." | Probe deeper, important area |
| Vague answer | Ask follow-up for specifics |

---

## Start Now

1. Detect project state (GREENFIELD vs EXISTING)
2. Read CLAUDE.md and docs/*.md for context
3. Read plan file if provided in `$ARGUMENTS`
4. Announce planning mode
5. Begin interview with first batch of questions

$ARGUMENTS
