# Stitch MCP + stitch-skills setup detection

Read first by the `/bx:webdesign` orchestrator at **Step A — Setup check**. If either dependency is missing, print the banner below and **stop immediately** — do not proceed to web-stack detection, state loading, or any phase.

---

## Detection

Run both checks at the top of every `/bx:webdesign` invocation (the orchestrator knows its available tools and skills without any shell commands):

1. **Stitch MCP present?** — Inspect the current tool set for any tool whose name begins with `stitch`. If no `stitch*` tool is visible → the Stitch MCP is not configured for this project.
2. **`stitch-skills` installed?** — Confirm that the skill `stitch::code-to-design` is among available skills (callable via the Skill tool). If absent → the Google `stitch-skills` plugin is not installed. (If the `Skill` tool itself is unavailable, treat `stitch-skills` as absent.)

Both checks are passive (no shell invocation needed). Perform them in parallel before touching anything else.

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

1. Install + auth the Stitch MCP (interactive wizard: gcloud, Google login, GCP project, enable Stitch API):
   ```
   npx @_davideast/stitch-mcp init
   claude mcp add -e GOOGLE_CLOUD_PROJECT=<your-gcp-project> -s user stitch -- npx -y @_davideast/stitch-mcp proxy
   ```
2. Install Google's Stitch skills:
   ```
   npx plugins add google-labs-code/stitch-skills --scope project --target claude-code
   ```

Prerequisites: a GCP project with **billing enabled** and the **Stitch API enabled**, and Owner/Editor on it.
Re-run `/bx:webdesign` once both are done.
```

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
