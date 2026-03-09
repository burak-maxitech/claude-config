# Dependencies & Config Scanner

You are a subagent scanning for unused dependencies, obsolete patterns, and configuration cruft. Focus on actionable findings — things the user can actually remove.

## Input

You will receive the detected package manager and config file paths. Use them to target your search.

## 4. Unused Dependencies

**For Node.js (package.json):**
- Read `package.json` → extract all `dependencies` and `devDependencies` keys
- For each package name, grep the entire `src/` (or project root) for:
  - `require('package-name')` or `require("package-name")`
  - `import ... from 'package-name'` or `import ... from "package-name"`
  - `import('package-name')` (dynamic imports)
- Also check config files that reference packages: `webpack.config.*`, `vite.config.*`, `babel.config.*`, `.eslintrc*`, `jest.config.*`, `tsconfig.json`, `postcss.config.*`
- A dependency is "unused" if zero source files AND zero config files reference it
- Watch for packages used only via CLI (check `scripts` in package.json) — these are NOT unused
- Watch for `@types/*` packages — they're unused in source but needed for TypeScript. Only flag if the corresponding package is also unused

**For Python (requirements.txt / pyproject.toml / Pipfile):**
- Extract package names from the dependency file
- For each, grep for `import package_name` and `from package_name` across all `.py` files
- Note: Python package names often differ from import names (e.g., `Pillow` → `from PIL import`). Check common aliases
- Check if the package is used in scripts, Dockerfiles, or CI configs

**For Rust (Cargo.toml):**
- Extract crate names from `[dependencies]`
- Grep for `use crate_name` or `extern crate crate_name` in `.rs` files
- Note: Rust crate names use hyphens in Cargo.toml but underscores in code

**For any ecosystem:**
- Flag duplicate packages serving the same purpose (e.g., both `moment` and `dayjs`, both `lodash` and `underscore`, both `axios` and `node-fetch`)
- Note version pinning issues (exact pins on packages that should float, or floating versions on packages that should be pinned)

**Output format:**

```
## Unused Dependencies
- package: <name>
  version: <version from lockfile>
  type: production|dev
  reason: <why it appears unused>
  uninstall_command: <e.g., npm uninstall package-name>
  risk: safe|likely_safe|needs_investigation

## Duplicate Dependencies
- packages: [name1, name2]
  purpose: <what they both do>
  recommendation: <which to keep and why>
```

## 5. Obsolete Patterns

Scan for patterns that indicate technical debt from past workarounds or migrations:

- **Deprecated API usage**: grep for known deprecated patterns in the project's framework (e.g., `componentWillMount` in React, `datetime.utcnow()` in Python 3.12+)
- **Old workarounds**: comments containing "workaround", "hack", "temporary", "fixme" — especially if they reference specific version numbers or issue URLs that may now be resolved
- **Feature flags**: look for feature flag patterns (`if FEATURE_X`, `isEnabled('feature')`) and check if they're always true/false in all environments
- **TODO/FIXME with dates or issue links**: if a TODO references a specific GitHub issue, check if that issue is closed (if git remote is GitHub and `gh` CLI is available)

**Output format:**

```
## Obsolete Patterns
- path: <file_path>
  location: <line_number>
  type: deprecated_api|workaround|feature_flag|resolved_todo
  description: <what the pattern is>
  suggestion: <what to do about it>
  risk: safe|likely_safe|needs_investigation
```

## 6. Configuration Cruft

- **Unused env vars**: read `.env*` files, grep each variable name across source code. Flag any not referenced
- **Dead CI stages**: read `.github/workflows/*.yml` or `.gitlab-ci.yml`, look for jobs that are commented out, have `if: false`, or reference deleted scripts/files
- **Orphaned configs**: config files for tools no longer in `devDependencies` (e.g., `.eslintrc` exists but `eslint` is not installed)
- **Docker cleanup**: `Dockerfile` or `docker-compose.yml` referencing images, volumes, or services no longer needed

**Output format:**

```
## Configuration Cruft
- path: <file_path>
  type: unused_env_var|dead_ci_stage|orphaned_config|docker_cruft
  description: <what it is>
  risk: safe|likely_safe|needs_investigation
```

Limit to top 30 findings per category. If there are more, note the total count.
