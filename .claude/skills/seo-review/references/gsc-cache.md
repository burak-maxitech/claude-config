# GSC API Response Cache — TTL Policy + Wrapper

Loaded by the orchestrator (Step 1.6) when fetching GSC API responses. Caches **Search Analytics** (Q1/Q2/Q3) and **URL Inspection** responses to disk so reruns within the TTL window don't burn API quota. The **auth probe** (sites.list) is **not cached** — it's the live mode-detection check and must reflect current API reachability on every run.

For curl invocation templates (request bodies, headers, post-processing), see `gsc-api-queries.md`. For schema + quota model, see `gsc-api-schema.md`.

---

## Why cache

URL Inspection has a strict **2,000-calls/day per-property quota**. A single `/seo-review` run uses up to 100. Iterating on a fix and rerunning the audit 3-5 times in a session can chew through quota that the next run will need. Search Analytics has a more generous 1,200 QPM but still benefits from cache-hit speed (faster total wall time on rerun).

GSC's own data freshness ceiling is **~2 days** (Search Analytics has a 2-day finalization lag; URL Inspection reflects Google's most recent crawl, which also moves slowly). Reruns within that window can't yield fresher data from upstream — caching for ~24h trades zero data freshness for guaranteed quota savings.

---

## TTL policy

**Default TTL: 24 hours** (86400 seconds).

Rationale:
- Aligns with GSC's own data refresh cadence (no upstream change within the same calendar day).
- Same-day reruns hit cache → zero quota cost on iteration.
- Next-day reruns get fresh data when GSC has fresh data anyway.
- Stale entries auto-expire on next run's TTL check; no manual eviction needed for correctness.

**Override at the run level** with `--no-cache` (Step 2 Mode Dispatch). The flag forces every call to skip the cache lookup and refetch. Fresh responses are still written to cache after the bypass run, so subsequent runs without `--no-cache` benefit from the refresh.

**TTL is not user-configurable per-run.** Adding a `--cache-ttl <hours>` flag would invite footgun configurations (sub-hour TTL defeats the point; week-long TTL hides stale data); 24h is the only sensible default. If a use case for tunable TTL surfaces later, revisit.

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
- Per-URL caching means partial cache hits across a 100-URL batch are common (e.g., 80 URLs cached from yesterday's run + 20 new URLs from today's git-changed paths → 80 cache hits, 20 fresh calls).

---

## Cache wrapper (per-call inline bash)

Each curl call uses a wrapper that checks cache, falls through on miss, and writes atomically. Single bash invocation per call so the orchestrator can fire N parallel cache-or-curl calls in one tool-use block:

```bash
CACHE_FILE=".seo-data/gsc/cache/<prefix>-<hash>.json"
TTL_MIN=1440  # 24 hours in minutes

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

At the start of Step 1.6 (after mode detection, before fetch dispatch), prune cache entries older than **7 days**:

```bash
find .seo-data/gsc/cache -type f -mtime +7 -delete 2>/dev/null
```

Rationale:
- TTL is 24h, so entries older than 24h are already cache-misses by lookup time.
- 7-day retention catches the long-tail rerun case (user reruns same audit a week later → entries auto-expire instead of accumulating forever).
- `find -mtime +7` is broadly portable across GNU + BSD + MSYS `find` (same family as the wrapper's `-mmin -N` TTL check).
- `-delete` is safer than `-exec rm` (no race window) and supported on both `find` flavors.
- `2>/dev/null` swallows the "directory not found" warning when cache dir doesn't exist yet (first run).
- No `-name "*.json"` filter — the cache dir is skill-owned and only contains `<prefix>-<hash>.json` plus transient `<...>.tmp.$$` files from interrupted runs. Letting prune catch both improves janitorial hygiene.

Prune is a single command, not per-file. If pruning fails (read-only filesystem, permission issue), the failure is silent and harmless — cache just doesn't grow-prune; entries still age out via the TTL check on lookup.

---

## Footer line

Step 1.6.12 footer gains a new line summarizing cache activity for the run:

```
GSC API cache: 102/103 hits (24h TTL, 1 fresh call: ui-https://example.com/new-page). Use --no-cache to force refresh.
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

The orchestrator fires Turn 2a (3 Search Analytics calls) and Turn 2b (up to 100 URL Inspection calls) as parallel batches. Each call's wrapper writes to its own `$CACHE_FILE.tmp.$$` and renames atomically — there's no shared-file contention. PID-suffixed tempfiles handle the (unlikely) case where two parallel invocations produce identical hashes.

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
| Cache stats CLI subcommand (e.g., `/seo-review --cache-stats`) | Three `ls -la` / `find -mtime` shell calls cover the same need with no skill surface area. |
| Cross-property cache sharing | Each `site_url` is part of the cache key. Multi-property aggregation is a separate feature. |
| Cache compression (gzip JSON bodies) | Cache size is small (~100KB-1MB per run); compression not worth the complexity. |
| Cache invalidation on git push / deploy | The TTL handles this naturally — 24h covers a typical commit-to-recrawl cycle. |
