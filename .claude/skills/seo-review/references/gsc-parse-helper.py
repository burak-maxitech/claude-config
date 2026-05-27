#!/usr/bin/env python3
"""GSC API response parser — stable helper script for /seo-review orchestrator.

Replaces inline Python heredocs that proved fragile across the S31 dogfood:
- Different quoting strategies per call risk bash parser failures
- One failure cancelled parallel calls (Q2/Q3 cancelled when Q1 died)
- Disk-write boundary violations when bash heredoc EOF errors forced
  the orchestrator to write `_parse_clusters.py` into `.seo-data/gsc/cache/`

Invoke once per parse operation. UTF-8 enforced via `# -*- coding: utf-8 -*-`
header + explicit `encoding='utf-8'` on every `open()`. Works regardless of
shell's PYTHONIOENCODING setting.

USAGE
-----
    python gsc-parse-helper.py <subcommand> <cache_file> [options]

Subcommands:
    q1 <path>         Parse Q1 (queries digest, position-band 5-20, imp >= 100)
    q2 <path>         Parse Q2 (pages digest, top-50 by impressions, imp >= 10)
    q3 <path>         Parse Q3 (full url_impressions_map, no client-side cap)
    clusters <dir>    Parse all ui-*.json in cache dir into coverageState clusters
    ctr <path>        Compute median CTR + ctr_opportunity findings from Q2
    brand <q1_path> <brand_name>
                      Sub-dim 13 brand-query anomaly detection
    snapshot-write <cache_dir> <run_ts> <commit_sha> <site_url> <output_path>
                      Sub-dim 14 — write a snapshot of {url: coverageState} from
                      ui-*.json files in cache_dir, wrapped with metadata.
                      Atomic write via .tmp + os.replace.
    regression <current_snapshot> <previous_snapshot>
                      Sub-dim 14 — diff two snapshots, emit transitions +
                      path_clusters + count_deltas (machine-parseable lines).
    inspect-batch <cache_dir> <site_url> <urls_file>
                      Turn 2b URL Inspection dispatch — parallel HTTP via
                      ThreadPoolExecutor (20 workers), per-URL cache check
                      (7d TTL on ui-* — coverageState is weeks-stable), atomic
                      write via .tmp + os.replace, never caches non-200.
                      Reads GCLOUD_TOKEN + GCLOUD_QUOTA_PROJECT from env;
                      NO_CACHE=1 bypasses cache lookup (writes still happen).
                      Replaces the prior "N parallel Bash curl calls" spec —
                      closes the S31cont.²+S34 boundary-violation pattern.
    history-update <findings_jsonl> <history_path> <commit_sha> <run_date>
                      Group D: read newline-delimited finding objects, hash by
                      sub_dim+location, update finding-history.json's run_count
                      + first_seen + last_seen. Emit per-finding run_count to
                      stdout so the orchestrator can append escalation hints.
    watchpoint-emit <findings_jsonl> <watchpoints_path> <commit_sha> <run_date>
                      Group D: scan findings for code_changed_since_gsc_window=
                      true, auto-emit watchpoint entries with expected_recheck_
                      date = applied_date + 21 days (typical GSC pipeline lag).
    watchpoint-check <watchpoints_path> <q2_pages_path> <run_date>
                      Group D: at run start, scan watchpoints; for any past
                      recheck date with current GSC data available, compare
                      baseline vs current metric. Emit machine-parseable lines
                      for the orchestrator to render as top-level banners.
                      Also auto-evicts watchpoints > 90 days old.

All subcommands print:
    <metric>:<value>          # one per line, machine-parseable
    --- <section> ---         # human-readable section separators
    <records>                 # data lines, format documented per subcommand

Exit codes:
    0   success (incl. zero findings)
    1   file not found / unreadable
    2   JSON parse error
    3   unknown subcommand / bad arguments
"""
# -*- coding: utf-8 -*-
import json
import os
import sys
import glob
import hashlib
import time
import urllib.request
import urllib.error
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from urllib.parse import urlparse


def load_json(path):
    """Open with explicit UTF-8 encoding — survives Windows charmap default,
    Turkish characters, and the GSC prompt-injection garbage queries."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse failed for {path}: {e}", file=sys.stderr)
        sys.exit(2)


def parse_q1(path):
    """Q1 (queries digest): keep rows with impressions >= 100 AND
    position between 5.0 and 20.0 (the position-band opportunity zone)."""
    data = load_json(path)
    rows = data.get('rows', [])
    print(f"rows_received:{len(rows)}")
    print(f"rowLimit_requested:25000")
    filt = [r for r in rows
            if r.get('impressions', 0) >= 100
            and 5.0 <= r.get('position', 0) <= 20.0]
    filt.sort(key=lambda r: -r['impressions'])
    top = filt[:50]
    print(f"q1_position_band_5_20_imp_100plus:{len(top)}")
    print("--- top queries ---")
    for r in top[:30]:
        key = r['keys'][0]
        print(f"  {key} | imps={r['impressions']} clicks={r['clicks']} "
              f"ctr={r['ctr']:.4f} pos={r['position']:.2f}")


def parse_q2(path):
    """Q2 (pages digest): impressions >= 10, sort desc, take top 50.
    Also computes median CTR for sub-dim 10 ctr_opportunity threshold."""
    data = load_json(path)
    rows = data.get('rows', [])
    print(f"rows_received:{len(rows)}")
    print(f"rowLimit_requested:25000")
    filt = [r for r in rows if r.get('impressions', 0) >= 10]
    filt.sort(key=lambda r: -r['impressions'])
    top = filt[:50]
    print(f"q2_filtered_top:{len(top)}")

    if top:
        ctrs = sorted([r['ctr'] for r in top])
        n = len(ctrs)
        median = ctrs[n // 2] if n % 2 else (ctrs[n // 2 - 1] + ctrs[n // 2]) / 2
        print(f"q2_median_ctr:{median:.6f}")
        print(f"q2_ctr_threshold_subdim10:{median * 0.5:.6f}")

    print("--- top pages ---")
    for r in top:
        key = r['keys'][0]
        print(f"  {key} | imps={r['impressions']} clicks={r['clicks']} "
              f"ctr={r['ctr']:.4f} pos={r['position']:.2f}")


def parse_q3(path):
    """Q3 (full url_impressions_map): no client-side cap, all URLs with imp >= 1.
    Used for traffic_weight ranking + URL Inspection budget selection."""
    data = load_json(path)
    rows = data.get('rows', [])
    print(f"rows_received:{len(rows)}")
    print(f"rowLimit_requested:25000")
    filt = [r for r in rows if r.get('impressions', 0) >= 1]
    filt.sort(key=lambda r: -r['impressions'])
    print(f"url_impressions_map_size:{len(filt)}")
    print("--- top 80 by impressions (URL Inspection candidates) ---")
    for r in filt[:80]:
        key = r['keys'][0]
        print(f"  {key} | imps={r['impressions']}")


def parse_ctr_opportunities(path):
    """sub-dim 10 ctr_opportunity: find pages where CTR is catastrophically low.

    Dual trigger (S31 dogfood fix):
    1. Standard band: position 5-20 AND ctr < median*0.5 AND imp >= 500
    2. High-volume override: imp >= 10000 AND ctr < 0.005 (regardless of position)
       — catches the smartphone-vs-mirrorless-2026 case (59,679 imp @ pos 4.65 @ 0.28% CTR)
       that the original trigger excluded."""
    data = load_json(path)
    rows = data.get('rows', [])
    filt = [r for r in rows if r.get('impressions', 0) >= 10]
    filt.sort(key=lambda r: -r['impressions'])
    top = filt[:50]

    if not top:
        print("q2_median_ctr:0")
        print("ctr_opportunities:0")
        return

    ctrs = sorted([r['ctr'] for r in top])
    n = len(ctrs)
    median = ctrs[n // 2] if n % 2 else (ctrs[n // 2 - 1] + ctrs[n // 2]) / 2
    threshold = median * 0.5

    print(f"q2_median_ctr:{median:.6f}")
    print(f"q2_ctr_threshold_subdim10:{threshold:.6f}")

    opportunities = []
    for r in top:
        url = r['keys'][0]
        imp = r['impressions']
        ctr = r['ctr']
        pos = r['position']
        # Standard band: pos 5-20 AND below median/2 threshold
        in_band = 5.0 <= pos <= 20.0 and imp >= 500 and ctr < threshold
        # High-volume override: catastrophic CTR regardless of position
        high_vol_anomaly = imp >= 10000 and ctr < 0.005
        if in_band or high_vol_anomaly:
            reason = 'high_volume_anomaly' if high_vol_anomaly else 'position_band'
            opportunities.append({
                'url': url, 'imp': imp, 'ctr': ctr, 'pos': pos, 'reason': reason
            })

    print(f"ctr_opportunities:{len(opportunities)}")
    print("--- opportunities ---")
    for o in opportunities[:10]:
        print(f"  [{o['reason']}] {o['url']} | imps={o['imp']} "
              f"ctr={o['ctr']:.4f} pos={o['pos']:.2f}")


def cluster_for(coverage, fetch):
    """coverageState + pageFetchState -> sub-dim cluster (see gsc-api-queries.md
    lookup table). Returns one of:
    submitted_indexed, crawled_not_indexed, discovered_not_indexed,
    not_found_404, redirect_hygiene, canonical_conflict, blocked_access,
    soft_404, server_errors, unknown_to_google, other"""
    c = (coverage or '').strip().lower()
    f = (fetch or '').strip().upper()
    if 'submitted and indexed' in c:
        return 'submitted_indexed'
    if 'crawled' in c and 'not indexed' in c:
        return 'crawled_not_indexed'
    if 'discovered' in c and 'not indexed' in c:
        return 'discovered_not_indexed'
    if 'not found' in c or f == 'NOT_FOUND':
        return 'not_found_404'
    if 'redirect' in c or f == 'REDIRECT_ERROR':
        return 'redirect_hygiene'
    if 'duplicate' in c or 'canonical' in c:
        return 'canonical_conflict'
    if 'blocked' in c or 'noindex' in c or 'excluded' in c or f in ('BLOCKED_ROBOTS_TXT', 'ACCESS_FORBIDDEN', 'BLOCKED_4XX'):
        return 'blocked_access'
    if 'soft 404' in c or f == 'SOFT_404':
        return 'soft_404'
    if 'server error' in c or f == 'SERVER_ERROR':
        return 'server_errors'
    if 'unknown' in c:
        return 'unknown_to_google'
    return 'other'


def parse_clusters(cache_dir):
    """Aggregate all ui-*.json in cache_dir into sub-dim clusters."""
    pattern = os.path.join(cache_dir, 'ui-*.json')
    files = sorted(glob.glob(pattern))
    print(f"inspected_count:{len(files)}")

    clusters = defaultdict(list)
    other_states = []  # unmapped coverage states for footer audit

    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

        result = data.get('inspectionResult', {}).get('indexStatusResult', {})
        coverage = result.get('coverageState', '')
        fetch = result.get('pageFetchState', '')
        cluster = cluster_for(coverage, fetch)

        url = data.get('inspectionUrl') or ''
        # Carry per-URL diagnostics for cluster findings
        evidence = {
            'url': url,
            'coverage_state': coverage,
            'fetch_state': fetch,
            'last_crawl_time': result.get('lastCrawlTime', ''),
            'google_canonical': result.get('googleCanonical', ''),
            'user_canonical': result.get('userCanonical', ''),
            'crawled_as': result.get('crawledAs', ''),
            'indexing_state': result.get('indexingState', ''),
        }
        clusters[cluster].append(evidence)
        if cluster == 'other':
            other_states.append(f"{coverage} | {fetch}")

    print("--- cluster_counts ---")
    for cluster, urls in sorted(clusters.items(), key=lambda x: -len(x[1])):
        print(f"  {cluster}: {len(urls)}")

    if other_states:
        print("--- unmapped_coverage_states (footer audit) ---")
        for s in set(other_states):
            print(f"  {s}")

    # Emit cluster details for findings (sample top 10 by last_crawl_time)
    print("--- cluster_details ---")
    for cluster, urls in clusters.items():
        if cluster == 'submitted_indexed':
            continue  # Healthy state; no finding
        # Sort by last_crawl_time desc (most recent first)
        urls_sorted = sorted(urls, key=lambda u: u.get('last_crawl_time', ''), reverse=True)
        top = urls_sorted[:10]
        print(f"## cluster={cluster} total_count={len(urls)}")
        for u in top:
            print(f"  url={u['url']} | last_crawl={u['last_crawl_time']} | "
                  f"google_canonical={u['google_canonical']} | "
                  f"user_canonical={u['user_canonical']}")


def detect_brand_anomaly(q1_path, brand_name):
    """sub-dim 13 brand_query_anomaly (S31 dogfood fix).

    Brand queries SHOULD rank at position 1 with CTR >30%. When a query matching
    the project's brand/author name (from CLAUDE.md or Schema Person.name) ranks
    worse than pos 3 OR has CTR < 0.10 (10%), flag it as an entity-recognition
    deficit. Cross-link to Person @id/sameAs Wikidata findings."""
    data = load_json(q1_path)
    rows = data.get('rows', [])
    brand_lower = brand_name.lower()
    matches = []
    for r in rows:
        query = r['keys'][0].lower()
        # Substring match — catches "burak arık" matching "burak arık fotografçı"
        if brand_lower in query:
            matches.append(r)

    print(f"brand_name:{brand_name}")
    print(f"brand_query_matches:{len(matches)}")

    anomalies = []
    for r in matches:
        if r['position'] > 3.0 or r['ctr'] < 0.10:
            anomalies.append(r)

    print(f"brand_anomalies:{len(anomalies)}")
    print("--- brand anomalies ---")
    for r in anomalies:
        print(f"  query='{r['keys'][0]}' pos={r['position']:.2f} "
              f"ctr={r['ctr']:.4f} imps={r['impressions']}")


def snapshot_write(cache_dir, run_timestamp, commit_sha, site_url, output_path):
    """sub-dim 14 step 1.6.13.1 — write current run's snapshot.

    Walks all ui-*.json in cache_dir, extracts {inspectionUrl: coverageState},
    wraps with metadata, writes atomically (tmp + os.replace).

    Output schema:
        {
          "run_timestamp": "2026-05-26T143200",
          "commit_sha": "5a441d1",
          "site_url": "sc-domain:burakarik.com",
          "inspection_count": 194,
          "inspections": {
            "<url>": "<coverageState>",
            ...
          }
        }

    Atomic via os.replace — partial-write interrupts can't leave half-written
    snapshot files that would corrupt the next run's regression diff."""
    pattern = os.path.join(cache_dir, 'ui-*.json')
    files = sorted(glob.glob(pattern))

    inspections = {}
    for fp in files:
        try:
            with open(fp, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            continue

        result = data.get('inspectionResult', {}).get('indexStatusResult', {})
        url = data.get('inspectionUrl') or ''
        coverage = result.get('coverageState', '')
        if url:
            inspections[url] = coverage

    snapshot = {
        'run_timestamp': run_timestamp,
        'commit_sha': commit_sha,
        'site_url': site_url,
        'inspection_count': len(inspections),
        'inspections': inspections,
    }

    # Delegate to _atomic_write_json — single source of atomic-write truth
    # (PID-suffixed tmp, parent-mkdir, OSError handling). _code-review
    # finding #15: previously this function had its own inline atomic-write
    # block that drifted from _atomic_write_json's contract.
    print(f"inspection_count:{len(inspections)}")
    if not _atomic_write_json(output_path, snapshot):
        print(f"snapshot_write_failed:{output_path}")
        sys.exit(1)
    print(f"snapshot_written:{output_path}")


def classify_transition(cur_state_lower):
    """Map current coverageState (lowercased) to transition class for severity calc.

    Class priority for sort (lower number = higher priority in report ordering):
        0  server_error    — availability regression (always critical)
        1  broken_url      — 404
        2  redirect        — Page with redirect (burakarik6 pattern)
        3  canonical       — Google chose different canonical
        4  quality         — Crawled - not indexed (E-E-A-T signal)
        5  crawl_budget    — Discovered - not indexed
        6  rendering       — Soft 404
        7  access          — 403 / blocked (often intentional)
        8  other           — unmapped state
    """
    if 'server error' in cur_state_lower or '5xx' in cur_state_lower:
        return 'server_error'
    # Parens are load-bearing: without them `and` would bind tighter than `or`,
    # and the 'soft' guard would protect only the '404' branch, letting a state
    # like 'Soft 404 (not found...)' fall through to broken_url instead of the
    # rendering bucket. _code-review finding #5._
    if ('not found' in cur_state_lower or '404' in cur_state_lower) and 'soft' not in cur_state_lower:
        return 'broken_url'
    if 'redirect' in cur_state_lower:
        return 'redirect'
    if 'duplicate' in cur_state_lower or 'canonical' in cur_state_lower:
        return 'canonical'
    if 'crawled' in cur_state_lower and 'not indexed' in cur_state_lower:
        return 'quality'
    if 'discovered' in cur_state_lower and 'not indexed' in cur_state_lower:
        return 'crawl_budget'
    if 'soft 404' in cur_state_lower:
        return 'rendering'
    if 'blocked' in cur_state_lower or '403' in cur_state_lower or 'noindex' in cur_state_lower:
        return 'access'
    return 'other'


def compute_path_clusters(urls):
    """Group URLs by path prefix (1-3 leading segments).

    Returns up to 3 (prefix, count) tuples where count >= 3, sorted desc by count.

    Path prefix construction: for each URL, generate 1, 2, and 3-segment prefixes,
    increment a counter per prefix. Top 3 clusters by count, filtered to count >= 3.

    Example: /en/photo/foo, /en/photo/bar, /en/photo/baz, /en/gallery/qux yield:
        /en/* → 4
        /en/photo/* → 3
        /en/gallery/* → 1 (filtered out, < 3)
    Result: [(/en/*, 4), (/en/photo/*, 3)]"""
    prefix_counts = defaultdict(int)
    for url in urls:
        try:
            path = urlparse(url).path
        except Exception:
            continue
        if not path or path == '/':
            continue
        segs = [s for s in path.split('/') if s]
        for n in (1, 2, 3):
            if len(segs) >= n:
                prefix = '/' + '/'.join(segs[:n]) + '/*'
                prefix_counts[prefix] += 1

    # Filter count >= 3 and take top 3
    sorted_clusters = sorted(prefix_counts.items(), key=lambda x: -x[1])
    return [(p, c) for p, c in sorted_clusters if c >= 3][:3]


def regression(current_path, previous_path):
    """sub-dim 14 step 1.6.13.3 — diff two snapshots, emit transitions + clusters.

    Compares {url: coverageState} maps between current and previous snapshots.
    Emits:
      - transitions: URLs whose state flipped (positive or negative)
      - path_clusters: top 3 path-prefix groupings of transition URLs
      - count_deltas: per-coverageState count changes across the full inspection set
      - recoveries: count of any-non-indexed → indexed transitions (info-only)

    Negative transitions (indexed → anything-non-indexed) are the primary signal —
    these are what trigger the sub-dim 14 finding."""
    cur = load_json(current_path)
    prev = load_json(previous_path)

    cur_inspections = cur.get('inspections', {})
    prev_inspections = prev.get('inspections', {})

    transitions = []
    no_change_count = 0
    recoveries = 0

    for url, current_state in cur_inspections.items():
        if url not in prev_inspections:
            continue  # new URL this run; no transition data
        previous_state = prev_inspections[url]
        if previous_state == current_state:
            no_change_count += 1
            continue

        prev_lower = (previous_state or '').strip().lower()
        cur_lower = (current_state or '').strip().lower()

        prev_was_indexed = 'submitted and indexed' in prev_lower
        cur_is_indexed = 'submitted and indexed' in cur_lower

        # Recovery: was non-indexed, now indexed
        if cur_is_indexed and not prev_was_indexed:
            recoveries += 1
            continue

        # Negative transition: was indexed, now not
        if prev_was_indexed and not cur_is_indexed:
            transition_class = classify_transition(cur_lower)
            transitions.append({
                'url': url,
                'previous_state': previous_state,
                'current_state': current_state,
                'transition_class': transition_class,
            })
            continue

        # Other state-to-state transitions (e.g., crawled-not-indexed → 404) — not
        # currently surfaced as findings. Future enhancement: a 'lateral' bucket.

    critical_count = sum(1 for t in transitions if t['transition_class'] == 'server_error')
    high_count = len(transitions) - critical_count

    print(f"transitions_total:{len(transitions)}")
    print(f"critical_transitions:{critical_count}")
    print(f"high_transitions:{high_count}")
    print(f"recoveries:{recoveries}")
    print(f"no_change_count:{no_change_count}")
    print(f"previous_run_date:{prev.get('run_timestamp', '')[:10]}")
    print(f"previous_commit:{prev.get('commit_sha', '')}")
    print(f"current_commit:{cur.get('commit_sha', '')}")

    # Transitions detail — sorted by class priority then URL
    class_priority = {
        'server_error': 0, 'broken_url': 1, 'redirect': 2, 'canonical': 3,
        'quality': 4, 'crawl_budget': 5, 'rendering': 6, 'access': 7, 'other': 8,
    }
    transitions.sort(key=lambda t: (class_priority.get(t['transition_class'], 9), t['url']))
    print("--- transitions ---")
    for t in transitions:
        print(f"  {t['url']}|{t['previous_state']}|{t['current_state']}|{t['transition_class']}")

    # Path clusters from transition URLs
    clusters = compute_path_clusters([t['url'] for t in transitions])
    print("--- path_clusters ---")
    for prefix, count in clusters:
        print(f"  {prefix}|{count}")

    # Count deltas across the full inspection set (not just transitions)
    prev_counts = defaultdict(int)
    for url, state in prev_inspections.items():
        prev_counts[state] += 1
    cur_counts = defaultdict(int)
    for url, state in cur_inspections.items():
        cur_counts[state] += 1

    all_states = set(prev_counts.keys()) | set(cur_counts.keys())
    deltas = []
    for state in all_states:
        p = prev_counts[state]
        c = cur_counts[state]
        delta = c - p
        deltas.append((state, p, c, delta))
    deltas.sort(key=lambda d: -abs(d[3]))

    print("--- count_deltas ---")
    for state, p, c, d in deltas[:10]:
        sign = '+' if d >= 0 else ''
        print(f"  {state}|{p}|{c}|{sign}{d}")


# ---------------------------------------------------------------------------
# inspect-batch — Turn 2b URL Inspection dispatch (Group A, S34 cont. follow-up)
# ---------------------------------------------------------------------------

UI_CACHE_TTL_SEC = 7 * 86400  # 7d — coverageState is weeks-stable (Group C)
INSPECT_MAX_WORKERS = 6       # conservative vs GSC URL Inspection per-property
                              # QPS (lowered from 20 after /code-review finding #8
                              # — 20 workers × ~400ms/call = ~50 req/sec well above
                              # GSC's typical limit; 6 workers ≈ 10-15 req/sec,
                              # plus 429-aware backoff below for the tail).
INSPECT_TIMEOUT_SEC = 30      # per-call HTTP timeout
INSPECT_MAX_RETRIES = 3       # per-URL retry budget on 429 / 5xx
INSPECT_BACKOFF_BASE_SEC = 2  # exponential: 2s, 4s, 8s with jitter
INSPECT_ENDPOINT = ('https://searchconsole.googleapis.com/v1/'
                    'urlInspection/index:inspect')


def _ui_cache_path(cache_dir, site_url, inspection_url):
    """Match gsc-cache.md cache-key strategy: sha1(site_url|inspection_url),
    filename ui-<hash>.json. Critical — must match the bash cache wrapper
    so the same key produces the same file across dispatch paths."""
    key = f"{site_url}|{inspection_url}".encode('utf-8')
    return os.path.join(cache_dir, f"ui-{hashlib.sha1(key).hexdigest()}.json")


def _ui_cache_is_fresh(path, ttl_sec):
    """True if file exists AND mtime is within TTL window."""
    try:
        return (time.time() - os.path.getmtime(path)) < ttl_sec
    except OSError:
        return False


def _inspect_one(url, site_url, cache_dir, token, quota_project, no_cache):
    """Inspect a single URL: cache lookup → API call → atomic write.

    Returns dict with status in {'hit', 'miss', 'error'} + coverage_state when
    available + http_code/error_msg on error. The orchestrator aggregates these
    into the cache_hits/cache_misses/http_errors footer line."""
    cache_file = _ui_cache_path(cache_dir, site_url, url)

    # Cache lookup (skipped under NO_CACHE=1)
    if not no_cache and _ui_cache_is_fresh(cache_file, UI_CACHE_TTL_SEC):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            coverage = (data.get('inspectionResult', {})
                            .get('indexStatusResult', {})
                            .get('coverageState', ''))
            return {'url': url, 'status': 'hit', 'coverage_state': coverage}
        except (OSError, json.JSONDecodeError):
            pass  # Corrupted cache file → fall through to miss

    # Cache miss: fresh API call
    body = json.dumps({
        'inspectionUrl': url,
        'siteUrl': site_url,
        'languageCode': 'en',
    }).encode('utf-8')

    req = urllib.request.Request(
        INSPECT_ENDPOINT,
        data=body,
        method='POST',
        headers={
            'Authorization': f'Bearer {token}',
            'x-goog-user-project': quota_project,
            'Content-Type': 'application/json',
        },
    )

    # 429/5xx retry with exponential backoff. _code-review finding #8:_ the
    # earlier no-retry path silently lost URLs to transient rate-limit bursts.
    response_bytes = None
    http_code = 0
    last_err = None
    for attempt in range(INSPECT_MAX_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=INSPECT_TIMEOUT_SEC) as resp:
                response_bytes = resp.read()
                http_code = resp.status
            break  # success (any 2xx)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode('utf-8', errors='replace')[:200]
            except Exception:
                err_body = str(e.reason or 'HTTPError')
            last_err = ('http', e.code, err_body)
            # Retry only on 429 and 5xx; 4xx (other) is the caller's bug.
            if e.code == 429 or 500 <= e.code < 600:
                if attempt < INSPECT_MAX_RETRIES - 1:
                    # Deterministic jitter: 0..1s based on url hash, no rand import
                    jitter = (int(hashlib.sha1(url.encode()).hexdigest()[:4], 16)
                              % 1000) / 1000.0
                    time.sleep(INSPECT_BACKOFF_BASE_SEC * (2 ** attempt) + jitter)
                    continue
            return {'url': url, 'status': 'error', 'http_code': e.code,
                    'error_msg': err_body}
        except urllib.error.URLError as e:
            last_err = ('url', 0, str(e.reason)[:200])
            if attempt < INSPECT_MAX_RETRIES - 1:
                time.sleep(INSPECT_BACKOFF_BASE_SEC * (2 ** attempt))
                continue
            return {'url': url, 'status': 'error', 'http_code': 0,
                    'error_msg': last_err[2]}
        except Exception as e:
            return {'url': url, 'status': 'error', 'http_code': 0,
                    'error_msg': f'{type(e).__name__}: {e}'[:200]}

    if response_bytes is None:
        # All retries exhausted on transient failures
        kind, code, msg = last_err or ('unknown', 0, 'no response')
        return {'url': url, 'status': 'error', 'http_code': code,
                'error_msg': f'exhausted retries: {msg}'}

    # Accept full 2xx range — defensive against future API additions.
    # _code-review finding #7 (Angle A item 7) inherited concern._
    if not (200 <= http_code < 300):
        return {'url': url, 'status': 'error', 'http_code': http_code,
                'error_msg': response_bytes.decode('utf-8', errors='replace')[:200]}

    # 200 OK → atomic write (.tmp + os.replace; never cache non-200)
    tmp_file = f"{cache_file}.tmp.{os.getpid()}.{hashlib.sha1(url.encode()).hexdigest()[:6]}"
    try:
        with open(tmp_file, 'wb') as f:
            f.write(response_bytes)
        os.replace(tmp_file, cache_file)
    except OSError as e:
        try:
            os.remove(tmp_file)
        except OSError:
            pass
        return {'url': url, 'status': 'error', 'http_code': 200,
                'error_msg': f'cache write failed: {e}'}

    try:
        data = json.loads(response_bytes)
        coverage = (data.get('inspectionResult', {})
                        .get('indexStatusResult', {})
                        .get('coverageState', ''))
    except json.JSONDecodeError:
        coverage = '(parse-error)'

    return {'url': url, 'status': 'miss', 'http_code': http_code,
            'coverage_state': coverage}


def inspect_batch(cache_dir, site_url, urls_file):
    """Parallel URL Inspection dispatch — replaces N-parallel-bash-curl spec.

    Closes the S31cont.²+S34 boundary-violation pattern: orchestrators kept
    writing ad-hoc Python scripts into .seo-data/gsc/ to bundle this dispatch
    (perceived as "more efficient than 200 parallel bash invocations").
    Shipping it as a canonical subcommand removes the spec-shaped hole.

    See gsc-cache.md "Cache key strategy" for the ui-<hash>.json scheme — this
    function matches it exactly so partial cache hits across Bash-wrapper and
    helper-driven runs interoperate cleanly."""
    token = os.environ.get('GCLOUD_TOKEN', '').strip()
    if not token:
        print('ERROR: GCLOUD_TOKEN env var not set or empty', file=sys.stderr)
        sys.exit(1)
    quota_project = os.environ.get('GCLOUD_QUOTA_PROJECT', '').strip()
    if not quota_project:
        print('ERROR: GCLOUD_QUOTA_PROJECT env var not set or empty', file=sys.stderr)
        sys.exit(1)
    no_cache = os.environ.get('NO_CACHE', '') == '1'

    os.makedirs(cache_dir, exist_ok=True)

    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = []
            seen = set()
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if line in seen:
                    continue
                seen.add(line)
                urls.append(line)
    except FileNotFoundError:
        print(f'ERROR: URLs file not found: {urls_file}', file=sys.stderr)
        sys.exit(1)

    if not urls:
        print('total_attempted:0')
        print('cache_hits:0')
        print('cache_misses:0')
        print('http_errors:0')
        return

    results = []
    with ThreadPoolExecutor(max_workers=INSPECT_MAX_WORKERS) as executor:
        futures = {
            executor.submit(_inspect_one, url, site_url, cache_dir,
                            token, quota_project, no_cache): url
            for url in urls
        }
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                url = futures[fut]
                results.append({'url': url, 'status': 'error', 'http_code': 0,
                                'error_msg': f'worker exception: {e}'[:200]})

    hits = sum(1 for r in results if r['status'] == 'hit')
    misses = sum(1 for r in results if r['status'] == 'miss')
    errors = sum(1 for r in results if r['status'] == 'error')

    print(f'total_attempted:{len(results)}')
    print(f'cache_hits:{hits}')
    print(f'cache_misses:{misses}')
    print(f'http_errors:{errors}')

    # Cluster preview — full classification (with pageFetchState) requires the
    # `clusters` subcommand on the cache dir post-dispatch.
    cluster_counts = defaultdict(int)
    for r in results:
        if r['status'] in ('hit', 'miss'):
            cluster_counts[cluster_for(r.get('coverage_state', ''), '')] += 1

    print('--- cluster_counts ---')
    for cluster, count in sorted(cluster_counts.items(), key=lambda x: -x[1]):
        print(f'  {cluster}: {count}')

    if errors:
        print('--- errors ---')
        for r in results:
            if r['status'] == 'error':
                print(f"  {r['url']}|http={r.get('http_code', 0)}|"
                      f"{r.get('error_msg', '')[:120]}")


# ---------------------------------------------------------------------------
# Group D: Finding lifecycle (history + watchpoints)
# ---------------------------------------------------------------------------

WATCHPOINT_RECHECK_DAYS = 21         # typical GSC pipeline reflection window
WATCHPOINT_EVICT_DAYS = 90           # auto-evict stale watchpoints
ESCALATION_THRESHOLD = 3             # run_count at which escalation hint fires


def _finding_hash(sub_dim, location):
    """Stable identity for a finding across runs.

    Title is excluded from the hash because count-bearing titles ('48 of 194
    inspected pages...') change between runs without representing a different
    finding. sub_dim + location is enough for the same diagnostic to match
    across runs."""
    key = f"{sub_dim or ''}|{location or ''}".encode('utf-8')
    return hashlib.sha1(key).hexdigest()[:16]


def _load_json_safe(path, default):
    """Load JSON or return default if file missing/corrupt. Doesn't sys.exit
    (unlike load_json above) — used for finding-history / watchpoints where
    missing-or-corrupt files mean 'no prior state, start fresh'."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_write_json(path, data):
    """Atomic write via .tmp + os.replace. PID-suffixed tmp so two concurrent
    /seo-review processes writing the same target don't interleave content in
    a shared `<path>.tmp` — each process gets its own tmp, only the os.replace
    races, which is atomic. _code-review finding #7._"""
    parent = os.path.dirname(path)
    if parent:  # bare filename has empty dirname → os.makedirs('') errors on Windows
        os.makedirs(parent, exist_ok=True)
    tmp_path = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except OSError as e:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        print(f"ERROR: write failed for {path}: {e}", file=sys.stderr)
        # Return False instead of sys.exit so callers can still flush their
        # in-memory results before exiting. _code-review finding #9._
        return False
    return True


def _read_findings_jsonl(path):
    """Read newline-delimited JSON findings. Each line is one finding object
    with at minimum: sub_dim, location, title. Optional: url, source,
    code_changed_since_gsc_window, impressions, ctr, position."""
    findings = []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, raw in enumerate(f, 1):
                raw = raw.strip()
                if not raw or raw.startswith('#'):
                    continue
                try:
                    findings.append(json.loads(raw))
                except json.JSONDecodeError as e:
                    print(f"WARN: skipping malformed JSONL line {line_num}: {e}",
                          file=sys.stderr)
    except FileNotFoundError:
        print(f"ERROR: findings JSONL not found: {path}", file=sys.stderr)
        sys.exit(1)
    return findings


def history_update(findings_jsonl, history_path, commit_sha, run_date):
    """Group D: update finding-history.json with this run's findings.

    For each finding, increment run_count + update last_seen. New findings get
    run_count=1 + first_seen + last_seen set to current run. **Same-commit
    guard:** if commit_sha == entry.last_seen_commit, run_count is NOT
    incremented — methodology-variance reruns on identical code don't inflate
    the counter into bogus stale-finding escalations. _code-review finding #6._

    Emits per-finding lines to stdout so the orchestrator can append escalation
    hints to findings whose run_count >= ESCALATION_THRESHOLD:

        <hash>|<run_count>|<sub_dim>|<location>|<first_seen_date>

    Output is printed BEFORE the atomic write so a disk-full/AV-lock failure
    doesn't silently nuke the orchestrator's downstream parsing.
    _code-review finding #9._"""
    findings = _read_findings_jsonl(findings_jsonl)
    history = _load_json_safe(history_path, {'schema_version': 1, 'findings': {}})

    if not isinstance(history.get('findings'), dict):
        history['findings'] = {}

    for f in findings:
        sub_dim = f.get('sub_dim') or f.get('sub_dimension') or ''
        location = f.get('location', '')
        if not sub_dim and not location:
            continue
        h = _finding_hash(sub_dim, location)
        entry = history['findings'].get(h)
        # `or ''` handles JSONL with explicit `"title": null` (f.get returns
        # None even with a default arg when the key is present with null value).
        # _code-review finding #11._
        title_seed = (f.get('title') or '')[:120]
        if entry is None:
            history['findings'][h] = {
                'first_seen_date': run_date,
                'first_seen_commit': commit_sha,
                'last_seen_date': run_date,
                'last_seen_commit': commit_sha,
                'run_count': 1,
                'sub_dim': sub_dim,
                'location': location,
                'title_seed': title_seed,
            }
        else:
            # Same-commit guard: skip increment when this commit already
            # contributed to run_count (S31 methodology-variance reruns).
            same_commit = entry.get('last_seen_commit') == commit_sha
            entry['last_seen_date'] = run_date
            entry['last_seen_commit'] = commit_sha
            if not same_commit:
                entry['run_count'] = entry.get('run_count', 0) + 1
            if not entry.get('title_seed') and title_seed:
                entry['title_seed'] = title_seed

    # Print results BEFORE attempting the write so partial-failure
    # observability is preserved. _code-review finding #9._
    print(f"findings_tracked:{len(history['findings'])}")
    print(f"findings_this_run:{len(findings)}")
    print("--- per_finding ---")
    for f in findings:
        sub_dim = f.get('sub_dim') or f.get('sub_dimension') or ''
        location = f.get('location', '')
        if not sub_dim and not location:
            continue
        h = _finding_hash(sub_dim, location)
        entry = history['findings'].get(h, {})
        run_count = entry.get('run_count', 1)
        first_seen = entry.get('first_seen_date', run_date)
        marker = ' ESCALATE' if run_count >= ESCALATION_THRESHOLD else ''
        print(f"  {h}|{run_count}|{sub_dim}|{location}|{first_seen}{marker}")

    if not _atomic_write_json(history_path, history):
        print("history_write_failed:1")
        sys.exit(1)


def _parse_date(s):
    """Lenient YYYY-MM-DD parser → datetime.date. Returns None on malformed.

    Uses datetime.date (calendar arithmetic, DST-immune) rather than the
    earlier time.mktime+localtime path which had a real off-by-one bug:
    orchestrator passes UTC dates from `date -u +%Y-%m-%d`, mktime interpreted
    them as local-time, and crossing DST transitions made `epoch + N*86400`
    land at the wrong calendar day. _code-review finding #2._"""
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _add_days(date_str, days):
    """Add N days to YYYY-MM-DD. Returns YYYY-MM-DD or empty on parse failure."""
    d = _parse_date(date_str)
    if d is None:
        return ''
    return (d + timedelta(days=days)).isoformat()


def watchpoint_emit(findings_jsonl, watchpoints_path, commit_sha, run_date):
    """Group D: auto-emit watchpoint entries for findings with
    code_changed_since_gsc_window=true.

    Dedup by finding_hash — re-running on the same finding doesn't create
    duplicate watchpoints; only refreshes applied_commit + applied_date when
    the inheritance commit changes."""
    findings = _read_findings_jsonl(findings_jsonl)
    wp_doc = _load_json_safe(watchpoints_path,
                             {'schema_version': 1, 'watchpoints': []})
    # Defensive: corrupted/hand-edited file may have `watchpoints: null` or
    # non-list type; reset rather than crash on `for w in ...`.
    if not isinstance(wp_doc.get('watchpoints'), list):
        wp_doc['watchpoints'] = []

    existing_by_hash = {w.get('finding_hash'): w for w in wp_doc['watchpoints']}
    emitted = 0
    updated = 0

    for f in findings:
        if not f.get('code_changed_since_gsc_window'):
            continue
        sub_dim = f.get('sub_dim') or f.get('sub_dimension') or ''
        location = f.get('location', '')
        if not sub_dim and not location:
            continue
        h = _finding_hash(sub_dim, location)
        baseline = {
            'impressions': f.get('impressions'),
            'ctr': f.get('ctr'),
            'position': f.get('position'),
        }
        # Only include non-null baseline fields
        baseline = {k: v for k, v in baseline.items() if v is not None}

        new_entry = {
            'finding_hash': h,
            'url': f.get('url') or f.get('location') or '',
            'sub_dim': sub_dim,
            'applied_commit': commit_sha,
            'applied_date': run_date,
            'expected_recheck_date': _add_days(run_date, WATCHPOINT_RECHECK_DAYS),
            'baseline_metric': baseline,
            # `or ''` handles JSONL with explicit null title.
            # _code-review finding #11._
            'title_seed': (f.get('title') or '')[:120],
        }

        if h in existing_by_hash:
            # Refresh — the user re-applied a fix on the same finding
            old = existing_by_hash[h]
            if old.get('applied_commit') != commit_sha:
                old.update(new_entry)
                updated += 1
        else:
            wp_doc['watchpoints'].append(new_entry)
            existing_by_hash[h] = new_entry
            emitted += 1

    # Print results BEFORE the write — partial-failure observability.
    # _code-review finding #9._
    print(f"watchpoints_emitted:{emitted}")
    print(f"watchpoints_updated:{updated}")
    print(f"watchpoints_total:{len(wp_doc['watchpoints'])}")

    if not _atomic_write_json(watchpoints_path, wp_doc):
        print("watchpoints_write_failed:1")
        sys.exit(1)


def watchpoint_check(watchpoints_path, q2_pages_path, run_date):
    """Group D: at Step 1.6 Turn 1, evaluate watchpoints whose recheck date
    has elapsed. Auto-evict watchpoints > WATCHPOINT_EVICT_DAYS old.

    Output schema (machine-parseable for orchestrator banner rendering):
        watchpoints_active:<N>
        watchpoints_due:<M>             # past recheck date
        watchpoints_evicted:<K>         # auto-evicted as stale
        --- due ---
        <hash>|<url>|<applied_date>|<applied_commit>|<sub_dim>|<baseline_json>|<current_json>|<status>

    status ∈ {improved, unchanged, regressed, no_data}
        improved   — primary metric moved in favorable direction (ctr↑ or pos↓)
        unchanged  — within ±10% of baseline
        regressed  — moved unfavorably (ctr↓ or pos↑)
        no_data    — URL not found in Q2 pages digest this run
    """
    wp_doc = _load_json_safe(watchpoints_path,
                             {'schema_version': 1, 'watchpoints': []})
    # Defensive: corrupted file may have null or non-list watchpoints field.
    if not isinstance(wp_doc.get('watchpoints'), list):
        wp_doc['watchpoints'] = []

    run_dt = _parse_date(run_date)
    if run_dt is None:
        print(f"ERROR: invalid run_date format '{run_date}' (expected YYYY-MM-DD)",
              file=sys.stderr)
        sys.exit(1)

    # Evict stale watchpoints (> 90 days old) — calendar arithmetic.
    evict_threshold = run_dt - timedelta(days=WATCHPOINT_EVICT_DAYS)
    surviving = []
    evicted = 0
    for w in wp_doc['watchpoints']:
        applied_dt = _parse_date(w.get('applied_date'))
        if applied_dt is not None and applied_dt < evict_threshold:
            evicted += 1
            continue
        surviving.append(w)
    wp_doc['watchpoints'] = surviving

    # Load Q2 pages digest for current-metric comparison.
    # Filter None values from each row — GSC may omit a metric for low-volume
    # URLs, and downstream _watchpoint_status would crash on None operands.
    # _code-review finding #3._
    q2_url_map = {}
    if q2_pages_path and os.path.exists(q2_pages_path):
        try:
            with open(q2_pages_path, 'r', encoding='utf-8') as f:
                q2 = json.load(f)
            for row in q2.get('rows', []):
                keys = row.get('keys', [])
                if not keys:
                    continue
                metric = {
                    'impressions': row.get('impressions'),
                    'ctr': row.get('ctr'),
                    'position': row.get('position'),
                }
                q2_url_map[keys[0]] = {k: v for k, v in metric.items()
                                       if v is not None}
        except (OSError, json.JSONDecodeError) as e:
            print(f"WARN: Q2 cache at '{q2_pages_path}' unreadable ({e}); "
                  f"watchpoint metrics will all resolve as no_data.",
                  file=sys.stderr)

    # Find due watchpoints
    due_records = []
    for w in surviving:
        recheck_dt = _parse_date(w.get('expected_recheck_date'))
        if recheck_dt is None or run_dt < recheck_dt:
            continue
        url = w.get('url', '')
        current = q2_url_map.get(url)
        baseline = w.get('baseline_metric', {})

        if not current:  # None or empty dict (all metrics filtered as None)
            status = 'no_data'
            current_for_emit = {}
        else:
            current_for_emit = current
            status = _watchpoint_status(baseline, current)

        due_records.append({
            'hash': w.get('finding_hash', ''),
            'url': url,
            'applied_date': w.get('applied_date', ''),
            'applied_commit': w.get('applied_commit', ''),
            'sub_dim': w.get('sub_dim', ''),
            'baseline': baseline,
            'current': current_for_emit,
            'status': status,
        })

    # Print results BEFORE attempting any disk write — partial-failure
    # observability. _code-review finding #9._
    print(f"watchpoints_active:{len(surviving)}")
    print(f"watchpoints_due:{len(due_records)}")
    print(f"watchpoints_evicted:{evicted}")

    if due_records:
        print("--- due ---")
        for r in due_records:
            baseline_json = json.dumps(r['baseline'], separators=(',', ':'))
            current_json = json.dumps(r['current'], separators=(',', ':'))
            print(f"  {r['hash']}|{r['url']}|{r['applied_date']}|"
                  f"{r['applied_commit']}|{r['sub_dim']}|"
                  f"{baseline_json}|{current_json}|{r['status']}")

    # Persist eviction last (auto-evicted entries removed from disk).
    # Failure here doesn't kill the run — banners already printed.
    if evicted > 0 and not _atomic_write_json(watchpoints_path, wp_doc):
        print("watchpoints_evict_write_failed:1")


def _watchpoint_status(baseline, current):
    """Compare baseline vs current metrics. Decide on the primary metric:
    if baseline has ctr → ctr-anchored (lower-is-worse); if baseline has
    position → position-anchored (lower-is-better); else impressions."""
    if 'ctr' in baseline and 'ctr' in current:
        b = baseline['ctr']
        c = current['ctr']
        if b <= 0:
            return 'unchanged' if c <= 0 else 'improved'
        delta_ratio = (c - b) / b
        if delta_ratio > 0.10:
            return 'improved'
        elif delta_ratio < -0.10:
            return 'regressed'
        return 'unchanged'

    if 'position' in baseline and 'position' in current:
        b = baseline['position']
        c = current['position']
        if b <= 0:
            return 'unchanged'
        delta_ratio = (b - c) / b  # lower position is better → invert
        if delta_ratio > 0.10:
            return 'improved'
        elif delta_ratio < -0.10:
            return 'regressed'
        return 'unchanged'

    if 'impressions' in baseline and 'impressions' in current:
        b = baseline['impressions']
        c = current['impressions']
        if b <= 0:
            return 'unchanged' if c <= 0 else 'improved'
        delta_ratio = (c - b) / b
        if delta_ratio > 0.10:
            return 'improved'
        elif delta_ratio < -0.10:
            return 'regressed'
        return 'unchanged'

    return 'unchanged'


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(3)

    cmd = sys.argv[1]
    arg = sys.argv[2]

    if cmd == 'q1':
        parse_q1(arg)
    elif cmd == 'q2':
        parse_q2(arg)
    elif cmd == 'q3':
        parse_q3(arg)
    elif cmd == 'ctr':
        parse_ctr_opportunities(arg)
    elif cmd == 'clusters':
        parse_clusters(arg)
    elif cmd == 'brand':
        if len(sys.argv) < 4:
            print("ERROR: brand subcommand needs <q1_path> <brand_name>", file=sys.stderr)
            sys.exit(3)
        detect_brand_anomaly(arg, sys.argv[3])
    elif cmd == 'snapshot-write':
        if len(sys.argv) < 7:
            print("ERROR: snapshot-write subcommand needs "
                  "<cache_dir> <run_timestamp> <commit_sha> <site_url> <output_path>",
                  file=sys.stderr)
            sys.exit(3)
        snapshot_write(arg, sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6])
    elif cmd == 'regression':
        if len(sys.argv) < 4:
            print("ERROR: regression subcommand needs "
                  "<current_snapshot> <previous_snapshot>", file=sys.stderr)
            sys.exit(3)
        regression(arg, sys.argv[3])
    elif cmd == 'inspect-batch':
        if len(sys.argv) < 5:
            print("ERROR: inspect-batch subcommand needs "
                  "<cache_dir> <site_url> <urls_file>", file=sys.stderr)
            sys.exit(3)
        inspect_batch(arg, sys.argv[3], sys.argv[4])
    elif cmd == 'history-update':
        if len(sys.argv) < 6:
            print("ERROR: history-update subcommand needs "
                  "<findings_jsonl> <history_path> <commit_sha> <run_date>",
                  file=sys.stderr)
            sys.exit(3)
        history_update(arg, sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == 'watchpoint-emit':
        if len(sys.argv) < 6:
            print("ERROR: watchpoint-emit subcommand needs "
                  "<findings_jsonl> <watchpoints_path> <commit_sha> <run_date>",
                  file=sys.stderr)
            sys.exit(3)
        watchpoint_emit(arg, sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == 'watchpoint-check':
        if len(sys.argv) < 5:
            print("ERROR: watchpoint-check subcommand needs "
                  "<watchpoints_path> <q2_pages_path> <run_date>",
                  file=sys.stderr)
            sys.exit(3)
        watchpoint_check(arg, sys.argv[3], sys.argv[4])
    else:
        print(f"ERROR: unknown subcommand '{cmd}'. Run with no args for usage.",
              file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main()
