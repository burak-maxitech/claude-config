# Phase 2 — Design & Review

**Goal:** generate Stitch screens from the Phase-1 briefs, then stop for mandatory human review before any code is touched. On completion, `state.json` carries `pages[].status = generated` + `phase = review_pending`.

There are **three phases only**: Phase 1 (Extract & Stage), Phase 2 (this file), Phase 3 (Inject & Verify). Never reference a Phase 4 or Phase 5.

**Inputs from `state.json` (written by Phase 1):**
- `design_system_id` — applied to every `generate_screen_from_text` call so colors/fonts come from the project design system, not from the prompt.
- `stitch_project_id` — the Stitch project where screens are created.
- `pages[]` — one entry per page (slug, route, brief path, states object). Phase 2 fills in `screen_id` + per-state `status`. Page-level `pages[].status` is what Phase 3's per-page loop checks; `pages[].states.<name>.screen_id` is what Phase 3 passes to `get_screen`.

---

## Step 1 — Quota Pre-Flight

Before calling `generate_screen_from_text` even once, compute the estimated screen count and ask for confirmation.

### 1.1 — Count screens

Compute the screen count from `pages[]` in `state.json` (already in context from SKILL.md Step B — no file reads needed):

```
estimated_screens = Σ len(pages[i].states) for each page entry
```

`pages[i].states` is an object keyed by state name; `len` = number of keys. A page with only `default` counts as 1.

**Examples:**
- 4 pages × 1 state each = 4 screens
- 2 static pages + 1 dynamic page with `{empty, loading, loaded, error}` = 6 screens

### 1.2 — Show the pre-flight prompt and wait

Print the following and **wait for explicit user confirmation before generating anything**:

```
## Stitch quota pre-flight

Briefs on file: <N pages>
Estimated screens: <estimated_screens>   (Σ states per page)
Free-tier budget: ~350 screens/month

⚠ Dynamic pages multiply the count — each state in a brief's `states:` list is
  one screen. Review the states lists in .webdesign/briefs/ before confirming.

Proceed with generation? [yes / no / edit briefs first]
```

- **"yes"** — continue to Step 2.
- **"no"** — stop cleanly; remind the user they can trim states in the briefs, then re-run.
- **"edit briefs first"** — pause; proceed only when the user says to continue.
- **Explicit user override** (the user says to skip the pre-flight, e.g. "skip the quota check"): skip this step and proceed directly to Step 2. There is no dedicated flag for this — it is a natural-language override only; do not invent or advertise one.

---

## Step 2 — Generate Screens Per Brief

**Guard — `design_system_id` must be set before generating.** At the start of Step 2, read `state.json["design_system_id"]`. If it is absent or null, print:
```
No design system found — Phase 1 Step 5 must set the design direction before generating. Re-run /bx:webdesign to finish Phase 1.
```
Then STOP. Do not call `generate_screen_from_text` with a null design system.

**Guard — `stitch_project_id` must be set before generating.** Also read `state.json["stitch_project_id"]`. If it is absent or null, this almost always means Phase 1 took the source-only fallback (app not runnable) and no project was established yet. **Offer recovery before stopping** — do not dead-end:

```
No Stitch project is recorded yet (Phase 1 likely ran the source-only fallback because the
app wasn't runnable). To generate screens I need a project. Create one in the Stitch web
canvas (https://stitch.withgoogle.com) seeded from the DESIGN.md Phase 1 wrote, then paste
its project ID here — or type "skip" to stop.
```

- **If the user pastes a project ID:** write `{ "stitch_project_id": "<id>" }` to `state.json` (merge) and to `.webdesign/SITE.md`, then continue to Step 2.1. This is the closure for the `app_runnable:false` path — without it the skill would dead-end here forever.
- **If the user types "skip" (or the runnable app simply needs a re-run):** print `Stopping — re-run /bx:webdesign once the app builds/serves, or once you've supplied a project ID.` and STOP.

Never call `generate_screen_from_text` with a null project id.

Iterate over every page brief. For each page, generate one screen per state.

### 2.1 — Build the generation prompt

For each `(page, state)` pair, construct a prompt from the brief using the **layout/content-only format** from `stitch-formats.md § Per-screen generation prompt format`. Populate the PAGE STRUCTURE sections from the brief's fields (Header → nav/branding, Hero → headline/subtext/CTA, Content → Key components, Footer → links/legal), per the format defined there.

> Layout/content/structure ONLY — never colors, fonts, roundness, or hex codes. See `stitch-formats.md § Per-screen generation prompt format`.

For dynamic pages (brief has multiple `states:`), generate each state as a separate screen. Adjust the one-line purpose to name the state: e.g. `"Blog listing — loading state, skeleton placeholders"`.

### 2.2 — Invoke `stitch::generate-design`

For each `(page, state)` pair call `stitch::generate-design` via the Skill tool, which internally calls `generate_screen_from_text`:

```
Skill("stitch::generate-design")
  → generate_screen_from_text(
      project_id       = state.json["stitch_project_id"],
      designSystem     = state.json["design_system_id"],
      prompt           = <prompt from 2.1>,
      deviceType       = "desktop"
    )
```

Collect the returned screen ID for each call. The page/state ↔ screen_id mapping is tracked in `state.json` (Step 2.3); no `screen_name` parameter exists on this API.

Generate pages **sequentially** (Stitch screen generation is stateful and rate-sensitive; do not parallelise).

### 2.3 — Record results in `state.json`

After each successful generation, update `state.json` — merge, do not overwrite. Set `pages[].states.<name>.screen_id` and `pages[].states.<name>.status` on each generated state; set the page-level `pages[].status` once all of a page's states have been attempted:

```json
{
  "pages": [
    {
      "slug": "<page>",
      "status": "generated",
      "states": {
        "<state>": { "screen_id": "<id>", "status": "generated" }
      }
    }
  ]
}
```

`pages[].states` is an **object keyed by state name** (initialized by Phase 1 with `screen_id: null, status: "pending"`). Phase 2 fills in the `screen_id` and sets `status` to `"generated"` (or `"failed"` on error). The page-level `pages[].status` is set only once every state for that page has been attempted: `"generated"` if **at least one** state generated, `"failed"` if **every** state failed. If a single call fails, mark that state `"status": "failed"` and continue with remaining pages — do not abort the whole run. (Phase 3 Step 1 skips null-`screen_id` states, so a partially-generated page still gets restyled from its successful states.)

Print a one-line progress note after each page completes:
```
Generated: <page> (<N> state(s)) — screen IDs: <id1>, <id2>, ...
```

---

## Step 3 — Mandatory Visual-Review Checkpoint

**Generation is complete. Do NOT inject any code yet.** Designs are never auto-injected unreviewed.

### 3.1 — Print the review card

```
## 🎨 Review your new designs in Stitch
Open: https://stitch.withgoogle.com/project/<stitch_project_id>
Review: <bulleted list of generated pages/states, e.g.:
  • home / default
  • blog / empty · loading · loaded · error
  • about / default>
Tweak: use Voice Canvas / direct edits in the canvas, OR tell me
  "edit <page> to <change>" and I'll call edit_screens.
When you're happy, re-run /bx:webdesign to inject the approved designs.
```

### 3.2 — Write `phase = review_pending` and stop

Merge into `state.json`:
```json
{ "phase": "review_pending" }
```

Then stop. The session is now resumable — the user reviews in the Stitch UI at their own pace.

---

## Resume Behavior (`phase = review_pending`)

When `/bx:webdesign` is invoked and `state.json["phase"] == "review_pending"`, the skill skips Phases 1 and 2 and enters this resume flow:

1. **Ask:** `"Are the designs approved, or would you like to request changes?"`

2. **If approved:** print:
   ```
   Designs approved. Proceeding to Phase 3 — Inject & Verify.
   ```
   Then advance to Phase 3 **in the same turn** — do NOT write an intermediate `phase = approved` to `state.json`. The phase state machine has no `approved` state; `phase` stays `review_pending` until Phase 3 writes its own values (`tokens_injected` / `injecting_pages`).

3. **If changes requested:** route through `edit_screens`.

   For each change the user describes (e.g. "edit about to move the CTA above the fold"), call `stitch::generate-design` via the Skill tool to invoke `edit_screens`:
   ```
   Skill("stitch::generate-design")
     → edit_screens(
         project_id = state.json["stitch_project_id"],
         screen_id  = <screen_id from state.json["pages"][...]["states"][...]["screen_id"]>,
         prompt     = "<single focused change — location + change>"
       )
   ```

   Apply one change per `edit_screens` call (see `stitch-formats.md § Per-screen generation prompt format` edits guidance: single-purpose, under ~5000 chars). Update the screen ID in `state.json` if a new screen ID is returned.

   After all edits, re-present the review card (Step 3.1) and set `phase = review_pending` again. Repeat until the user approves.

---

## State Keys Written in Phase 2

| Key | Type | Written in | Consumed by |
|-----|------|-----------|-------------|
| `pages[].states.<state>.screen_id` | string | Step 2.3 | Phase 3 `get_screen` call, resume `edit_screens` |
| `pages[].states.<state>.status` | string (`generated` \| `failed`) | Step 2.3 | Generation detail; Phase 3 per-state lookup |
| `pages[].status` | string (`generated` \| `failed`) | Step 2.3 (all states done) | Phase 3 per-page loop |
| `phase` | string (`review_pending`) | Step 3.2 / resume edits | skill entry-point routing; cleared by Phase 3 |

## Artefact Paths in Phase 2

| Artefact | Path |
|----------|------|
| State file (updated) | `.webdesign/state.json` |
| Stitch screens (remote) | `https://stitch.withgoogle.com/project/<stitch_project_id>` |
