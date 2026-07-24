# /bx:webdesign — first-run prompt (target repo: `kaanarik`)

Paste the block below into a **fresh Claude Code session in the target web repo** to kick off the first-ever end-to-end `/bx:webdesign` run. Prepared Session 51 (2026-07-23).

## Before you start — context

- **Two one-time dependencies**, from two different sources:
  - **Stitch MCP** — [`@_davideast/stitch-mcp`](https://github.com/davideast/stitch-mcp): a personal, Apache-2.0 package by **David East** (a Google DevRel engineer). Google-adjacent, **NOT** first-party Google. It holds your Google OAuth token / talks to your GCP project, so it's a real (but reasonable) trust decision — it's open source and you can pin a version.
  - **`stitch-skills`** — [`google-labs-code/stitch-skills`](https://github.com/google-labs-code): the **official Google Labs** Agent Skills.
- **GCP project:** `kaanarik` (project ID). Billing appears linked ($0.00 estimated charges shown for a real billing period). Confirm the **Stitch API** is enabled during setup — the `init` wizard should do this.
- **Scope reasoning:** the MCP add uses `-s user` (machine-global, location-independent); the skills install uses `--scope project` (must live in the target repo). So run the whole setup **in the target repo**. This config repo (`claude-config`) is not a web project and would be rejected at the web-gate anyway.
- **Safety:** web-only + refactor-only; all work on a throwaway `webdesign/<date>` branch; nothing injected without explicit approval; resumable via `.webdesign/state.json`.

## The prompt

```text
I want to run /bx:webdesign for the first time on this repo to re-skin its
visual design via Google Stitch. It's my first time using the skill and I want
to go carefully — walk me through each step and PAUSE at every checkpoint
before spending any Stitch quota or touching code. Treat this as a shakedown
run and flag anything that looks off.

Context so you don't have to re-derive it (I've already vetted this — don't
re-litigate the trust question):
- /bx:webdesign needs two one-time dependencies: (1) the Stitch MCP,
  @_davideast/stitch-mcp — a personal Apache-2.0 package by David East, a Google
  DevRel engineer (Google-adjacent, NOT first-party); (2)
  google-labs-code/stitch-skills — the official Google Labs skills.
- The skill only works on web projects, only refactors an existing design, does
  all its work on a throwaway webdesign/<date> git branch, injects nothing
  without my explicit approval, and is fully resumable via .webdesign/state.json.
- My GCP project ID is `kaanarik` (billing linked). Confirm the Stitch API is
  enabled during setup.

Please do this in order, confirming with me between major steps:

1. Make sure the bx plugin is current: run /plugin update bx, then /reload-plugins.

2. Check whether the Stitch MCP and stitch-skills are already installed. If
   either is missing, help me set it up. The `npx @_davideast/stitch-mcp init`
   wizard and the Google login are interactive, so tell me exactly which
   commands to run myself with the `!` prefix. Expected commands:
     - init (I run this):  ! npx @_davideast/stitch-mcp init
     - MCP add:   claude mcp add -e GOOGLE_CLOUD_PROJECT=kaanarik -s user stitch -- npx -y @_davideast/stitch-mcp proxy
     - Skills:    npx plugins add google-labs-code/stitch-skills --scope project --target claude-code

3. Once both dependencies are confirmed present, run /bx:webdesign. Go through
   Phase 1 (stack detection → branch → page inventory → before-screenshots →
   Stitch seeding) and STOP at the page-inventory review AND again at the
   design-direction choice, so I can check everything before any Stitch screens
   are generated.

4. In Phase 2, show me the quota pre-flight (estimated screen count vs the
   ~350/month free tier) and wait for my explicit "yes" before generating
   anything. Then stop at the mandatory review checkpoint so I can review the
   designs in the Stitch canvas before any code is touched.
```

## Usage notes

- The `! npx @_davideast/stitch-mcp init` line is **interactive** (Google login) — run it yourself with the `!` prefix. The other two commands the assistant can run for you.
- If setup was already done in a prior attempt, the skill skips step 2 and goes straight to Phase 1 — the prompt handles both cases.
- Sources: [npm `@_davideast/stitch-mcp`](https://www.npmjs.com/package/@_davideast/stitch-mcp) · [David East GitHub](https://github.com/davideast) · [google-labs-code](https://github.com/google-labs-code)
