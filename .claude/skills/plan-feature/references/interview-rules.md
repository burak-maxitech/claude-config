# Interview Rules & Question Types

## Rules

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
