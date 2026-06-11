---
name: webdesign
description: "Totally re-skins an existing web project's visual design via Google Stitch (driven through the Stitch MCP + Google's stitch-skills), while preserving all functionality. Extracts the current design, applies a new design language, and safely injects it page-by-page with verification."
when_to_use: When the user wants to redesign, re-skin, restyle, or totally change the UI/UX / look-and-feel / design language of an existing web project using Google Stitch. Web projects only (rejects non-web repos). Refactor of an existing project only in v1 — greenfield/new projects exit with a 'not yet supported' note. Distinct from /bx:arch (code structure) and /bx:seo (search). NOT for fixing bugs or behavior.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Glob, Grep, Skill, Agent, WebFetch, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(curl:*), Bash(mkdir:*), Bash(hugo:*), Bash(bundle:*), mcp__stitch__*, mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_wait_for, mcp__plugin_playwright_playwright__browser_close
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

> **Flag precedence:** `--force-setup` is handled in Step A and takes precedence over `status` and `page <name>` — it shows the setup banner and stops regardless of other arguments.

---

## Step A — Setup check

Read `references/setup-stitch-mcp.md`. Run both dependency checks per that file's Detection section (passive — no shell invocation needed). If either is missing (or `--force-setup` was passed), apply that file's banner/sentinel logic and **stop**. Do not proceed to stack detection, state loading, or any phase.

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

> **Note:** the design spec lists 8 conceptual states; this skill persists only **5** distinct `phase` values (`direction_set`, `review_pending`, `tokens_injected`, `injecting_pages`, `done`) — `setup`, `extracted`, and `generating` are transient/in-session and never written to `state.json`. (The initial "no `state.json`" case is not a stored value.)

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
  "port": 3000,
  "app_runnable": true,
  "tokens_applied": false,
  "pages": [
    {
      "slug": "home",
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

`port` (integer, written by `web-stack-detection.md` Pass 4) is the dev-server port used for screenshots and Playwright verification. On a page failure, Phase 3 also adds `pages[].failure_reason` (string) to the failing page entry — it is not present until something fails.

`pages[].states` is an **object keyed by state name** (not an array). Phase 1 initializes it with `screen_id: null, status: "pending"` for each state. Phase 2 fills in `screen_id` and sets `status: "generated"`. Phase 3 sets `status` to `"injected"` → `"verified"` (or `"failed"` / `"manual"`).

Per-page `status` lifecycle: `pending → generated → injected → verified`, terminal: `failed` / `manual`.

Phase 1 sets `slug` from each brief's `page:` frontmatter field (e.g. `page: home` → `slug: "home"`).

### Argument handling

**`status` arg** — If `.webdesign/state.json` does not exist, print `No /bx:webdesign run started in this project yet. Run /bx:webdesign to begin Phase 1.` and stop. Otherwise read `state.json`, print the current phase, the `design_direction` (if set), and a table of all pages with their `status` and per-state `screen_id` / `status`. Stop — take no action.

**`page <name>` arg** — Read `state.json`. Locate the page entry where `slug == <name>` (match by `slug` first, then by `route` if no slug match). If not found, print an error and stop.

Before routing to the Phase-3 per-page loop, apply this guard:

- If `tokens_applied` is `false` OR the page's top-level `status` is `pending` (i.e. it has no `screen_id` yet), print:

  ```
  Cannot inject <name> yet — finish design generation + review (Phase 2) and the tokens step
  (Phase 3) first. Run /bx:webdesign with no arguments to continue the normal flow.
  ```

  and **stop**.

Only proceed to the Phase-3 per-page loop when `tokens_applied == true` AND the page's `status` is one of `generated` / `injected` / `verified` / `failed` / `manual`. (Re-validate the stack cheaply first — see Step C.)

When entering via `page <name>`, **first run `references/phase3-inject.md` Step 1 scoped to this one page** (re-issue `get_screen` for its state(s) and re-download the HTML/screenshot), *then* run Step 3 for this page only — **including Step 3's pre-loop setup, not just the loop body**: start the dev server once if `app_runnable == true` (Step 3 pre-step 2) so verification has a live server, and assert a clean working tree. You may skip the `phase` rewrite to `injecting_pages` if `phase` is already `done`. The Step-1 re-fetch is mandatory: `get_screen`'s signed URLs are short-lived and the prior `.webdesign/tmp/stitch-<page>-<state>.html` download may have expired or been cleaned in a later session, so the restyle loop cannot assume it is still on disk.

---

## Step C — Route by phase

> Always run `references/web-stack-detection.md` before Phase 1 (all four passes). On RESUME (`state.json` already exists, phase is not a first-run state), run ONLY Passes 1 (web gate) and 4 (runnability) from `references/web-stack-detection.md` to refresh `app_runnable`. Do NOT run the full detection and do NOT re-enter `references/phase1-extract.md` — no branch re-creation, no `.gitignore` re-append, no Stitch re-seeding. Phase 1's steps run only on the initial (no-state.json) run.

Read `.webdesign/state.json` if it exists. Route as follows:

### No `state.json` (first run) → Phase 1

Run `references/web-stack-detection.md` (all four passes in a single parallel turn). On pass failure (non-web or greenfield), stop cleanly per that file's exit messages. On success, proceed to `references/phase1-extract.md`.

### `phase = direction_set` → Phase 2

Cheaply re-validate (web gate + `app_runnable`). Read `references/phase2-design-review.md` and execute it from Step 1.

### `phase = review_pending` → Approval check → Phase 3

Cheaply re-validate. Execute `references/phase2-design-review.md` "Resume Behavior": ask for approval; if approved → proceed to `references/phase3-inject.md` Step 1 (there is **no intermediate `approved` phase** written); if changes requested → `edit_screens` → re-present review card → `phase = review_pending` again.

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
