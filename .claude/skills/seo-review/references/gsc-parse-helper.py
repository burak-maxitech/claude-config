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
from collections import defaultdict
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

    # Ensure parent dir exists (orchestrator creates it in Turn 1, but be defensive)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Atomic write: .tmp then os.replace
    tmp_path = output_path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, output_path)
    except OSError as e:
        # Clean up tmp on failure
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        print(f"ERROR: snapshot write failed: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"snapshot_written:{output_path}")
    print(f"inspection_count:{len(inspections)}")


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
    if 'not found' in cur_state_lower or '404' in cur_state_lower and 'soft' not in cur_state_lower:
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
    else:
        print(f"ERROR: unknown subcommand '{cmd}'. Run with no args for usage.",
              file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main()
