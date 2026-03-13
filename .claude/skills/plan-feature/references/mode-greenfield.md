# MODE: GREENFIELD (New Project / Major Feature)

Cover ALL categories systematically:

## Technical Implementation
- Tech stack, framework, architecture pattern
- Data flow, API contracts, database schema
- Auth approach, state management
- External dependencies, performance requirements
- Caching, error handling, logging
- Testing strategy: which test types matter most? (unit, integration, e2e)
- What testing frameworks/tools do you want to use?

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
- Rollback strategy: if a phase fails, how should we recover? (revert commit, feature flag, migration rollback)

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

## Finishing Up (GREENFIELD)

After all categories are covered, provide:

1. **Summary** of key decisions/requirements by category
2. **Architecture overview** based on decisions
3. **Open questions** still to resolve
4. **Risks identified** with rollback strategy per phase
5. **Implementation phases** — numbered, with specific deliverables and test types (unit/integration/e2e) per phase

### Then ask:
> "Ready to proceed with implementation, or dig deeper on anything?"

**Only after I confirm -> proceed to Plan Mode.**
