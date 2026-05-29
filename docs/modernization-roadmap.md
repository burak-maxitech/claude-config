# Modernization Roadmap — Cutting-Edge `bx-*` Toolkit

> **Created:** 2026-05-28 (Session 37) · **Status:** plan-of-record, execution in progress
> **Scope:** Ship 4 modernization items against the mid-2026 Claude Code feature surface.
> **Source of truth:** verified against live docs (`code.claude.com/docs`) + live local config inspection on 2026-05-28 — not model recall. See [Verified facts](#verified-facts).

---

## TL;DR

The `bx-*` toolkit is **already modern on the frontmatter axis** (S33 did that: `when_to_use`, `disable-model-invocation`, `effort`, `allowed-tools`, `argument-hint`, `Task` dispatch are all in place). The remaining frontier is **external capability** (MCP/Playwright/LSP) and **orchestration-as-code** — replacing hand-rolled Grep/curl/gcloud heuristics and prose-encoded dispatch with ground-truth tools and real manifests.

Four items, in recommended execution order:

| # | Item | Effort | Risk | Blocks on user |
|---|------|--------|------|----------------|
| ~~**#1**~~ | ~~Retire `gsc-parse-helper.py` → **GSC MCP server**~~ — **DECLINED (S37)**, quota regression | M | Low | — |
| **#2** | **Playwright rendered audit** in `bx-seo` — *deferred, no current dependency* | S | Low | `npx playwright install` (browser binaries) |
| **#4** | Package toolkit as a **versioned `bx` plugin** | L | Med | Naming decision (`bx-arch` → `bx:arch`) |
| **#6** | **Orchestration-as-code** for `bx-seo` | M | Low | none (mostly subsumed by #1) |

---

## Verified facts

These corrected my initial assumptions and shape the plan:

1. **Playwright is installed but not live.** `playwright@claude-plugins-official` is enabled and ships an MCP server (`npx @playwright/mcp@latest`), but `claude mcp list` shows it **✗ Failed to connect** — it needs a first-run `npx playwright install` (browser binaries) before tools surface. So #2 is "make it connect + wire it in," not "install it."
2. **GSC MCP servers already exist — no need to build one.** Mature community options:
   - [`ahonn/mcp-server-gsc`](https://github.com/ahonn/mcp-server-gsc) — search analytics (query/page/device filtering) + URL inspection + a `detectQuickWins` helper.
   - [`sarahpark/google-search-console-mcp`](https://mcpservers.org/servers/sarahpark/google-search-console-mcp) — **read-only**: search analytics + URL inspection + sitemaps. Read-only matches `bx-seo`'s needs exactly (it never writes to GSC).
3. **This repo is not a plugin yet.** Skills/agents are symlinked into `~/.claude/`. The active marketplace is `claude-plugins-official`. Becoming a plugin is a genuine restructure (see #4), because **plugins can't reference files outside their own directory** (path-traversal is blocked; the symlink-into-`~/.claude` model doesn't carry over).
4. **Plugin manifest schema** (`.claude-plugin/plugin.json`): only `name` required; component dirs (`skills/`, `agents/`, `hooks/hooks.json`, `.mcp.json`, `.lsp.json`) live at **plugin root**, not inside `.claude-plugin/`. Omitting `version` makes every git commit a new version (ideal for a private, fast-iterating personal toolkit).
5. **`userConfig` with `sensitive: true`** prompts the user for secrets at enable-time and stores them in the keychain — the clean path for GSC credentials inside the plugin's `.mcp.json` (`${user_config.KEY}` substitution).
6. **Plugin-shipped agents cannot declare `hooks`/`mcpServers`/`permissionMode`** (security). The 13 `bx` agents only use `name`/`description`/`model`/`tools`/`user-invocable` → they port cleanly (`user-invocable` is an unrecognized field → load-time warning only, harmless; can drop it).
7. **Official LSP plugins already exist** (`pyright-lsp`, `typescript-lsp`, `rust-analyzer-lsp`) — installable from the marketplace. The dead-code/unused-export precision win (deferred item, see below) is mostly "install + reference," not "build."
8. **The `Workflow` tool needs explicit user opt-in and runs in the background.** A skill (SKILL.md prose) cannot silently force it. This reshapes #6 (below) — the real "orchestration as code" win is the MCP server (#1) plus a plugin `bin/` executable, not a forced Workflow.

---

## #1 — Retire `gsc-parse-helper.py` for a GSC MCP server

> **STATUS: EVALUATED AND DECLINED (S37, 2026-05-28).** The candidate server (`mcp-search-console`) has **no response caching** and **caps `batch_url_inspection` at 10 URLs/call** — adopting it would regress the quota economics the S31/S35 cache layer protects (the helper inspects up to 200 URLs in parallel with a 7-day cache). `/bx:seo` stays on gcloud ADC + the helper. The `gsc` MCP server stays configured machine-local for *ad-hoc interactive* GSC queries only. Reopen only if the server gains caching + a higher batch cap. See [key-decisions.md](key-decisions.md). The goal below is preserved as the original plan-of-record.

**Goal.** Replace the 1279-line `gsc-parse-helper.py` + the hand-built cache (atomic writes, TTL split, PID-suffixed temp files), 429/5xx retry/backoff, `inspect-batch` ThreadPoolExecutor, and the `gcloud`/`curl` shelling with **typed MCP tool calls**.

**Why it's the biggest win.** Across S30→S35 the recurring failure mode was *"every new dispatch shape that lives in spec-prose-only gets improvised by the orchestrator into `.seo-data/gsc/`"* (S35 altitude lesson) — 3+ disk-write-boundary violations. **Root cause: GSC ingestion logic lives in prose for a model to reconstruct.** An MCP server makes it a tool call with a fixed contract — there is no longer a "dispatch shape" to improvise. This kills the bug class, not just an instance.

**Verified mechanism.** Configure `ahonn/mcp-server-gsc` (or `sarahpark/...` for read-only) as an MCP server. Tools surface as `mcp__gsc__*` and are callable from the `bx-seo` orchestrator and the `seo-gsc-insights` subagent (subagents reach session MCP tools via `allowed-tools`).

**Steps.**
1. Choose server (recommend `sarahpark` read-only — least privilege; `bx-seo` never mutates GSC). Confirm its exact tool names + arg schema.
2. Add MCP config — at project scope first (`.mcp.json`) for iteration, later folded into the `bx` plugin's `.mcp.json` with `userConfig` for the service-account JSON path (`sensitive: true`).
3. Rewrite `bx-seo` SKILL.md Turn-1/Turn-2 ingestion: replace `gsc-parse-helper.py` subcommands + `curl`/`gcloud` calls with MCP tool calls. The parse/aggregate logic the helper did (Q1/Q2/Q3 clustering, CTR, brand-anomaly, deindex snapshot diff) moves into either the subagent's reasoning or a thin `bin/` post-processor (see #6).
4. Delete `references/gsc-parse-helper.py`, `gsc-cache.md`, and the disk-write-boundary prose rules that exist only to police the improvised scripts. Trim `gsc-ingestion.md` / `gsc-api-queries.md` to the MCP contract.
5. Keep `finding-history.json` / `watchpoints.json` (those are `bx-seo`'s own state, not GSC ingestion) — but they can live under `${CLAUDE_PLUGIN_DATA}` once plugin-ized.

**Blocks on user.** GSC API auth — a Google Cloud service account with Search Console access, or OAuth. I can stage everything else; the auth secret is theirs to provide.

**Net.** Deletes ~1300+ lines of brittle Python + cache/retry/boundary prose. Removes the entire class of "orchestrator wrote a script into `.seo-data/`" bugs.

---

## #2 — Playwright rendered audit in `bx-seo`

**Goal.** Let `seo-technical` and `seo-content` audit the **hydrated DOM** and capture **real Core Web Vitals** instead of grepping static HTML.

**Why.** burakarik.com is Next.js. Client-rendered meta tags, JSON-LD, canonical links, and headings are **invisible to a static `curl`/Grep fetch** — the current scans report false negatives on exactly the kind of site the user runs. A static SEO scan of a JS app is structurally blind.

**Verified mechanism.** The Playwright MCP is already installed (just not connected). Once `npx playwright install` provisions browsers, tools like `browser_navigate` / `browser_snapshot` / `browser_evaluate` surface and let the skill read post-hydration DOM + measure LCP/CLS/INP via the Performance API.

**Steps.**
1. Get the server healthy: `npx playwright install` (chromium), confirm `claude mcp list` shows ✓.
2. Add a **rendered-audit branch** to `bx-seo`: when `--url <deployed-url>` is given (or a deployed URL is detected), navigate with Playwright, snapshot the rendered DOM, and feed *that* to `seo-content`/`seo-technical` instead of (or alongside) the static source.
3. Capture CWV (LCP/CLS/INP) from the live page → feed `seo-technical`'s performance signals with real numbers, not static "image/font/script" heuristics.
4. Gate it: static-only scan stays the default for repo-only runs (no browser needed); rendered audit activates when a URL is available. Document the fallback when Playwright is unavailable.

**Blocks on user.** Browser-binary install (`npx playwright install`) on each machine — one-time, scriptable in the SessionStart hook.

**Net.** Turns `bx-seo` from a source-code scanner into an actual rendered-page auditor. Accuracy fix, not a nicety.

---

## #4 — Package the toolkit as a versioned `bx` plugin

**Goal.** Convert the 9 skills + 13 agents from "symlinked loose files" into **one installable, versioned `bx` plugin** that also bundles the GSC + Playwright MCP config (#1, #2) and is the natural home for LSP config and a `SessionEnd` hook.

**Why.** The S36 `bx-` prefix was a *workaround* for namespace collisions with built-ins. A plugin is the principled fix: skills namespace as `bx:arch` / `bx:seo` (collision-proof by construction), you get real versioning, `claude plugin validate` as a CI gate, and a single `/plugin install` replaces the symlink dance across machines.

**Verified structure.**
```
claude-config/                      ← marketplace repo (already git)
├── .claude-plugin/
│   └── marketplace.json            ← { name, owner, plugins:[{ name:"bx", source:"./bx" }] }
└── bx/                             ← the plugin
    ├── .claude-plugin/
    │   └── plugin.json             ← { name:"bx", description, (version omitted → commit-SHA) }
    ├── skills/
    │   ├── arch/SKILL.md           ← was bx-arch  → invokes as /bx:arch
    │   ├── seo/SKILL.md            ← was bx-seo
    │   └── … (7 more)
    ├── agents/                     ← the 13 agents (drop user-invocable: field)
    ├── .mcp.json                   ← GSC (#1) + (optionally) Playwright pin, ${user_config.*} for creds
    ├── .lsp.json                   ← optional; or rely on official LSP plugins
    ├── hooks/hooks.json            ← SessionEnd → nudge /bx:docs (closes resume↔docs loop)
    └── bin/                        ← deterministic helpers (see #6), bare-command on PATH
```

Install flow becomes: `/plugin marketplace add ./claude-config` (or the GitHub repo) → `/plugin install bx@<marketplace-name>`.

**The decision that gates this (see open question).** Skill **names**. Inside plugin `bx`, a skill named `arch` invokes as `/bx:arch`. So the clean move is to **rename the skill dirs/`name:` fields from `bx-arch` → `arch`** and let the plugin prefix supply `bx:`. Keeping `bx-arch` yields the redundant `/bx:bx-arch`. Renaming means another cross-reference sweep (like S36) across all SKILL.md bodies (`/bx-arch` → `/bx:arch`, etc.) — that's the main cost.

**Steps.**
1. **[decision first]** Confirm naming: `bx-arch` → `bx:arch` (rename) vs. keep prefix.
2. Create `bx/` plugin dir; `git mv` the 9 skills + 13 agents in (drop the `bx-` dir prefix if renaming).
3. Write `bx/.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json`.
4. Cross-reference sweep: update inter-skill references in SKILL.md bodies + `bx-health`'s routing table + `README`/`workflow.md` to the new invocation names.
5. Migrate the SessionStart hook (S33) into the plugin's `hooks/hooks.json`; add the `SessionEnd` → `/bx:docs` nudge.
6. Move `bx-seo` runtime state (`finding-history.json`, `watchpoints.json`, GSC cache) to `${CLAUDE_PLUGIN_DATA}` (survives plugin updates).
7. `claude plugin validate ./bx --strict` → fix warnings → install locally → smoke-test each skill.
8. Update the symlink docs (README/workflow.md) — the symlink model is replaced by `/plugin install`.

**Blocks on user.** The naming decision (#1 above). Everything else I can execute + validate.

**Risk.** Medium — it's invasive and touches the daily-driver setup. Mitigation: build `bx/` additively alongside the existing `.claude/` symlinks, validate the plugin install works, *then* retire the symlinks in a separate commit. Reversible at each step.

---

## #6 — Orchestration-as-code for `bx-seo`

**Honest reframing (see verified fact #8).** The original framing — "move the orchestration into a Workflow script" — collides with a real constraint: the `Workflow` tool requires explicit user opt-in and runs in the background, so a skill can't silently invoke it. The "orchestration as code" win is therefore delivered in two grounded pieces, not one forced Workflow:

1. **The deterministic ingestion is solved by #1.** The GSC MCP server *is* the orchestration-as-code for the part that kept breaking (HTTP + cache + retry + URL-inspection batching). This is the bulk of the win.
2. **Residual deterministic logic → a plugin `bin/` executable.** The non-GSC deterministic bits the parse-helper did (snapshot diffing for sub-dim 14 deindex regression, finding-history/watchpoint bookkeeping, cluster math) become a single `bin/bx-seo-postprocess` script. Because `bin/` is on the Bash `$PATH` while the plugin is enabled, the orchestrator calls a **bare command** — there is nothing left to improvise into `.seo-data/`. This is the canonical-primitive fix (the S35 lesson: "ship the canonical primitive, not tell the orchestrator harder").

3. **Optional top layer — a saved Workflow.** For the parallel scan fan-out (the 4 scan subagents) + schema-validated returns (killing the JSON-parse fragility that caused bugs), ship `.claude/workflows/bx-seo.js` that the user can run with the `workflow` keyword when they want the fully deterministic, schema-checked pass. `bx-seo` SKILL.md gains a note: "for a deterministic, structured-output run, invoke the bx-seo workflow." This is opt-in by design and complements (doesn't replace) the skill.

**Steps.**
1. After #1, extract the surviving deterministic logic into `bin/bx-seo-postprocess` (stdin JSON → stdout JSON; no disk writes outside `${CLAUDE_PLUGIN_DATA}`).
2. Repoint `bx-seo` prose at the bare command; delete the inline-heredoc / improvise-prone instructions.
3. (Optional) Author `workflows/bx-seo.js` using `pipeline()`/`parallel()` + `schema` for the scan fan-out; document the opt-in invocation.

**Net.** The "improvise a script" bug class is gone (it was already gone after #1; the `bin/` script closes the residual). Subagent returns get a structured contract.

---

## Sequencing & dependencies

```
#1 GSC MCP ───────────────┐
   (independent, biggest)  │
#2 Playwright ─────────────┤──► #4 plugin (folds #1+#2 MCP into .mcp.json,
   (independent)           │        adds hooks/bin/lsp) ──► #6 bin/ + workflow
                           │
   both prototyped at project scope first, then absorbed by the plugin
```

- **#1 and #2 are independent** and can be done at project/user MCP scope *before* the plugin exists, then folded into the plugin's `.mcp.json` during #4.
- **#4 is the consolidation** — do it once #1/#2 prove out, so the plugin ships them bundled.
- **#6's `bin/` piece wants the plugin** (`bin/` on PATH), so it lands with/after #4.

**Recommended order:** #1 → #2 → #4 → #6. (Or #4 scaffold first if the user prefers the container in place before wiring MCP — see open question.)

---

## What I can do headlessly vs. what needs the user

| Work | I can do now | Needs user |
|------|--------------|------------|
| GSC MCP config + `bx-seo` prose rewrite + delete parse-helper | ✅ | GSC service-account auth to test live |
| Playwright config fix + rendered-audit branch in `bx-seo` | ✅ | `npx playwright install` + live render test |
| Plugin scaffold, manifests, `git mv`, cross-ref sweep, `claude plugin validate` | ✅ | naming decision; final `/plugin install` smoke test |
| `bin/` post-processor + optional workflow script | ✅ | — |

---

## Deferred (not in this batch, but easy adds the plugin enables)

- **#3 LSP-backed dead-code precision** for `bx-clean`/`bx-arch`/`bx-tests` — install official `pyright-lsp`/`typescript-lsp`/`rust-analyzer-lsp`, then teach those skills to prefer LSP "find references" over Grep heuristics. Highest accuracy-per-effort once the plugin is the container.
- **#5 `SessionEnd` hook → `/bx:docs` nudge** — closes the resume↔docs loop. Trivial once the plugin's `hooks/hooks.json` exists (folded into #4 step 5).
- **`bx-health` MCP-awareness** — teach the router to recommend *which MCP servers* to connect per project type.

---

## Open questions (gating execution)

1. **Skill naming under the plugin:** rename `bx-arch` → `bx:arch` (clean, but another cross-ref sweep), or keep the `bx-` prefix (→ redundant `/bx:bx-arch`)?
2. **First execution step:** start with #1 (GSC MCP — needs your Google auth) or scaffold #4 (the plugin container, fully doable now) first?
