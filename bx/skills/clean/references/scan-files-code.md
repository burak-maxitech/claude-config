# Files & Dead Code Scanner

You are a subagent scanning for unused files and dead code. Be thorough but conservative — false positives waste the user's time, false negatives are acceptable since this is an audit, not an auto-delete.

## Input

Your task prompt gives you the project stack (language, framework, file extensions), the **scope** (a directory, or the repo root), and the **excluded paths** the orchestrator computed from `scan-exclusions.md`. Use the stack to focus your search. Report only items inside the scope, but search for *references* across the whole repo — a file inside `src/payments/` that is imported from `src/billing/` is used. Never report a finding inside an excluded path, and never widen the scope on your own: if something outside it looks relevant, say so in a note. **References from an excluded path still count** — a fixture-named tree can hold real support code (`e2e/fixtures/personas.ts` is Playwright setup, `__fixtures__/` holds the inputs a real test reads), so a `src/` module imported only from there is used. Include excluded trees in the reference search; exclude them only from the candidate list. **A reference to a code symbol is a use in code**: source, tests, scripts, templates and config files. A mention in markdown or other prose (`CLAUDE.md`, `docs/**`, changelogs, session logs) is not a use: a project that logs its sessions names dead functions in the log long after the last caller is gone. Search code files only for function, export and type references, and name any doc mention in the finding's `reason` so the reader can update the doc too. Assets are different: a doc that embeds an image does use it (the orphaned-assets method says so).

## 1. Unused Files

Scan for files that are never imported, required, or referenced anywhere else in the codebase.

**Method:**
- List source files with `git ls-files` (honors `.gitignore` automatically — no need to maintain a hardcoded skip list — and is much faster than `find` on large repos). Fall back to `find` only if the project isn't a git repo, and then apply the excluded paths by hand.
- **Batch the reference search.** Do not loop one-grep-per-file. With hundreds of files that's hundreds of Grep calls. Make a single `Grep` call with a regex alternating across all candidate basenames, e.g. pattern `\b(userProfile|authMiddleware|dateUtils|...)\b` with `output_mode: count` so each file's match count comes back in one shot. Then bucket: any basename with zero hits across all files (excluding self-matches in the basename's own file) is a "potentially unused" candidate. For ~50–100 candidates per call, this collapses 50–100 Grep runs into one.
- A file is "unused" if zero other files reference it AND it's not an entry point (like `index.*`, `main.*`, `app.*`, `server.*`, `manage.py`, `setup.py`, `__init__.py`)
- A basename that appears only inside a string or template literal (`import(\`./plugins/${name}\`)`, `require(path.join(dir, file))`, a route table, a plugin registry) is loaded dynamically: cap it at `likely_safe` and say what pattern you saw. Deleting a dynamically-loaded module breaks the app at runtime, where no grep would have warned.

**Also flag:**
- Files with backup/old suffixes: `.old`, `.bak`, `.backup`, `_v2`, `_old`, `_backup`, `.orig`, `Copy of *`
- Empty files (0 bytes or only whitespace/comments)
- One-time scripts: files in `scripts/` or `tools/` that look like one-offs. Batch-check with two commands: `git log --format="%ad" --date=short --name-only --diff-filter=A -- scripts/ tools/` gives every file its creation date, and `git log --format= --name-only -- scripts/ tools/ | sort | uniq -c` gives the number of commits touching each; a file with one commit, more than 6 months old, is a candidate (`likely_safe` at most — a script that runs from CI or a cron job has no in-repo caller). Avoid running `git log` per-file — it's too slow on large repos.
- **Never treat migrations as one-off scripts.** `migrations/`, `alembic/versions/`, `db/migrate/`, `prisma/migrations/`, `supabase/migrations/`, Flyway/Liquibase changelogs and similar are the database's permanent history: every applied migration is a single old commit by design, and deleting one breaks fresh setups and rollbacks. Exclude these directories from this heuristic entirely; do not list them even as `needs_investigation`.
- Duplicate files: same content, different names (compare with `md5sum` on a sample)

**Method — Orphaned assets:**
- Enumerate binary and static assets with `git ls-files` filtered to `public/`, `assets/`, `static/`, `media/`, `img/`, `images/`, `fonts/` and to the extensions `png jpg jpeg gif svg webp avif ico woff woff2 ttf otf eot mp3 mp4 webm pdf` anywhere outside the excluded paths.
- **Batch the reference search by basename** (with and without extension) across source, templates, stylesheets (`url(...)`), HTML (`href`, `src`, `srcset`, `<link rel="icon">`, `og:image` metas), manifests (`site.webmanifest`, `manifest.json`, `browserconfig.xml`), markdown and config. An asset referenced only from CSS or only from `index.html` is used; a source-only grep false-positives on both.
- Zero hits → `type: orphaned_asset`, `risk: safe`. These are often the largest files in a repo, so report their size in `lines:` as `<n> KB` instead of a line count.
- **Cap at `likely_safe` and say why** when the directory is consumed wholesale: `import.meta.glob('./assets/*')`, `require.context(...)`, `fs.readdir`, a static-site generator or framework that serves the whole folder, or a CMS that references files by name at runtime. Never flag framework-convention files that are loaded without any reference: `favicon.ico`, `robots.txt`, `sitemap.xml`, `_redirects`, `_headers`, `apple-touch-icon*.png`, `.nojekyll`, `CNAME`.
- A fingerprinted name (`logo.3f2a9c.png`) is build output, not a source asset — it belongs to the excluded generated trees, not here.

**Method — Trivial directories:**
- A directory whose only contents are a `.gitkeep`/`.keep`, an empty `__init__.py`, or an `index.*` that exports nothing (`export {}` or no `export` at all) and that no file imports → `type: trivial_directory`, `risk: safe`. Report the directory path; `--fix` treats it as one item.
- Do NOT flag: a `.gitkeep` directory a config names as a target (`uploads/`, `logs/`, `tmp/`, a Docker volume mount, a CI artifact path) — the directory is the deliverable; a Python package directory whose empty `__init__.py` has subpackages or modules beneath it (that is a namespace, not cruft); a directory the dynamic-import scan above identified as a plugin folder.

**Do NOT flag:**
- Config files (`.env*`, `*.config.*`, `tsconfig.json`, `jest.config.*`, etc.)
- Entry points and framework-required files
- Files referenced in config files (webpack, vite, etc.)
- Type declaration files (`.d.ts`) unless truly orphaned

## 2. Dead Code

Scan for code that exists but is never executed.

**Method — Functions/Methods:**
- Extract all function/method definitions using grep patterns appropriate for the project language
- **Batch the call-site search.** Make a single `Grep` call alternating across all extracted function names: pattern `\b(funcA|funcB|funcC|...)\b` with `output_mode: count`. Bucket matches by name; any name whose only match is its own definition line is a "dead" candidate.
- A function is "dead" if it has zero call sites AND is not exported from a public API
- **Test-only references.** A file, function or export whose only references are test files is never `safe` or `likely_safe`: it is `needs_investigation` with `reason:` starting `test-only —`. It is either dead production code that still has a test, or a pure helper kept for the tests, and only the author knows which. Test-support files (`*-test-mocks.*`, `*.fixture.*`, `testing/`) imported by tests are used, not test-only

**Method — Unused exports:**
- Extract every exported symbol: TS/JS `export (async )?(function|const|let|class|enum)\s+(\w+)`, `export \{ a, b \}`, `module.exports.x =`, `exports.x =`; Python names listed in `__all__`. Then **one batched `Grep`** alternating the names across every other file (`output_mode: count`, exclude the defining file). A name with zero hits outside its own file is a candidate — the dead-function rule (no call site AND not exported) lets every `export` escape, and unused exports are the largest dead-code class in TypeScript and Python codebases. **Then split the candidates by their use inside the defining file**: a name with no reference besides its own definition is `type: unused_export` (the symbol is dead and goes); a name used locally (called, passed, used in a signature — **in code, not in a comment or string**: a defining file's doc comment that says "why this exists separately from `foo`" does not keep `foo` alive, so strip comments before counting local uses) is **`type: export_only`**. Decide it per name with this exact command, not by a raw match count: `git grep -nw <name> -- <file> | grep -vE "^[^:]*:[0-9]+:[[:space:]]*(//|/?\*)" | grep -vE "^[^:]*:[0-9]+:[[:space:]]*export (default )?(declare )?(async )?(function\*?|const|let|var|class|interface|type|enum|abstract class) <name>\b"` — it drops comment lines and **only the definition line itself**. Never drop every line that starts with `export`: a type used only in another export's signature (`export function radarModel(): RadarPoint[]`) sits on such a line, and dropping it calls a live type dead (S64: one run reported ~48 live types as `unused_type`, `risk: safe`); **one or more remaining lines → `export_only`, zero → `unused_export`**. For more than 50 candidates, run it in a loop over the names in one Bash call and print only the names with zero lines — the symbol is live and only the `export` keyword is unneeded. An `export_only` item is never a deletion: removing the symbol breaks its own file. Report those only in the `## De-export candidates` block below, never under `## Dead Code`, and give them no `risk` or `quick_win`.
- Follow one barrel hop: if the only importer is an `index.*` that re-exports the name, grep for the name again from that barrel's importers; a name that dies at the barrel is still unused.
- `type: unused_export`, `risk: safe` for an application (no `main`/`exports`/`types` field in `package.json`, no `pyproject` `[project]` with a package name consumed elsewhere); `risk: likely_safe` for anything publishable, where the consumer is outside the repo by design.
- **Never flag framework-convention exports**, which the framework imports with no greppable reference: route/page `default` exports and `metadata`, `getServerSideProps`, `getStaticProps`, `generateMetadata`, `loader`, `action`, `handle`, `config`, `middleware` (Next.js/Remix/SvelteKit/Nuxt/Astro), Storybook `default`/`Primary`-style story exports, Vite/Vitest/Jest/ESLint/Tailwind config `default`s, test files, `register`/`activate`/`deactivate` in plugins, the unused parts of a generated UI kit's components (`components/ui/*` when a shadcn `components.json` exists — the kit is regenerated by `shadcn add` and trimmed exports conflict with it; name them in one note line instead), Django `urlpatterns`/`app_name`, FastAPI/Flask `app`, Celery `celery_app`, `__version__`. Fields of a settings class bound to the environment (`Settings(BaseSettings)`, `environ.Env`, dataclass configs loaded from `.env`) are not exports either: an unread field is an unused env var, owned by the dependencies & config scanner (§6) — do not report it here, or the same key arrives twice under two types. When the repo's own convention is unclear, cap at `likely_safe` and name the framework you suspect.

**Measure every Dead Code finding's extent.** `location:` is `<start>-<end>` and `lines:` is the count, both taken from the file, not estimated: read from the definition line to its end (the matching closing brace or `)`; for Python, the last line before the next statement at the definition's indentation), including the symbol's leading doc comment. `--dry-run` builds its impact table from `lines:`, so `unknown` or `?` leaves a hole in it. A grouped finding (several names on one line) gives the summed count.

**Method — Unused type definitions:**
- Extract `interface X`, `type X =`, `enum X`, `declare` names in `.d.ts`, Python `class X(TypedDict|Protocol|BaseModel|Enum)` and `@dataclass` classes. One batched `Grep` for the names across all files; a type whose only match is its own definition (and, for exports, no importer) is `type: unused_type`, `risk: safe`. An exported type used in its own file's signatures is `export_only` (above), not `unused_type`.
- Do NOT flag: ambient and global augmentations (`declare global`, `declare module 'x'`, `interface Window`, `ProcessEnv`) — they are consumed by the compiler, not by an import; types referenced only in JSDoc `@type {X}` / `@param {X}` in JS files (grep the JSDoc form too); Pydantic/SQLAlchemy/Django models registered by import or metaclass; `enum` members read by string (`Status[value]`).

**Method — Commented-out code:**
- Find blocks of 5 or more consecutive commented lines that look like code (contain `=`, `{`, `(`, `function`, `class`, `def`, `import`, `return`)
- Report the file, line range, and a short preview

**Method — Unreachable code:**
- Look for code after unconditional `return`, `throw`, `exit`, `break`, `continue` statements
- Look for branches that are always false (e.g., `if (false)`, `if 0:`, `#if 0`)

**Method — Unused imports:**
- **TypeScript:** when `typescript` is installed (`node_modules/.bin/tsc` exists), you may run `npx tsc --noEmit --incremental false --noUnusedLocals -p <tsconfig>` and read only the TS6133/TS6192/TS6196 diagnostics. `--incremental false` is mandatory: with `incremental: true` in the tsconfig, `--noEmit` alone still rewrites `tsconfig.tsbuildinfo`, and this scan writes nothing (S64: a bare `--noEmit` run rewrote it in a repo another session was working in). Ignore every other diagnostic; type errors are not this scan's business. No other compiler, linter, package script or interpreter (`node`, `python`, `tsx`) may be run, and **nothing may be written inside the repo**. Scratch files (word lists, intermediate results) go only in the OS temp directory and are deleted before you return; helper scripts are never written, since no interpreter may run them. Prefer piping intermediate lists between commands in one Bash call (`git ls-files | grep ... | while read f; do ...; done`). Everything you produce goes in your reply; a long list is capped as the output format says, not saved to a file a later session cannot see — the agent's `tools:` list is not enforced, so this sentence is the boundary.
- Otherwise, for each import/require statement, check if the imported name is used anywhere in that file
- This is a Quick Win category — high confidence, safe to auto-remove — **but only when the import binds a name that is never used.** "No reference in this file" is not "unused" for these forms, which `--fix` would otherwise delete and break something that no grep can see; tag them `quick_win: false` and `risk: needs_investigation`, or do not report them at all:
  - **Side-effect imports** — `import './polyfills'`, `import 'reflect-metadata'`, `require('dotenv/config')`, a bare Python `import app.signals` that registers handlers on import. They bind nothing by design.
  - **Re-export and barrel files** — `index.ts` / `index.js` that `export { x } from`, Python `__init__.py` that imports names so callers can `from pkg import x`, Go `_ "embed"`-style blank imports. The "unused" name is the file's public surface.
  - **Suppressed lines** — an import carrying `# noqa`, `# type: ignore`, `// eslint-disable-line`, `// @ts-ignore` or `#[allow(unused_imports)]` was kept on purpose by someone who saw the warning.
  - **Type-only and macro imports** used by a type position, a decorator, JSX pragma or a template (`React` in a JSX file on the classic runtime, `h` for Preact) — check the usage form the language actually needs.

**Output format (return as structured text):**

```
## Unused Files
- path: <file_path or directory path>
  type: unused_source|backup|empty|one_time_script|duplicate|orphaned_asset|trivial_directory
  reason: <why it's unused>
  lines: <line count, or "<n> KB" for an asset>
  risk: safe|likely_safe|needs_investigation
  quick_win: true|false

## Dead Code
- path: <file_path>
  location: <start_line>-<end_line>
  type: function|unused_export|unused_type|commented_block|unreachable|unused_import
  name: <function name or description>
  reason: <why it appears dead>
  lines: <removable line count — measured, never "unknown">
  risk: safe|likely_safe|needs_investigation
  quick_win: true|false

## De-export candidates
- <file_path>: <name>, <name>, … (<n> symbols)   ← one line per file, at most 50 lines; then "+<n> more in <m> files"
Count: <total symbols> across <files> files. Not findings: the symbols are live; dropping `export` is a lint tidy-up, never a `--fix` action.

## Unavailable checks
- check: <one_time_scripts|duplicate_files|orphaned_assets|unused_exports|...>
  reason: <e.g., "not a git repository — no creation dates or touch counts; listed scripts/ files without the age filter">
```

**`quick_win` is a closed set, not a confidence level.** Tag `quick_win: true` only for the four classes `--fix` may remove without asking: an empty file, a file with a backup/old suffix, a commented-out block of 5 or more lines, and an unused import that passes the carve-outs above. Everything else — a whole unused module, a dead function, an orphaned test — is `quick_win: false` however certain you are; `risk: safe` already says it is certain. The orchestrator auto-applies what you tag, so a loose tag deletes a file the user never agreed to. A `quick_win: true` finding is always `risk: safe`: if you would rate it `likely_safe` ("verify there is no `pytest.` use"), do the verification and either rate it `safe` or tag it `false`.

The `## Unavailable checks` block is not a list of findings and never ranks: it tells the orchestrator which checks could not be performed here, so the report can say "unavailable" instead of showing a 0 that looks like "clean". Emit `- (none)` when every check ran. An opt-in section the orchestrator did not request is "not scanned", not unavailable; a category whose precondition is absent (no `scripts/` directory, no git history) is unavailable, and say which precondition. A section the orchestrator told you to skip is **skipped**, not unavailable — omit it; the orchestrator renders that state. A check that ran and had nothing to examine (no issue-linked TODOs to look up, no hard-coded flags to date, no `__all__` so call sites were counted instead) is **clean**, not unavailable — omit it too: never write an entry here whose reason says "clean" or "nothing to check"; the orchestrator reads every entry in this block as a gap in coverage. Unavailable means a precondition or tool the check needs is absent: no lockfile, no locale files, no snapshot mechanism, no git history, `gh` missing.

Limit to top 50 findings per category. If there are more, note the count and say "showing top 50 by confidence."
