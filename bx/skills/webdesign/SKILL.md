---
name: webdesign
description: "Totally re-skins an existing web project's visual design via Google Stitch (driven through the Stitch MCP + Google's stitch-skills), while preserving all functionality. Extracts the current design, applies a new design language, and safely injects it page-by-page with verification."
when_to_use: When the user wants to redesign, re-skin, restyle, or totally change the UI/UX / look-and-feel / design language of an existing web project using Google Stitch. Web projects only (rejects non-web repos). Refactor of an existing project only in v1 — greenfield/new projects exit with a 'not yet supported' note. Distinct from /bx:arch (code structure) and /bx:seo (search). NOT for fixing bugs or behavior.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Glob, Grep, Skill, Task, WebFetch, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(curl:*), mcp__stitch__*, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_wait_for, mcp__plugin_playwright_playwright__browser_close
effort: high
argument-hint: "[status | page <name>] [--force-setup]"
---

# /bx:webdesign — Stitch-driven Web Design Refactor

Totally re-skin an existing **web** project's visual design language using **Google Stitch**, without breaking any functionality. This skill is a thin orchestrator: it **delegates** the Stitch-side work (design extraction, design system, screen generation) to Google's official `stitch-skills` (via the Stitch MCP), and **owns** the parts Google's kit lacks — web-project detection, preserve-aware page briefs, **safe injection into existing code**, and **verification**.

**Web projects only.** Rejects non-web repos. **Refactor only in v1** — greenfield/new projects get a clean "not yet supported" exit.

**Companion skills:** `/bx:seo` (web audit) · `/bx:plan` (feature planning) · `/bx:save` (end-of-session save).

> ⚠️ Stitch produces **static visuals, no logic.** This skill therefore *restyles existing pages in place* — it never replaces working components, and never delegates behavior to Stitch.

---

## How to run

`/bx:webdesign` is a **single auto-detecting command** — it reads `.webdesign/state.json` and continues from where it left off. No arguments needed on a normal resume.

Two overrides:

- **`/bx:webdesign status`** — Print current phase + per-page status table. Take no action.
- **`/bx:webdesign page <name>`** — Re-run or force a single page. Skip straight to the Phase-3 per-page loop for that page slug (useful for retrying a `failed` page).

One setup override:

- **`/bx:webdesign --force-setup`** — Re-show the Stitch setup banner (see `references/setup-stitch-mcp.md`). If both dependencies are already present, prints a confirmation instead. Always stops after the banner.

---

## Step A — Setup check

Read `references/setup-stitch-mcp.md` and run both checks in parallel (passive — no shell invocation needed):

1. **Stitch MCP present?** Inspect available tools for any name beginning with `stitch` (i.e. `mcp__stitch__*`). If none visible → Stitch MCP not configured.
2. **`stitch-skills` installed?** Confirm `stitch::code-to-design` is among available skills (callable via the Skill tool). If absent → `stitch-skills` not installed.

If either dependency is missing → print the banner from `setup-stitch-mcp.md` (applying its specificity rule and sentinel-dedup logic), write `.webdesign/.setup-shown` if this is the first display, and **stop**. Do not proceed to stack detection, state loading, or any phase.

If `--force-setup` was passed → apply the banner/confirmation logic from `setup-stitch-mcp.md` and **stop** regardless of dependency state.

> **Note:** The exact Stitch MCP tool-name prefix (`mcp__stitch__*`) depends on the server name used in `claude mcp add ... stitch ...`. On first dogfood, confirm the prefix matches the installed MCP registration — if the server was registered under a different name, the pattern above needs updating in `allowed-tools` and in this file.

---

## Step B — Load or initialize state

### State machine

The persisted phase progression (the values `phase` actually takes in `state.json`):

```
(no state.json)    → start Phase 1
direction_set      → start Phase 2
review_pending     → ask "approved?"; on yes → start Phase 3 in-session (no intermediate phase written)
tokens_injected    → resume Phase 3 (token commit done; page loop not yet started)
injecting_pages    → resume Phase 3 per-page loop mid-run
done               → print final report; offer to retry a page
```

There is **no `approved` phase** — Phase 2 transitions directly into Phase 3 in the same turn after approval without writing an intermediate state value. There is **no `setup`, `extracted`, or `generating` phase** — these are not written by any reference file.

### Canonical `state.json` shape

```json
{
  "phase": "direction_set",
  "mode": "refactor",
  "styling_system": "tailwind",
  "branch": "webdesign/2026-06-06",
  "stitch_project_id": "…",
  "design_system_id": "…",
  "design_direction": "…",
  "build_cmd": "npm run build",
  "serve_cmd": "npm run dev",
  "app_runnable": true,
  "tokens_applied": false,
  "pages": [
    {
      "route": "/",
      "file": "src/app/page.tsx",
      "status": "pending",
      "states": {
        "default": { "screen_id": null, "status": "pending" }
      }
    }
  ]
}
```

`pages[].states` is an **object keyed by state name** (not an array). Phase 1 initializes it with `screen_id: null, status: "pending"` for each state. Phase 2 fills in `screen_id` and sets `status: "generated"`. Phase 3 sets `status` to `"injected"` → `"verified"` (or `"failed"` / `"manual"`).

Per-page `status` lifecycle: `pending → generated → injected → verified`, terminal: `failed` / `manual`.

### Argument handling

**`status` arg** — Read `state.json`. Print the current phase and a table of all pages with their `status` and per-state `screen_id` / `status`. Stop — take no action.

**`page <name>` arg** — Read `state.json`. Locate the page entry with `slug == <name>` (or `route` matching `<name>`). If not found, print an error and stop. Otherwise **skip to the Phase-3 per-page loop** and process only that page. (Re-validate the stack cheaply first — see Step C.)

---

## Step C — Route by phase

> Always run `references/web-stack-detection.md` before Phase 1 (all four passes). On resume (`state.json` already exists), cheaply re-validate web-project gate and update `app_runnable` only if a key detection signal has changed — do not re-enumerate routes or re-draft briefs.

Read `.webdesign/state.json` if it exists. Route as follows:

### No `state.json` (first run) → Phase 1

Run `references/web-stack-detection.md` (all four passes in a single parallel turn). On pass failure (non-web or greenfield), stop cleanly per that file's exit messages. On success, proceed to `references/phase1-extract.md`.

### `phase = direction_set` → Phase 2

Cheaply re-validate (web gate + `app_runnable`). Read `references/phase2-design-review.md` and execute it from Step 1.

### `phase = review_pending` → Approval check → Phase 3

Cheaply re-validate. Ask:

```
The designs are generated and waiting for review.
Are they approved, or would you like to request changes?
```

- **Approved** → print `Designs approved. Proceeding to Phase 3 — Inject & Verify.` then execute `references/phase3-inject.md` starting at Step 1. Do **not** write an intermediate `phase = approved` — the phase stays `review_pending` until Phase 3 writes `tokens_injected`.
- **Changes requested** → route through `edit_screens` per Phase 2's Resume Behavior section (`references/phase2-design-review.md`), then re-present the review card and set `phase = review_pending` again.

### `phase = tokens_injected` → Phase 3 (resume, skip token step)

Cheaply re-validate. Execute `references/phase3-inject.md` starting at Step 3 (the per-page loop). The token commit already landed; do not re-apply tokens.

### `phase = injecting_pages` → Phase 3 (resume mid-loop)

Cheaply re-validate. Execute `references/phase3-inject.md` Step 3 per-page loop. Pages with `status = verified` are skipped automatically per that file's resume rule.

### `phase = done` → Final report

Print the final report from `references/phase3-inject.md` Step 4. Then offer:

```
All pages processed. Options:
  • /bx:webdesign page <name>  — retry a failed or manual page
  • /bx:webdesign status       — review the full page table
  • Merge the webdesign/<date> branch when satisfied.
```

---

## Guardrails

- **Web + refactor only.** Non-web repos and greenfield projects exit cleanly with the messages defined in `references/web-stack-detection.md`. No exceptions.
- **Never raw-replace a page.** Every restyle is in-place: logic, handlers, content, and assets from the existing source are preserved. Stitch placeholder text and stock images are discarded. See `references/phase3-inject.md` preservation rules.
- **Never delegate behavior to Stitch.** Stitch produces static visuals only. No event handlers, API calls, routes, or state variables are sourced from Stitch output.
- **Never auto-inject unreviewed designs.** Phase 2 always ends with `phase = review_pending` and stops. Phase 3 starts only after the user explicitly approves in the next invocation (or same-session continuation after the approval prompt in Step C above).
- **All commits on the `webdesign/<date>` branch.** No commits to `main` or any other branch. The branch is created by Phase 1 Step 1.2 and recorded in `state.json["branch"]`; all subsequent phases check it out before writing.
- **On any Stitch / MCP error, surface it and stop.** Never silently continue past a failed `get_screen`, `generate_screen_from_text`, or `edit_screens` call. Print the error response and instruct the user to re-run once the issue is resolved.
