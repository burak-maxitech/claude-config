# Interview Rules & Question Types

## Tool: use `AskUserQuestion`

Drive the interview with the **`AskUserQuestion`** tool, not freeform numbered prompts in chat. Per the official best-practices doc, this is the recommended interview pattern — the user gets a structured multi-choice UI, several questions can be batched in one turn, and answers come back cleanly attributed to each question.

When `AskUserQuestion` is unavailable in the current environment, fall back to numbered Q&A in plain text — the rules below apply either way.

## Rules

1. **Batch 3-4 questions per `AskUserQuestion` call** (or per chat turn in fallback mode) — the tool's `questions` array is capped at 4; passing 5 errors with `too_big maximum: 4`
2. For each question, supply **2-4 multi-choice options** that cover the realistic answer space, plus an "Other / explain" option for anything you didn't anticipate. This is faster for the user than typing freeform answers and surfaces options they may not have considered.
3. Be specific to the plan/feature content — no generic questions
4. **Reference existing code/docs** when relevant (EXISTING mode)
5. **Skip questions already answered** by CLAUDE.md or PRD
6. Probe deeper on vague or "Other" answers: ask a follow-up question with refined options
7. Note open questions when the user picks "I don't know" / "skip"
8. Circle back if new answers invalidate earlier ones — re-ask with updated options
9. After each category, ask one wrap-up question: "Anything else on [category] before we move on?" (yes / no / specific concern)

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
