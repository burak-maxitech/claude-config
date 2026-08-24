# Scan: Structure + Design (complexity, coupling, layering, circular deps, D-prefix design principles)

Loaded by the orchestrator and passed to the `arch-structure` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Workspaces` — list or "none"
- `Linter` — name + invocation, OR "heuristic"
- `Tier` — full | bounded | sample
- `Scope file list` — exact paths to scan
- `Design catalog` — full content of `catalog-rules.md` + `catalog-design.md` (D-prefix). You
  receive the D-entries only; other prefixes belong to other scanners. Cite by ID.
- `Intended Architecture summary` — 3-5 bullets
- `Scoring contract` — the full contents of `finding-rubrics.md`. It is the canonical owner
  of the `severity` / `certainty` / `effort_estimate` anchors and of the two mandatory
  justification fields, `evidence` and `why_this_might_be_wrong`. Score against it rather than
  against your own sense of confidence — five scanners never see each other's output, and the
  orchestrator gates, ranks, and groups on exactly these numbers.

## Step 1 — Run the linter (if available)

If `Linter` is not "heuristic":

| Linter | Invocation | Output to parse |
|--------|------------|-----------------|
| `eslint` (with `complexity` rule) | `npx eslint --no-eslintrc -c <config> -f json <files...>` | JSON, look for `messages[].ruleId == 'complexity'` |
| `eslint-plugin-sonarjs` | same invocation, config enabling `sonarjs/cognitive-complexity` | JSON, `messages[].ruleId == 'sonarjs/cognitive-complexity'` — the message text carries the score |
| `radon` | `radon cc -j <files...>` | JSON, complexity per function |
| `ruff` | `ruff check --select C901 --output-format json <files...>` | JSON |
| `lizard` | `lizard -X <files...>` | XML, parse `<measure type="Function">` |
| `pmd` / `checkstyle` | (project-specific) | Parse XML report |

Cap the file list to the scope. Capture per-function CCN values. If the linter fails to run (config missing, version mismatch), log to your output as `linter_error: "<reason>"` and fall back to heuristic.

## Step 1b — Heuristic complexity (when no linter)

Two metrics, computed separately. Report both — they diverge, and that divergence is the point.

### Cyclomatic (McCabe)

For each function in scope, count occurrences of these decision-point patterns and add 1:

```
Grep pattern (per function body): \b(if|else if|elif|for|while|case|catch|except)\b|&&|\|\||\?[^.]
```

Document any function with count >10.

### Cognitive (simplified Sonar)

**Always compute this, even when a cyclomatic linter is available** — no cyclomatic tool
(`radon`, `ruff`, `lizard`, `pmd`) reports cognitive complexity. Only `eslint-plugin-sonarjs`
does, and only for JS/TS. Score per function:

| Rule | Points |
|------|--------|
| Each decision point (`if`, `for`, `while`, `case` group, `catch`) | +1 |
| **Nesting increment** — the same decision point, per level of nesting it sits inside | +1 per level |
| Each break in a sequence of boolean operators (`a && b \|\| c` = 2 sequences = 1 break) | +1 |
| Recursion (function calls itself) | +1 |
| `else` / `elif` continuing a chain | +1 (no nesting increment) |

Estimate nesting depth from indentation relative to the function header.

The nesting increment is what separates the two metrics: flattening a triply-nested `if` ladder
into guard clauses removes **zero** decision points (CCN unchanged) but strips every nesting
increment (cognitive drops sharply). That is why `R01` and `R09` exist, and why a CCN-only gate
used to delete every finding citing them.

Document any function with cognitive score >15.

## Step 2 — Identify hotspots

From the complexity data, surface:

- All functions with CCN > linter's threshold (or >10 in heuristic mode)
- All functions with cognitive score >15
- Top 20 functions by `max(ccn, cognitive)` across the scope, regardless of threshold

For each, also capture:

- File path and line range
- LOC of the function
- **Both** scores — a function at CCN 8 / cognitive 28 is a real hotspot that a CCN threshold
  misses entirely, and it is the shape guard-clause and named-predicate refactors target
- Whether the file is a test file (deprioritize tests — they often have high CCN by nature)

## Step 3 — God functions / files

- Functions: any function >100 LOC with CCN >15 → propose decomposition (R07)
- Files: any non-test file >500 LOC → flag for "consider module split" but keep certainty <0.6 unless intended-architecture summary mentions a layering model that this file violates

## Step 4 — Coupling smells

Use Grep to count import relationships:

```
For each source file F:
  fan_out = count of distinct files imported by F
  fan_in  = count of distinct files importing F
```

Flag outliers:

- `fan_out > 15` AND `fan_in < 3` → "shotgun importer" (likely a controller doing too much)
- `fan_in > 30` → "everyone depends on this" (likely a god module; coordinate with R07/R11 if applicable)

## Step 5 — Layering violations

### 5a — Against a documented layering

**When the Intended Architecture summary names specific layers** (e.g. "domain / adapters / infra", "feature folders with no cross-feature imports"), identify which directories belong to each. Then Grep for imports that violate the documented direction:

- Hexagonal: `domain/` must not import from `infrastructure/` or `adapters/`
- Feature folders: `features/X/` must not import from `features/Y/`
- Custom: whatever the summary specifies

These are full-confidence findings — the intended direction is stated, and the import contradicts it.

### 5b — Against an *observed* convention (when nothing is documented)

Most repos document no layering. Skipping the step entirely there — which is what this scan used
to do — means the common case gets no boundary analysis at all. Instead, **infer the dominant
direction and report violations of the codebase's own convention**:

1. Group files by top-level source directory (the natural module unit).
2. For each ordered pair of groups, count imports in each direction.
3. Where one direction dominates (**≥5 imports one way, ≤20% of that count the other**), treat the
   dominant direction as the observed convention.
4. Report the minority-direction imports as violations of it.

Frame these as **"this contradicts the convention the rest of the codebase follows"**, never as
"you are violating hexagonal architecture." The evidence is the ratio, and the finding must quote
it (`14 imports core → adapters, 2 the other way`).

**Cap certainty at 0.7 for every 5b finding** and set `respects_documented_decision: true` — there
is no documented decision to respect or violate. If the dominance test finds no clear direction
anywhere, say so: "no consistent module direction observed" is a legitimate architectural finding
about a codebase with no boundaries, and more useful than silence.

## Step 5c — Design principles (D-entries)

Scan the **D-prefix entries** in the design catalog passed in your task prompt (`catalog-design.md`,
shared rules in `catalog-rules.md`). Cite by ID in `cite_catalog_entry`.

These are the SOLID/OO checks — LSP, ISP, DIP, Law of Demeter, anemic domain model, feature envy,
primitive obsession, god class. Each entry carries its own detect-when trigger and
false-positive guards; follow them rather than the principle's textbook definition.

Two rules bind this step:

- **A finding must name the change that becomes expensive**, not the principle that is bent.
  "This violates SRP" is not a finding. "Every new payment method requires editing this class, its
  enum, and three switch statements" is.
- **`D03` (DIP violation) requires a named layering.** If the Intended Architecture summary names
  no layers — or says there are none deliberately — do not flag D03 at all. A layering inferred by
  Step 5b is **not** sufficient evidence for it; 5b establishes a convention, not an intended
  dependency direction. The other seven D-entries do not depend on layering and always apply.

`D03` is the counterpart of the simplification scanner's `S01`, which is hard-suppressed at
exactly the boundaries D03 protects. The two must never fire on the same interface.

## Step 6 — Circular dependencies

Build the import graph for the scope. For each edge `A -> B`, check if there is a (possibly transitive) path `B -> ... -> A`. Tools that help (use if available):

- JS/TS: `madge --circular <entry>` (only if installed)
- Python: `pydeps --max-bacon=2 --no-show <pkg>` (only if installed)

If neither, build the graph manually via Grep of imports. Cap analysis depth at 5 hops to avoid blowup.

## Output format (return per finding)

```
{
  "dimension": "structure",
  "location": "src/api/handler.ts:45-180",
  "title": "God function — handleRequest CCN 24, 180 LOC",
  "severity": "high",
  "certainty": 0.95,
  "effort_estimate": "medium",
  "ccn_current": 24,
  "ccn_projected": 6,
  "cognitive_current": 41,
  "cognitive_projected": 9,
  "respects_documented_decision": true,
  "recommended_refactor": "Decompose into 6 named steps per R07; the function fans out into auth, validation, dispatch, persistence, response, error handling — each is a natural extraction boundary.",
  "evidence": "Read handler.ts:45-180 in full. 6 blank-line-separated blocks, each with its own early-return. sonarjs reports cognitive 41. Grepped callers of handleRequest: 2 (routes/index.ts:14, test/handler.test.ts:9).",
  "why_this_might_be_wrong": "If the 6 blocks share more local state than the read suggests, extraction needs a context object and the projected cognitive drop is optimistic."
}
```

Do not return prose. Return only structured findings, ordered by `severity × certainty`. Cap output at 15 findings.
