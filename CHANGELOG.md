# Changelog

All notable changes to the `bx` plugin, newest first. Versioning follows [semver](https://semver.org). The `version` field in `bx/.claude-plugin/plugin.json` is the plugin's **update cache key**: users receive an update only when it changes, so every change under `bx/` must bump it (automated by `/bx:save`'s commit checkpoint).

## 1.0.0 — 2026-08-11

First explicitly-versioned release. The plugin previously used commit-SHA versioning (no `version` field in the manifest), so users saw commit hashes as version identifiers.

- **Versioning:** added `version` + `displayName` to the plugin manifest; `/bx:save`'s commit checkpoint now enforces the bump; this changelog started.
- **/bx:evolve:** docs-lane pinned allowlist grown 9 → 11 pages (added `checkpointing` and `code-review`); full upstream audit run — watermark advanced 2.1.217 → 2.1.228, 4 new findings registered and applied.
- **Fixed (from the audit's `--fix` pass):**
  - Corrected the wrong "per-edit undo" checkpoint claim at 9 sites across 8 files (clean, arch, tests, seo, evolve skills + workflow.md): checkpoints are captured per user prompt, so one `/rewind` reverts a whole `--fix` batch, never a single edit.
  - README's review ladder now flags that bare `/review` is an alias of built-in `/code-review` (v2.1.223), not `/bx:review`.
  - `/bx:evolve` fix-mode notes carry the v2.1.221 "plugins activate immediately when safe" signal (hedged; manual refresh steps intact pending a smoke-test).
  - workflow.md's `/loop` + `disable-model-invocation` caveat upgraded from speculative to documented-for-scheduled-tasks, quoting Anthropic's code-review docs.
