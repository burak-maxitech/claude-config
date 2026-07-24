# Per-Page Verification Procedure

**Scope:** this file is the authoritative spec for Phase 3, Step 3c. `phase3-inject.md` carries a short summary that points here — the rules below govern.

**Core principle:** this is a DESIGN change. Pixel-identical regression is the wrong bar. The bar is **functionality preserved**. The brief's "Functionality to PRESERVE" list (`.webdesign/briefs/<page>.md`) IS the assertion set — every bullet maps 1-to-1 to a concrete check.

---

## Inputs

| Input | Source |
|-------|--------|
| `app_runnable` | `state.json` (set by Phase 1 stack detection) |
| `build_cmd` | `state.json` (may be `null`) |
| Page route | `pages[].route` in `state.json` |
| Verification contract | `.webdesign/briefs/<page>.md` — **"Functionality to PRESERVE"** section |
| Before screenshot | `.webdesign/before/<page>.png` (captured in Phase 1) |

---

## Step 1 — Static Checks (always run)

Run ALL of the following checks that exist, **in this order**. Detect availability from the project's `package.json` `scripts` block.

### 1a — Typecheck

Detection: `package.json` has a `typecheck` script, OR the project has a `tsconfig.json` (TypeScript project without a dedicated script).

Run, in priority order (first match wins):
```bash
npm run typecheck          # if "typecheck" script exists in package.json
npx tsc --noEmit           # fallback for TypeScript projects without the script
```

Skip (not a failure) if neither condition is met (non-TypeScript project).

### 1b — Build

Run `build_cmd` from `state.json` if non-null:
```bash
<build_cmd>                # e.g. "npm run build" or "next build"
```

Skip if `build_cmd` is `null`.

### 1c — Tests

Detection: `package.json` has a `test` script AND the script is not the placeholder (`"echo \"Error: no test specified\" && exit 1"`).

Run, in priority order (first match wins):
```bash
npm test                   # if "test" script exists and is non-placeholder
npm run test:unit          # fallback if "test:unit" exists
npx vitest run             # fallback for Vitest projects without a script
npx jest --passWithNoTests # fallback for Jest projects without a script
```

### 1d — Failure rule

**Any static check failure → verification fails for this page.** Do not proceed to Step 2. Record the failure output in `pages[].failure_reason` and go to phase3-inject.md Step 3e.

---

## Step 2 — Playwright Behavior Check (`app_runnable == true` only)

Skip this step entirely if `app_runnable` is `false`. When `app_runnable == false`, BOTH Step 2 (Playwright behavior check) and Step 3 (screenshot capture) are skipped entirely — proceed directly to Step 4. Green static checks (Step 1) alone constitute green ("build-only") verification in that case.

### 2a — Connect to the running dev server

The dev server is started **once** by Phase 3 before the per-page loop (see `phase3-inject.md`). Verification assumes it is already running. Read the port from `state.json["port"]`.

If the server is not yet responding (e.g. verification is being run standalone), poll:
```bash
curl -sf --retry 30 --retry-delay 1 --retry-connrefused "http://localhost:<port>/" >/dev/null
```

If `serve_cmd` is ever needed (e.g. running verification outside the normal Phase 3 flow), use `state.json["serve_cmd"]` — never guess `npm run dev` or `npm start` directly. `serve_cmd` is resolved by Pass 4 of `web-stack-detection.md` and includes Hugo, Jekyll, and other non-Node frameworks.

### 2b — Navigate to the page

Use the Playwright MCP tool:
```
mcp__plugin_playwright_playwright__browser_navigate(url = "http://localhost:<port><pages[].route>")
```

### 2c — Map each PRESERVE bullet to a concrete assertion

Read the **"Functionality to PRESERVE"** list from `.webdesign/briefs/<page>.md`. Each bullet becomes one or more assertions using the Playwright MCP tools below. Apply the mapping rules:

| PRESERVE bullet pattern | Playwright assertion |
|-------------------------|---------------------|
| Element must render | `browser_snapshot()` — confirm element text/role appears in the accessibility tree |
| Button/link click → expected DOM change | `browser_click(element = <selector>)` then `browser_snapshot()` — confirm expected change |
| Form submit → API call / success signal | `browser_fill_form(...)` then `browser_click(submit)` then `browser_snapshot()` — confirm success indicator (toast, redirect, message) is present |
| Filter / toggle → results update | `browser_click(element = <control>)` then `browser_snapshot()` — confirm results list changed |
| Route link → navigation | `browser_click(element = <link>)` then confirm URL changed via snapshot or `browser_navigate` |
| Client-side state (modal, drawer, tab) | `browser_click(element = <trigger>)` then `browser_snapshot()` — confirm expected state element visible |

**Worked example:**

Brief PRESERVE bullets for a Contact page:
```
- Submit button POSTs /api/contact and shows success toast
- Name, email, and message fields are required (inline validation fires on blur)
- "Back to home" link navigates to /
```

Assertions:
1. `browser_snapshot()` — confirm `<form>`, name/email/message inputs, and submit button are present in the tree.
2. `browser_fill_form(fields = {name: "Test User", email: "test@example.com", message: "Hello"})` → `browser_click(element = "submit button")` → `browser_snapshot()` — confirm a success toast or confirmation message appears.
3. `browser_click(element = "name input")` then `browser_click(element = "email input")` (blur name) → `browser_snapshot()` — confirm a validation error for name appears.
4. `browser_click(element = "Back to home link")` → confirm navigation to `/` (snapshot shows home-page content or URL changed).

### 2d — Console error check

After all PRESERVE assertions:
```
mcp__plugin_playwright_playwright__browser_console_messages()
```

Filter for `type == "error"`. Any uncaught console error → verification fails. Ignore warnings (`type == "warning"`). Record error text in `pages[].failure_reason`.

### 2e — Assertion failure rule

If any PRESERVE assertion fails (element absent, expected DOM change did not occur, form submit did not produce success signal, console error present) → verification fails for this page. Go to phase3-inject.md Step 3e.

---

## Step 3 — Before/After Capture (`app_runnable == true` only)

After all PRESERVE assertions pass (Step 2):

```
mcp__plugin_playwright_playwright__browser_take_screenshot(filename = "<page>-post-inject.png")
mv .playwright-mcp/<page>-post-inject.png .webdesign/after/
```

> Same Playwright-output convention as Phase 1 (see `phase1-extract.md` Step 3.2): the MCP writes under `.playwright-mcp/` regardless of the name you pass, so capture with a bare filename and `mv` it into `.webdesign/after/`.

Surface paths to the human for visual confirmation:
```
Before: .webdesign/before/<page>.png
After:  .webdesign/after/<page>-post-inject.png
```

**This is NOT a pass/fail gate.** Visuals are expected to change — that is the entire point of the restyle. The screenshots are for the human's eyes only; no pixel-diff comparison is performed.

---

## Step 4 — Graceful Degradation (`app_runnable == false`)

When `app_runnable` is `false`, Step 2 (Playwright behavior check) and Step 3 (before/after capture) are skipped entirely. The verification gate is **build-only**: green static checks (Step 1) = green verification.

In the page's commit message and in the Phase 3 final report, add the note:
```
⚠ Runtime behavior not auto-verified (app_runnable: false). Functionality preserved
  per static analysis only. Manual review against .webdesign/briefs/<page>.md recommended.
```

---

## Step 5 — Result Contract

Verification returns **green** if and only if ALL applicable checks pass:

| Condition | `app_runnable == true` | `app_runnable == false` |
|-----------|----------------------|------------------------|
| Typecheck | must pass (if applicable) | must pass (if applicable) |
| Build | must pass (if non-null) | must pass (if non-null) |
| Tests | must pass (if non-placeholder) | must pass (if non-placeholder) |
| Playwright PRESERVE assertions | must ALL pass | N/A — skipped |
| Console errors | none allowed | N/A — skipped |

**Phase 3 commits only on green.** A single failing check → this page goes to Step 3e (rollback, `status = failed`). The run continues to the next page.

---

## Quick Reference: Playwright MCP Tools Used

| Tool | Purpose |
|------|---------|
| `mcp__plugin_playwright_playwright__browser_navigate` | Load the page route |
| `mcp__plugin_playwright_playwright__browser_snapshot` | Assert element presence / DOM state |
| `mcp__plugin_playwright_playwright__browser_click` | Trigger interactions |
| `mcp__plugin_playwright_playwright__browser_fill_form` | Fill and submit forms |
| `mcp__plugin_playwright_playwright__browser_console_messages` | Check for uncaught errors |
| `mcp__plugin_playwright_playwright__browser_take_screenshot` | Capture the after/ artefact |
