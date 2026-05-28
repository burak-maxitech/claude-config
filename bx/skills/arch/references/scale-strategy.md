# Scale Strategy — Sample-Based Drill-Down

Used when repo size tier from Step 0 is `sample` (>500 files), or the user passed a path argument that still resolves to >500 files.

## Tier definitions

| Tier | Files in scope | Behavior |
|------|----------------|----------|
| `full` | <100 | Subagents read every file. CCN computed for every function. |
| `bounded` | 100-500 | Subagents quick-scan all files; deep-read top-30 by hotspot score per dimension. |
| `sample` | >500 | Smart sample selection (below); drill-down on hotspots. Cap deep-reads at 50 files. |

`--full-scan` forces `full` regardless. Warn the user if they pass `--full-scan` on a >2000-file repo (will be slow / expensive).

## Smart sampling formula

For each candidate file in scope, compute a priority score:

```
priority = log(LOC + 1) × (1 + churn_score) × (1 + fan_in_score)
```

Where:

- **LOC** = `wc -l <file>` (uncomment-stripped not necessary; raw lines is fine)
- **churn_score** = number of commits touching this file in the last 90 days, normalized to 0..1 across all files in scope:
  ```
  git log --since='90 days ago' --name-only --pretty=format: | sort | uniq -c | sort -rn
  ```
- **fan_in_score** = number of distinct files importing this file, normalized to 0..1 across all files in scope. For JS/TS/Python, count `from <path>` / `import <path>` references via Grep. For other languages, fall back to filename-as-symbol Grep.

Take the **top 50 files by priority** as the sample. Add any file matching:

- A configured "always include" path from CLAUDE.md or README (e.g., `src/index.ts`, `main.py`)
- Any file >800 LOC even if low churn (large files often hide complexity)

## Drill-down triggers

After subagents return findings on the sampled set, drill down on:

- Any sampled file with at least one finding of severity `high` → also read its **importer** files (one hop) and **direct dependencies** (one hop). Re-run the same dimension's checks on those.
- Any **module** (directory) where ≥2 sampled files had high-severity findings → read all remaining files in that module.

Cap drill-downs at 50 additional files total. Beyond that, surface a warning in the report footer.

## "What was sampled vs skipped" disclosure

The report footer must include:

```
Files in scope: <total>
Files sampled: <N> (priority-ranked)
Files via drill-down: <M>
Files skipped: <total - N - M>

Top skipped (low priority): <up to 10 paths>
```

This lets the user spot blind spots. If a known hotspot is in the skipped list, they can re-run with `--full-scan` or with a path argument.
