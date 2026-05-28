# GSC API Response Cache — TTL Policy + Wrapper

Loaded by the orchestrator (Step 1.6) when fetching GSC API responses. Caches **Search Analytics** (Q1/Q2/Q3) and **URL Inspection** responses to disk so reruns within the TTL window don't burn API quota. The **auth probe** (sites.list) is **not cached** — it's the live mode-detection check and must reflect current API reachability on every run.

For curl invocation templates (request bodies, headers, post-processing), see `gsc-api-queries.md`. For schema + quota model, see `gsc-api-schema.md`.

---

## Why cache

URL Inspection has a strict **2,000-calls/day per-property quota**. A single `/bx:seo` run uses up to 200 (4-slice budget: 80 impressions-top + 20 git-changed + 100 shared bucket between user-supplied `known-bad-urls.txt` and sitemap-orphan). Iterating on a fix and rerunning the audit 3-5 times in a session can chew through quota that the next run will need. Search Analytics has a more generous 1,200 QPM but still benefits from cache-hit speed (faster total wall time on rerun).

GSC's own data freshness ceiling is **~2 days** (Search Analytics has a 2-day finalization lag; URL Inspection reflects Google's most recent crawl, which also moves slowly). Reruns within that window can't yield fresher data from upstream — caching for ~24h trades zero data freshness for guaranteed quota savings.

---

## TTL policy (split by call-type — codified after S34 burakarik6 dogfood)

**Two TTL tiers — different freshness needs per endpoint:**

| Cache prefix | TTL | Rationale |
|---|---|---|
| `sa-q1-*` / `sa-q2-*` / `sa-q3-*` (Search Analytics) | **24 hours** (86400 s) | Rolling-window date keys (e.g., `endDate=2026-05-27` today, `2026-05-28` tomorrow) → hash naturally invalidates day-over-day. 24h TTL aligns with GSC's own ~2-day finalization lag; cross-day reruns naturally miss because the cache key changed. Going longer would hide stale data; going shorter defeats the purpose of caching at all. |
| `ui-*` (URL Inspection per-URL) | **7 days** (604800 s) | `coverageState` is genuinely weeks-stable — a URL's "Submitted and indexed" state doesn't flip day-over-day under normal operation. The S34 burakarik6 dogfood scored 0/197 cache hits despite 85 prior cache entries from Session 71 (3 days earlier) because the original 24h TTL had expired all of them. Raising ui-* to 7d means typical 2-7-day iteration loops (the actual user pattern) benefit from cache. URLs that *did* flip state (which is exactly the signal sub-dim 14 wants to catch) are still surfaced by the snapshot-diff path independent of cache freshness. |

**Override at the run level** with `--no-cache` (Step 2 Mode Dispatch). The flag forces every call to skip the cache lookup and refetch — applies to BOTH tiers uniformly. Fresh responses are still written to cache after the bypass run, so subsequent runs without `--no-cache` benefit from the refresh.

**TTL is not user-configurable per-run.** Adding a `--cache-ttl <hours>` flag would invite footgun configurations (sub-hour TTL defeats the point; month-long TTL hides stale data); the two-tier default is the only sensible configuration. If a use case for tunable TTL surfaces later, revisit.

**Why split rather than unify at 7d for both?** Search Analytics keys shift daily anyway (rolling 90-day window) — raising sa-* TTL to 7d would produce zero additional hits (the key has already changed). It would also extend the staleness window for the rare case where GSC backfills a same-day metric correction. URL Inspection keys are stable (`site_url|url` — no date component), so longer TTL DOES help. The split matches each endpoint's actual cache-friendliness.

---

## Cache location

```
.seo-data/gsc/cache/
├── sa-q1-<hash>.json     # Search Analytics — Q1 (queries digest)
├── sa-q2-<hash>.json     # Search Analytics — Q2 (pages digest)
├── sa-q3-<hash>.json     # Search Analytics — Q3 (url_impressions_map)
├── ui-<hash>.json        # URL Inspection — one file per inspected URL
├── ...
```

Already covered by the `.gitignore` sentinel block (`.seo-data/gsc/` is fully ignored). No additional gitignore entry needed.

**Disk-write boundary entry.** The Ingestion conventions section in `SKILL.md` reserves `.seo-data/gsc/` for user config + skill-auto-generated content. The `cache/` subdirectory is one of the allowed entries under that rule (skill-auto-managed; orchestrator owns its lifecycle). Raw curl responses written elsewhere in `.seo-data/gsc/` still violate the boundary — use system temp (`mktemp`) for ephemeral parsing buffers.

**Distinction from `snapshots/`.** `.seo-data/gsc/snapshots/` is a SIBLING directory with a different purpose and retention policy — do not confuse the two:

| | `cache/` | `snapshots/` |
|---|---|---|
| Purpose | Same-day quota savings (avoid refetching API responses) | Longitudinal coverage-state history (regression detection) |
| Retention | 7 days (auto-prune) | 30 days (auto-prune) |
| TTL on read | 24h for `sa-*` / 7d for `ui-*` (cache hit/miss decision; see "TTL policy" above) | None (every snapshot is read on demand for diff) |
| Files | `sa-q{1,2,3}-<hash>.json` + `ui-<hash>.json` (raw API responses) | `<YYYY-MM-DDTHHMMSS>-<commit_sha7>.json` (orchestrator-aggregated `{url: coverageState}` map + metadata) |
| Managed by | This file's cache wrapper | `references/gsc-ingestion.md` sub-dim 14 + `SKILL.md` Step 1.6.13 |
| Reproducible | Yes (from API on demand) | Yes (from cache files on the same run) |

Both subdirectories live under `.seo-data/gsc/` and are covered by the same `.gitignore` sentinel block. The orchestrator pre-creates both in Turn 1's batch.

---

## Cache key strategy

Cache key inputs vary per call type. The key is `sha1` of a deterministic concatenation of input fields.

### Search Analytics (Q1, Q2, Q3)

```
key_input = "<site_url>|<endDate>|<startDate>|<dimensions>|<rowLimit>|<type>"
hash      = sha1(key_input)
filename  = "sa-<q_tag>-<hash>.json"     # q_tag ∈ {q1, q2, q3}
```

- `site_url` distinguishes properties when a user audits multiple repos.
- `endDate` (today) and `startDate` (today − lookback_days) shift daily — the hash naturally invalidates day-over-day even within a 7-day cache window. Same-day reruns produce the same hash → cache hit.
- `dimensions` / `rowLimit` / `type` are constants per Q-call but included for forward-compat if the templates change.

Q1 vs Q2 vs Q3 use distinct file prefixes (`sa-q1-`, `sa-q2-`, `sa-q3-`) even though Q2 + Q3 share the same request body today, so each Q-call has its own cache slot. Decouples cache hits if one Q-call is later parameterized differently.

### URL Inspection (one entry per URL)

```
key_input = "<site_url>|<inspection_url>"
hash      = sha1(key_input)
filename  = "ui-<hash>.json"
```

- `site_url` + `inspection_url` are the only inputs to the API call. `languageCode` is fixed at `en` per the template.
- Per-URL caching means partial cache hits across a 200-URL batch are common (e.g., 180 URLs cached from yesterday's run + 20 new URLs from today's git-changed paths or newly-listed sitemap entries → 180 cache hits, 20 fresh calls).

---

## Cache wrapper (per-call inline bash — Turn 2a Search Analytics only)

**Scope:** This wrapper is the canonical dispatch for **Search Analytics** (Q1/Q2/Q3) calls in Turn 2a. URL Inspection (Turn 2b) uses a DIFFERENT dispatch — a single Bash invocation of `gsc-parse-helper.py inspect-batch`, which parallelizes via Python's `ThreadPoolExecutor` and applies the same cache key + TTL + atomic-write contract internally. See SKILL.md Step 1.6.6 Turn 2b for the helper invocation; the helper's cache logic matches what's described here so `ui-*.json` files written by either path are mutually consumable. The boundary-violation history (S31 cont.², S34) makes the helper-driven dispatch the only sanctioned path for URL Inspection — never re-introduce per-URL Bash-curl loops.

Each Q1/Q2/Q3 call uses a wrapper that checks cache, falls through on miss, and writes atomically. Single bash invocation per call so the orchestrator can fire 3 parallel cache-or-curl calls in one tool-use block:

```bash
CACHE_FILE=".seo-data/gsc/cache/<prefix>-<hash>.json"
# TTL by prefix — sa-* is 24h (rolling date keys shift daily anyway);
# ui-* is 7d (coverageState is weeks-stable). See "TTL policy" above.
case "$CACHE_FILE" in
  *.seo-data/gsc/cache/sa-*) TTL_MIN=1440   ;;  # 24h
  *.seo-data/gsc/cache/ui-*) TTL_MIN=10080  ;;  # 7d
  *)                         TTL_MIN=1440   ;;  # default: 24h
esac

# Cache hit check (skipped when NO_CACHE=1).
# `find -mmin -N` matches files modified in the last N minutes — portable across
# GNU/BSD/MSYS find. Empty output (no match) means miss; any output means hit.
if [ "$NO_CACHE" != "1" ] && [ -n "$(find "$CACHE_FILE" -mmin "-$TTL_MIN" 2>/dev/null)" ]; then
  echo "CACHE_STATUS:HIT"
  cat "$CACHE_FILE"
  exit 0
fi

# Cache miss → fresh curl, atomic write on 200
TMP="$CACHE_FILE.tmp.$$"
HTTP_STATUS=$(curl -s -w '%{http_code}' -o "$TMP" -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "x-goog-user-project: $QUOTA_PROJECT" \
  -H "Content-Type: application/json" \
  -d "$BODY" \
  "$URL")

echo "CACHE_STATUS:MISS http=${HTTP_STATUS}"

if [ "$HTTP_STATUS" = "200" ]; then
  mv "$TMP" "$CACHE_FILE"   # atomic — partial writes can't corrupt cache
  cat "$CACHE_FILE"
else
  cat "$TMP"                # surface error body to orchestrator for parsing
  rm -f "$TMP"              # do NOT cache non-200 responses
fi
```

### Wrapper invariants

1. **Atomic write.** Always write to `$CACHE_FILE.tmp.$$` then `mv` to final path on success. Mid-write interruption can't corrupt cache (next run sees either old-good or no file, never half-written).
2. **Skip cache on non-200.** Error responses (quota exhausted, auth fail, 4xx site-config issue) are NEVER cached — caching a 403 would lock the run into heuristic mode for 24h after fixing the auth.
3. **TTL check via `find -mmin`** (not `stat`). `stat -c` / `stat -f` flags diverge across GNU + BSD, and on Windows MSYS the chained fallback can silently degrade every call to a cache miss. `find -mmin -N` is one flag that works the same across GNU + BSD + MSYS — same family of `find` flags used by the eviction step. Trade-off: `find` runs a subprocess per call, ~2-5ms slower than `stat`; acceptable given parallel dispatch amortizes it.
4. **Cache dir is pre-created in Step 1.6.1.** The wrapper does NOT `mkdir -p` per call — `SKILL.md` Turn 1 batch creates `.seo-data/gsc/cache` before dispatch. Skipping ~100 redundant `mkdir` syscalls per run.
5. **Status line on stdout before body.** Orchestrator parses the first line (`CACHE_STATUS:HIT` or `CACHE_STATUS:MISS http=200`) for the footer summary, then treats the rest of stdout as the JSON response body.

### Wrapper variables

The orchestrator substitutes before invocation:

| Variable | Source | Example |
|---|---|---|
| `<prefix>-<hash>` | Per-call, computed from cache key inputs (above) | `sa-q1-a1b2c3...` |
| `$TOKEN` | Turn 1 probe output | (1-hour ADC token) |
| `$QUOTA_PROJECT` | Turn 1 probe output | `my-gcp-project` |
| `$BODY` | Per-call JSON body from `gsc-api-queries.md` | — |
| `$URL` | Per-call endpoint URL with site_url substituted | — |
| `$NO_CACHE` | `1` when `--no-cache` flag passed, else unset | `1` or empty |

---

## Eviction policy

At the start of Step 1.6 (after mode detection, before fetch dispatch), prune cache entries:

```bash
# Two prunes for the two TTL tiers — keep at the eviction window matching the
# longest active TTL so we don't delete files that the per-prefix TTL check
# would still consider fresh.
find .seo-data/gsc/cache -type f -name 'sa-*' -mtime +7  -delete 2>/dev/null   # sa-* age cap: 7d (1d TTL + 6d slack)
find .seo-data/gsc/cache -type f -name 'ui-*' -mtime +14 -delete 2>/dev/null   # ui-* age cap: 14d (7d TTL + 7d slack)
find .seo-data/gsc/cache -type f ! -name 'sa-*' ! -name 'ui-*' -mtime +7 -delete 2>/dev/null   # janitorial: orphaned .tmp.$$ + future prefixes
```

Rationale:
- TTL gates the cache-hit decision at lookup time (24h for sa-*, 7d for ui-*). Eviction is the secondary janitor.
- Slack between TTL and eviction prevents thrash: if a cache entry is at TTL boundary (e.g., 23h59m old) when the run starts, eviction shouldn't delete it before the lookup check has a chance to use it.
- `ui-*` eviction at 14d catches the long-tail rerun case (user reruns same audit two weeks later → entries auto-expire instead of accumulating).
- `sa-*` eviction at 7d is tighter — rolling-window keys mean entries past 7d are guaranteed stale-by-key anyway; no point keeping them.
- `find -mtime +7` is broadly portable across GNU + BSD + MSYS `find` (same family as the wrapper's `-mmin -N` TTL check).
- `-delete` is safer than `-exec rm` (no race window) and supported on both `find` flavors.
- `2>/dev/null` swallows the "directory not found" warning when cache dir doesn't exist yet (first run).
- No `-name "*.json"` filter — the cache dir is skill-owned and only contains `<prefix>-<hash>.json` plus transient `<...>.tmp.$$` files from interrupted runs. Letting prune catch both improves janitorial hygiene.

Prune is a single command, not per-file. If pruning fails (read-only filesystem, permission issue), the failure is silent and harmless — cache just doesn't grow-prune; entries still age out via the TTL check on lookup.

---

## Footer line

Step 1.6.12 footer gains a new line summarizing cache activity for the run:

```
GSC API cache: 102/103 hits (split TTL: 24h on sa-*, 7d on ui-*; 1 fresh call: ui-https://example.com/new-page). Use --no-cache to force refresh.
```

Construction:
- **N/M hits** — count of `CACHE_STATUS:HIT` responses / total API calls dispatched this run.
- **Fresh call list** — when 1-5 fresh calls, list them by file prefix (e.g., `sa-q1`, `ui-https://...`); when >5, summarize as `N fresh calls`.
- **`--no-cache` reminder** — always present so the user knows the bypass is available.

When `gsc_mode: disabled`: the line is omitted (no cache activity).

When `--no-cache` was passed: render as
```
GSC API cache: 0/103 hits (--no-cache bypass; all responses refetched + cache rewritten for next run).
```

The cache stats line sits between the "URL Inspection: N/M attempted" line and the "Search Analytics rows" line in the footer order.

---

## Concurrency

The orchestrator fires Turn 2a (3 Search Analytics calls) and Turn 2b (up to 200 URL Inspection calls) as parallel batches. Each call's wrapper writes to its own `$CACHE_FILE.tmp.$$` and renames atomically — there's no shared-file contention. PID-suffixed tempfiles handle the (unlikely) case where two parallel invocations produce identical hashes.

---

## What's NOT cached

| Call | Why not |
|---|---|
| **Auth probe** (`sites.list` in Turn 1) | This is the live mode-detection check. Caching it would let a stale "API enabled" state mask a broken auth (token expired, scope revoked, property unverified). The probe is one cheap call — keep it live. |
| **Per-run error responses** | A 403/429/500 isn't useful to cache. Subsequent runs should retry. |
| **Best-practices brief** (Step 1 WebSearch + WebFetch) | Different cache domain (web search results, not GSC quota). Out of scope here. |

---

## Manual cache management

The cache is skill-managed; users shouldn't normally touch it. For edge cases:

**Force a single signal refetch** without a full `--no-cache` run:
```bash
rm .seo-data/gsc/cache/sa-q1-*.json     # next run refetches Q1 only
```

**Nuke the whole cache**:
```bash
rm -rf .seo-data/gsc/cache/             # next run is full-fresh; safe — cache is reproducible from API
```

**Inspect cache age**:
```bash
ls -la .seo-data/gsc/cache/
```

These are not orchestrator-invoked workflows — the user runs them when needed. The skill itself never deletes cache outside the 7-day prune step.

---

## Future considerations (deferred)

| Capability | Why deferred |
|---|---|
| Per-call TTL override (`--cache-ttl <h>` flag) | One default TTL is the right ergonomics until a real use case surfaces. |
| Cache stats CLI subcommand (e.g., `/bx:seo --cache-stats`) | Three `ls -la` / `find -mtime` shell calls cover the same need with no skill surface area. |
| Cross-property cache sharing | Each `site_url` is part of the cache key. Multi-property aggregation is a separate feature. |
| Cache compression (gzip JSON bodies) | Cache size is small (~100KB-1MB per run); compression not worth the complexity. |
| Cache invalidation on git push / deploy | The TTL handles this naturally — 24h covers a typical commit-to-recrawl cycle. |
