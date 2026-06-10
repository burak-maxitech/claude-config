# Dependencies & Config Scanner

You are a subagent scanning for unused dependencies, obsolete patterns, and configuration cruft. Focus on actionable findings — things the user can actually remove.

## Input

You will receive the detected package manager and config file paths. Use them to target your search.

## 4. Unused Dependencies

### 4.0 Workspace detection (do this BEFORE per-manifest scanning)

A monorepo has multiple `package.json` / `Cargo.toml` files. Scanning only the root will both miss workspace-only deps and false-positive root deps consumed by children. Detect workspaces first:

- **npm / yarn classic / yarn berry:** root `package.json` has a `workspaces` field (array of globs like `["packages/*", "apps/*"]` or object form `{"packages": [...]}`)
- **pnpm:** `pnpm-workspace.yaml` at repo root with top-level `packages:` list
- **Cargo:** root `Cargo.toml` has `[workspace]` table with `members = [...]`

If any of the above is present, expand the globs to enumerate each child manifest. Treat each manifest as an independent scan target:
- A dep listed in a workspace's manifest is "unused" only if **that workspace's own source subtree** never references it (sibling-workspace usage doesn't count — that's misplaced, not used)
- A dep listed in the root manifest is "used" if **any workspace** references it (root deps are typically hoisted)

Tag every finding with the workspace it belongs to (use `root` for the top-level manifest). If there's no workspace config, scan the single root manifest as before and tag everything `root`.

### 4.1 Per-manifest scan

**For Node.js (package.json):**
- Extract `dependencies` and `devDependencies` keys from the manifest
- **Batch the search.** Do not loop one-grep-per-package — that's O(N) Grep calls on potentially hundreds of deps. Use the `Grep` tool once with a single regex that alternates all package names, e.g.:
  ```
  pattern: from ['"](pkg1|pkg2|pkg3|...)['"]|require\(['"](pkg1|pkg2|pkg3|...)['"]\)|import\(['"](pkg1|pkg2|pkg3|...)['"]\)
  output_mode: content
  glob: *.{js,jsx,ts,tsx,mjs,cjs}
  ```
  Then post-process the matches: any package name from the manifest that didn't appear in any match line is an "unused" candidate. Re-verify those candidates with a second targeted Grep pass to rule out string templates and other dynamic references. Escape regex metacharacters in package names (`@scope/pkg` → `@scope/pkg`, but `pkg-name` is literal-safe).
- Scope the scan to the workspace's source subtree (e.g., `packages/api/src/**` for the `packages/api` workspace; root `src/**` for root) — use the Grep tool's `path` parameter
- Also check config files that reference packages: `webpack.config.*`, `vite.config.*`, `babel.config.*`, `.eslintrc*`, `jest.config.*`, `tsconfig.json`, `postcss.config.*`
- A dependency is "unused" if zero source files AND zero config files reference it AND it's not used via CLI (check `scripts` in that manifest)
- Watch for `@types/*` packages — only flag if the corresponding runtime package is also unused

**For Python (requirements.txt / pyproject.toml / Pipfile):**
- Extract package names from the dependency file
- For each, grep for `import package_name` and `from package_name` across all `.py` files
- **IMPORTANT**: Python package names often differ from import names. Use this lookup table for the most common mismatches before falling back to the raw package name:

  | PyPI Package | Import Name(s) |
  |---|---|
  | Pillow | PIL |
  | beautifulsoup4 | bs4 |
  | python-dateutil | dateutil |
  | scikit-learn | sklearn |
  | scikit-image | skimage |
  | opencv-python / opencv-contrib-python | cv2 |
  | PyYAML | yaml |
  | python-dotenv | dotenv |
  | attrs | attr |
  | google-cloud-storage | google.cloud.storage |
  | google-auth | google.auth |
  | python-jose | jose |
  | python-multipart | multipart |
  | Pygments | pygments |
  | msgpack-python | msgpack |
  | pycryptodome | Crypto |
  | py-cpuinfo | cpuinfo |
  | ruamel.yaml | ruamel.yaml (same, but note the dot) |
  | python-magic | magic |
  | python-Levenshtein | Levenshtein |
  | pymongo | pymongo (same, but submodules like bson come bundled) |
  | psycopg2-binary / psycopg2 | psycopg2 |
  | mysqlclient | MySQLdb |
  | ujson | ujson (same, but sometimes installed as `python-ujson`) |
  | Faker | faker |
  | Jinja2 | jinja2 |
  | MarkupSafe | markupsafe |
  | Werkzeug | werkzeug |

  For packages not in this table, try both the raw package name and the name with hyphens replaced by underscores.
- Check if the package is used in scripts, Dockerfiles, or CI configs

**For Rust (Cargo.toml):**
- If the root `Cargo.toml` has `[workspace]` with `members = [...]`, scan each member crate's `Cargo.toml` separately (the workspace detection above already handled this)
- Extract crate names from `[dependencies]` (and `[dev-dependencies]`, `[build-dependencies]`)
- Batch the search: one Grep call with all crate names alternated (`use (crate1|crate2|...)|extern crate (crate1|crate2|...)`), scoped to the workspace's `src/` and `tests/` via `path`
- Grep for `use crate_name` or `extern crate crate_name` in `.rs` files
- Note: Rust crate names use hyphens in Cargo.toml but underscores in code — when alternating, include both forms (`tokio_util|tokio-util`)

**For Go (go.mod):**
- Extract module paths from the `require` block, skipping `// indirect` entries (those are transitive — not the user's to remove)
- Go import paths contain the module path verbatim, so one batched Grep alternating the module paths across `*.go` files finds usage directly
- A module with zero import hits is an "unused" candidate; the `uninstall_command` is simply `go mod tidy` (it removes unrequired modules natively)

**For PHP (composer.json) / Ruby (Gemfile):**
- PHP: grep for the package's autoload namespace (`use Vendor\Package`) across `.php` files; Ruby: grep for `require "gem_name"` / `require 'gem_name'` across `.rb` files
- Composer autoloading, Laravel service discovery, and Rails' implicit `Bundler.require` all load packages with zero greppable references — cap these findings at `likely_safe`, never `safe`

**For any ecosystem:**
- Flag duplicate packages serving the same purpose (e.g., both `moment` and `dayjs`, both `lodash` and `underscore`, both `axios` and `node-fetch`)
- Note version pinning issues (exact pins on packages that should float, or floating versions on packages that should be pinned)

**Output format:**

```
## Unused Dependencies
- package: <name>
  workspace: <workspace name, or "root">
  version: <version from lockfile>
  type: production|dev
  reason: <why it appears unused>
  uninstall_command: <e.g., npm uninstall package-name -w packages/api>
  risk: safe|likely_safe|needs_investigation

## Misplaced Dependencies (monorepos only)
- package: <name>
  declared_in: <workspace manifest where it's listed>
  used_in: <workspace(s) that actually import it>
  recommendation: <move it, or hoist to root>

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

---

## 4.5 Vulnerable Dependencies (only when `--vulns` is requested)

**Skip this entire section unless your task prompt explicitly says `--vulns` is enabled.** Vulnerability scanning hits network registries, is slower than the rest of the audit, and may fail in offline environments — running it by default would surprise users.

When `--vulns` is enabled, run the appropriate audit command per detected stack and surface known CVEs. This is *additive* to (not replacing) the unused-deps scan.

### 4.5.1 Per-stack audit commands

Pick the command(s) matching the detected stack. Prefer JSON output where available so the agent can parse rather than scrape text.

**Node / npm-family — pick by lockfile:**
- `package-lock.json` present → `npm audit --json` (set `--audit-level=low` to include everything; default omits low-severity)
- `yarn.lock` present → `yarn npm audit --json --recursive` (Yarn Berry) or `yarn audit --json` (Yarn Classic — line-delimited JSON, parse line-by-line)
- `pnpm-lock.yaml` present → `pnpm audit --json`
- For monorepos, run the audit per workspace where each child has its own lockfile; otherwise run once at the root.

**Python:**
- Prefer `pip-audit --format=json` (works against `requirements.txt`, `pyproject.toml`, or the active environment)
- Fallback `safety check --json` if `pip-audit` is unavailable
- If neither tool is installed, emit a single finding noting which tool to install rather than scraping CVE databases manually

**Rust:**
- `cargo audit --json` (requires `cargo-audit` installed; emit an install hint if missing: `cargo install cargo-audit`)

**Go:**
- `govulncheck -json ./...` (requires `golang.org/x/vuln/cmd/govulncheck`; emit an install hint if missing)

**PHP:**
- `composer audit --format=json` (Composer 2.4+)

**Ruby:**
- `bundle audit check --update --format json` (requires `bundler-audit` gem)

**For any ecosystem:**
- If the audit tool isn't installed and can't be invoked, return ONE finding describing how to install it, and skip the rest of the vuln scan for that stack. Do not silently emit zero findings — that's indistinguishable from "everything is safe."
- If the audit command fails for a non-tool reason (network error, lockfile out of sync), surface the error verbatim as a single finding. Don't pretend it succeeded.
- Set a 60-second timeout on the audit subprocess. If it doesn't return in time, surface a "timed out" finding and move on.

### 4.5.2 Severity-to-risk mapping

Audit tools report severity (CVSS-derived). Map to the existing `risk` field:

| Audit severity | bx:clean risk |
|---|---|
| critical | safe (in the sense that the *finding* is high-confidence and actionable — the *upgrade* is what's risky, see below) |
| high | safe |
| moderate / medium | likely_safe |
| low | needs_investigation |
| info / negligible | (drop — not worth surfacing) |

**Important:** the `risk` field here describes confidence that the finding is real and worth acting on, not the risk of running an upgrade. Vulnerability fixes can still break the app — `--fix` mode does NOT auto-upgrade vulnerable deps (see SKILL.md Fix Mode).

### 4.5.3 Output format

```
## Vulnerable Dependencies
- package: <name>
  workspace: <workspace name, or "root">
  installed_version: <version from lockfile>
  vulnerable_range: <e.g., "<2.4.5">
  fixed_version: <version that resolves the CVE, if known; "no fix available" otherwise>
  cve: <CVE-YYYY-NNNNN, or advisory ID like GHSA-xxxx-xxxx-xxxx>
  severity: critical|high|moderate|low
  title: <short CVE title>
  fix_command: <e.g., "npm install package@2.4.5" or "no fix yet — pin alternative">
  risk: safe|likely_safe|needs_investigation
  source: <audit tool name, e.g., "npm audit" or "pip-audit">
```

If the audit tool returns zero vulnerabilities, emit ONE summary line:
```
## Vulnerable Dependencies
- (none — <tool> reported 0 vulnerabilities at <severity threshold>)
```

If the audit tool isn't available:
```
## Vulnerable Dependencies
- tool_unavailable: <tool name>
  install_command: <how to install it>
  reason: <e.g., "cargo-audit binary not found">
```

### 4.5.4 What to skip

- **GitHub Dependabot alerts.** They overlap with `npm audit` / `pip-audit` and require API auth. Audit-CLI output is the simpler signal.
- **Transitive vs. direct distinction beyond what the tool reports.** The audit tools already surface this; don't try to re-derive it from lockfile traversal.
- **CVE de-duplication across workspaces.** If the same CVE appears in 3 workspaces of a monorepo, emit 3 findings (with the workspace tag) — they may need separate fixes if pinned differently.