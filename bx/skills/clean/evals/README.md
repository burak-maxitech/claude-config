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
| 3 (bx 2.13.0 content review; baseline = the 2.12.2 skill, not no-skill) | all three | 42/42 both versions — detection and fix-mode discipline held through the rewrite. The runs surfaced one defect neither review had: scanners tagged whole-file deletions `quick_win: true` because the tag was never defined; both orchestrators reconciled by hand, and 2.13.0 pins the closed set in every scan file |
| 4 (bx 2.13.0, seven new categories; baseline = the pre-change 2.13.0 skill) | all three | new skill 60/60; baseline 59/60. Both found every planted hit, so raw detection is again a tie. The one discriminating assertion is a precision trap: the baseline flagged the env-driven `FLAGS.beta` (`import.meta.env.VITE_BETA`) as an obsolete pattern because no `.env` defines it; the new scan file's rule that environment- and service-driven flags are never stale-flag candidates held |

Iteration 4 added one hit and one trap per new category to both fixtures (see GROUND-TRUTH.md); 11 node, 6 python and 1 fix-mode assertions were appended.

Iteration 3 was a regression check on a rewrite, so its baseline is the previous skill version rather than raw Claude; a tie is the expected pass. The eval subagents were able to dispatch the real `bx:cleanup-*` agents, so the runs exercised the Agent-tool fan-out, not an inline fallback.

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
