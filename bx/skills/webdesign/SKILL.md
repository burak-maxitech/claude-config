---
name: webdesign
description: "Totally re-skins an existing web project's visual design via Google Stitch (driven through the Stitch MCP + Google's stitch-skills), while preserving all functionality. Extracts the current design, applies a new design language, and safely injects it page-by-page with verification."
when_to_use: When the user wants to redesign, re-skin, restyle, or totally change the UI/UX / look-and-feel / design language of an existing web project using Google Stitch. Web projects only (rejects non-web repos). Refactor of an existing project only in v1 — greenfield/new projects exit with a 'not yet supported' note. Distinct from /bx:arch (code structure) and /bx:seo (search). NOT for fixing bugs or behavior.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Glob, Grep, Skill, Task, WebFetch, Bash(git:*), Bash(npm:*), Bash(npx:*), Bash(curl:*), Bash(find:*), Bash(ls:*), Bash(node:*), mcp__plugin_playwright_playwright__browser_navigate, mcp__plugin_playwright_playwright__browser_take_screenshot, mcp__plugin_playwright_playwright__browser_snapshot, mcp__plugin_playwright_playwright__browser_click, mcp__plugin_playwright_playwright__browser_fill_form, mcp__plugin_playwright_playwright__browser_console_messages, mcp__plugin_playwright_playwright__browser_wait_for, mcp__plugin_playwright_playwright__browser_close
effort: high
argument-hint: "[status | page <name>] [--force-setup]"
---

# /bx:webdesign — Stitch-driven Web Design Refactor

Totally re-skin an existing **web** project's visual design language using **Google Stitch**, without breaking any functionality. This skill is a thin orchestrator: it **delegates** the Stitch-side work (design extraction, design system, screen generation) to Google's official `stitch-skills` (via the Stitch MCP), and **owns** the parts Google's kit lacks — web-project detection, preserve-aware page briefs, **safe injection into existing code**, and **verification**.

**Web projects only.** Rejects non-web repos. **Refactor only in v1** — greenfield/new projects get a clean "not yet supported" exit.

**Companion skills:** `/bx:seo` (web audit) · `/bx:plan` (feature planning) · `/bx:save` (end-of-session save).

> ⚠️ Stitch produces **static visuals, no logic.** This skill therefore *restyles existing pages in place* — it never replaces working components, and never delegates behavior to Stitch.

---

<!-- ORCHESTRATOR BODY ADDED IN TASK 10 -->
