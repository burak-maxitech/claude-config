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
    else:
        print(f"ERROR: unknown subcommand '{cmd}'. Run with no args for usage.",
              file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main()
