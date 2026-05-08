# Scan: Structure (cyclomatic + cognitive complexity, coupling, layering, circular deps)

Loaded by the orchestrator and passed to the `arch-structure` subagent. Detailed scanning instructions follow.

## Inputs you receive in your task prompt

- `Detected stack` — language(s), framework(s)
- `Workspaces` — list or "none"
- `Linter` — name + invocation, OR "heuristic"
- `Tier` — full | bounded | sample
- `Scope file list` — exact paths to scan
- `Intended Architecture summary` — 3-5 bullets

## Step 1 — Run the linter (if available)

If `Linter` is not "heuristic":

| Linter | Invocation | Output to parse |
|--------|------------|-----------------|
| `eslint` (with `complexity` rule) | `npx eslint --no-eslintrc -c <config> -f json <files...>` | JSON, look for `messages[].ruleId == 'complexity'` |
| `radon` | `radon cc -j <files...>` | JSON, complexity per function |
| `ruff` | `ruff check --select C901 --output-format json <files...>` | JSON |
| `lizard` | `lizard -X <files...>` | XML, parse `<measure type="Function">` |
| `pmd` / `checkstyle` | (project-specific) | Parse XML report |

Cap the file list to the scope. Capture per-function CCN values. If the linter fails to run (config missing, version mismatch), log to your output as `linter_error: "<reason>"` and fall back to heuristic.

## Step 1b — Heuristic CCN (when no linter)

For each function in scope, count occurrences of these decision-point patterns and add 1:

```
Grep pattern (per function body): \b(if|else if|elif|for|while|case|catch|except)\b|&&|\|\||\?[^.]
```

This approximates McCabe CCN. Document any function with count >10.

## Step 2 — Identify hotspots

From CCN data, surface:

- All functions with CCN > linter's threshold (or >10 in heuristic mode)
- Top 20 highest-CCN functions across the scope, regardless of threshold

For each, also capture:

- File path and line range
- LOC of the function
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

**Only run this step if the Intended Architecture summary names specific layers** (e.g. "domain / adapters / infra", "feature folders with no cross-feature imports"). Otherwise skip — there's no defined ordering to violate.

For each named layer, identify which directories belong to it. Then Grep for imports that violate the documented direction:

- Hexagonal: `domain/` must not import from `infrastructure/` or `adapters/`
- Feature folders: `features/X/` must not import from `features/Y/`
- Custom: whatever the summary specifies

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
  "respects_documented_decision": true,
  "recommended_refactor": "Decompose into 6 named steps per R07; the function fans out into auth, validation, dispatch, persistence, response, error handling — each is a natural extraction boundary."
}
```

Do not return prose. Return only structured findings, ordered by `severity × certainty`. Cap output at 30 findings.
