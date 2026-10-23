# Dependencies & Config Scanner

You are a subagent scanning for unused dependencies, obsolete patterns, and configuration cruft. Focus on actionable findings — things the user can actually remove.

## Input

Your task prompt gives you the detected package manager(s), the config file paths, the **scope** (a directory, or the repo root), and the **excluded paths** the orchestrator computed from `scan-exclusions.md`. Use them to target your search. Never read a manifest inside an excluded path — a fixture tree's `package.json` declares the fixture's dependencies, not the project's — and never widen the scope on your own.

**Scoped runs.** Dependencies and configuration are declared at the repo or workspace root. The orchestrator dispatches you under a directory scope only when that directory is itself a workspace root; then §4 and §6 apply to *that* manifest and *that* workspace's source, while §5 (obsolete patterns) reports only files inside the scope. If you are handed a scope that is not a workspace root, say so in `## Unavailable checks` and skip §4 and §6 rather than grepping one directory for every dependency in the root manifest — that would flag everything the rest of the app uses.

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
- **Batch the search.** Do not loop one-grep-per-package — that's O(N) Grep calls on potentially hundreds of deps. Use the `Grep` tool once with a single regex that alternates all package names and **allows a subpath after the name** — `import debounce from 'lodash/debounce'` and `import 'swiper/css'` are uses of `lodash` and `swiper`, and a pattern that demands the closing quote right after the name misses every one of them:
  ```
  pattern: (from|import|require\(|import\()\s*['"](pkg1|pkg2|pkg3|...)(/[^'"]*)?['"]
  output_mode: content
  glob: *.{js,jsx,ts,tsx,mjs,cjs,mts,cts,vue,svelte,astro,mdx,scss,sass,less,css}
  ```
  The style extensions are there for `@import 'normalize.css'` / `@use 'bootstrap/scss/bootstrap'` — a CSS-only package has no JS import anywhere. Then post-process the matches: any package name from the manifest that didn't appear in any match line is an "unused" candidate. Re-verify those candidates with a second targeted Grep pass to rule out string templates and other dynamic references. Escape regex metacharacters in package names before alternating: `.` is the common one (`socket.io` → `socket\.io`, `lodash.debounce` → `lodash\.debounce`); `@scope/name` and hyphens are literal-safe.
- Scope the scan to the workspace's source subtree (e.g., `packages/api/src/**` for the `packages/api` workspace; root `src/**` for root) — use the Grep tool's `path` parameter
- Also check config files that reference packages: `webpack.config.*`, `vite.config.*`, `babel.config.*`, `.eslintrc*`, `eslint.config.*`, `jest.config.*`, `vitest.config.*`, `tsconfig.json`, `postcss.config.*`, `tailwind.config.*`, `.prettierrc*`, `.stylelintrc*`. Tool plugins and presets are often named there as bare strings (`"plugins": ["autoprefixer"]`, `"extends": "@acme/eslint-config"`) and nowhere in source.
- A dependency is "unused" if zero source files AND zero config files reference it AND it's not used via CLI (check `scripts` in that manifest)
- Watch for `@types/*` packages — only flag if the corresponding runtime package is also unused

**For Python (requirements.txt / pyproject.toml / Pipfile):**
- Extract package names from the dependency file. A requirement line carries more than the name — strip extras, version specifiers, markers and comments (`requests[security]>=2.31 ; python_version>"3.8"  # http` → `requests`); in `pyproject.toml` read `[project] dependencies` / `optional-dependencies` and `[tool.poetry.dependencies]`.
- Resolve each name to its import name(s) (table below), then **batch the search**: one `Grep` call with pattern `^\s*(from|import)\s+(name1|name2|...)\b` across `*.py` (and `*.ipynb` if present). Any name with zero hits is an "unused" candidate.
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
- Check if the package is used in scripts, Dockerfiles, or CI configs. Some packages are consumed by the runtime, not imported: `uvicorn`/`gunicorn` appear in a `CMD` or Procfile, `psycopg2` is loaded by SQLAlchemy from a `postgresql+psycopg2://` URL, `python-multipart` is required by FastAPI form handling with no import of its own, pytest plugins (`pytest-asyncio`, `pytest-cov`) are discovered by entry point, and a transitive runtime requirement of a package the code does import (`requests` under `google.auth.transport.requests`, `aiohttp` under slack-sdk's async client) is used through it. **A package whose mechanism you have confirmed in the repo is used — do not report it**, not even at `likely_safe`: `--aggressive --fix` offers every `likely_safe` dependency for removal, so a finding annotated "do NOT remove" is a deletion candidate with a warning attached. Name it on one line under `## Used without import` instead. Report at `likely_safe` only when you suspect a mechanism you could not confirm (the Procfile is absent, the URL scheme is not in the repo).

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

## Used without import
- <package>: <confirmed mechanism, e.g. "Procfile `uvicorn main:app`"> — not a finding, never ranks

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

### 4.2 Lockfile and manifest drift

The lockfile is derived from the manifest, so the two disagreeing is cruft nobody authored:

- **Lockfile entries the manifest no longer lists.** npm: compare `packages[""].dependencies` / `devDependencies` in `package-lock.json` (v2/v3) against `package.json`; yarn: the top-level entries of `yarn.lock` whose descriptor is not in the manifest; pnpm: `importers` in `pnpm-lock.yaml`; Python: `poetry.lock` / `Pipfile.lock` top-level packages against `pyproject.toml` / `Pipfile`. Only compare **direct** entries — transitive packages are supposed to be in the lockfile and absent from the manifest. `Cargo.lock` and `go.sum` prune themselves and are out of scope.
- **Two lockfiles for different package managers side by side** (`package-lock.json` + `yarn.lock` + `pnpm-lock.yaml`, or `poetry.lock` + `Pipfile.lock`). Decide which one the repo uses from the `packageManager` field, `engines`, CI workflow commands or the README, and flag the other. If none of those say, flag the pair as `needs_investigation` — never guess which to delete.
- **`@types/*` whose runtime package is gone from every manifest**, and type stubs (`types-requests`) whose package is gone from the requirements.

A drift finding's `uninstall_command` is the regenerating command (`npm install`, `pnpm install`, `poetry lock --no-update`) or `git rm <stale lockfile>`; the manifest is authoritative. Risk: `safe` for stale entries, `likely_safe` for a duplicate lockfile with a clear owner.

```
## Lockfile Drift
- path: <lockfile>
  type: stale_lock_entry|duplicate_lockfile|orphaned_types
  package: <name, or the second lockfile's name>
  reason: <e.g., "listed in package-lock.json packages[\"\"].dependencies, absent from package.json">
  fix_command: <e.g., npm install>
  risk: safe|likely_safe|needs_investigation
```

## 5. Obsolete Patterns

Scan for patterns that indicate technical debt from past workarounds or migrations:

- **Deprecated API usage**: grep for known deprecated patterns in the project's framework (e.g., `componentWillMount` in React, `datetime.utcnow()` in Python 3.12+)
- **Old workarounds**: comments containing "workaround", "hack", "temporary", "fixme" — especially if they reference specific version numbers or issue URLs that may now be resolved
- **Feature flags**: look for feature flag patterns (`if FEATURE_X`, `isEnabled('feature')`) and check if they're always true/false in all environments. A flag whose value is a **hard-coded literal** (`export const ENABLE_X = true`, `ENABLE_X = False`, `"enableX": true` in a config) that code branches on is a candidate the moment it is written — one branch is dead in every environment. Date it: `git log -1 --format=%cs -S<flag name> -- <file>` gives the last change to its value; more than 6 months old → `type: stale_feature_flag`, `risk: likely_safe` (remove the flag and the dead branch); younger → report, `needs_investigation`; no git history → list it undated and record `stale_feature_flag_age` under `## Unavailable checks`. A flag read from the environment, a remote config service, a database or a request header is **not** a candidate — its value genuinely varies — so never flag `process.env.*`, `import.meta.env.*`, `os.getenv(...)`, LaunchDarkly/Unleash/Statsig/ConfigCat lookups or anything with a default fallback.
- **TODO/FIXME with dates or issue links**: if a TODO references a specific GitHub issue, check if that issue is closed (if git remote is GitHub and `gh` CLI is available). If `gh` is missing or unauthenticated, list the issue-linked TODOs without a resolved/open verdict and record `resolved_todo` under `## Unavailable checks` — an unchecked TODO is not a resolved one.

**Output format:**

```
## Obsolete Patterns
- path: <file_path>
  location: <line_number>
  type: deprecated_api|workaround|feature_flag|stale_feature_flag|resolved_todo
  description: <what the pattern is>
  suggestion: <what to do about it>
  risk: safe|likely_safe|needs_investigation
```

## 6. Configuration Cruft

- **Unused env vars**: read `.env*` files, grep each variable name across source code **and** across `docker-compose*`, `Dockerfile*`, CI workflows, Procfiles and deployment manifests (`${VAR}` substitution there is a use). Flag any not referenced anywhere. Cap at `likely_safe` — never `safe` — when the variable is consumed without its name appearing in the repo: framework-prefixed vars that a bundler injects wholesale (`VITE_*`, `NEXT_PUBLIC_*`, `REACT_APP_*`, `EXPO_PUBLIC_*`), vars a library reads by convention (`DATABASE_URL` for Prisma / `dj-database-url`, `REDIS_URL`, `SENTRY_DSN`, `OPENAI_API_KEY`, `AWS_*`, `GOOGLE_APPLICATION_CREDENTIALS`), and platform vars (`PORT`, `NODE_ENV`, `PYTHONPATH`, `TZ`). Say which convention you suspect. **A variable or settings field the repo itself marks as kept on purpose is not a finding** — an inline or adjacent comment saying so (`# unused in code; kept so .env var isn't rejected`, `# reserved`, `# kept for compat`): the author has already made the decision the finding would ask for, and a finding annotated "not a deletion candidate" is still one under `--aggressive --fix`. Name it on one line under `## Kept deliberately`, quoting the comment.
- **Dead CI stages**: read `.github/workflows/*.yml` or `.gitlab-ci.yml`, look for jobs that are commented out, have `if: false`, or reference deleted scripts/files
- **Orphaned configs**: config files for tools no longer in `devDependencies` (e.g., `.eslintrc` exists but `eslint` is not installed)
- **Docker cleanup**: `Dockerfile` or `docker-compose.yml` referencing images, volumes, or services no longer needed
- **Dead i18n keys**: translation files under `locales/`, `i18n/`, `lang/`, `translations/`, `messages/` (`*.json`, `*.yaml`, `*.ts` message maps). Read only the **default/source** locale (`en`, the one named in the i18n config, or the largest); other locales mirror its key set and a key missing in one of them is a translation gap, not cruft. Flatten nested keys to dotted paths, strip plural/context suffixes (`_one`, `_other`, `_plural`, `_zero`, `_male`), then one batched `Grep` of the literal keys (quoted: `['"\`]key['"\`]`) across source and templates. A key with zero hits → `type: dead_i18n_key`, `risk: safe`. **Dynamic prefixes are the trap**: when code builds a key (`` t(`error.${code}`) ``, `t('status.' + s)`, `t(key)` with `key` from data), every key under that prefix is live — collect the literal prefixes from such calls and exclude their subtrees, saying so in the finding block. A translation file with no `t(`/`$t(`/`i18n.t(`/`gettext(`/`<Trans` call sites anywhere is served to the client wholesale: record the check as unavailable rather than flag every key.
- **Dead config keys**: keys in `config/*.{yaml,yml,json,toml}`, `settings.py`, `appsettings*.json`, `application*.yml` that no code reads. Flatten nested keys; a key is read when its name appears as `cfg["key"]`, `cfg.get("key")`, `config.key`, `settings.KEY`, `getenv`-style lookups, `@Value("${key}")`, `Configuration["Key:Sub"]`, or a dotted path. **Never flag keys the framework itself consumes** — Django `DEBUG`/`ALLOWED_HOSTS`/`INSTALLED_APPS`/`MIDDLEWARE`/`DATABASES`, Spring `server.*`/`spring.*`/`logging.*`, ASP.NET `Logging`/`ConnectionStrings`/`AllowedHosts`, Rails `config.*`, Next.js/Vite config keys — nor keys a schema or a `Settings(BaseSettings)` class binds by name (Pydantic, `environ.Env`, `dynaconf`, `node-config`), where the class fields are the readers. **Before reporting any key, grep its quoted name (`['"]key['"]`) across all source** — one batched alternation for the whole file's keys; any hit outside the config file itself is a reader, and the key is live. When the file is exposed through an accessor (`ConfigLoader.assistant`, `settings.FEATURES`, `CONFIG`), follow that accessor to its call sites and read the `.get("key")` / `["key"]` accesses on it — including through `self.config.<accessor>` and local aliases — before concluding a key is unread; a pass-through you did not trace is not evidence of absence. Report at `likely_safe` only when the traced object leaves the repo or is consumed generically (dumped whole into a template, prompt or response); say which. A key the project's own docs describe as configurable but no code reads is still a finding — name the doc, because the fix may be wiring it in rather than deleting it. **Check the docs for every key you report**, in the same batched alternation, over `*.md`, `docs/**` and `README*` (not the config file itself): a key any doc mentions is capped at `needs_investigation` and the finding names the file and line. Never write "no doc mentions it" without having run that search.

**Output format:**

```
## Configuration Cruft
- path: <file_path>
  type: unused_env_var|dead_ci_stage|orphaned_config|docker_cruft|dead_i18n_key|dead_config_key
  key: <dotted key, for the two key types>
  description: <what it is>
  risk: safe|likely_safe|needs_investigation

## Kept deliberately
- <file:line> <key>: "<the comment that says so>" — not a finding, never ranks

## Unavailable checks
- check: <resolved_todo|stale_feature_flag_age|dead_i18n_keys|lockfile_drift|unused_dependencies|configuration_cruft|vulnerable_dependencies|...>
  reason: <e.g., "gh not installed — 4 issue-linked TODOs listed without a closed/open verdict">
```

The `## Unavailable checks` block is not a list of findings and never ranks: it tells the orchestrator which checks could not be performed here, so the report can say "unavailable" instead of showing a 0 that looks like "clean". Emit `- (none)` when every check ran. §4.5 when `--vulns` was not requested is "not scanned", not unavailable — the orchestrator already renders that; list it here only when `--vulns` was requested and the audit tool was missing or failed. A section the orchestrator told you to skip is **skipped**, not unavailable — omit it; the orchestrator renders that state. A check that ran and had nothing to examine (no issue-linked TODOs to look up, no hard-coded flags to date, no `__all__` so call sites were counted instead) is **clean**, not unavailable — omit it too: never write an entry here whose reason says "clean" or "nothing to check"; the orchestrator reads every entry in this block as a gap in coverage. Unavailable means a precondition or tool the check needs is absent: no lockfile, no locale files, no snapshot mechanism, no git history, `gh` missing.

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
