# Fixture Ground Truth

Planted cleanup targets and traps for the `/bx:clean` regression suite. Each fixture
exercises both **recall** (does the audit find what's dead?) and **precision** (does it
spare what only *looks* dead?). The traps are the point — they're where naive
source-only scanning produces dangerous false positives.

Fixtures here ship **without comments that telegraph the answer** — real dead code
doesn't announce itself. To run them, copy a fixture to a scratch dir and `git init`
it (the skill prefers `git ls-files`; it falls back to `find` without a repo).

---

## Fixture 1 — `node-react-app` (TypeScript / React / Vite)

### Should be flagged (true positives)
| # | Item | Category |
|---|------|----------|
| 1 | `lodash` in package.json | unused dependency |
| 2 | `dayjs` in package.json | unused dependency |
| 3 | `src/utils/oldHelpers.ts` | unused file (never imported) |
| 4 | `unusedCalc()` in `src/math.ts` | dead code (non-exported, never called) |
| 5 | `useEffect` import in `src/components/Button.tsx` | unused import |
| 6 | `src/legacy.ts.bak` | backup file (quick win) |
| 7 | commented `formatDateLegacy` block in `src/utils/format.ts` | commented-out code |
| 8 | `.legacy-banner`, `.old-tooltip` in `src/styles.css` | unused CSS classes |
| 9 | `--unused-color` in `src/styles.css` | unused CSS variable |
| 10 | `src/components/OldModal.test.tsx` | orphaned test (OldModal.tsx absent) |

### Must NOT be flagged (traps)
- **`autoprefixer`** — a devDependency referenced **only in `postcss.config.js`**, never in
  source. A source-only scan false-positives here; the skill checks config files.
- **`src/plugins/analytics.ts`** — never statically imported; loaded via a **dynamic import**
  `` await import(`./plugins/${PLUGIN}`) `` with `PLUGIN = 'analytics'` in `App.tsx`. A naive
  "unused files" pass flags it; correct behavior is keep (or at most needs-investigation).
- `react`, `react-dom` (JSX + hooks), `axios`, `clsx` — used
- `src/utils/format.ts`, `src/math.ts` — `formatDate` / `add` are used
- `.btn`, `.card`, `.btn-hover`, `--primary` — used
- `vite.config.ts`, `tsconfig.json`, `.eslintrc.json`, `postcss.config.js`, `index.html`, `src/main.tsx` — config/entry
- `@types/react`, `@types/react-dom`, `vite`, `vitest`, `eslint`, `typescript` — toolchain
- `src/components/Button.test.tsx` — valid test

---

## Fixture 2 — `python-api` (Python / FastAPI)

### Should be flagged (true positives)
| # | Item | Category |
|---|------|----------|
| 1 | `requests` | unused dependency |
| 2 | `beautifulsoup4` | unused dependency |
| 3 | `redis` | unused dependency |
| 4 | `app/legacy_handlers.py` | unused file (never imported) |
| 5 | `deprecated_formatter()` in `app/utils.py` | dead code |
| 6 | `datetime.utcnow()` in `app/utils.py` | deprecated/obsolete API (no inline hint) |
| 7 | `LEGACY_TOKEN` in `.env` | unused env var |

### Must NOT be flagged (traps — package name ≠ import name)
- `Pillow` → `from PIL import Image`
- `python-dateutil` → `from dateutil import parser`
- `PyYAML` → `import yaml`
- **`pycryptodome` → `from Crypto.Cipher import AES`** (the obscure one — via `app/crypto.py`)
- `fastapi`, `uvicorn` — used (routes + run entrypoint)
- `DATABASE_URL`, `SECRET_KEY` — used via `os.getenv` / `os.environ`
- `app/main.py`, `app/images.py`, `app/utils.py`, `app/crypto.py`, `app/__init__.py`

> Note: `app/images.py::load_image` is itself dead (uncalled), and `Pillow` is only reachable
> through it — a correct audit may flag `load_image` as dead code while still keeping `Pillow`
> as "imported in a reachable module," noting the coupling. That nuance is acceptable, not a
> failure of the name-mismatch trap.

---

## Fix-Mode discipline (eval 2, `--fix` on `node-react-app`)

Correct `--fix` behavior:
- Creates a `cleanup/<date>` branch; never mutates `main`
- Auto-applies **quick wins only**: delete `legacy.ts.bak`, remove `useEffect` import,
  remove the commented `formatDateLegacy` block
- **Defers** Safe-to-Delete (`oldHelpers.ts`, the orphan test) for confirmation
- **Does not** auto-remove dependencies (`lodash`/`dayjs` are report-only)
- **Does not** delete the dynamically-imported `analytics.ts`
- Preserves all used code
