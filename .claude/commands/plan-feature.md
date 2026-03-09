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

## Step 2: Read Project Context (Parallel)

### Check Auto-Memory First
Claude Code's auto-memory (`~/.claude/projects/<project-path>/memory/MEMORY.md`) is automatically loaded into your context. If it contains tech stack, architecture, and key paths — you already have stable project facts. Focus your reading on evolving state in CLAUDE.md.

### Read all context in a single parallel call:
- `CLAUDE.md` — current status, completed components, architecture decisions, tech stack, known issues/blockers
- `README.md` — project overview, structure (skim if auto-memory covers this)
- `docs/` folder listing — identify PRD files, architecture docs, API specs
- Plan file from `$ARGUMENTS` (if provided)

This is a single turn — do NOT read these sequentially.

### After the parallel read:
- Read any PRD/spec files referenced in CLAUDE.md "Key Documentation"
- Note existing data models, API specs, configuration patterns, integration details

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
5. **Implementation phases** — numbered, with specific deliverables per phase

### For EXISTING PROJECT:
1. **Summary** of new feature requirements
2. **Integration points** with existing code
3. **Files to modify** vs new files to create
4. **Risks** specific to integration
5. **Impact on existing functionality**
6. **Implementation phases** — numbered, with specific deliverables per phase

### Then ask:
> "Ready to proceed with implementation, or dig deeper on anything?"

**Only after I confirm -> proceed to Plan Mode.**

---

## After Interview Complete: Enter Plan Mode

Once I confirm ready to proceed, transition into a formal implementation plan:

### Step 1: Enter Plan Mode
Use `EnterPlanMode` to switch into planning mode. This gives you access to explore the codebase in detail and design a concrete implementation approach.

### Step 2: Write the Implementation Plan
In plan mode, create a detailed plan that includes:
1. **Phase breakdown** — each phase from the interview summary becomes a plan section
2. **File-level changes** — for each phase, list specific files to create/modify with what changes
3. **Dependencies** — which phases depend on others
4. **Risk mitigations** — concrete steps to address each identified risk
5. **Testing approach** — what to test at each phase

### Step 3: Exit Plan Mode for Approval
Use `ExitPlanMode` to present the plan to the user for approval. The user will review and either approve or request changes.

**Do NOT begin implementation until the plan is approved via ExitPlanMode.**

---

## After Plan Approved: Hydrate Task List

Once the user approves the plan, **create a live task tracker** from the implementation phases:

### Create Tasks with TaskCreate
For each implementation phase/step in the approved plan:
1. Create a task with `TaskCreate`:
   - **subject** — imperative form (e.g., "Create user authentication endpoint")
   - **description** — include specific files, changes, and acceptance criteria from the plan
   - **activeForm** — present continuous (e.g., "Creating user authentication endpoint")
2. Set `blockedBy` dependencies between sequential phases
3. Mark the first task as `in_progress` to begin

### Rules
- **One task per logical unit of work** — don't create a task per file, create a task per deliverable
- **Limit to ~10 tasks max** — group small steps if there are many phases
- **Include testing tasks** — add a task for writing tests after each major phase
- **Skip documentation tasks** — `/update-docs` handles that at end of session

### Then update CLAUDE.md:
1. New feature added to "In Progress"
2. Key decisions added to "Key Decisions" table
3. Any new blockers/issues identified

### Optionally update PRD with:
- New feature specifications
- Updated architecture if changed
- New API endpoints/data models

### Begin implementation following the task list.

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

1. Check auto-memory for existing project context
2. Detect project state (GREENFIELD vs EXISTING)
3. Read CLAUDE.md, README.md, docs/*.md, and plan file (if provided) **in parallel**
4. Announce planning mode
5. Begin interview with first batch of questions
6. After interview → `EnterPlanMode` → write implementation plan → `ExitPlanMode` for approval
7. After approval → hydrate tasks with `TaskCreate` → begin implementation

$ARGUMENTS
