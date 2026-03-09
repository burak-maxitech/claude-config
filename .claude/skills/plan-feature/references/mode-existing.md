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

## Finishing Up (EXISTING PROJECT)

After all categories are covered, provide:

1. **Summary** of new feature requirements
2. **Integration points** with existing code
3. **Files to modify** vs new files to create
4. **Risks** specific to integration
5. **Impact on existing functionality**
6. **Implementation phases** — numbered, with specific deliverables per phase

### Then ask:
> "Ready to proceed with implementation, or dig deeper on anything?"

**Only after I confirm -> proceed to Plan Mode.**
