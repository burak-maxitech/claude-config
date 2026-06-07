# Per-page brief format

Claude auto-drafts one brief per page from the codebase; the user refines it before generation. The brief is BOTH the Stitch-generation input AND the Phase-3 verification contract.

## Template (`.webdesign/briefs/<page>.md`)

```markdown
---
page: <slug>
route: <url-path>
file: <source/file/path>
device: desktop   # v1 restyles within existing breakpoints; Stitch generates desktop
states: [default] # add empty/loading/error/loaded/modal-open for dynamic pages
---

## Purpose
<what this page is for, who uses it, the user intent>

## Functionality to PRESERVE   ← this list IS the verification contract
- <handler / API call / route / state / form / interaction that MUST keep working>
- <e.g. "submit button POSTs /api/contact and shows success toast">
- <e.g. "filter dropdown updates the results list client-side">

## Key components
- <component → what it does>

## UX notes / new-design intent
- <layout hierarchy, emphasis, what the redesign should improve>

## States (dynamic pages only)
- default: <description>
- empty: <description>
- loading: <description>
- error: <description>
- modal-open: <description>
```

## Rules
1. **Functionality to PRESERVE** is the most important section — it drives both what Phase 3 must keep and the exact Playwright assertions in verification (see `verification.md`). Be concrete and behavioral.
2. For **dynamic/JS-heavy pages**, enumerate each meaningful UI state in `states:` — each becomes a separate Stitch screen (see `stitch-formats.md` "Dynamic / JS-heavy pages").
3. Briefs describe **structure + content + behavior** — never colors/fonts (those live in the project-level design system).
4. Keep real content/copy intent in the brief; the redesign reuses the page's real content, not Stitch placeholders.
