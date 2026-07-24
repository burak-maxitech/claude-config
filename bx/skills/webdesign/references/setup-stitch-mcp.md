# Stitch MCP + stitch-skills setup detection

Read first by the `/bx:webdesign` orchestrator at **Step A — Setup check**. If either dependency is missing, print the banner below and **stop immediately** — do not proceed to web-stack detection, state loading, or any phase.

---

## Detection

Run both checks at the top of every `/bx:webdesign` invocation (the orchestrator knows its available tools and skills without any shell commands):

1. **Stitch MCP present?** — Inspect the current tool set for any `mcp__stitch__*` tool (the server registered under the name `stitch`). If none is visible → the Stitch MCP is not configured for this session.
2. **`stitch-skills` installed?** — Confirm that the skill `stitch-design:code-to-design` is among available skills (callable via the Skill tool). The Google `stitch-skills` marketplace installs **three** plugins — `stitch-build`, `stitch-design`, `stitch-utilities` — and every skill this refactor delegates to is namespaced `stitch-design:<name>` (NOT `stitch::<name>`). If `stitch-design:code-to-design` is absent → `stitch-skills` is not installed. (If the `Skill` tool itself is unavailable, treat `stitch-skills` as absent.)

Both checks are passive (no shell invocation needed). Perform them in parallel before touching anything else.

> **Note — don't be misled by `claude mcp list`.** For a remote HTTP MCP server, an out-of-session `claude mcp list` can report `Connected · tools fetch failed` even when the server is perfectly healthy — it can't always complete the streamable-HTTP session handshake a live in-session connection does. The authoritative check is the passive in-session one above (are `mcp__stitch__*` tools visible? does a zero-cost `list_projects` round-trip succeed?), **not** `claude mcp list`.

---

## Banner (printed when a dependency is missing)

When **either** dependency is absent, print the relevant section(s) of the banner below, then **exit cleanly** (do not continue the invocation).

**Specificity rule:** show only the install step(s) for what is actually missing:
- If only the Stitch MCP is absent → show step 1 only.
- If only `stitch-skills` is absent → show step 2 only.
- If both are absent → show the full banner.

```markdown
## ⚙️ One-time setup needed for /bx:webdesign

This skill drives Google Stitch through its MCP + Google's official skills. Set up once:

1. **Install + auth the Stitch MCP.** Run the init wizard **in a real external terminal** (Windows Terminal / PowerShell / iTerm) — it is a full-screen arrow-key TUI and **cannot** be driven through Claude Code's `!` prefix (the prompt force-closes):
   ```
   npx @_davideast/stitch-mcp init
   ```
   The wizard offers two auth modes — pick either:
   - **API key (Direct)** — simplest. No gcloud, no GCP project, no billing. You paste a Stitch API key; the wizard offers to store it in a `.env` file.
   - **gcloud / Google login** — Application Default Credentials against a GCP project (this path is the one that needs **billing enabled**, the **Stitch API enabled**, and Owner/Editor on the project).

   When it finishes, the wizard **prints the exact `claude mcp add …` command to run — copy that one.** It differs by auth mode (e.g. an `http` transport with an `X-Goog-Api-Key` header for API-key mode — NOT a fixed `… -- npx … proxy` command, and NOT `-e GOOGLE_CLOUD_PROJECT=…`). Keep the server name `stitch` and use **`-s user`** so it saves to `~/.claude.json`, outside the repo.
2. **Install Google's Stitch skills:**
   ```
   npx plugins add google-labs-code/stitch-skills --scope project --target claude-code
   ```

Then **restart Claude Code** (or `/reload-plugins` — a newly-added MCP server's tools appear only on reconnect) and re-run `/bx:webdesign`.
```

> 🔒 **Secret hygiene (API-key mode).** The `claude mcp add` command the wizard prints embeds your **raw API key** in a `--header`. Run it in the external terminal, **never via `!`**, so the key never lands in the Claude Code transcript. If the wizard wrote the key to `.env`, confirm `.env` is gitignored (`git check-ignore .env`) before any commit. Use `-s user`, **not** `-s project` — `-s project` writes `./.mcp.json` into the repo and risks committing the key. (The `.env` copy is redundant once the key is in `~/.claude.json` for the `http` transport; it can be deleted afterward.)

After printing the applicable steps, **stop**. Do not print a phase summary, do not touch `state.json`, do not run any other detection pass.

---

## Idempotency / `--force-setup`

To avoid spamming the banner in a project where the user has already seen it and is mid-install, the orchestrator uses a sentinel file:

- **First banner display:** after printing, write the file `.webdesign/.setup-shown` (create the `.webdesign/` directory if it does not exist). This is a zero-byte marker — no content required.
- **Subsequent invocations:** if `.webdesign/.setup-shown` exists **and** the dependency is still missing, print a shorter one-liner reminder instead of the full banner:
  ```
  ⚙️ /bx:webdesign setup incomplete — [Stitch MCP | stitch-skills | both] still missing. Run `/bx:webdesign --force-setup` to see the install commands again.
  ```
  Then **stop** as before.
- **`--force-setup` argument:** if the user passes `--force-setup`, re-print the banner applying the **same specificity rule** — i.e. show only the install step(s) for whatever is still missing, then stop. If **both** dependencies are now present, skip the banner entirely and print a brief confirmation instead:
  ```
  ✅ Stitch MCP + stitch-skills both detected — setup complete.
  ```

The sentinel is only a display-dedup device — the dependency check always runs, and the skill always stops when a dependency is absent.

> Note: `.webdesign/` is a runtime directory created in the target web project (where the skill operates), not in this config repo. Do not create it here.

> **Gitignore:** `.webdesign/.setup-shown` (and the entire `.webdesign/` directory) is per-machine state and must NOT be committed. Phase 1 adds `.webdesign/` to the target repo's `.gitignore` — mirroring how `/bx:seo` gitignores its `.seo-data/.gsc-banner-shown` sentinel. A committed sentinel would suppress the setup banner for collaborators who lack Stitch credentials.
