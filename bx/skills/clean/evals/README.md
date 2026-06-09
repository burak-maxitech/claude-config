# `/bx:clean` eval suite

A small regression suite for the `/bx:clean` skill, built with `skill-creator`.

## Files

- `evals.json` — 3 evals (node report, python report, node `--fix`) with verifiable assertions.
- `GROUND-TRUTH.md` — every planted removable item + every trap, per fixture.
- `fixtures/node-react-app/` — TypeScript/React/Vite app. Traps: a config-only dep
  (`autoprefixer`) and a dynamic-`import()` module (`src/plugins/analytics.ts`).
- `fixtures/python-api/` — FastAPI app. Traps: four PyPI→import name mismatches incl. the
  obscure `pycryptodome`→`Crypto`.

Fixtures ship **without `.git` and without giveaway comments**. To run, copy a fixture to a
scratch dir and `git init` it (the skill prefers `git ls-files`, falling back to `find`).

## How it was built / run

Driven by `skill-creator`: each eval was dispatched twice — once **with** the skill, once as a
**baseline** with no skill — then graded against the assertions. Two iterations:

| Iteration | Eval | Result |
|-----------|------|--------|
| 1 (self-labeling fixtures) | all | with-skill 100% vs baseline 95.8% (+0.04) |
| 2 (these de-hinted + trap fixtures) | node report | tie, 18/18 both — raw Claude detects as well as the skill |
| 2 | python report | skill 14/14 vs baseline 13/14 — baseline skipped `datetime.utcnow()` |
| 2 | node `--fix` | skill 10/10 vs baseline 7/10 — baseline over-deleted Safe-to-Delete files + deps |

**Takeaway:** the skill's measurable value is in (a) **destructive-mode discipline** (quick-wins
only, defer the rest, never auto-remove deps) and (b) **comprehensive category coverage**
regardless of how narrowly the user phrases the request — not in raw detection, where a capable
model already does well. These evals are designed to keep those two properties from regressing.

## Re-running

These were run by hand via skill-creator's dispatch+grade flow (no committed runner). On
**Windows**, force UTF-8 for the skill-creator viewer or it crashes on its banner:

```
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 python <skill-creator>/eval-viewer/generate_review.py ...
```
