#!/usr/bin/env python3
"""GSC API response parser — stable helper script for /bx:seo orchestrator.

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
                      ThreadPoolExecutor (6 workers + 429/5xx retry with
                      exponential backoff), per-URL cache check
                      (7d TTL on ui-* — coverageState is weeks-stable), atomic
                      write via .tmp + os.replace, never caches non-200.
                      Mints its own token via resolve_credentials() (token never
                      leaves this process); NO_CACHE=1 bypasses cache lookup
                      (writes still happen). Replaces the prior "N parallel Bash
                      curl calls" spec — closes the S31cont.²+S34 boundary-
                      violation pattern.
    crux <targets_file>
                      Real-user Core Web Vitals (p75 LCP/INP/CLS/TTFB) from the
                      CrUX API — the GSC API has no CWV endpoint. Targets file:
                      `origin <url>` / `url <url>` per line (cap 25). Key from
                      CRUX_API_KEY env, never printed; unset → CRUX_ERROR:no_key.
                      404 = not enough Chrome traffic → status=no_data.
    page-audit <targets_file>
                      Fetch up to 25 URLs (one per line) WITHOUT running JS, as
                      a non-rendering crawler sees them: uncompressed bytes vs
                      Googlebot's 2 MB limit, title/canonical/robots/h1/JSON-LD
                      presence, visible word count, empty SPA root, and inline-
                      script back-button-hijack signals (popstate listener that
                      navigates or re-pushes history). No credentials.
    sa-trends <cache_dir> <site_url> <end_date> <lookback_days> [<brand_csv>]
                      Keyword cannibalization (query×page over the lookback
                      window; non-brand queries ≥100 imps where 2+ URLs each
                      hold ≥10%) + content decay (three 28-day page windows
                      ending at end_date; clicks fell twice, newest ≤70% of
                      oldest, oldest ≥30). Mints its own token; 24h cache as
                      sa-trend-*.json; NO_CACHE=1 bypasses lookup.
                      2.20.0: also query×page for the newest and previous
                      28-day windows → ctr_segments (aio_prone vs other) +
                      ai_overview_compression. Optional flags:
                      --out FILE (full JSON) --question-words a,b,c
    page-audit <targets_file> [--out FILE]
                      2.20.0: --out writes JSON records incl. jsonld [{type,
                      fields}], jsonld_count, jsonld_parse_errors, robots_meta,
                      visible_dates, main_text_chars, schema_visible_checks.
    bot-probe --base-url URL [--pages URL,URL] [--robots-file PATH]
              [--indexnow-key KEY] --out FILE
                      Fetch base + ≤5 pages as each AI bot UA (AI_BOTS) and a
                      browser control; challenge markers, per-bot verdicts,
                      cdn_waf_suspect, robots Content-Signal / Content-Usage /
                      __usage_ groups, policy_conflicts, utm survival, IndexNow.
    render-compare --raw FILE --rendered FILE --url URL --out FILE
                      Raw vs rendered robots/canonical/JSON-LD/main text.
                      --rendered may be raw HTML or a JSON string literal.
    update-windows [--cache PATH] [--max-age-days 7] [--overlap START,END]
                   --out FILE
                      Google ranking updates from status.search.google.com
                      incidents.json (cache-first; offline → cache →
                      unavailable).
    bing-exports [--dir .seo-data/bing/exports] --out FILE
                      Tolerant parser for Bing AI Performance CSV exports.
    auth-token       Mint + print credentials for the Search Analytics curl
                      path: two lines (access token, then quota project). Capture
                      into shell vars in the SAME Bash call that runs curl; never
                      run standalone (would leak a live token to the transcript).
    sitemaps-list <site_url>
                      Authenticated GSC sitemaps.list — print the sitemap URLs
                      submitted for the property (authoritative discovery). Non-
                      fatal on API error (exit 0); credential failure exits 4.
    sitemap-urls <sitemap_url> <base_or_-> <out_file> [<q3_cache> <orphan_limit>]
                      Fetch + parse the LIVE sitemap (handles sitemapindex
                      recursion, .gz, relative URLs) → write all <loc> URLs to
                      <out_file>. Optionally print up to <orphan_limit> sitemap-
                      orphan URLs (not in the Q3 url_impressions_map). Non-fatal
                      on fetch error (exit 0, sitemap_urls:0).
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

Credentials (inspect-batch + auth-token):
    Resolved by resolve_credentials() — gcloud ADC as the user (authorized_user),
    NOT a service account. Looks at GCLOUD_TOKEN/GCLOUD_QUOTA_PROJECT env, then
    GOOGLE_APPLICATION_CREDENTIALS (set by the orchestrator from config.yaml
    `adc_credentials_path`), then gcloud's default ADC path. Token minted via
    stdlib refresh-token grant (no google-auth dependency).

Exit codes:
    0   success (incl. zero findings)
    1   file not found / unreadable
    2   JSON parse error
    3   unknown subcommand / bad arguments
    4   credential resolution / token mint failure
"""
# -*- coding: utf-8 -*-
import contextlib
import json
import os
import re
import sys
import glob
import gzip
import hashlib
import html
import time
import subprocess
import urllib.request
import urllib.error
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from urllib.parse import urlparse, urlencode, urljoin, quote


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


# ---------------------------------------------------------------------------
# Authentication — mint a GSC access token from gcloud ADC
# ---------------------------------------------------------------------------
# The user authenticates AS THEMSELVES via gcloud Application Default
# Credentials (type: authorized_user), NOT a service account. (Adding a service
# account to GSC is blocked by an open Google bug, and domain-wide delegation
# needs Google Workspace, which a personal @gmail account lacks.) The ADC file
# holds a refresh token that is NOT machine-locked, so it can live in a synced
# folder (Drive/OneDrive/Dropbox) and be pointed at from every machine via the
# config.yaml `adc_credentials_path` key → "configure once, all machines".
#
# Token minting is stdlib-only (no google-auth dependency): a refresh-token
# grant POST to Google's OAuth endpoint. The token is minted INSIDE this helper
# so it never crosses into the orchestrator's (model's) context for the URL
# Inspection path; the `auth-token` subcommand exposes it for the Search
# Analytics curl path, which must capture it into a shell var in the same call.

OAUTH_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
TOKEN_REFRESH_TIMEOUT_SEC = 20
TOKEN_REFRESH_ATTEMPTS = 3        # network / 5xx only; 4xx is never retried
TOKEN_REFRESH_BACKOFF_SEC = 2
GCLOUD_TOKEN_TIMEOUT_SEC = 30
REAUTH_HINT = ("gcloud auth application-default login "
               "--scopes=https://www.googleapis.com/auth/webmasters.readonly,"
               "https://www.googleapis.com/auth/cloud-platform")


class CredentialError(Exception):
    """Credential resolution failure with a machine-parseable `reason` so the
    orchestrator can render the right remediation instead of one generic
    'no credentials' message. reason ∈ {no_credentials, unreadable, wrong_type,
    mint_failed, quota_missing}."""

    def __init__(self, reason, message, detail=''):
        super().__init__(message)
        self.reason = reason
        self.detail = detail  # non-secret server/OS error text, may be ''


def _default_adc_path():
    """gcloud's well-known Application Default Credentials path, cross-platform.

    Windows: %APPDATA%\\gcloud\\application_default_credentials.json
    POSIX:   ~/.config/gcloud/application_default_credentials.json"""
    if os.name == 'nt':
        base = os.environ.get('APPDATA') or os.path.join(
            os.path.expanduser('~'), 'AppData', 'Roaming')
        return os.path.join(base, 'gcloud',
                            'application_default_credentials.json')
    return os.path.join(os.path.expanduser('~'), '.config', 'gcloud',
                        'application_default_credentials.json')


def _refresh_user_token(adc, cred_path):
    """Mint an OAuth2 access token from an authorized_user ADC dict via a
    refresh-token grant. Stdlib only — same flow gcloud performs internally.

    Validates required fields up front (raises CredentialError('unreadable')
    on a malformed/partial file) so a KeyError isn't later mistaken for a
    network/revoked-token failure."""
    missing = [k for k in ('client_id', 'client_secret', 'refresh_token')
               if not (adc.get(k) or '').strip()]
    if missing:
        raise CredentialError(
            'unreadable',
            f"authorized_user credential file '{cred_path}' is missing "
            f"field(s) {', '.join(missing)}. Re-create it with: {REAUTH_HINT}")
    body = urlencode({
        'client_id': adc['client_id'],
        'client_secret': adc['client_secret'],
        'refresh_token': adc['refresh_token'],
        'grant_type': 'refresh_token',
    }).encode('utf-8')
    req = urllib.request.Request(
        OAUTH_TOKEN_ENDPOINT, data=body, method='POST',
        headers={'Content-Type': 'application/x-www-form-urlencoded'})
    last_exc = None
    for attempt in range(TOKEN_REFRESH_ATTEMPTS):
        try:
            with urllib.request.urlopen(
                    req, timeout=TOKEN_REFRESH_TIMEOUT_SEC) as resp:
                payload = json.loads(resp.read().decode('utf-8'))
            break
        except urllib.error.HTTPError as e:
            # 4xx is a definitive answer from Google (revoked, reauth, bad
            # client) — retrying cannot change it. Only 5xx is retried.
            if e.code < 500:
                raise
            last_exc = e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_exc = e
        if attempt + 1 < TOKEN_REFRESH_ATTEMPTS:
            time.sleep(TOKEN_REFRESH_BACKOFF_SEC * (attempt + 1))
    else:
        raise last_exc
    token = (payload.get('access_token') or '').strip()
    if not token:
        raise RuntimeError('OAuth token endpoint returned no access_token')
    return token


def _classify_mint_error(exc):
    """Map a refresh-grant failure to (reason, detail) so the orchestrator can
    tell "log in again" apart from "the network is down, just retry".

    Google's token endpoint answers a dead refresh token with HTTP 400 and a
    JSON body: {"error": "invalid_grant", "error_description": "..."}. A
    Workspace session-control policy shows up as invalid_grant with
    error_subtype "invalid_rapt" (reauth required). Neither body contains a
    secret, so `detail` is safe to print.

      token_revoked    invalid_grant           → re-run gcloud ADC login
      reauth_required  invalid_rapt / reauth   → re-login; session policy expired it
      client_invalid   invalid_client/unauth.. → ADC file from a deleted client; re-login
      network          URLError/timeout/5xx    → retry later, do NOT re-login
      mint_failed      anything else           → generic (old behaviour)"""
    if isinstance(exc, urllib.error.HTTPError):
        err, desc, subtype = '', '', ''
        try:
            body = json.loads(exc.read().decode('utf-8', 'replace') or '{}')
            err = str(body.get('error') or '')
            desc = str(body.get('error_description') or '')
            subtype = str(body.get('error_subtype') or '')
        except Exception:
            pass
        detail = f"HTTP {exc.code} {err}".strip()
        if desc:
            detail += f": {desc}"
        low = f"{err} {subtype} {desc}".lower()
        if exc.code >= 500:
            return 'network', detail
        if 'rapt' in low or 'reauth' in low:
            return 'reauth_required', detail
        if err == 'invalid_grant':
            return 'token_revoked', detail
        if err in ('invalid_client', 'unauthorized_client'):
            return 'client_invalid', detail
        return 'mint_failed', detail
    if isinstance(exc, (urllib.error.URLError, TimeoutError, OSError)):
        return 'network', f"{type(exc).__name__}: {exc}"
    return 'mint_failed', f"{type(exc).__name__}: {exc}"


# Reasons for which a gcloud CLI fallback cannot help: gcloud reads the same
# ADC file and gets the same answer from the same endpoint (S68: it only
# added up to 30s before the same failure).
_NO_GCLOUD_FALLBACK = {'token_revoked', 'reauth_required', 'client_invalid',
                       'network'}


def _gcloud_token():
    """Fallback mint via the gcloud CLI (uses gcloud's own ADC resolution).
    Returns '' on any failure — caller decides whether that's fatal."""
    try:
        out = subprocess.run(
            ['gcloud', 'auth', 'application-default', 'print-access-token'],
            capture_output=True, text=True, timeout=GCLOUD_TOKEN_TIMEOUT_SEC)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return ''


SKILL_CONFIG_PATH = os.path.join('.seo-data', 'gsc', 'config.yaml')


def _read_skill_config():
    """Best-effort flat parse of .seo-data/gsc/config.yaml (relative to CWD =
    the audited project root) for credential keys. Mirrors the orchestrator's
    flat-key parser: only top-level `key: value` lines, nested keys ignored.
    Returns {} when the file is missing/unreadable."""
    cfg = {}
    try:
        with open(SKILL_CONFIG_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if not line.strip() or line.lstrip().startswith('#'):
                    continue
                if line[0].isspace() or ':' not in line:  # nested / non-kv
                    continue
                k, _, v = line.partition(':')
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return cfg


def _expand_path(p):
    """Expand ~ and $VARS so a config path resolves the same on Win/Mac."""
    return os.path.expanduser(os.path.expandvars(p)) if p else p


def resolve_credentials():
    """Resolve (access_token, quota_project) for GSC API calls.

    Credential file priority:
      1. GCLOUD_TOKEN + GCLOUD_QUOTA_PROJECT env (explicit override / back-compat)
      2. GOOGLE_APPLICATION_CREDENTIALS env (orchestrator may set it)
      3. config.yaml `adc_credentials_path` — point every machine at one synced
         authorized_user file for "configure once, all machines"
      4. gcloud's default well-known ADC path
    Quota project priority: GCLOUD_QUOTA_PROJECT env → config.yaml `quota_project`
      → the credential file's `quota_project_id`.

    authorized_user files are minted via stdlib refresh-token grant. The gcloud
    CLI fallback is used ONLY when no credential path was explicitly configured
    (so an explicitly-pointed-at file that is missing / wrong-type / fails to
    mint raises a clear error instead of silently authenticating as gcloud's
    default — possibly different — identity).

    Raises CredentialError(reason, message) when resolution fails; reason lets
    the orchestrator pick the right remediation."""
    tok = os.environ.get('GCLOUD_TOKEN', '').strip()
    qp = os.environ.get('GCLOUD_QUOTA_PROJECT', '').strip()
    if tok and qp:
        return tok, qp

    cfg = _read_skill_config()
    # `explicit` = the user pointed us at a specific file. When true we must NOT
    # fall back to gcloud's default identity on failure (that's the wrong-account
    # bug); we surface the specific error for the configured file instead.
    cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '').strip()
    explicit = bool(cred_path)
    if not cred_path:
        cred_path = _expand_path((cfg.get('adc_credentials_path') or '').strip())
        explicit = bool(cred_path)
    if not cred_path:
        cred_path = _default_adc_path()

    adc = None
    if cred_path and os.path.exists(cred_path):
        try:
            with open(cred_path, 'r', encoding='utf-8') as f:
                adc = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise CredentialError(
                'unreadable', f"credential file '{cred_path}' is unreadable: {e}")
    elif explicit:
        raise CredentialError(
            'unreadable',
            f"configured adc_credentials_path '{cred_path}' does not exist on "
            f"this machine. Check the path resolves here (synced folder mounted?) "
            f"or re-create it with: {REAUTH_HINT}")

    cred_type = adc.get('type') if adc is not None else None

    if not tok and cred_type == 'authorized_user':
        try:
            tok = _refresh_user_token(adc, cred_path)
        except CredentialError:
            raise
        except Exception as e:
            reason, detail = _classify_mint_error(e)
            if reason == 'network':
                msg = (f"could not reach Google's token endpoint to mint a "
                       f"token from '{cred_path}' ({detail}). The login is "
                       f"probably fine — check the connection and retry.")
            else:
                msg = (f"failed to mint a token from '{cred_path}' ({detail}). "
                       f"Re-auth with: {REAUTH_HINT}")
            if explicit or reason in _NO_GCLOUD_FALLBACK:
                raise CredentialError(reason, msg, detail)
            tok = _gcloud_token()  # unknown failure: gcloud may still work
            if not tok:
                raise CredentialError(reason, msg, detail)
    elif not tok and cred_type == 'service_account':
        raise CredentialError(
            'wrong_type',
            f"'{cred_path}' is a service-account key, but /bx:seo needs an "
            f"authorized_user ADC file. Run: {REAUTH_HINT}. (Service accounts "
            f"can't be added to GSC — open Google bug; use ADC as yourself.)")
    elif not tok:
        # No usable credential file (none configured, default path absent or an
        # unrecognized type) → let gcloud try its own resolution.
        tok = _gcloud_token()

    if not qp:
        qp = (cfg.get('quota_project') or '').strip()
    if not qp and adc is not None:
        qp = (adc.get('quota_project_id') or '').strip()

    if not tok:
        raise CredentialError(
            'no_credentials',
            "no GSC credentials found. Set 'adc_credentials_path' in "
            ".seo-data/gsc/config.yaml (point it at an "
            "application_default_credentials.json), or run: " + REAUTH_HINT)
    if not qp:
        raise CredentialError(
            'quota_missing',
            "GSC quota project not set. Add 'quota_project' to "
            ".seo-data/gsc/config.yaml, or run 'gcloud auth "
            "application-default set-quota-project <project>'. Without it the "
            "API returns 403 SERVICE_DISABLED.")
    return tok, qp


def cmd_auth_token():
    """Print credentials for the Search Analytics curl path: two lines —
    the access token, then the quota project.

    SECURITY: capture this into shell variables in the SAME Bash call that
    issues the curl; never run it standalone (a standalone run prints a live
    OAuth token into the model transcript). URL Inspection does NOT use this —
    inspect-batch mints internally so the token never leaves the helper.

    On failure: prints `AUTH_ERROR:<reason>` to stdout (machine-parseable so the
    probe can pick the right remediation) + the human message to stderr, exit 4.
    The reason token is NOT a secret."""
    try:
        token, quota = resolve_credentials()
    except CredentialError as e:
        print(f"AUTH_ERROR:{e.reason}")
        if e.detail:
            # One line, no secrets: Google's error code/description or the
            # OS error. Lets the orchestrator quote the actual cause.
            print("AUTH_DETAIL:" + ' '.join(str(e.detail).split())[:300])
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(4)
    sys.stdout.write(token + '\n')
    sys.stdout.write(quota + '\n')


# ---------------------------------------------------------------------------
# Sitemap discovery + fetch
# ---------------------------------------------------------------------------
# The skill used to only read a repo-local static sitemap.xml — invisible for
# the common case of a framework-generated sitemap (Next.js app/sitemap.ts,
# CMS-driven, build-time output not committed). That silently emptied the
# URL-Inspection sitemap-orphan slice (sub-dim 14 deindex detection) and the
# URL-health probe. These subcommands fetch the LIVE sitemap instead:
#   sitemaps-list <site_url>   — authenticated GSC sitemaps.list (authoritative:
#                                the sitemap URLs you actually submitted)
#   sitemap-urls <url> ...     — fetch + parse the sitemap XML (handles
#                                sitemapindex recursion, .gz, relative URLs),
#                                materialize the full <loc> list to a file.

SITEMAP_FETCH_TIMEOUT_SEC = 30
SITEMAP_MAX_CHILDREN = 50          # cap child sitemaps in an index (runaway guard)
SITEMAP_USER_AGENT = 'bx-seo-sitemap/1.0'
_LOC_RE = re.compile(r'<loc>\s*([^<\s][^<]*?)\s*</loc>', re.IGNORECASE)


def _fetch_text(url):
    """Fetch a URL and return decoded text; transparently gunzips .gz / gzip
    magic-byte bodies (sitemaps are commonly served gzipped)."""
    req = urllib.request.Request(url, headers={'User-Agent': SITEMAP_USER_AGENT})
    with urllib.request.urlopen(req, timeout=SITEMAP_FETCH_TIMEOUT_SEC) as resp:
        raw = resp.read()
    if url.lower().endswith('.gz') or raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return raw.decode('utf-8', errors='replace')


def _collect_sitemap_urls(url, base, _depth=0):
    """Return (urls, is_index). Recurses one level into <sitemapindex> children
    (capped). Resolves relative <loc> values against `base` (or the sitemap's
    own URL). Best-effort: a child that fails to fetch is skipped, not fatal."""
    text = _fetch_text(url)
    is_index = '<sitemapindex' in text.lower()
    locs = [m.group(1).strip() for m in _LOC_RE.finditer(text)]
    resolve_base = base or url
    locs = [urljoin(resolve_base, u) if not urlparse(u).scheme else u
            for u in locs]
    if is_index and _depth == 0:
        out = []
        for child in locs[:SITEMAP_MAX_CHILDREN]:
            try:
                child_urls, _ = _collect_sitemap_urls(child, base, _depth + 1)
                out.extend(child_urls)
            except Exception:
                pass  # one bad child shouldn't sink the whole sitemap
        return out, True
    return locs, is_index


def cmd_sitemaps_list(site_url):
    """Authenticated GSC `sitemaps.list` — prints the sitemap URLs submitted for
    the property (the authoritative discovery source). Non-fatal on API error
    (exit 0, sitemaps_found:0) so the orchestrator can fall back to robots.txt /
    conventional paths; only a credential failure exits 4."""
    try:
        token, quota = resolve_credentials()
    except CredentialError as e:
        print('sitemaps_found:0')
        print(f'sitemaps_error:{e.reason}')
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(4)
    api = (f'https://www.googleapis.com/webmasters/v3/sites/'
           f'{quote(site_url, safe="")}/sitemaps')
    req = urllib.request.Request(api, headers={
        'Authorization': f'Bearer {token}', 'x-goog-user-project': quota})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print('sitemaps_found:0')
        print(f'sitemaps_error:api')
        print(f'ERROR: sitemaps.list failed: {e}', file=sys.stderr)
        sys.exit(0)
    entries = data.get('sitemap', []) or []
    print(f'sitemaps_found:{len(entries)}')
    print('--- sitemaps ---')
    for s in entries:
        contents = s.get('contents') or [{}]
        submitted = contents[0].get('submitted', '?')
        print(f"  {s.get('path', '')}|{s.get('type', '?')}|{submitted}")


def cmd_sitemap_urls(args):
    """Fetch + parse a sitemap into a flat URL list.

    Usage: sitemap-urls <sitemap_url> <base_or_-> <out_file> [<q3_cache> <orphan_limit>]
      - Writes ALL <loc> URLs (deduped, document order) to <out_file>, one per
        line — for the URL-health probe + traffic_orphan, kept out of the model
        context.
      - Prints sitemap_urls:N / source / is_index to stdout (bounded).
      - When <q3_cache> + <orphan_limit> are given, also prints up to
        <orphan_limit> sitemap-orphan URLs (in the sitemap but NOT in the Q3
        url_impressions_map) under `--- orphans ---` — the bounded list the
        orchestrator feeds into the inspect-batch sitemap-orphan slice.
    Non-fatal on fetch error (exit 0, sitemap_urls:0) so the run continues."""
    sitemap_url = args[0]
    base = '' if args[1] == '-' else args[1]
    out_file = args[2]
    q3_cache = args[3] if len(args) > 3 else None
    orphan_limit = int(args[4]) if len(args) > 4 and args[4].isdigit() else 0

    try:
        locs, is_index = _collect_sitemap_urls(sitemap_url, base)
    except Exception as e:
        print('sitemap_urls:0')
        print('sitemap_error:fetch')
        print(f'ERROR: failed to fetch sitemap {sitemap_url}: {e}',
              file=sys.stderr)
        sys.exit(0)

    seen, urls = set(), []
    for u in locs:
        if u and u not in seen:
            seen.add(u)
            urls.append(u)

    try:
        with open(out_file, 'w', encoding='utf-8') as f:
            for u in urls:
                f.write(u + '\n')
    except OSError as e:
        print('sitemap_urls:0')
        print('sitemap_error:write')
        print(f'ERROR: could not write {out_file}: {e}', file=sys.stderr)
        sys.exit(0)

    print(f'sitemap_urls:{len(urls)}')
    print(f'source:{sitemap_url}')
    print(f'is_index:{1 if is_index else 0}')

    if q3_cache and orphan_limit:
        impressions = set()
        try:
            with open(q3_cache, 'r', encoding='utf-8') as f:
                d = json.load(f)
            for row in d.get('rows', []):
                keys = row.get('keys', [])
                if keys:
                    impressions.add(keys[0])
        except (OSError, json.JSONDecodeError):
            pass  # no Q3 yet → every sitemap URL counts as an orphan candidate
        orphans = [u for u in urls if u not in impressions][:orphan_limit]
        print(f'orphans_found:{len(orphans)}')
        print('--- orphans ---')
        for u in orphans:
            print(f'  {u}')


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


def _median_ctr(rows):
    """Median CTR across rows. Shared by parse_q2 and parse_ctr_opportunities."""
    ctrs = sorted([r['ctr'] for r in rows])
    n = len(ctrs)
    return ctrs[n // 2] if n % 2 else (ctrs[n // 2 - 1] + ctrs[n // 2]) / 2


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
        median = _median_ctr(top)
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

    median = _median_ctr(top)
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
    submitted_indexed, indexed_info, crawled_not_indexed,
    discovered_not_indexed, not_found_404, redirect_hygiene,
    canonical_conflict, blocked_access, soft_404, server_errors,
    unknown_to_google, other

    indexed_info covers the indexed-with-caveat states ("Indexed, not
    submitted in sitemap", "Indexed, though blocked by robots.txt") —
    info-only footer counts, never sub-dim findings."""
    c = (coverage or '').strip().lower()
    f = (fetch or '').strip().upper()
    if 'submitted and indexed' in c:
        return 'submitted_indexed'
    # Indexed-with-caveat states ("Indexed, not submitted in sitemap",
    # "Indexed, though blocked by robots.txt") are info-only per the
    # gsc-api-queries.md lookup table — NOT sub-dim findings. Must check
    # before the 'blocked' substring match below claims the robots variant.
    if c.startswith('indexed'):
        return 'indexed_info'
    # "Alternate page with proper canonical tag" is sub-dim 7 blocked_access
    # (alt-canonical variant) per the lookup table — must check before the
    # 'canonical' substring match below misroutes it to canonical_conflict.
    if 'alternate page' in c:
        return 'blocked_access'
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
    """Aggregate this run's ui-*.json (see _run_ui_files) into sub-dim clusters."""
    files, scoped = _run_ui_files(cache_dir)
    print(f"inspected_count:{len(files)}")
    if not scoped:
        print("scope:all_cached_ui_files (no run manifest)")

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
        if cluster in ('submitted_indexed', 'indexed_info'):
            continue  # Healthy / info-only states; no finding
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
    # brand_name may be a comma-separated alias list (site-profile.yaml
    # brand_terms, e.g. "burak arık, burakarik, burak arik").
    aliases = [a.strip().lower() for a in brand_name.split(',') if a.strip()]
    # Substring match — catches "burak arık" matching "burak arık fotografçı"
    matches = [r for r in rows
               if any(a in r['keys'][0].lower() for a in aliases)]

    print(f"brand_name:{brand_name}")
    print(f"brand_query_matches:{len(matches)}")

    # Brand / non-brand split. The Search Console branded-queries filter is
    # UI-only, so this approximation from user-supplied terms is the API path.
    total_clicks = sum(r.get('clicks', 0) for r in rows)
    total_imps = sum(r.get('impressions', 0) for r in rows)
    b_clicks = sum(r.get('clicks', 0) for r in matches)
    b_imps = sum(r.get('impressions', 0) for r in matches)
    nb_clicks, nb_imps = total_clicks - b_clicks, total_imps - b_imps
    print(f"brand_clicks:{b_clicks}")
    print(f"brand_impressions:{b_imps}")
    print(f"nonbrand_clicks:{nb_clicks}")
    print(f"nonbrand_impressions:{nb_imps}")
    print(f"brand_click_share:"
          f"{(b_clicks / total_clicks) if total_clicks else 0:.4f}")
    print(f"nonbrand_ctr:{(nb_clicks / nb_imps) if nb_imps else 0:.4f}")

    anomalies = [r for r in matches if r['position'] > 3.0 or r['ctr'] < 0.10]

    print(f"brand_anomalies:{len(anomalies)}")
    print("--- brand anomalies ---")
    for r in anomalies:
        print(f"  query='{r['keys'][0]}' pos={r['position']:.2f} "
              f"ctr={r['ctr']:.4f} imps={r['impressions']}")


CRUX_ENDPOINT = ('https://chromeuxreport.googleapis.com/v1/'
                 'records:queryRecord')
# p75 thresholds: (good_max, poor_min) — web.dev/articles/vitals.
CRUX_THRESHOLDS = {
    'largest_contentful_paint': ('lcp', 2500, 4000),
    'interaction_to_next_paint': ('inp', 200, 500),
    'cumulative_layout_shift': ('cls', 0.1, 0.25),
}


def _crux_rate(value, good, poor):
    if value is None:
        return 'n/a'
    if value <= good:
        return 'good'
    return 'poor' if value > poor else 'needs_improvement'


def crux_query(kind, target, form_factor, key):
    """One CrUX queryRecord call. Returns (status, metrics_dict). status is
    'ok', 'no_data' (404: not enough Chrome traffic), or 'error:<code>'."""
    body = {kind: target, 'formFactor': form_factor,
            'metrics': list(CRUX_THRESHOLDS) +
            ['experimental_time_to_first_byte']}
    req = urllib.request.Request(
        CRUX_ENDPOINT + '?' + urlencode({'key': key}),
        data=json.dumps(body).encode(), method='POST',
        headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return ('no_data' if e.code == 404 else f'error:{e.code}'), {}
    except (urllib.error.URLError, OSError, ValueError):
        return 'error:network', {}
    out = {}
    for name, m in data.get('record', {}).get('metrics', {}).items():
        p75 = m.get('percentiles', {}).get('p75')
        try:
            out[name] = float(p75) if p75 is not None else None
        except (TypeError, ValueError):
            out[name] = None
    return 'ok', out


def cmd_crux(targets_path):
    """Real-user Core Web Vitals from the CrUX API (the GSC API has no CWV
    endpoint). <targets_path>: one target per line, `origin <url>` or
    `url <url>`. Origins are queried PHONE + DESKTOP, URLs PHONE only (most
    URLs lack desktop data). Key read from CRUX_API_KEY env — never printed."""
    key = os.environ.get('CRUX_API_KEY', '').strip()
    if not key:
        print('CRUX_ERROR:no_key')
        return
    try:
        with open(targets_path, encoding='utf-8') as f:
            lines = [ln.split(None, 1) for ln in f if ln.strip()]
    except OSError as e:
        print(f"ERROR: cannot read {targets_path}: {e}", file=sys.stderr)
        sys.exit(1)
    jobs = []
    for parts in lines[:25]:
        if len(parts) != 2 or parts[0] not in ('origin', 'url'):
            continue
        kind, target = parts[0], parts[1].strip()
        for ff in (('PHONE', 'DESKTOP') if kind == 'origin' else ('PHONE',)):
            jobs.append((kind, target, ff))
    print(f"crux_queries:{len(jobs)}")
    print("--- crux records ---")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda j: (j, crux_query(*j, key)), jobs))
    poor = 0
    for (kind, target, ff), (status, metrics) in results:
        if status != 'ok':
            print(f"  {kind}={target} ff={ff} status={status}")
            continue
        parts = []
        for name, (short, good, bad) in CRUX_THRESHOLDS.items():
            v = metrics.get(name)
            rate = _crux_rate(v, good, bad)
            poor += rate == 'poor'
            shown = 'n/a' if v is None else (f"{v:.3f}" if short == 'cls'
                                              else f"{v:.0f}")
            parts.append(f"{short}_p75={shown}({rate})")
        ttfb = metrics.get('experimental_time_to_first_byte')
        parts.append(f"ttfb_p75={'n/a' if ttfb is None else f'{ttfb:.0f}'}")
        print(f"  {kind}={target} ff={ff} status=ok " + ' '.join(parts))
    print(f"crux_poor_metrics:{poor}")


# ---------------------------------------------------------------------------
# Raw-HTML page audit — what a crawler that does not run JavaScript receives.
# Feeds three technical checks: content/metadata present only after JS
# (rendering), Googlebot's 2 MB HTML limit, and back-button hijacking signals
# in inline scripts (a Google spam policy).
# ---------------------------------------------------------------------------
PAGE_AUDIT_MAX_TARGETS = 25
PAGE_AUDIT_TIMEOUT_SEC = 30
PAGE_AUDIT_READ_CAP = 16 * 1024 * 1024      # never buffer more than 16 MB
GOOGLEBOT_HTML_LIMIT = 2 * 1024 * 1024       # Googlebot indexes the first 2 MB
PAGE_AUDIT_THIN_WORDS = 50
PAGE_AUDIT_USER_AGENT = 'bx-seo-audit/1.0'

_BODY_RE = re.compile(r'<body\b[^>]*>(.*)', re.I | re.S)
_STRIP_BLOCK_RE = re.compile(
    r'<(script|style|noscript|template|svg)\b.*?</\1\s*>', re.I | re.S)
_TAG_RE = re.compile(r'<[^>]+>')
_TITLE_RE = re.compile(r'<title\b[^>]*>(.*?)</title\s*>', re.I | re.S)
_LINK_TAG_RE = re.compile(r'<link\b[^>]*>', re.I)
_META_TAG_RE = re.compile(r'<meta\b[^>]*>', re.I)
_H1_RE = re.compile(r'<h1\b', re.I)
_JSONLD_RE = re.compile(
    r'<script\b[^>]*type\s*=\s*["\']application/ld\+json["\']', re.I)
_SCRIPT_RE = re.compile(r'<script\b([^>]*)>(.*?)</script\s*>', re.I | re.S)
_EMPTY_ROOT_RE = re.compile(
    r'<div\b[^>]*\bid\s*=\s*["\'](?:root|app|__next|__nuxt|svelte|main)["\']'
    r'[^>]*>\s*</div>', re.I)
_HISTORY_RE = re.compile(r'history\s*\.\s*(?:pushState|replaceState)\s*\(')
_POPSTATE_RE = re.compile(
    r'addEventListener\s*\(\s*["\']popstate["\']|onpopstate\s*=')
_NAVIGATE_RE = re.compile(
    r'location(?:\s*\.\s*href)?\s*=(?!=)|location\s*\.\s*(?:replace|assign)'
    r'\s*\(|history\s*\.\s*pushState\s*\(')


def _attr(tag, name):
    m = re.search(r'\b' + name + r'\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s>]+))',
                  tag, re.I)
    if not m:
        return None
    return next(g for g in m.groups() if g is not None)


# --- 2.20.0: JSON-LD fields, visible dates, main text, schema-vs-visible ----
_JSONLD_BLOCK_RE = re.compile(
    r'<script\b[^>]*type\s*=\s*["\']?application/ld\+json["\']?[^>]*>'
    r'(.*?)</script\s*>', re.I | re.S)
_MAIN_RE = re.compile(r'<(main|article)\b[^>]*>(.*)</\1\s*>', re.I | re.S)
_CHROME_BLOCK_RE = re.compile(
    r'<(nav|header|footer|aside)\b.*?</\1\s*>', re.I | re.S)
_TIME_DT_RE = re.compile(
    r'<time\b[^>]*\bdatetime\s*=\s*["\']?(\d{4}-\d{2}-\d{2})', re.I)
_ISO_DATE_RE = re.compile(r'\b((?:19|20)\d\d)-(\d\d)-(\d\d)\b')
_MONTHS = {m: i + 1 for i, m in enumerate(
    ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct',
     'nov', 'dec'])}
_MONTH_WORD = (r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|'
               r'june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|'
               r'nov(?:ember)?|dec(?:ember)?)\.?')
_MDY_RE = re.compile(_MONTH_WORD + r'\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+'
                     r'((?:19|20)\d\d)\b', re.I)
_DMY_RE = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+' + _MONTH_WORD +
                     r',?\s+((?:19|20)\d\d)\b', re.I)
JSONLD_FIELDS = ('name', 'headline', 'author', 'datePublished',
                 'dateModified', 'price', 'priceCurrency', 'address',
                 'telephone')
SCHEMA_CHECK_FIELDS = ('name', 'headline', 'price', 'address', 'telephone',
                       'author', 'datePublished')
SCHEMA_CHECK_CAP = 40
# Wrapper types whose `name` mirrors <title>/site name, not body copy: not
# checked against visible text (they would be noise, not truthfulness).
SCHEMA_CHECK_SKIP_TYPES = {'website', 'webpage', 'collectionpage', 'itempage',
                           'aboutpage', 'contactpage', 'profilepage',
                           'searchresultspage', 'breadcrumblist', 'itemlist',
                           'listitem', 'imageobject', 'searchaction',
                           'sitenavigationelement'}
VISIBLE_DATES_CAP = 20


def _visible_text(fragment):
    return ' '.join(html.unescape(
        _TAG_RE.sub(' ', _STRIP_BLOCK_RE.sub(' ', fragment))).split())


def main_text_chars(body):
    """Characters of visible text in <main>/<article> if present, else in the
    body minus nav/header/footer/aside chrome."""
    m = _MAIN_RE.search(body)
    frag = m.group(2) if m else _CHROME_BLOCK_RE.sub(' ', body)
    return len(_visible_text(frag))


def _mk_date(y, mo, d):
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except (ValueError, TypeError):
        return None


def find_visible_dates(body, visible):
    """ISO dates a reader can see: <time datetime>, ISO text, and 'March 5,
    2026' / '5 March 2026' forms. Sorted, de-duplicated, capped."""
    found = set()
    for d in _TIME_DT_RE.findall(body):
        iso = _mk_date(*d.split('-'))
        if iso:
            found.add(iso)
    for y, mo, d in _ISO_DATE_RE.findall(visible):
        iso = _mk_date(y, mo, d)
        if iso:
            found.add(iso)
    for mon, d, y in _MDY_RE.findall(visible):
        iso = _mk_date(y, _MONTHS[mon[:3].lower()], d)
        if iso:
            found.add(iso)
    for d, mon, y in _DMY_RE.findall(visible):
        iso = _mk_date(y, _MONTHS[mon[:3].lower()], d)
        if iso:
            found.add(iso)
    return sorted(found)[:VISIBLE_DATES_CAP]


def _ld_text(v):
    """Flatten a JSON-LD value (string / Person / list / PostalAddress) to a
    display string, or None."""
    if v is None or v == '' or v == []:
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, str):
        return ' '.join(v.split())
    if isinstance(v, list):
        parts = [p for p in (_ld_text(x) for x in v) if p]
        return ', '.join(parts) or None
    if isinstance(v, dict):
        if v.get('name'):
            return _ld_text(v['name'])
        parts = [_ld_text(v.get(k)) for k in (
            'streetAddress', 'addressLocality', 'addressRegion', 'postalCode',
            'addressCountry')]
        parts = [p for p in parts if p]
        return ', '.join(parts) or None
    return None


def _ld_offer_field(node, key):
    offers = node.get('offers')
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if isinstance(offers, dict):
        v = offers.get(key)
        if v is None and key == 'price':
            v = offers.get('lowPrice')
        return v
    return None


def _ld_nodes(data):
    """Top-level nodes: a list, an @graph, or a single object."""
    if isinstance(data, list):
        out = []
        for x in data:
            out.extend(_ld_nodes(x))
        return out
    if isinstance(data, dict):
        if isinstance(data.get('@graph'), list):
            return [n for n in data['@graph'] if isinstance(n, dict)]
        return [data]
    return []


def extract_jsonld(text):
    """Parse every JSON-LD block. Returns ([{type, fields}], parse_errors).
    `fields` holds only the JSONLD_FIELDS present on the node (price and
    priceCurrency may come from `offers`)."""
    nodes, errors = [], 0
    for raw in _JSONLD_BLOCK_RE.findall(text):
        s = raw.strip()
        s = re.sub(r'^\s*(?:<!--|<!\[CDATA\[)', '', s)
        s = re.sub(r'(?:-->|\]\]>)\s*$', '', s).strip()
        if not s:
            continue
        try:
            data = json.loads(s)
        except ValueError:
            errors += 1
            continue
        for n in _ld_nodes(data):
            t = n.get('@type')
            t = ','.join(str(x) for x in t) if isinstance(t, list) else t
            fields = {}
            for k in JSONLD_FIELDS:
                v = n.get(k)
                if v is None and k in ('price', 'priceCurrency'):
                    v = _ld_offer_field(n, k)
                v = _ld_text(v)
                if v:
                    fields[k] = v
            nodes.append({'type': t, 'fields': fields})
    return nodes, errors


def _norm_words(s):
    return ' '.join(re.sub(r'[^\w]+', ' ', s.casefold()).split())


def _numbers_in(s):
    out = set()
    for tok in re.findall(r'\d[\d.,\s]*\d|\d', s):
        tok = tok.replace(' ', '')
        # 1,299.00 / 1.299,00 / 49,00 → float
        if ',' in tok and '.' in tok:
            tok = (tok.replace('.', '').replace(',', '.')
                   if tok.rfind(',') > tok.rfind('.') else tok.replace(',', ''))
        elif ',' in tok:
            head, _, tail = tok.rpartition(',')
            tok = (head.replace(',', '') + '.' + tail if len(tail) == 2
                   else tok.replace(',', ''))
        try:
            out.add(round(float(tok), 2))
        except ValueError:
            pass
    return out


def _phrase_in(value, visible_norm):
    n = _norm_words(value)
    return bool(n) and (' ' + n + ' ') in visible_norm


def _value_in_visible(field, value, visible_norm, visible_raw, dates):
    if field == 'price':
        try:
            want = round(float(str(value).replace(',', '')), 2)
        except ValueError:
            return _phrase_in(value, visible_norm)
        return want in _numbers_in(visible_raw)
    if field == 'telephone':
        digits = re.sub(r'\D', '', value)
        if len(digits) < 6:
            return False
        tail = digits[-9:]
        runs = re.findall(r'[+\d][\d\s().\-/]{5,}\d', visible_raw)
        return any(re.sub(r'\D', '', r).endswith(tail) for r in runs)
    if field in ('datePublished', 'dateModified'):
        return str(value)[:10] in dates
    if field == 'address':
        return _phrase_in(value.split(',')[0], visible_norm)
    if field == 'author':
        names = [n for n in (x.strip() for x in value.split(',')) if n]
        return bool(names) and all(_phrase_in(n, visible_norm) for n in names)
    return _phrase_in(value, visible_norm)


def schema_visible_checks(nodes, visible, dates):
    """Each checked JSON-LD value vs the page's visible raw text (normalised:
    case-folded, punctuation-insensitive; prices numeric; phones by digits;
    dates by ISO day against visible_dates)."""
    visible_norm = ' ' + _norm_words(visible) + ' '
    out = []
    for node in nodes:
        types = {t.strip().lower() for t in str(node['type'] or '').split(',')}
        if types and types <= SCHEMA_CHECK_SKIP_TYPES:
            continue
        for f in SCHEMA_CHECK_FIELDS:
            v = node['fields'].get(f)
            if not v:
                continue
            out.append({'type': node['type'], 'field': f, 'value': v,
                        'in_visible_text': _value_in_visible(
                            f, v, visible_norm, visible, set(dates))})
            if len(out) >= SCHEMA_CHECK_CAP:
                return out
    return out


def analyze_html(text):
    """Pure function: raw HTML string → facts a non-rendering crawler sees."""
    title_m = _TITLE_RE.search(text)
    title = ' '.join(html.unescape(title_m.group(1)).split()) if title_m else ''
    canonical = None
    for tag in _LINK_TAG_RE.findall(text):
        rel = (_attr(tag, 'rel') or '').lower().split()
        if 'canonical' in rel:
            canonical = _attr(tag, 'href') or ''
            break
    robots = None
    for tag in _META_TAG_RE.findall(text):
        if (_attr(tag, 'name') or '').lower() in ('robots', 'googlebot'):
            robots = (_attr(tag, 'content') or '').replace(' ', '')
            break
    body_m = _BODY_RE.search(text)
    body = body_m.group(1) if body_m else text
    visible = html.unescape(_TAG_RE.sub(' ', _STRIP_BLOCK_RE.sub(' ', body)))
    inline = [s for attrs, s in _SCRIPT_RE.findall(text)
              if not re.search(r'\bsrc\s*=', attrs, re.I)]
    history_calls = sum(len(_HISTORY_RE.findall(s)) for s in inline)
    popstate = any(_POPSTATE_RE.search(s) for s in inline)
    # Suspect = one inline script both listens for popstate AND navigates /
    # re-pushes history: the back button no longer goes back.
    hijack = any(_POPSTATE_RE.search(s) and _NAVIGATE_RE.search(s)
                 for s in inline)
    jsonld_nodes, jsonld_errors = extract_jsonld(text)
    visible_dates = find_visible_dates(body, visible)
    return {
        'title': title,
        'canonical': canonical,
        'robots': robots,
        'robots_meta': robots,
        'h1': len(_H1_RE.findall(body)),
        # 2.20.0: `jsonld` is the parsed node list; the count moved to
        # `jsonld_count` (the text record still prints `jsonld=<count>`).
        'jsonld_count': len(_JSONLD_RE.findall(text)),
        'jsonld': jsonld_nodes,
        'jsonld_parse_errors': jsonld_errors,
        'visible_dates': visible_dates,
        'main_text_chars': main_text_chars(body),
        'schema_visible_checks': schema_visible_checks(
            jsonld_nodes, visible, visible_dates),
        'words': len(visible.split()),
        'empty_root': bool(_EMPTY_ROOT_RE.search(body)),
        'inline_scripts': len(inline),
        'history_calls': history_calls,
        'popstate': popstate,
        'hijack_suspect': hijack,
    }


def _fetch_raw_page(url):
    """GET without running JS. Returns (status, final_url, body_bytes,
    charset, x_robots, truncated)."""
    req = urllib.request.Request(url, headers={
        'User-Agent': PAGE_AUDIT_USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Encoding': 'identity'})
    try:
        with urllib.request.urlopen(req, timeout=PAGE_AUDIT_TIMEOUT_SEC) as resp:
            raw = resp.read(PAGE_AUDIT_READ_CAP + 1)
            if (resp.headers.get('Content-Encoding') or '').lower() == 'gzip':
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass
            truncated = len(raw) > PAGE_AUDIT_READ_CAP
            return (resp.status, resp.geturl(), raw[:PAGE_AUDIT_READ_CAP],
                    resp.headers.get_content_charset() or 'utf-8',
                    resp.headers.get('X-Robots-Tag') or '', truncated)
    except urllib.error.HTTPError as e:
        return e.code, url, b'', 'utf-8', '', False
    except (urllib.error.URLError, OSError, ValueError) as e:
        # Name the cause: an `error:ssl` is usually the local Python's CA
        # store, not the site — the orchestrator must not report it as broken.
        reason = str(getattr(e, 'reason', e)).lower()
        kind = ('ssl' if 'ssl' in reason or 'certificate' in reason else
                'timeout' if 'timed out' in reason else 'network')
        return f'error:{kind}', url, b'', 'utf-8', '', False


def _audit_one(url):
    status, final, raw, charset, x_robots, truncated = _fetch_raw_page(url)
    rec = {'url': url, 'status': status, 'final': final,
           'bytes': len(raw), 'truncated': truncated, 'x_robots': x_robots}
    if status == 200 and raw:
        try:
            text = raw.decode(charset, errors='replace')
        except LookupError:
            text = raw.decode('utf-8', errors='replace')
        rec.update(analyze_html(text))
    return rec


def _yn(v):
    return 'yes' if v else 'no'


def cmd_page_audit(targets_path, out_path=None):
    """Fetch up to 25 URLs as a non-rendering crawler and print one record
    per URL. Byte counts are of the uncompressed HTML (the size Googlebot's
    limit applies to)."""
    try:
        with open(targets_path, encoding='utf-8') as f:
            urls = [ln.strip() for ln in f if ln.strip()]
    except OSError as e:
        print(f"ERROR: cannot read {targets_path}: {e}", file=sys.stderr)
        sys.exit(1)
    urls = list(dict.fromkeys(urls))[:PAGE_AUDIT_MAX_TARGETS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        recs = list(pool.map(_audit_one, urls))
    over = thin = hijack = 0
    print(f"pages_audited:{len(recs)}")
    print("--- page audit records ---")
    for r in recs:
        if r['status'] != 200 or 'words' not in r:
            print(f"  url={r['url']} status={r['status']}")
            continue
        is_over = r['bytes'] > GOOGLEBOT_HTML_LIMIT or r['truncated']
        is_thin = r['words'] < PAGE_AUDIT_THIN_WORDS
        over += is_over
        thin += is_thin
        hijack += r['hijack_suspect']
        size = (f">{PAGE_AUDIT_READ_CAP}" if r['truncated'] else str(r['bytes']))
        print(f"  url={r['url']} status=200 final={r['final']} bytes={size} "
              f"over_2mb={_yn(is_over)} title={_yn(r['title'])} "
              f"canonical={r['canonical'] if r['canonical'] is not None else 'none'} "
              f"robots={r['robots'] or 'none'} "
              f"x_robots={r['x_robots'].replace(' ', '') or 'none'} "
              f"h1={r['h1']} jsonld={r['jsonld_count']} words={r['words']} "
              f"empty_root={_yn(r['empty_root'])} "
              f"inline_scripts={r['inline_scripts']} "
              f"history_calls={r['history_calls']} "
              f"popstate={_yn(r['popstate'])} "
              f"hijack_suspect={_yn(r['hijack_suspect'])} "
              f"jsonld_types={','.join(str(n['type']) for n in r['jsonld']) or 'none'} "
              f"jsonld_parse_errors={r['jsonld_parse_errors']} "
              f"main_text_chars={r['main_text_chars']} "
              f"schema_visible_mismatch="
              f"{sum(1 for c in r['schema_visible_checks'] if not c['in_visible_text'])}")
    print(f"over_2mb_count:{over}")
    print(f"thin_raw_count:{thin}")
    print(f"hijack_suspect_count:{hijack}")
    if out_path:
        _write_json_out(out_path, {'status': 'ok', 'pages': recs})
        print(f"page_audit_json:{out_path}")


# ---------------------------------------------------------------------------
# Search Analytics trends — keyword cannibalization + content decay.
# Two signals Q1-Q3 cannot give: Q1/Q2 have one dimension each, and every
# query covers a single window.
# ---------------------------------------------------------------------------
SA_TREND_TTL_SEC = 24 * 3600
SA_ROW_LIMIT = 25000
CANNIBAL_MIN_QUERY_IMPS = 100
CANNIBAL_MIN_PAGE_SHARE = 0.10
DECAY_WINDOW_DAYS = 28
DECAY_MIN_BASE_CLICKS = 30
DECAY_MAX_RATIO = 0.70        # newest window ≤ 70% of oldest
TREND_TOP_N = 20


def _strip_fragment(u):
    return u.split('#', 1)[0]


def find_cannibalization(rows, brand_terms=()):
    """rows: Search Analytics rows with keys [query, page]. Returns a list of
    {query, impressions, clicks, pages:[{url, share, position, clicks}]} for
    non-brand queries where 2+ URLs each hold ≥10% of the impressions."""
    brand = [b.strip().lower() for b in brand_terms if b.strip()]
    by_q = defaultdict(dict)
    for r in rows:
        keys = r.get('keys') or []
        if len(keys) < 2:
            continue
        q, page = keys[0], _strip_fragment(keys[1])
        slot = by_q[q].setdefault(page, {'imps': 0, 'clicks': 0, 'pos_w': 0.0})
        imps = r.get('impressions', 0) or 0
        slot['imps'] += imps
        slot['clicks'] += r.get('clicks', 0) or 0
        slot['pos_w'] += (r.get('position', 0) or 0) * imps
    out = []
    for q, pages in by_q.items():
        if any(b in q.lower() for b in brand):
            continue
        total = sum(p['imps'] for p in pages.values())
        if total < CANNIBAL_MIN_QUERY_IMPS:
            continue
        sig = [(u, p) for u, p in pages.items()
               if p['imps'] / total >= CANNIBAL_MIN_PAGE_SHARE]
        if len(sig) < 2:
            continue
        sig.sort(key=lambda x: -x[1]['imps'])
        out.append({
            'query': q, 'impressions': total,
            'clicks': sum(p['clicks'] for p in pages.values()),
            'pages': [{'url': u, 'share': p['imps'] / total,
                       'position': p['pos_w'] / p['imps'] if p['imps'] else 0,
                       'clicks': p['clicks']} for u, p in sig]})
    out.sort(key=lambda x: -x['impressions'])
    return out


def find_decay(windows):
    """windows: [oldest, middle, newest] — each {page: (clicks, imps)}.
    Decay = clicks fell in both steps, newest ≤ 70% of oldest, oldest ≥ 30."""
    w1, w2, w3 = windows
    out = []
    for page, (c1, i1) in w1.items():
        if c1 < DECAY_MIN_BASE_CLICKS:
            continue
        c2, i2 = w2.get(page, (0, 0))
        c3, i3 = w3.get(page, (0, 0))
        if not (c1 > c2 > c3 or (c1 > c2 and c3 == 0)):
            continue
        if c3 > c1 * DECAY_MAX_RATIO:
            continue
        if i3 == 0:
            pattern = 'vanished'
        elif i3 <= i1 * 0.8:
            pattern = 'visibility_loss'
        else:
            pattern = 'ctr_loss'
        out.append({'url': page, 'clicks': (c1, c2, c3),
                    'imps': (i1, i2, i3), 'lost': c1 - c3,
                    'pattern': pattern})
    out.sort(key=lambda x: -x['lost'])
    return out


# --- 2.20.0: AI-Overview-prone query segmentation -------------------------
AIO_QUESTION_WORDS = ('who', 'what', 'when', 'where', 'why', 'how', 'which',
                      'can', 'does', 'is', 'are', 'should', 'vs', 'best',
                      'difference')
AIO_MIN_WORDS = 6
AIO_CTR_DROP = 0.20          # CTR fell ≥ 20% relative
AIO_MAX_POS_DELTA = 1.0      # while position moved ≤ 1.0
AIO_MIN_SHARE = 0.60         # and ≥ 60% of impressions are aio_prone
AIO_MIN_PAGE_IMPS = 100      # noise floor, both windows
AIO_TOP_N = 50


def aio_prone(query, question_words=AIO_QUESTION_WORDS):
    """Question-form (a question word anywhere as a whole word) or long-tail
    (≥ 6 words). English by default; --question-words overrides."""
    words = re.findall(r"[\w'’-]+", (query or '').casefold())
    if len(words) >= AIO_MIN_WORDS:
        return True
    qw = {w.casefold() for w in question_words}
    return any(w in qw for w in words)


def _seg_stats(rows, question_words):
    """rows: query×page rows → {aio_prone|other: [clicks, imps, pos_w]} and
    per page {page: {'aio': imps, 'all': [clicks, imps, pos_w]}}."""
    seg = {'aio_prone': [0, 0, 0.0], 'other': [0, 0, 0.0]}
    pages = defaultdict(lambda: {'aio': 0, 'all': [0, 0, 0.0]})
    for r in rows:
        keys = r.get('keys') or []
        if len(keys) < 2:
            continue
        c = r.get('clicks', 0) or 0
        i = r.get('impressions', 0) or 0
        pw = (r.get('position', 0) or 0) * i
        name = 'aio_prone' if aio_prone(keys[0], question_words) else 'other'
        for slot in (seg[name], pages[_strip_fragment(keys[1])]['all']):
            slot[0] += c
            slot[1] += i
            slot[2] += pw
        if name == 'aio_prone':
            pages[_strip_fragment(keys[1])]['aio'] += i
    return seg, pages


def _ratio(a, b):
    return a / b if b else None


def ctr_segments(rows_now, rows_prev, question_words=AIO_QUESTION_WORDS):
    """CTR/position now vs previous window, split aio_prone vs other, plus
    ai_overview_compression pages: CTR fell ≥ 20% relative, |Δpos| ≤ 1.0,
    ≥ 60% of current impressions aio_prone, ≥ 100 impressions both windows.
    ctr_delta is the relative change ((now − prev) / prev)."""
    seg_now, pages_now = _seg_stats(rows_now, question_words)
    seg_prev, pages_prev = _seg_stats(rows_prev, question_words)
    segments = {}
    for name in ('aio_prone', 'other'):
        cn, inow, pwn = seg_now[name]
        cp, iprev, pwp = seg_prev[name]
        segments[name] = {
            'clicks': cn, 'impressions': inow,
            'clicks_prev': cp, 'impressions_prev': iprev,
            'ctr_now': _ratio(cn, inow), 'ctr_prev': _ratio(cp, iprev),
            'pos_now': _ratio(pwn, inow), 'pos_prev': _ratio(pwp, iprev)}
    comp = []
    for page, now in pages_now.items():
        prev = pages_prev.get(page)
        if not prev:
            continue
        cn, inow, pwn = now['all']
        cp, iprev, pwp = prev['all']
        if inow < AIO_MIN_PAGE_IMPS or iprev < AIO_MIN_PAGE_IMPS or cp == 0:
            continue
        ctr_now, ctr_prev = cn / inow, cp / iprev
        rel = (ctr_now - ctr_prev) / ctr_prev
        pos_delta = pwn / inow - pwp / iprev
        share = now['aio'] / inow
        if (rel <= -AIO_CTR_DROP and abs(pos_delta) <= AIO_MAX_POS_DELTA
                and share >= AIO_MIN_SHARE):
            comp.append({'page': page, 'aio_share': round(share, 4),
                         'ctr_delta': round(rel, 4),
                         'pos_delta': round(pos_delta, 2),
                         'ctr_now': round(ctr_now, 4),
                         'ctr_prev': round(ctr_prev, 4),
                         'impressions': inow, 'clicks': cn,
                         'clicks_prev': cp})
    comp.sort(key=lambda x: (x['ctr_delta'], -x['impressions']))
    return segments, comp[:AIO_TOP_N]


def _sa_rows(site_url, body, cache_dir, no_cache, creds):
    """One cached Search Analytics call. creds is a 1-slot list filled lazily
    so a fully cached run never mints a token. Returns (rows, status)."""
    key = hashlib.sha1(
        (site_url + '|' + json.dumps(body, sort_keys=True)).encode()).hexdigest()
    path = os.path.join(cache_dir, f'sa-trend-{key}.json')
    if not no_cache and _ui_cache_is_fresh(path, SA_TREND_TTL_SEC):
        data = _load_json_safe(path, None)
        if isinstance(data, dict):
            return data.get('rows', []) or [], 'hit'
    if not creds:
        creds.append(resolve_credentials())   # raises CredentialError
    token, quota = creds[0]
    api = (f'https://www.googleapis.com/webmasters/v3/sites/'
           f'{quote(site_url, safe="")}/searchAnalytics/query')
    req = urllib.request.Request(
        api, data=json.dumps(body).encode(), method='POST', headers={
            'Authorization': f'Bearer {token}',
            'x-goog-user-project': quota,
            'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return [], f'error:{e.code}'
    except (urllib.error.URLError, OSError, ValueError):
        return [], 'error:network'
    _atomic_write_json(path, data)
    return data.get('rows', []) or [], 'miss'


def cmd_sa_trends(cache_dir, site_url, end_date, lookback_days, brand_csv='',
                  out_path=None, question_words=AIO_QUESTION_WORDS):
    """Cannibalization (query×page over the lookback window) + decay (three
    consecutive 28-day page windows ending at end_date) + 2.20.0 CTR
    segmentation (query×page for the newest and previous 28-day windows)."""
    end = _parse_date(end_date)
    if end is None:
        print(f"ERROR: bad end_date '{end_date}'", file=sys.stderr)
        sys.exit(3)
    no_cache = os.environ.get('NO_CACHE') == '1'
    creds = []
    statuses = []
    try:
        start = end - timedelta(days=int(lookback_days) - 1)
        rows, st = _sa_rows(site_url, {
            'startDate': start.isoformat(), 'endDate': end.isoformat(),
            'dimensions': ['query', 'page'], 'type': 'web',
            'rowLimit': SA_ROW_LIMIT}, cache_dir, no_cache, creds)
        statuses.append(st)
        windows = []
        for k in (2, 1, 0):  # oldest first
            w_end = end - timedelta(days=DECAY_WINDOW_DAYS * k)
            w_start = w_end - timedelta(days=DECAY_WINDOW_DAYS - 1)
            w_rows, w_st = _sa_rows(site_url, {
                'startDate': w_start.isoformat(), 'endDate': w_end.isoformat(),
                'dimensions': ['page'], 'type': 'web',
                'rowLimit': SA_ROW_LIMIT}, cache_dir, no_cache, creds)
            statuses.append(w_st)
            agg = defaultdict(lambda: [0, 0])
            for r in w_rows:
                p = _strip_fragment((r.get('keys') or [''])[0])
                agg[p][0] += r.get('clicks', 0) or 0
                agg[p][1] += r.get('impressions', 0) or 0
            windows.append({p: tuple(v) for p, v in agg.items()})
        seg_rows = []
        for k in (1, 0):  # previous, then newest 28-day window
            w_end = end - timedelta(days=DECAY_WINDOW_DAYS * k)
            w_start = w_end - timedelta(days=DECAY_WINDOW_DAYS - 1)
            q_rows, q_st = _sa_rows(site_url, {
                'startDate': w_start.isoformat(), 'endDate': w_end.isoformat(),
                'dimensions': ['query', 'page'], 'type': 'web',
                'rowLimit': SA_ROW_LIMIT}, cache_dir, no_cache, creds)
            statuses.append(q_st)
            seg_rows.append(q_rows)
    except CredentialError as e:
        if out_path:
            _write_json_out(out_path, {'status': 'unavailable',
                                       'reason': f'auth:{e.reason}'})
        print(f"AUTH_ERROR:{e.reason}")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(4)

    print(f"sa_trend_calls:{' '.join(statuses)}")
    cannibal = find_cannibalization(rows, brand_csv.split(',') if brand_csv else ())
    print(f"cannibal_queries:{len(cannibal)}")
    print("--- cannibalization ---")
    for c in cannibal[:TREND_TOP_N]:
        pages = ' ; '.join(
            f"{p['url']} ({p['share']:.0%}, pos {p['position']:.1f}, "
            f"clicks {p['clicks']})" for p in c['pages'])
        q = c['query'].replace("'", "’")
        print(f"  query='{q}' imps={c['impressions']} clicks={c['clicks']} "
              f"pages={len(c['pages'])} | {pages}")
    decay = find_decay(windows) if len(windows) == 3 else []
    print(f"decay_pages:{len(decay)}")
    print("--- content decay ---")
    for d in decay[:TREND_TOP_N]:
        c1, c2, c3 = d['clicks']
        i1, i2, i3 = d['imps']
        print(f"  url={d['url']} clicks={c1}>{c2}>{c3} "
              f"change={(c3 - c1) / c1:+.0%} imps={i1}>{i2}>{i3} "
              f"pattern={d['pattern']}")
    segments, compression = ctr_segments(seg_rows[1], seg_rows[0],
                                         question_words)
    print("--- ctr segments (newest vs previous 28 days) ---")
    for name in ('aio_prone', 'other'):
        g = segments[name]
        print(f"  segment={name} clicks={g['clicks']} "
              f"imps={g['impressions']} ctr={_fmt_pct(g['ctr_prev'])}>"
              f"{_fmt_pct(g['ctr_now'])} pos={_fmt_num(g['pos_prev'])}>"
              f"{_fmt_num(g['pos_now'])}")
    print(f"ai_overview_compression:{len(compression)}")
    for c in compression[:TREND_TOP_N]:
        print(f"  url={c['page']} aio_share={c['aio_share']:.0%} "
              f"ctr_delta={c['ctr_delta']:+.0%} pos_delta={c['pos_delta']:+.1f}")
    if out_path:
        _write_json_out(out_path, {
            'status': 'ok', 'calls': statuses,
            'cannibalization': cannibal, 'decay': decay,
            'question_words': list(question_words),
            'ctr_segments': segments,
            'ai_overview_compression': compression})
        print(f"sa_trends_json:{out_path}")


def _fmt_pct(v):
    return 'n/a' if v is None else f"{v:.2%}"


def _fmt_num(v):
    return 'n/a' if v is None else f"{v:.1f}"


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
    snapshot files that would corrupt the next run's regression diff.

    Only this run's URLs are included (the manifest inspect-batch writes), so
    consecutive snapshots compare like with like."""
    files, _ = _run_ui_files(cache_dir)

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
    if not inspections:
        # An empty snapshot would become the next run's "previous" baseline and
        # silently disable regression detection (nothing to flip from). It also
        # must not trigger retention, which could then evict a real baseline.
        print("snapshot_write_failed:no_inspections_in_cache")
        sys.exit(1)
    if not _atomic_write_json(output_path, snapshot):
        print(f"snapshot_write_failed:{output_path}")
        sys.exit(1)
    print(f"snapshot_written:{output_path}")
    removed, kept = snapshot_prune(os.path.dirname(output_path) or '.')
    print(f"snapshots_pruned:{removed}")
    print(f"snapshots_retained:{kept}")


# Snapshot retention. Runs ONLY after a successful snapshot write — never at
# run start. S68 (burakarik.com): the old Turn-1 `find -mtime +30 -delete`
# deleted the 31-day-old baseline a planned month-later comparison depended
# on, and did so before the auth probe failed, so the run lost its baseline
# AND wrote no replacement. Rules:
#   - the newest SNAPSHOT_KEEP_MIN snapshots are kept regardless of age, so a
#     site audited every few months still has a baseline;
#   - older ones are removed once past SNAPSHOT_MAX_AGE_DAYS.
# Age comes from the filename's run timestamp (<YYYY-MM-DDTHHMMSS>-<sha7>.json),
# not mtime — copying or syncing .seo-data/ resets mtimes.
SNAPSHOT_KEEP_MIN = 5
SNAPSHOT_MAX_AGE_DAYS = 180
_SNAPSHOT_NAME_RE = re.compile(r'^(\d{4}-\d{2}-\d{2})T\d{6}-[0-9a-f]+\.json$')


def snapshot_prune(snap_dir, today=None):
    """Apply the retention rule to snap_dir. Returns (removed, kept).
    Files that don't match the snapshot name pattern are left alone."""
    today = today or date.today()
    try:
        names = sorted(n for n in os.listdir(snap_dir)
                       if _SNAPSHOT_NAME_RE.match(n))
    except OSError:
        return 0, 0
    protected = set(names[-SNAPSHOT_KEEP_MIN:])
    removed = 0
    for n in names:
        if n in protected:
            continue
        try:
            run_day = date.fromisoformat(_SNAPSHOT_NAME_RE.match(n).group(1))
        except ValueError:
            continue
        if (today - run_day).days > SNAPSHOT_MAX_AGE_DAYS:
            try:
                os.remove(os.path.join(snap_dir, n))
                removed += 1
            except OSError:
                pass
    return removed, len(names) - removed


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


_INDEXED_CLUSTERS = ('submitted_indexed', 'indexed_info')


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

        # "Indexed, not submitted in sitemap" / "Indexed, though blocked by
        # robots.txt" are still indexed (cluster_for's indexed_info). Counting
        # only "Submitted and indexed" reported a URL merely dropped from the
        # sitemap as a deindex regression.
        prev_was_indexed = cluster_for(prev_lower, '') in _INDEXED_CLUSTERS
        cur_is_indexed = cluster_for(cur_lower, '') in _INDEXED_CLUSTERS

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


RUN_MANIFEST_NAME = 'last-inspect-run.json'


def _run_ui_files(cache_dir):
    """The ui-*.json files belonging to the most recent inspect-batch run.

    The cache keeps ui-* entries for up to 14 days, so globbing every ui-*
    file mixed URLs this run never selected (stale coverage states, other
    properties sharing the cache) into clusters and snapshots — and two
    snapshots then covered different URL sets, so the regression diff read
    set drift as transitions. inspect-batch writes a manifest of its URL set;
    use it when present. Returns (files, scoped: bool)."""
    manifest = os.path.join(cache_dir, RUN_MANIFEST_NAME)
    try:
        with open(manifest, 'r', encoding='utf-8') as f:
            m = json.load(f)
        site, urls = m['site_url'], m['urls']
    except (OSError, ValueError, KeyError, TypeError):
        return sorted(glob.glob(os.path.join(cache_dir, 'ui-*.json'))), False
    files = [_ui_cache_path(cache_dir, site, u) for u in urls]
    return sorted(p for p in files if os.path.exists(p)), True


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
    # Mint credentials inside the helper — the token never leaves this process,
    # so URL Inspection never exposes it to the orchestrator/model context.
    try:
        token, quota_project = resolve_credentials()
    except CredentialError as e:
        # Emit a stdout marker BEFORE exiting non-zero so the orchestrator can't
        # mistake a credential failure for "total_attempted:0 / zero findings"
        # and silently drop the entire indexing signal.
        print(f'inspect_batch_error:{e.reason}')
        if e.detail:
            print('AUTH_DETAIL:' + ' '.join(str(e.detail).split())[:300])
        print(f'ERROR: {e}', file=sys.stderr)
        sys.exit(4)
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

    # Record this run's URL set so clusters/snapshot-write read only these
    # entries, not every ui-* file still in the 14-day cache.
    _atomic_write_json(os.path.join(cache_dir, RUN_MANIFEST_NAME),
                       {'site_url': site_url, 'urls': urls})

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


@contextlib.contextmanager
def _rmw_lock(path, timeout=10.0):
    """Advisory lock for a read-modify-write cycle on `path`.

    _atomic_write_json makes the final os.replace atomic, which stops two
    processes interleaving *content*. It does nothing about two processes
    reading the same pre-mutation state and the second replace discarding the
    first's additions -- a lost update. A run_count increment or a watchpoint
    refresh silently reverts, and the escalation threshold downstream can then
    miss a real regression because the increment vanished. This closes that
    half of the race; the docstring below only ever claimed the other half.

    Degrades to unlocked after `timeout` rather than failing the run, so the
    worst case is the old behaviour and never worse.

    Do NOT add an age check inside the retry loop. One that fails for any
    reason reads as "stale", unlinks a LIVE lock, and admits several writers at
    once -- strictly worse than no lock. Reaping happens once, after the budget
    is spent. (An earlier version of the sibling shell fix had exactly that bug
    and only a concurrency test caught it.)
    """
    lock_path = f"{path}.lock"
    parent = os.path.dirname(lock_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd = None
    deadline = time.time() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() >= deadline:
                try:
                    os.unlink(lock_path)
                    fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except OSError:
                    fd = None
                break
            time.sleep(0.02)
        except OSError:
            fd = None
            break
    try:
        yield
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
            try:
                os.unlink(lock_path)
            except OSError:
                pass


def _atomic_write_json(path, data):
    """Atomic write via .tmp + os.replace. PID-suffixed tmp so two concurrent
    /bx:seo processes writing the same target don't interleave content in
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
    """Serialised read-modify-write. See _rmw_lock: the atomic replace alone
    does not stop a concurrent run's additions being discarded."""
    with _rmw_lock(history_path):
        return _history_update_unlocked(findings_jsonl, history_path, commit_sha, run_date)


def _history_update_unlocked(findings_jsonl, history_path, commit_sha, run_date):
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
    """Serialised read-modify-write. See _rmw_lock: the atomic replace alone
    does not stop a concurrent run's additions being discarded."""
    with _rmw_lock(watchpoints_path):
        return _watchpoint_emit_unlocked(findings_jsonl, watchpoints_path, commit_sha, run_date)


def _watchpoint_emit_unlocked(findings_jsonl, watchpoints_path, commit_sha, run_date):
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
    """Serialised read-modify-write. See _rmw_lock: the atomic replace alone
    does not stop a concurrent run's additions being discarded."""
    with _rmw_lock(watchpoints_path):
        return _watchpoint_check_unlocked(watchpoints_path, q2_pages_path, run_date)


def _watchpoint_check_unlocked(watchpoints_path, q2_pages_path, run_date):
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


def _threshold_status(b, c, invert=False):
    """Classify a baseline→current move as improved/regressed/unchanged.

    invert=True for position, where a LOWER value is better — it flips both the
    delta direction and the b<=0 case (a zero baseline position is meaningless,
    so it stays 'unchanged' rather than counting any current value as improved).
    """
    if b <= 0:
        if invert:
            return 'unchanged'
        return 'unchanged' if c <= 0 else 'improved'
    delta_ratio = (b - c) / b if invert else (c - b) / b
    if delta_ratio > 0.10:
        return 'improved'
    if delta_ratio < -0.10:
        return 'regressed'
    return 'unchanged'


def _watchpoint_status(baseline, current):
    """Compare baseline vs current metrics. Decide on the primary metric:
    if baseline has ctr → ctr-anchored (lower-is-worse); if baseline has
    position → position-anchored (lower-is-better); else impressions."""
    for metric, invert in (('ctr', False), ('position', True), ('impressions', False)):
        if metric in baseline and metric in current:
            return _threshold_status(baseline[metric], current[metric], invert)
    return 'unchanged'


# ---------------------------------------------------------------------------
# 2.20.0 — JSON-out subcommands: bot-probe, render-compare, update-windows,
# bing-exports. Each writes JSON to --out and prints one summary line; a
# network failure degrades to {"status":"unavailable","reason":...}.
# ---------------------------------------------------------------------------
def _write_json_out(path, data):
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _net_reason(e):
    if isinstance(e, urllib.error.HTTPError):
        return f'http:{e.code}'
    reason = str(getattr(e, 'reason', e)).lower()
    if 'ssl' in reason or 'certificate' in reason:
        return 'ssl'
    if 'timed out' in reason:
        return 'timeout'
    return 'network'


class _HopCounter(urllib.request.HTTPRedirectHandler):
    """Follows redirects like the default handler, recording each hop."""

    def __init__(self):
        super().__init__()
        self.hops = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append({'status': code, 'location': newurl})
        return super().redirect_request(req, fp, code, msg, headers, newurl)


BOT_PROBE_TIMEOUT_SEC = 10
BOT_PROBE_MAX_PAGES = 5
BOT_PROBE_WORKERS = 8
BOT_PROBE_READ_CAP = 4 * 1024 * 1024
BOT_PROBE_TINY_BODY = 2048          # a 403/429/503 under this is a stub page
BOT_PROBE_DIFFERS_RATIO = 0.5

# AI crawler table (as of 2026-11). `fetch`: probed over HTTP; robots-only
# tokens (Google-Extended, Applebot-Extended) are never fetched — they are not
# real crawlers, only robots.txt product tokens. CCBot is robots-only here too.
_MOZ = 'Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; '
AI_BOTS = [
    {'name': 'OAI-SearchBot', 'vendor': 'OpenAI', 'group': 'search',
     'fetch': True, 'ua': _MOZ + 'OAI-SearchBot/1.3; +https://openai.com/searchbot)'},
    {'name': 'Claude-SearchBot', 'vendor': 'Anthropic', 'group': 'search',
     'fetch': True, 'ua': _MOZ + 'Claude-SearchBot/1.0; +Claude-SearchBot@anthropic.com)'},
    {'name': 'PerplexityBot', 'vendor': 'Perplexity', 'group': 'search',
     'fetch': True, 'ua': _MOZ + 'PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)'},
    {'name': 'ChatGPT-User', 'vendor': 'OpenAI', 'group': 'user',
     'fetch': True, 'ua': _MOZ + 'ChatGPT-User/1.0; +https://openai.com/bot)'},
    {'name': 'Claude-User', 'vendor': 'Anthropic', 'group': 'user',
     'fetch': True, 'ua': _MOZ + 'Claude-User/1.0; +Claude-User@anthropic.com)'},
    {'name': 'Perplexity-User', 'vendor': 'Perplexity', 'group': 'user',
     'fetch': True, 'ua': _MOZ + 'Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)'},
    {'name': 'GPTBot', 'vendor': 'OpenAI', 'group': 'training',
     'fetch': True, 'ua': _MOZ + 'GPTBot/1.3; +https://openai.com/gptbot)'},
    {'name': 'ClaudeBot', 'vendor': 'Anthropic', 'group': 'training',
     'fetch': True, 'ua': _MOZ + 'ClaudeBot/1.0; +claudebot@anthropic.com)'},
    {'name': 'Google-Extended', 'vendor': 'Google', 'group': 'training',
     'fetch': False, 'ua': None},
    {'name': 'Applebot-Extended', 'vendor': 'Apple', 'group': 'training',
     'fetch': False, 'ua': None},
    {'name': 'Meta-ExternalAgent', 'vendor': 'Meta', 'group': 'training',
     'fetch': True, 'ua': 'meta-externalagent/1.1 (+https://developers.facebook.com/docs/sharing/webmasters/crawler)'},
    {'name': 'CCBot', 'vendor': 'Common Crawl', 'group': 'training',
     'fetch': False, 'ua': None},
    {'name': 'OAI-AdsBot', 'vendor': 'OpenAI', 'group': 'ads',
     'fetch': True, 'ua': _MOZ + 'OAI-AdsBot/1.0; +https://openai.com/adsbot)'},
]
CONTROL_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36')
CONTROL_NAME = 'control'

_CHALLENGE_BODY_ANY = [   # checked on any status
    ('cloudflare:challenge-title', re.compile(r'<title>\s*Just a moment', re.I)),
    ('cloudflare:cf-chl', re.compile(r'cf-chl|/cdn-cgi/challenge-platform/', re.I)),
    ('vercel:checkpoint', re.compile(r'Vercel Security Checkpoint', re.I)),
    ('imperva:incapsula', re.compile(r'_Incapsula_Resource|Incapsula incident', re.I)),
]
_CHALLENGE_BODY_ERR = [   # checked only on a 4xx/5xx response
    ('cloudflare:just-a-moment', re.compile(r'Just a moment', re.I)),
    ('akamai:access-denied', re.compile(r'Access Denied', re.I)),
    ('imperva:incapsula', re.compile(r'Incapsula', re.I)),
    ('vercel:checkpoint', re.compile(r'checkpoint', re.I)),
]


def detect_challenge(status, headers, body):
    """Return a challenge marker string, or None. headers: dict with
    lower-case keys; body: bytes (only the first 64 KB is inspected)."""
    if headers.get('cf-mitigated'):
        return 'cloudflare:cf-mitigated'
    if headers.get('x-vercel-mitigated'):
        return 'vercel:x-vercel-mitigated'
    text = body[:65536].decode('utf-8', errors='replace')
    for marker, rx in _CHALLENGE_BODY_ANY:
        if rx.search(text):
            return marker
    if isinstance(status, int) and status >= 400:
        for marker, rx in _CHALLENGE_BODY_ERR:
            if rx.search(text):
                return marker
        if status in (403, 429, 503) and len(body) < BOT_PROBE_TINY_BODY:
            return f'generic:{status}-tiny-body'
    return None


def _probe_get(url, ua, timeout=BOT_PROBE_TIMEOUT_SEC, count_hops=False):
    """One GET, redirects followed, no retries. Never raises."""
    hop = _HopCounter()
    opener = urllib.request.build_opener(hop)
    req = urllib.request.Request(url, headers={
        'User-Agent': ua, 'Accept': 'text/html,application/xhtml+xml,*/*',
        'Accept-Encoding': 'identity'})
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(BOT_PROBE_READ_CAP)
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            status, final = resp.status, resp.geturl()
    except urllib.error.HTTPError as e:
        try:
            body = e.read(BOT_PROBE_READ_CAP) or b''
        except OSError:
            body = b''
        hdrs = {k.lower(): v for k, v in (e.headers or {}).items()}
        status, final = e.code, e.geturl() or url
    except (urllib.error.URLError, OSError, ValueError) as e:
        return {'status': f'error:{_net_reason(e)}', 'bytes': 0,
                'final_url': url, 'headers': {}, 'body': b'',
                'hops': hop.hops}
    return {'status': status, 'bytes': len(body), 'final_url': final,
            'headers': hdrs, 'body': body, 'hops': hop.hops}


# --- robots.txt: groups, Content-Signal, Content-Usage, __usage_ groups ----
def parse_robots(text):
    """RFC 9309 grouping plus the AI-preference extensions. Returns
    {'groups': [{agents, rules:[{directive, path}], content_signals:[...],
    content_usage:[...]}], 'global_signals': [...], 'global_usage': [...]}."""
    groups, cur, last_was_agent = [], None, False
    global_signals, global_usage = [], []
    for line in (text or '').splitlines():
        line = line.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        key, _, val = line.partition(':')
        key, val = key.strip().lower(), val.strip()
        if key == 'user-agent':
            if cur is None or not last_was_agent:
                cur = {'agents': [], 'rules': [], 'content_signals': [],
                       'content_usage': []}
                groups.append(cur)
            cur['agents'].append(val)
            last_was_agent = True
            continue
        last_was_agent = False
        if key in ('allow', 'disallow'):
            if cur is not None:
                cur['rules'].append({'directive': key, 'path': val})
        elif key == 'content-signal':
            (cur['content_signals'] if cur is not None
             else global_signals).append(val)
        elif key == 'content-usage':
            (cur['content_usage'] if cur is not None
             else global_usage).append(val)
    return {'groups': groups, 'global_signals': global_signals,
            'global_usage': global_usage}


def _parse_prefs(val):
    """'search=yes, ai-train=no' or '/path train-ai=n' → (path, {k: v})."""
    path, prefs = None, {}
    for tok in re.split(r'[,\s]+', val):
        if not tok:
            continue
        if '=' in tok:
            k, _, v = tok.partition('=')
            prefs[k.strip().lower()] = v.strip().lower()
        elif tok.startswith('/') and path is None:
            path = tok
    return path, prefs


def _group_for(parsed, bot):
    """The group whose user-agent matches the bot token (case-insensitive),
    else the '*' group, else None. Returns (group, 'named'|'wildcard'|None)."""
    b = bot.lower()
    star = None
    for g in parsed['groups']:
        agents = [a.lower() for a in g['agents']]
        if b in agents:
            return g, 'named'
        if '*' in agents and star is None:
            star = g
    return (star, 'wildcard') if star else (None, None)


def _root_allowed(group):
    """RFC 9309 longest match for path '/' (allow wins a tie)."""
    best_len, verdict = -1, 'allow'
    for r in group['rules']:
        p = r['path']
        if r['directive'] == 'disallow' and p == '':
            continue  # empty Disallow = allow all
        pat = re.escape(p).replace(r'\*', '.*')
        if pat.endswith(r'\$'):
            pat = pat[:-2] + '$'
        if re.match(pat, '/'):
            ln = len(p)
            if ln > best_len or (ln == best_len and r['directive'] == 'allow'):
                best_len, verdict = ln, r['directive']
    return verdict


def _effective_prefs(parsed, field, bot):
    """Preferences declared for a bot: its named group's lines, else the '*'
    group's (the site-wide declaration), else lines outside any group."""
    g, _src = _group_for(parsed, bot)
    star, _ = _group_for(parsed, '*')
    vals = ((g[field] if g else []) or (star[field] if star else [])
            or parsed['global_signals' if field == 'content_signals'
                      else 'global_usage'])
    prefs = {}
    for v in vals:
        path, p = _parse_prefs(v)
        if path in (None, '/'):
            prefs.update(p)
    return prefs


def robots_report(text):
    """Contract shape: content_signals, usage_groups, content_usage,
    per_bot_allowed (+ per_bot_source), and policy_conflicts."""
    parsed = parse_robots(text)
    signals, usage = [], []
    for g in [{'agents': ['*(global)'],
               'content_signals': parsed['global_signals'],
               'content_usage': parsed['global_usage']}] + parsed['groups']:
        scope = ','.join(g['agents'])
        for v in g['content_signals']:
            _path, p = _parse_prefs(v)
            signals.append({'scope_user_agent': scope,
                            'search': p.get('search'),
                            'ai_input': p.get('ai-input'),
                            'ai_train': p.get('ai-train'), 'raw': v})
        for v in g['content_usage']:
            path, p = _parse_prefs(v)
            usage.append({'scope_user_agent': scope, 'path': path,
                          'prefs': p, 'raw': v})
    usage_groups = []
    for g in parsed['groups']:
        for a in g['agents']:
            if a.lower().startswith('__usage_'):
                usage_groups.append({'token': a, 'rules': g['rules'],
                                     'root': _root_allowed(g)})
    per_bot, per_src = {}, {}
    for b in AI_BOTS:
        g, src = _group_for(parsed, b['name'])
        per_bot[b['name']] = _root_allowed(g) if g else 'unspecified'
        per_src[b['name']] = src or 'none'
    conflicts = []
    by_group = defaultdict(list)
    for b in AI_BOTS:
        by_group[b['group']].append(b['name'])

    def allowed(names):
        return [n for n in names if per_bot[n] != 'disallow']

    def disallowed(names):
        return [n for n in names if per_bot[n] == 'disallow']

    for b in by_group['search'] + by_group['user']:
        p = _effective_prefs(parsed, 'content_signals', b)
        if p.get('ai-input') == 'no' and per_bot[b] != 'disallow':
            conflicts.append({'kind': 'ai_input_no_but_bot_allowed',
                              'detail': f'Content-Signal ai-input=no applies '
                                        f'to {b}, which robots.txt allows'})
        if p.get('search') == 'no' and per_bot[b] != 'disallow' \
                and b in by_group['search']:
            conflicts.append({'kind': 'search_no_but_bot_allowed',
                              'detail': f'Content-Signal search=no applies '
                                        f'to {b}, which robots.txt allows'})
    for b in by_group['training']:
        p = _effective_prefs(parsed, 'content_signals', b)
        u = _effective_prefs(parsed, 'content_usage', b)
        if p.get('ai-train') == 'yes' and per_bot[b] == 'disallow':
            conflicts.append({'kind': 'ai_train_yes_but_bot_disallowed',
                              'detail': f'Content-Signal ai-train=yes but '
                                        f'robots.txt disallows {b}'})
        if p.get('ai-train') == 'no' and per_bot[b] != 'disallow' \
                and per_src[b] == 'named':
            conflicts.append({'kind': 'ai_train_no_but_bot_allowed',
                              'detail': f'Content-Signal ai-train=no but a '
                                        f'named robots.txt group allows {b}'})
        if u.get('train-ai') in ('n', 'no') and per_bot[b] != 'disallow' \
                and per_src[b] == 'named':
            conflicts.append({'kind': 'content_usage_vs_bot_rules',
                              'detail': f'Content-Usage train-ai=n but a '
                                        f'named robots.txt group allows {b}'})
    for ug in usage_groups:
        if ug['token'].lower() != '__usage_ai-training':
            continue
        named = [n for n in ('GPTBot', 'ClaudeBot')
                 if per_src[n] == 'named']
        if ug['root'] == 'disallow' and allowed(named):
            conflicts.append({'kind': 'usage_group_vs_bot_rules',
                              'detail': '__usage_ai-training disallows / but '
                                        f'robots.txt allows {", ".join(allowed(named))}'})
        if ug['root'] == 'allow' and disallowed(named):
            conflicts.append({'kind': 'usage_group_vs_bot_rules',
                              'detail': '__usage_ai-training allows / but '
                                        f'robots.txt disallows {", ".join(disallowed(named))}'})
    return {'content_signals': signals, 'usage_groups': usage_groups,
            'content_usage': usage, 'per_bot_allowed': per_bot,
            'per_bot_source': per_src}, conflicts


_VERDICT_RANK = {'challenged': 4, 'blocked': 3, 'differs': 2,
                 'unreachable': 1, 'ok': 0}


def _fetch_verdict(f, ctrl):
    st = f['status']
    if f['challenge']:
        return 'challenged'
    if not isinstance(st, int):
        return 'unreachable'
    if st >= 400:
        return 'blocked'
    if (st == 200 and ctrl and ctrl['status'] == 200 and ctrl['bytes']
            and f['bytes'] < ctrl['bytes'] * BOT_PROBE_DIFFERS_RATIO):
        return 'differs'
    return 'ok'


def _with_query(url, key, value):
    pu = urlparse(url)
    q = (pu.query + '&' if pu.query else '') + urlencode({key: value})
    return pu._replace(path=pu.path or '/', query=q).geturl()


def cmd_bot_probe(base_url, pages=(), robots_file=None, indexnow_key=None):
    """Returns the bot-probe JSON dict (see contract)."""
    pu = urlparse(base_url)
    if not pu.scheme or not pu.netloc:
        return {'status': 'unavailable', 'reason': f'bad base url {base_url}'}
    origin = f'{pu.scheme}://{pu.netloc}'
    urls = [base_url]
    for p in pages:
        p = p.strip()
        if p:
            urls.append(urljoin(origin + '/', p))
    urls = list(dict.fromkeys(urls))[:1 + BOT_PROBE_MAX_PAGES]
    agents = [(CONTROL_NAME, 'control', CONTROL_UA)] + [
        (b['name'], b['group'], b['ua']) for b in AI_BOTS if b['fetch']]
    jobs = [(u, n, g, ua) for u in urls for n, g, ua in agents]

    def run_one(job):
        u, n, g, ua = job
        r = _probe_get(u, ua)
        marker = detect_challenge(r['status'], r['headers'], r['body'])
        return {'url': u, 'bot': n, 'group': g, 'status': r['status'],
                'bytes': r['bytes'], 'final_url': r['final_url'],
                'challenge': marker is not None, 'challenge_marker': marker}

    with ThreadPoolExecutor(max_workers=BOT_PROBE_WORKERS) as pool:
        fetches = list(pool.map(run_one, jobs))
    control = {f['url']: f for f in fetches if f['bot'] == CONTROL_NAME}
    if all(not isinstance(c['status'], int) for c in control.values()):
        return {'status': 'unavailable',
                'reason': f"control fetch failed: {control[base_url]['status']}",
                'fetches': fetches}
    per_bot, suspects = [], []
    for n, g, _ua in agents[1:]:
        worst, evidence, suspect = 'ok', [], False
        for f in (x for x in fetches if x['bot'] == n):
            ctrl = control.get(f['url'])
            v = _fetch_verdict(f, ctrl)
            if v != 'ok':
                evidence.append(
                    f"{f['url']} {f['status']} {f['bytes']}B "
                    f"(control {ctrl['status'] if ctrl else '?'} "
                    f"{ctrl['bytes'] if ctrl else '?'}B)"
                    + (f" marker={f['challenge_marker']}"
                       if f['challenge_marker'] else ''))
            if v in ('blocked', 'challenged') and ctrl and ctrl['status'] == 200:
                suspect = True
            if _VERDICT_RANK[v] > _VERDICT_RANK[worst]:
                worst = v
        per_bot.append({'bot': n, 'group': g, 'verdict': worst,
                        'evidence': '; '.join(evidence) or 'all fetches ok'})
        if suspect:
            suspects.append(n)
    # robots.txt
    robots_src = robots_file or f'{origin}/robots.txt'
    robots_text, robots_status = None, None
    if robots_file:
        try:
            with open(robots_file, encoding='utf-8', errors='replace') as f:
                robots_text, robots_status = f.read(), 'file'
        except OSError as e:
            robots_status = f'error:{e.__class__.__name__}'
    else:
        r = _probe_get(robots_src, CONTROL_UA)
        robots_status = r['status']
        if r['status'] == 200:
            robots_text = r['body'].decode('utf-8', errors='replace')
    robots, conflicts = robots_report(robots_text or '')
    robots.update({'source': robots_src, 'fetch_status': robots_status,
                   'present': robots_text is not None})
    # utm survival
    tested = _with_query(base_url, 'utm_source', 'chatgpt.com')
    r = _probe_get(tested, CONTROL_UA)
    utm = {'tested_url': tested, 'final_url': r['final_url'],
           'status': r['status'],
           'kept': 'utm_source=chatgpt.com' in urlparse(r['final_url']).query,
           'hops': len(r['hops'])}
    if not isinstance(r['status'], int):
        utm['kept'] = None
    # IndexNow key file
    indexnow = {'key_candidates': [], 'key_file_ok': None}
    if indexnow_key:
        k = indexnow_key.strip()
        r = _probe_get(f'{origin}/{quote(k)}.txt', CONTROL_UA)
        indexnow = {'key_candidates': [k], 'key_file_status': r['status'],
                    'key_file_ok': (r['status'] == 200 and r['body'].decode(
                        'utf-8', errors='replace').strip() == k)}
    return {'status': 'ok', 'base_url': base_url, 'urls': urls,
            'bots': [{k: b[k] for k in ('name', 'vendor', 'group', 'fetch')}
                     for b in AI_BOTS],
            'fetches': fetches, 'per_bot': per_bot,
            'cdn_waf_suspect': suspects, 'robots': robots,
            'policy_conflicts': conflicts, 'utm_survival': utm,
            'indexnow': indexnow}


# --- render-compare --------------------------------------------------------
_RESTRICTIVE = ('noindex', 'nofollow', 'none', 'nosnippet', 'noarchive',
                'noimageindex', 'notranslate', 'max-snippet:0')


def _render_facts(text):
    a = analyze_html(text)
    return {'robots_meta': a['robots_meta'], 'canonical': a['canonical'],
            'jsonld_count': a['jsonld_count'],
            'main_text_chars': a['main_text_chars']}


def _tokens(robots):
    return {t for t in (robots or '').lower().split(',') if t}


def _read_html_input(path):
    """Raw HTML, or a file holding the HTML as a JSON string literal (what
    Playwright's browser_evaluate writes via its `filename` param), or a JSON
    object whose only/`result` value is that string."""
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        text = f.read()
    s = text.strip()
    if s[:1] in ('"', '{', '['):
        try:
            v = json.loads(s)
        except ValueError:
            return text
        if isinstance(v, dict):
            strs = [x for x in v.values() if isinstance(x, str)]
            v = v.get('result') if isinstance(v.get('result'), str) else (
                strs[0] if len(strs) == 1 else None)
        if isinstance(v, str):
            return v
    return text


def cmd_render_compare(raw_path, rendered_path, url):
    try:
        raw_html = _read_html_input(raw_path)
        rendered_html = _read_html_input(rendered_path)
    except OSError as e:
        return {'status': 'unavailable', 'url': url,
                'reason': f'cannot read input: {e}'}
    raw, ren = _render_facts(raw_html), _render_facts(rendered_html)
    changes = []
    rt, nt = _tokens(raw['robots_meta']), _tokens(ren['robots_meta'])
    added = sorted(t for t in nt - rt if t in _RESTRICTIVE
                   or t.startswith('max-snippet'))
    removed = sorted(t for t in rt - nt if t in _RESTRICTIVE
                     or t.startswith('max-snippet'))
    if added:
        changes.append({'kind': 'robots_added', 'raw': raw['robots_meta'],
                        'rendered': ren['robots_meta'], 'tokens': added})
    if removed:
        changes.append({'kind': 'robots_removed', 'raw': raw['robots_meta'],
                        'rendered': ren['robots_meta'], 'tokens': removed})
    if raw['canonical'] != ren['canonical']:
        kind = ('canonical_added' if raw['canonical'] is None else
                'canonical_removed' if ren['canonical'] is None else
                'canonical_changed')
        changes.append({'kind': kind, 'raw': raw['canonical'],
                        'rendered': ren['canonical']})
    rendered_only = any(c['kind'] in ('robots_added', 'canonical_added',
                                      'canonical_changed') for c in changes)
    gap_main = (ren['main_text_chars'] >= 3 * raw['main_text_chars']
                and raw['main_text_chars'] < 500)
    return {'status': 'ok', 'url': url, 'raw': raw, 'rendered': ren,
            'rendered_only_directive': rendered_only,
            'directive_changes': changes,
            'raw_html_gap': {'jsonld': ren['jsonld_count'] > raw['jsonld_count'],
                             'main_content': gap_main}}


# --- update-windows (Google Search Status Dashboard) -----------------------
# Verified 2026-11-20: https://status.search.google.com/incidents.json is a
# JSON array of incidents ({id, begin, end?, external_desc, service_name,
# affected_products:[{title,id}], ...}); ranking updates carry
# service_name "Ranking". It holds roughly the last 12 months, so the cache
# merges fetched entries into what it already has.
UPDATE_WINDOWS_URL = 'https://status.search.google.com/incidents.json'
UPDATE_WINDOWS_CACHE = os.path.join('.seo-data', 'cache', 'ranking-updates.json')
UPDATE_WINDOWS_TIMEOUT_SEC = 20


def _update_kind(name):
    n = (name or '').lower()
    if 'core update' in n:
        return 'core'
    if 'spam' in n:
        return 'spam'
    return 'other'


def parse_status_incidents(data):
    """incidents.json → [{name, kind, start, end, id}] for the Ranking
    product, newest first."""
    out = []
    for inc in data if isinstance(data, list) else []:
        if not isinstance(inc, dict):
            continue
        prods = [p.get('title') for p in inc.get('affected_products') or []
                 if isinstance(p, dict)]
        if inc.get('service_name') != 'Ranking' and 'Ranking' not in prods:
            continue
        begin = (inc.get('begin') or '')[:10]
        if not _parse_date(begin):
            continue
        end = (inc.get('end') or '')[:10] or None
        name = ' '.join((inc.get('external_desc') or '').split())
        out.append({'name': name, 'kind': _update_kind(name), 'start': begin,
                    'end': end if end and _parse_date(end) else None,
                    'id': inc.get('id')})
    out.sort(key=lambda u: u['start'], reverse=True)
    return out


def _merge_updates(old, new):
    by_key = {}
    for u in old + new:          # new wins (an end date may have appeared)
        by_key[u.get('id') or (u['name'], u['start'])] = u
    return sorted(by_key.values(), key=lambda u: u['start'], reverse=True)


def updates_overlapping(updates, start, end, today=None):
    """Updates whose [start, end-or-today] window intersects [start, end]."""
    s, e = _parse_date(start), _parse_date(end)
    if s is None or e is None:
        return []
    today = today or date.today()
    out = []
    for u in updates:
        us = _parse_date(u['start'])
        ue = _parse_date(u['end']) if u.get('end') else today
        if us and ue and us <= e and ue >= s:
            out.append(u)
    return out


def cmd_update_windows(cache_path=UPDATE_WINDOWS_CACHE, max_age_days=7,
                       overlap=None, today=None):
    cached = _load_json_safe(cache_path, None) if os.path.exists(cache_path) \
        else None
    cached_updates = (cached or {}).get('updates') or []
    age_days = None
    if cached is not None:
        age_days = (time.time() - os.path.getmtime(cache_path)) / 86400
    result = None
    if cached is not None and age_days <= max_age_days:
        result = {'status': 'ok', 'source': 'cache',
                  'cache_age_days': round(age_days, 2),
                  'updates': cached_updates}
    else:
        try:
            req = urllib.request.Request(UPDATE_WINDOWS_URL, headers={
                'User-Agent': 'bx-seo-update-windows/1.0',
                'Accept': 'application/json'})
            with urllib.request.urlopen(
                    req, timeout=UPDATE_WINDOWS_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            fresh = parse_status_incidents(data)
            if not fresh and data:
                raise ValueError('no Ranking incidents parsed')
            updates = _merge_updates(cached_updates, fresh)
            try:
                _write_json_out(cache_path, {'source': UPDATE_WINDOWS_URL,
                                             'updates': updates})
            except OSError:
                pass
            result = {'status': 'ok', 'source': UPDATE_WINDOWS_URL,
                      'updates': updates}
        except (urllib.error.URLError, OSError, ValueError) as e:
            reason = (_net_reason(e) if not isinstance(e, ValueError)
                      else f'parse:{e}')
            if cached is not None:
                result = {'status': 'ok', 'source': 'cache', 'stale': True,
                          'cache_age_days': round(age_days, 2),
                          'fetch_error': reason, 'updates': cached_updates}
            else:
                result = {'status': 'unavailable', 'source': None,
                          'reason': reason, 'updates': []}
    if overlap:
        s, _, e = overlap.partition(',')
        hits = updates_overlapping(result['updates'], s.strip(), e.strip(),
                                   today)
        result['overlap'] = {'start': s.strip(), 'end': e.strip(),
                             'update_overlap': [u['name'] for u in hits],
                             'updates': hits}
    return result


# --- bing-exports (Bing Webmaster Tools AI Performance CSVs) ---------------
BING_EXPORTS_DIR = os.path.join('.seo-data', 'bing', 'exports')
BING_TOP_N = 200
_BING_DATE_FORMATS = ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d',
                      '%d.%m.%Y', '%m/%d/%y', '%b %d, %Y', '%d %b %Y')


def _read_csv_text(path):
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ('utf-8-sig', 'utf-16', 'cp1252'):
        try:
            text = raw.decode(enc)
            if enc == 'utf-16' and not raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
                continue
            return text
        except UnicodeDecodeError:
            continue
    return raw.decode('latin-1')


def _bing_date(s):
    from datetime import datetime
    s = (s or '').strip()
    if not s:
        return None
    s = re.split(r'[T ]\d{1,2}:\d{2}', s)[0].strip()
    for fmt in _BING_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _bing_int(s):
    s = re.sub(r'[,\s]', '', s or '')
    try:
        return int(float(s))
    except ValueError:
        return None


def _classify_columns(header):
    cols = {'citations': None, 'url': None, 'query': None, 'date': None}
    for i, h in enumerate(header):
        k = (h or '').strip().lower()
        if cols['citations'] is None and 'citation' in k:
            cols['citations'] = i
        elif cols['query'] is None and ('grounding' in k or 'query' in k):
            cols['query'] = i
        elif cols['url'] is None and ('url' in k or 'page' in k or 'cited' in k):
            cols['url'] = i
        elif cols['date'] is None and 'date' in k:
            cols['date'] = i
    return cols


def cmd_bing_exports(dir_path=BING_EXPORTS_DIR):
    import csv
    if not os.path.isdir(dir_path):
        return {'status': 'absent', 'reason': f'no directory {dir_path}'}
    paths = sorted(glob.glob(os.path.join(dir_path, '**', '*.csv'),
                             recursive=True))
    if not paths:
        return {'status': 'absent', 'reason': f'no .csv files in {dir_path}'}
    pages, queries = defaultdict(int), defaultdict(int)
    series_total, dates, files = 0, [], []
    has_series = False
    for p in paths:
        info = {'name': os.path.relpath(p, dir_path), 'kind': 'unknown',
                'rows': 0, 'columns': []}
        files.append(info)
        try:
            text = _read_csv_text(p)
        except OSError as e:
            info['error'] = str(e)
            continue
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel
        rows = [r for r in csv.reader(text.splitlines(), dialect) if any(
            c.strip() for c in r)]
        if not rows:
            continue
        header, body = rows[0], rows[1:]
        info['columns'] = [h.strip() for h in header]
        cols = _classify_columns(header)
        kind = ('pages' if cols['url'] is not None else
                'queries' if cols['query'] is not None else
                'timeseries' if cols['date'] is not None
                and cols['citations'] is not None else 'unknown')
        info['kind'] = kind
        for r in body:
            def cell(key):
                i = cols[key]
                return r[i].strip() if i is not None and i < len(r) else ''
            n = _bing_int(cell('citations')) if cols['citations'] is not None \
                else 1
            if n is None:
                continue
            info['rows'] += 1
            d = _bing_date(cell('date')) if cols['date'] is not None else None
            if d:
                dates.append(d)
            if kind == 'pages' and cell('url'):
                pages[cell('url')] += n
            elif kind == 'queries' and cell('query'):
                queries[cell('query')] += n
            elif kind == 'timeseries':
                series_total += n
                has_series = True
    page_list = [{'url': u, 'citations': c} for u, c in
                 sorted(pages.items(), key=lambda x: -x[1])][:BING_TOP_N]
    query_list = [{'query': q, 'citations': c} for q, c in
                  sorted(queries.items(), key=lambda x: -x[1])][:BING_TOP_N]
    total = (series_total if has_series else sum(pages.values()) if pages
             else sum(queries.values()))
    return {'status': 'ok', 'files': files, 'pages': page_list,
            'queries': query_list, 'total_citations': total,
            'period': ({'start': min(dates), 'end': max(dates)} if dates
                       else None)}


def _json_cmd_main(cmd, argv):
    """argparse front-end for the 2.20.0 JSON subcommands (and the --out /
    --question-words flags on page-audit and sa-trends)."""
    import argparse
    ap = argparse.ArgumentParser(prog=f'gsc-parse-helper {cmd}')
    if cmd == 'bot-probe':
        ap.add_argument('--base-url', required=True)
        ap.add_argument('--pages', default='')
        ap.add_argument('--robots-file')
        ap.add_argument('--indexnow-key')
        ap.add_argument('--out', required=True)
        a = ap.parse_args(argv)
        res = cmd_bot_probe(a.base_url, [p for p in a.pages.split(',') if p],
                            a.robots_file, a.indexnow_key)
        _write_json_out(a.out, res)
        if res['status'] != 'ok':
            print(f"bot_probe:unavailable reason={res.get('reason')} -> {a.out}")
            return
        counts = defaultdict(int)
        for b in res['per_bot']:
            counts[b['verdict']] += 1
        print(f"bot_probe:ok fetches={len(res['fetches'])} "
              + ' '.join(f"{k}={counts[k]}" for k in
                         ('ok', 'blocked', 'challenged', 'differs',
                          'unreachable'))
              + f" cdn_waf_suspect={len(res['cdn_waf_suspect'])} "
              f"policy_conflicts={len(res['policy_conflicts'])} "
              f"content_signals={len(res['robots']['content_signals'])} "
              f"utm_kept={res['utm_survival']['kept']} "
              f"indexnow_ok={res['indexnow']['key_file_ok']} -> {a.out}")
    elif cmd == 'render-compare':
        ap.add_argument('--raw', required=True)
        ap.add_argument('--rendered', required=True)
        ap.add_argument('--url', required=True)
        ap.add_argument('--out', required=True)
        a = ap.parse_args(argv)
        res = cmd_render_compare(a.raw, a.rendered, a.url)
        _write_json_out(a.out, res)
        if res['status'] != 'ok':
            print(f"render_compare:unavailable reason={res['reason']} -> {a.out}")
            return
        print(f"render_compare:ok url={a.url} "
              f"rendered_only_directive={res['rendered_only_directive']} "
              f"changes={len(res['directive_changes'])} "
              f"gap_jsonld={res['raw_html_gap']['jsonld']} "
              f"gap_main={res['raw_html_gap']['main_content']} -> {a.out}")
    elif cmd == 'update-windows':
        ap.add_argument('--cache', default=UPDATE_WINDOWS_CACHE)
        ap.add_argument('--max-age-days', type=float, default=7)
        ap.add_argument('--overlap', help='START,END (YYYY-MM-DD)')
        ap.add_argument('--out', required=True)
        a = ap.parse_args(argv)
        res = cmd_update_windows(a.cache, a.max_age_days, a.overlap)
        _write_json_out(a.out, res)
        line = (f"update_windows:{res['status']} source={res.get('source')} "
                f"updates={len(res['updates'])}")
        if res.get('stale'):
            line += ' stale=yes'
        if res.get('reason'):
            line += f" reason={res['reason']}"
        if 'overlap' in res:
            line += (' overlap=' + (';'.join(res['overlap']['update_overlap'])
                                    or 'none'))
        print(line + f' -> {a.out}')
    elif cmd == 'bing-exports':
        ap.add_argument('--dir', default=BING_EXPORTS_DIR)
        ap.add_argument('--out', required=True)
        a = ap.parse_args(argv)
        res = cmd_bing_exports(a.dir)
        _write_json_out(a.out, res)
        if res['status'] != 'ok':
            print(f"bing_exports:{res['status']} -> {a.out}")
            return
        print(f"bing_exports:ok files={len(res['files'])} "
              f"pages={len(res['pages'])} queries={len(res['queries'])} "
              f"total_citations={res['total_citations']} -> {a.out}")
    elif cmd == 'page-audit':
        ap.add_argument('targets')
        ap.add_argument('--out')
        a = ap.parse_args(argv)
        cmd_page_audit(a.targets, a.out)
    elif cmd == 'sa-trends':
        ap.add_argument('cache_dir')
        ap.add_argument('site_url')
        ap.add_argument('end_date')
        ap.add_argument('lookback_days')
        ap.add_argument('brand_csv', nargs='?', default='')
        ap.add_argument('--out')
        ap.add_argument('--question-words',
                        help='comma-separated; default English list')
        a = ap.parse_args(argv)
        qw = (tuple(w.strip() for w in a.question_words.split(',') if w.strip())
              if a.question_words else AIO_QUESTION_WORDS)
        cmd_sa_trends(a.cache_dir, a.site_url, a.end_date, a.lookback_days,
                      a.brand_csv, a.out, qw)


_JSON_CMDS = ('bot-probe', 'render-compare', 'update-windows', 'bing-exports')


def main():
    if len(sys.argv) >= 2 and (
            sys.argv[1] in _JSON_CMDS or (
                sys.argv[1] in ('page-audit', 'sa-trends')
                and any(a.startswith('--') for a in sys.argv[2:]))):
        try:
            _json_cmd_main(sys.argv[1], sys.argv[2:])
        except SystemExit as e:
            # argparse usage errors exit 2; the helper's convention is 3
            if e.code == 2:
                sys.exit(3)
            raise
        return
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(3)

    cmd = sys.argv[1]

    # Commands that take no positional file argument.
    if cmd == 'auth-token':
        cmd_auth_token()
        return

    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(3)

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
    elif cmd == 'sitemaps-list':
        cmd_sitemaps_list(arg)  # arg = site_url
    elif cmd == 'sitemap-urls':
        if len(sys.argv) < 5:
            print("ERROR: sitemap-urls subcommand needs <sitemap_url> "
                  "<base_or_-> <out_file> [<q3_cache> <orphan_limit>]",
                  file=sys.stderr)
            sys.exit(3)
        cmd_sitemap_urls(sys.argv[2:])
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
    elif cmd == 'crux':
        cmd_crux(arg)
    elif cmd == 'page-audit':
        cmd_page_audit(arg)
    elif cmd == 'sa-trends':
        if len(sys.argv) < 6:
            print("ERROR: sa-trends subcommand needs <cache_dir> <site_url> "
                  "<end_date> <lookback_days> [<brand_terms_csv>]",
                  file=sys.stderr)
            sys.exit(3)
        cmd_sa_trends(arg, sys.argv[3], sys.argv[4], sys.argv[5],
                      sys.argv[6] if len(sys.argv) > 6 else '')
    else:
        print(f"ERROR: unknown subcommand '{cmd}'. Run with no args for usage.",
              file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main()
