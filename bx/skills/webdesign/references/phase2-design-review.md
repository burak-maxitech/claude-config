# Phase 2 — Design & Review

**Goal:** generate Stitch screens from the Phase-1 briefs, then stop for mandatory human review before any code is touched. On completion, `state.json` carries `pages[].status = generated` + `phase = review_pending`.

There are **three phases only**: Phase 1 (Extract & Stage), Phase 2 (this file), Phase 3 (Inject & Verify). Never reference a Phase 4 or Phase 5.

**Inputs from `state.json` (written by Phase 1):**
- `design_system_id` — applied to every `generate_screen_from_text` call so colors/fonts come from the project design system, not from the prompt.
- `stitch_project_id` — the Stitch project where screens are created.
- `pages[]` — one entry per page (slug, route, brief path, states list).

---

## Step 1 — Quota Pre-Flight

Before calling `generate_screen_from_text` even once, compute the estimated screen count and ask for confirmation.

### 1.1 — Count screens

For each page brief in `.webdesign/briefs/`, read the `states:` list from the YAML frontmatter (see `brief-format.md`). A page with no explicit states list counts as 1 (the `default` state).

```
estimated_screens = Σ len(states) for each page brief
```

**Examples:**
- 4 pages × 1 state each = 4 screens
- 2 static pages + 1 dynamic page with `[empty, loading, loaded, error]` = 6 screens

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
- **Explicit override** (e.g. `--skip-quota-check` or "skip the pre-flight"): skip this step and proceed directly to Step 2.

---

## Step 2 — Generate Screens Per Brief

Iterate over every page brief. For each page, generate one screen per state.

### 2.1 — Build the generation prompt

For each `(page, state)` pair, construct a prompt from the brief using the **layout/content-only format** from `stitch-formats.md § Per-screen generation prompt format`:

```
[One-line page purpose + vibe, e.g. "Portfolio home — minimal, above-fold hero with CTA"]

**PLATFORM:** Web, Desktop-first

**PAGE STRUCTURE:**
1. **Header:** <from brief: navigation + branding>
2. **Hero Section:** <from brief: headline, subtext, primary CTA>
3. **<Content area>:** <component-by-component from brief's "Key components">
4. **Footer:** <from brief: links, legal>
```

**Critical constraint:** the prompt contains **layout, content, and structure ONLY — never colors, font names, roundness, or hex codes.** The `design_system_id` supplies all visual tokens; adding theme values to the prompt causes drift across pages. This is the multi-page consistency mechanism (see `stitch-formats.md`).

For dynamic pages (brief has multiple `states:`), generate each state as a separate screen. Adjust the one-line purpose to name the state: e.g. `"Blog listing — loading state, skeleton placeholders"`.

### 2.2 — Invoke `stitch::generate-design`

For each `(page, state)` pair call `stitch::generate-design` via the Skill tool, which internally calls `generate_screen_from_text`:

```
Skill("stitch::generate-design")
  → generate_screen_from_text(
      project_id    = state.json["stitch_project_id"],
      design_system_id = state.json["design_system_id"],
      prompt        = <prompt from 2.1>,
      screen_name   = "<page>/<state>"   # e.g. "blog/loaded"
    )
```

Collect the returned screen ID for each call.

Generate pages **sequentially** (Stitch screen generation is stateful and rate-sensitive; do not parallelise).

### 2.3 — Record results in `state.json`

After each successful generation, update `state.json` — merge, do not overwrite:

```json
{
  "pages": [
    {
      "slug": "<page>",
      "states": {
        "<state>": { "screen_id": "<id>", "status": "generated" }
      }
    }
  ]
}
```

Set `pages[].status = generated` once all states for a page are done. If a single call fails, mark that state `"status": "failed"` and continue with remaining pages — do not abort the whole run.

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

2. **If approved:** set `phase = approved` in `state.json`, print:
   ```
   Designs approved. Proceeding to Phase 3 — Inject & Verify.
   ```
   Then advance to Phase 3.

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
| `pages[].states.<state>.screen_id` | string | Step 2.3 | Phase 3 injection, resume edit_screens |
| `pages[].status` | string (`generated` \| `failed`) | Step 2.3 | Phase 3 skip-failed guard |
| `phase` | string (`review_pending` \| `approved`) | Step 3.2 / resume | skill entry-point routing |

## Artefact Paths in Phase 2

| Artefact | Path |
|----------|------|
| State file (updated) | `.webdesign/state.json` |
| Stitch screens (remote) | `https://stitch.withgoogle.com/project/<stitch_project_id>` |
