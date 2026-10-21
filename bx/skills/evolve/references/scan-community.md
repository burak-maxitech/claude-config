# Scan: Community Discovery (WebSearch + curated fetches)

Loaded by the orchestrator and passed to the `upstream-community` subagent. You are that subagent. Detailed scanning instructions follow.

You have these tools available: Read, Grep, Glob, WebSearch, WebFetch. Use WebSearch and WebFetch for all network access. No `curl`, no shell HTTP commands.

---

## PURPOSE — READ FIRST

**This lane emits no findings.** It is a discovery feed: it searches the open web for **official sources the other two lanes cannot see** — `code.claude.com` and `anthropic.com` pages that are not yet on `scan-docs.md`'s pinned allowlist, and posts by Anthropic maintainers in `anthropics/*` repositories (Issues, Discussions, PRs) that state a contract the bx plugin depends on — and returns them as `allowlist_candidates`. The docs lane owns the finding once a page is pinned; the changelog lane owns release notes.

Until bx 2.12.0 this lane emitted advisory `tier: community` findings. It was degraded in five of six runs, its findings were never fix-eligible, and most of its value turned out to be the official pages it stumbled on (the S53 lesson). The advisory findings are gone; the discovery is now the whole job. `findings` is always `[]` — except for the sentinel (§8 of the lane contract) when the lane cannot run at all.

---

## Inputs you receive in your task prompt

- `community_checked_at` — ISO date string (YYYY-MM-DD) or null. The date this lane last ran successfully. Used only to frame the report ("community checked as of <date>"); it does NOT gate what you search — you always search with fresh queries.
- The shared inputs — `capability_inventory`, `pain_point_list`, and the Grep scope — are defined in `bx/skills/evolve/references/lane-contract.md` §1. Read that file after this one; it owns everything this lane shares with the other two (sentinel, `lane_status`, hard rules, footer keys) and this file never restates it. §2–§6 (filter, `affected_files`, finding schema, class guidance) do not apply here, because this lane emits no findings.

Also Read `bx/skills/evolve/references/scan-docs.md`'s **Pinned URL allowlist** table before you search: a page already in it is never a candidate.

---

## Method

### Step 1 — Formulate queries (at most 3)

Derive at most **3** WebSearch queries per run. Use exactly this allocation — do not improvise additional slots:

1. **Fixed slot 1:** `site:code.claude.com/docs <capability area>` — replace `<capability area>` with the area that has the most inventory entries (count the `bx:<owner>/…` strings per owner; take the owner with the most, then its most common `/<area>` suffix, e.g. `allowed-tools`, `hooks`, `plugins`). This finds official pages the allowlist lacks for the plugin's heaviest dependency.
2. **Fixed slot 2:** `site:github.com/anthropics/claude-code <first pain point>` — the first entry of `pain_point_list` (registry order, oldest first), as plain words. This finds maintainer Issues, Discussions and PRs that answer a recorded pain.
3. **Variable slot 3:** `Claude Code <second pain point> docs` — the second pain point's words plus `docs`; when there is only one pain point, use `Claude Code <capability area> reference` with the area from slot 1. This catches an official page that search ranks under a different wording.

**Why 3 is the hard cap:** this lane has the worst signal-to-noise ratio of the three. Beyond 3 queries the marginal result is a listicle.

### Step 2 — Run WebSearch queries

For each query from Step 1, call WebSearch. Collect all returned URLs and their snippet text.

**Failure definition:** A WebSearch call fails if it returns an error. Zero results is not a failure — record it in `scan_note`.

**Keep only official sources.** A result is official when its URL is under `code.claude.com`, `docs.claude.com`, `anthropic.com`, or `github.com/anthropics/`. Discard everything else before fetching — blogs, forums, listicles, paraphrases of the docs. This lane does not evaluate community advice any more; a community page is never fetched.

**Discard before fetching:**
- Any URL already in `scan-docs.md`'s pinned allowlist (canonicalize both sides per state-schema.md's `source_url` canonicalization: lowercase host, no trailing slash, no fragment, no query).
- A GitHub result whose author is not an Anthropic maintainer (a Discussion or Issue opened by an outside user is community content; a maintainer's reply inside it is official — the fetch in Step 3 tells which).
- Release pages (`github.com/anthropics/claude-code/releases/…`) — the changelog lane owns them.

### Step 3 — Fetch shortlisted pages (at most 5 total)

**Hard cap: 5 WebFetch calls for this entire run.** Issue all shortlisted fetches in a single message — they are independent; tally `lane_status` after all return. For each shortlisted URL (in rank order, up to 5):

- Call WebFetch asking for the page's title, its headings, and which Claude Code contract (frontmatter key, hook event, permission syntax, plugin field, command, tool) it is the canonical owner of. If the fetch reports unread text past ~100,000 characters (Claude Code 2.1.290+), the headings you already have are enough — do not re-fetch; note `truncated` in the candidate's reason.
- **Failure definition:** A fetch fails if WebFetch returns an error, a redirect to an unrelated page, or empty content where content is expected. Record each failed URL in `pages_failed` for the footer and continue.
- For a GitHub thread, keep it only when a maintainer post (author is an Anthropic employee by badge, or the `anthropics` org) states a contract — a rename, a removal, a recommended pattern, a confirmed bug in something bx uses. Cite the maintainer's comment anchor, not the thread.

If 5 fetches have been used and shortlisted URLs remain, stop fetching and record the count of unfetched URLs in `scan_note` as `cap_reached: <n> unfetched`.

### Step 4 — Qualify each fetched page as a candidate

A fetched page becomes an `allowlist_candidates` entry only when **all** hold:

1. It is official (Step 2's domain rule) and not already pinned.
2. It is the **canonical owner** of a syntax or contract the bx plugin depends on — not a page that merely mentions it (the completeness rule in `scan-docs.md`: `permissions` belonged on the list because it defines `Tool(param:value)`, not because `settings` mentions permissions).
3. The dependency is real: Grep `bx/`, `README.md`, `workflow.md` for the contract's token (the key, event, command or syntax the page owns) and find at least one hit, or match the page to a `pain_point_list` entry by its `id`. Name what you matched in the reason.

A page that fails any test is discarded and counted in `discarded_candidates`. A maintainer post that states a *change* to a contract bx uses (not just a page that owns it) is still a candidate, with the reason saying what changed — the orchestrator pins it and the docs lane evaluates it next run; this lane never writes the finding itself.

---

## lane_status definitions

`lane_status` is declared in the footer addendum; its consequence for `community_checked_at` is lane-contract.md §7. For this lane the values mean:

| Value | Meaning |
|---|---|
| `ok` | All queries executed without error AND every attempted fetch succeeded. Zero results, or results that all failed qualification, are still `ok` — the lane ran; use `scan_note`. |
| `degraded` | At least one query or fetch succeeded but ≥1 query or fetch FAILED WITH AN ERROR. Candidates found are trustworthy; coverage is partial. |
| `unavailable` | Every query failed with an error, OR queries succeeded but every attempted fetch failed. Only the sentinel is emitted. |

These states are mutually exclusive: `ok` requires zero errors; `degraded` requires at least one success AND at least one error; `unavailable` requires total failure.

---

## Output

`findings: []` — always, on every non-sentinel run. The candidates go in the footer:

```
allowlist_candidates: [<canonical url> — <contract it owns> · <bx token or bx:pain/<id> that depends on it> · <one-line reason>, ...]   # [] when none
```

Each candidate is one line in that shape; the orchestrator renders them in the report's Section 3 and offers each as a new allowlist row in `--fix` (`fix-mode-evolve.md`, *Allowlist candidates*). The `<contract it owns>` phrase becomes the row's "Capability area" column, so write it as the allowlist table writes its own: the thing the page defines, in the plugin's words.

---

## lane_unavailable degenerate finding

When every query failed with an error, or every fetch failed, emit ONLY the sentinel of lane-contract.md §8 with `finding_id: "lane-unavailable-community"`, `tier: "community"`, `severity: "low"` (a missing discovery lane is not urgent — the two official sentinels are `high`), `upstream_delta: "<verbatim errors from each failed WebSearch and WebFetch call>"` and `proposed_edit: "Re-run /bx:evolve when network is available, or pass --no-community to skip this lane; community_checked_at was NOT advanced."`. Set `lane_status: unavailable`.

---

## Hard rules

lane-contract.md §9 applies where it can (zero results never silent, per-failure disclosure, official-source handoff, no restated algorithms). This lane adds:

- **No findings, ever.** `findings` is `[]` or the single sentinel. A contract change you discover is a candidate with a reason, not a finding; the lane that owns the source evaluates it after the page is pinned.
- **Official domains only.** Nothing outside `code.claude.com`, `docs.claude.com`, `anthropic.com` and `github.com/anthropics/` is fetched.
- **Never a pinned page.** Read the allowlist first; canonicalize before comparing.
- **The dependency is grepped, not assumed.** Every candidate names the bx token or pain id that depends on the page.

---

## Final output addendum

After `findings: []` (or after the single sentinel), append the shared keys of lane-contract.md §10 (`lane_status`, `allowlist_candidates`, `scan_note`, `discarded_findings` — always 0 here) plus this lane's own:

```
searches_run: <n>/3
pages_fetched: <n>/5
pages_failed: [<url>: <error>, ...]         # empty list [] if all fetches succeeded
searches_failed: [<query>: <error>, ...]    # empty list [] if no query failed with an error
discarded_candidates: <fetched pages that failed Step 4, or 0>
```

`scan_note` uses for this lane: zero results on a clean run, every result already pinned, `cap_reached: <n> unfetched`, a maintainer thread kept for a specific comment.
