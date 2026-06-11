# Stitch canonical formats

> Bundled baseline. Stitch evolves fast — **when Phase 1 begins executing** (setup passed, web/refactor gate passed), fetch the official prompting doc fresh and let it supersede anything here that diverges:
> `WebFetch https://stitch.withgoogle.com/docs/learn/prompting/ "Extract the current recommended prompt structure, frameworks, and any changes to design-system handling."`
> This fetch happens in `phase1-extract.md` Step 1 (after stack detection, before route enumeration). If the fetch fails, proceed with this baseline and note it in the run summary. Banner-stop sessions (Step A dependency missing) do not trigger this fetch.

## Per-screen generation prompt format

Once a design system exists at the project level, **generation prompts contain layout/content/structure ONLY — never colors, fonts, roundness, or theme tokens.** This is the mechanism that prevents visual drift across pages. (Hex codes are acceptable only in *edit* prompts for precise tweaks.)

```
[One-line page purpose + vibe]

**PLATFORM:** Web, Desktop-first

**PAGE STRUCTURE:**
1. **Header:** <navigation + branding>
2. **Hero Section:** <headline, subtext, primary CTA>
3. **<Content Area>:** <component-by-component breakdown>
4. **Footer:** <links, legal>
```

For **edits** to an existing screen, be specific and single-purpose: location + change. One screen + one change per prompt; keep prompts under ~5000 chars; Stitch loses context across large edits; screenshot after each good step.

## DESIGN.md schema (portable design system)

YAML frontmatter (drives Stitch theme tokens via `create_design_system_from_design_md`) + semantic prose body.

```markdown
---
name: <Design System Name>
colors:            # Material-3-style semantic tokens (hex). Full set includes:
  surface: '#...'  # surface, surface-dim/bright, surface-container[-low|-high|-highest],
  on-surface: '#...'  # on-surface, on-surface-variant, outline, outline-variant,
  primary: '#...'  # primary, on-primary, primary-container, on-primary-container, inverse-primary,
  secondary: '#...'  # secondary + on/container variants, tertiary + variants,
  error: '#...'    # error + on/container, plus *-fixed / *-fixed-dim / on-*-fixed[-variant],
  background: '#...'  # background, on-background, surface-variant
typography:        # named styles, each: fontFamily / fontSize / fontWeight / lineHeight / letterSpacing
  display-lg: { fontFamily: Inter, fontSize: 48px, fontWeight: '800', lineHeight: 56px, letterSpacing: -0.02em }
  headline-md: { ... }
  body-base: { ... }
  label-caps: { ... }
rounded:           # radii scale
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:           # 4px baseline
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
---

## Brand & Style
<personality, design philosophy>
## Colors
<semantic color roles>
## Typography
<font choices + why>
## Layout & Spacing
<grid model, baseline rhythm, touch targets>
## Elevation & Depth
<shadow/glass hierarchy>
## Shapes
<corner/shape language>
```

## `update_design_system` theme knobs (enums)

- `colorMode`: `LIGHT` | `DARK` (REQUIRED)
- `headlineFont` / `bodyFont` / `labelFont`: one of `INTER, ROBOTO, OPEN_SANS, LATO, MONTSERRAT, NOTO_SANS, NOTO_SERIF, PLUS_JAKARTA_SANS, BE_VIETNAM_PRO` (headline+body REQUIRED; label optional → defaults to body)
- `roundness`: `ROUND_FOUR` | `ROUND_EIGHT` | `ROUND_TWELVE` | `ROUND_FULL` (REQUIRED)
- `customColor`: primary/seed brand color, hex (REQUIRED)
- `colorVariant`: `FIDELITY` | `TONAL` | `VIBRANT` | `EXPRESSIVE` | `CONTENT` | `MONOCHROME` | `FRUIT_SALAD` | `RAINBOW` (optional)
- `overridePrimaryColor` / `overrideSecondaryColor` / `overrideTertiaryColor` / `overrideNeutralColor`: hex (optional)
- `designMd`: full DESIGN.md markdown string (optional)
- Omit the legacy `font` field (causes "invalid argument").

> Prefer `create_design_system_from_design_md` (auto-populates all tokens from DESIGN.md frontmatter) over hand-setting knobs. Use `update_design_system` only for targeted knob overrides.

## Vibe → design-system-knob mapping (starter table — tune per project)

Used by Phase 1 Step 5a (the Claude-led interview path) to translate the user's vibe words into knobs.

| Vibe words | colorVariant | roundness | headline/body font feel |
|---|---|---|---|
| elegant, refined, luxury | EXPRESSIVE or TONAL | ROUND_TWELVE | serif headline (NOTO_SERIF) + INTER body |
| minimal, simple, clean | MONOCHROME or CONTENT | ROUND_EIGHT | INTER / PLUS_JAKARTA_SANS |
| professional, trustworthy, corporate | FIDELITY or TONAL | ROUND_EIGHT | INTER / ROBOTO |
| playful, fun, friendly | VIBRANT or RAINBOW | ROUND_FULL | BE_VIETNAM_PRO / PLUS_JAKARTA_SANS |
| warm, inviting, artisanal | EXPRESSIVE | ROUND_TWELVE | LATO / MONTSERRAT |
| bold, energetic, high-performance | VIBRANT | ROUND_FOUR | MONTSERRAT / INTER (heavy weights) |
| retro, vintage | FRUIT_SALAD or EXPRESSIVE | ROUND_FOUR | NOTO_SERIF / LATO |

`colorMode` (LIGHT/DARK) and `customColor` (seed hex) come from the user's stated direction or a preserved brand color. This table is a starting point — always show the chosen knobs to the user before applying.

## Stitch MCP tool surface (called via Google's stitch-skills)

- Projects: `list_projects`, `create_project`, `get_project`
- Design system: `list_design_systems`, `create_design_system_from_design_md`, `update_design_system`, `apply_design_system`
- Screens: `generate_screen_from_text`, `generate_screen_from_image`, `edit_screens`, `get_screen`
- `get_screen` returns: `htmlCode.downloadUrl` (a **signed URL — fetch with `curl`**), `screenshot.downloadUrl`, `deviceType` (usually `DESKTOP`, 2560px base), and `data-stitch-id` attributes on elements (preserve as comments for future re-sync). The generated HTML `<head>` carries a localized `tailwind.config` that must be merged with the project theme.

## Google stitch-skills delegated to (invoke via the Skill tool)

| Need | Skill |
|---|---|
| Existing code → seeded Stitch project | `stitch::code-to-design` (chains the three below) |
| Standalone HTML from build output | `stitch::extract-static-html` |
| Source → DESIGN.md | `stitch::extract-design-md` |
| Upload + create design system | `stitch::manage-design-system` |
| Generate / edit screens | `stitch::generate-design` |

> `stitch::react-components` is **NOT** used in the refactor path (it generates *new* components rather than restyling existing ones).

## Dynamic / JS-heavy pages

Stitch makes **static screens, no logic.** For a dynamic page, generate **one screen per UI state** (empty · loading · error · loaded · modal-open · …) and record the **explicit interactions** ("when user clicks Filter → dropdown panel slides in") in the brief. Those interactions document what Phase 3 must **preserve in code** — they are never delegated to Stitch.
