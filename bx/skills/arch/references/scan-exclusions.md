# Scan Exclusions — what a repo-wide scanner must never scan

**Canonical owner** for the paths every repo-wide scanning skill excludes. Cited by `/bx:arch`
(Step 3 + all five `arch-*` agents) and `/bx:tests` (Step 0 + Step 3 + all three `test-*` agents).
Satellites cite this file; they do not restate the lists.

The orchestrator computes the scope **once** using these rules and passes the resulting file list to
its agents. Agents do not re-derive exclusions — that is how the lists drift apart.

---

## 1. Synthetic and fixture trees — the one that produces confident nonsense

**Exclude from every scan, and from stack/framework detection:**

```
**/evals/fixtures/**      **/__fixtures__/**      **/fixtures/**
**/testdata/**            **/.skill-creator-workspace/**
```

These hold **deliberately planted defects**. In this repo, `bx/skills/clean/evals/fixtures/` is a
synthetic project the `/bx:clean` eval suite grades against: `oldHelpers.ts` is unused *on purpose*,
`legacy_handlers.py` is dead *on purpose*, `OldModal.test.tsx` is orphaned *on purpose*. A scanner
that finds them reports true-shaped findings that are false by construction — and the run **looks
successful**, which is what makes this the most dangerous exclusion to omit.

**This also governs stack and framework detection, not just file scanning.** A fixture tree carries
its own manifests. `bx/skills/clean/evals/fixtures/node-react-app/package.json` declares
`"test": "vitest run"` and `vitest` in devDependencies; `python-api/requirements.txt` lists
`fastapi` and `redis`. Neither is this repo's stack. A detection step that reads any `package.json`
it can find will conclude this is a Vitest project and audit fabricated code.

**Rule:** resolve stack and framework signals from manifests **outside** the excluded trees only. If
the only manifest in a repo sits inside a fixture tree, the correct conclusion is "no stack
detected", not the fixture's stack.

**Not excluded:** a project's own `tests/` or `__tests__/` directory holding real tests. The trigger
is *fixture/testdata* naming, not *test* naming — `/bx:tests` must obviously still scan real tests.

## 2. Vendored and generated

```
node_modules   venv   .venv   .git       dist      build     target/
__pycache__    .next  .cache  vendor     coverage/ .tox      .mypy_cache
*.generated.*  **/__generated__/**       *.min.js  *.lock
```

Machine-authored or third-party. Findings here are not actionable by the reader, and on a large repo
they dominate the result set.

## 3. Immutable history

Dated planning records (`YYYY-MM-DD-*.md`, e.g. under `docs/superpowers/`) and the auto-managed
history archives are records of past state, never rewritten by a scan. The archive set and its
access rule are owned by `../save/references/doc-schema.md` — resolve against the citing skill's base
directory — not restated here.

---

## Applying this

1. **Compute scope once**, in the orchestrator's scope-selection step, after tier selection.
2. **Report what was excluded** in the run's footer, with counts — a reader cannot distinguish a
   clean codebase from a narrowed scan unless the scan says which it was. "Excluded: 26 planted eval
   fixtures" is the disclosure; silence is not.
3. **Never let an agent widen its own scope.** If an agent believes something outside its file list
   matters, it reports that as a note, not by reading it.

## Known restatements still to be swept

These files still carry their own copy of the §2 list and should be repointed here (S57 named-owner
principle). Tracked rather than silently tolerated:

`bx/agents/{cleanup-files-code,geo-generative,seo-content,seo-gsc-insights,seo-technical}.md`,
`bx/skills/seo/references/{scan-content,scan-geo,scan-technical}.md`,
`bx/skills/webdesign/references/{phase1-extract,phase3-inject,web-stack-detection}.md`.

`/bx:arch` and `/bx:tests` are already repointed.
