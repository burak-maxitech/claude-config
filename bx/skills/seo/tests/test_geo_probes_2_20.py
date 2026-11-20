"""Tests for gsc-parse-helper 2.20.0: bot-probe, page-audit JSON fields,
render-compare, sa-trends CTR segmentation, update-windows, bing-exports.

Run: python -m unittest discover -s bx/skills/seo/tests -p "test_*.py"
Stdlib only. Network tests use a local http.server on 127.0.0.1 — never the
live internet."""
import contextlib
import importlib.util
import io
import json
import os
import socket
import tempfile
import threading
import time
import unittest
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, '..', 'references', 'gsc-parse-helper.py')

spec = importlib.util.spec_from_file_location('gsc_helper_220', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def run(fn, *args, **kw):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args, **kw)
    return buf.getvalue()


def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def run_main(argv):
    buf = io.StringIO()
    with mock.patch.object(h.sys, 'argv', ['gsc-parse-helper'] + argv), \
            contextlib.redirect_stdout(buf):
        h.main()
    return buf.getvalue()


BIG_PAGE = ('<html><head><title>Home</title></head><body><main><h1>Home</h1>'
            '<p>' + ' '.join(['content'] * 400) + '</p></main></body></html>')
CF_CHALLENGE = ('<!DOCTYPE html><html><head><title>Just a moment...</title>'
                '</head><body><script src="/cdn-cgi/challenge-platform/h/b/'
                'orchestrate/chl_page/v1"></script></body></html>')

ROBOTS = """# test robots
User-agent: *
Content-Signal: search=yes, ai-input=no, ai-train=no
Allow: /

User-agent: GPTBot
Allow: /

User-agent: CCBot
Disallow: /

User-agent: __usage_ai-training
Disallow: /
"""


class Handler(BaseHTTPRequestHandler):
    utm_mode = 'strip'          # 'strip' | 'keep'

    def log_message(self, *a):
        pass

    def _send(self, code, body, headers=()):
        data = body.encode() if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        for k, v in headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        ua = self.headers.get('User-Agent', '')
        path = self.path
        if path == '/robots.txt':
            return self._send(200, ROBOTS)
        if path == '/k3y.txt':
            return self._send(200, 'k3y\n')
        if path.startswith('/?utm_source='):
            target = ('/home?' + path.split('?', 1)[1]
                      if Handler.utm_mode == 'keep' else '/home')
            self.send_response(301)
            self.send_header('Location', target)
            self.send_header('Content-Length', '0')
            self.end_headers()
            return
        if 'GPTBot' in ua:
            return self._send(403, CF_CHALLENGE, [('cf-mitigated', 'challenge')])
        if 'ClaudeBot' in ua:     # a full-size 403 page: blocked, no marker
            return self._send(403, '<html><body>Forbidden' + ' ' * 4000
                              + '</body></html>')
        if 'meta-externalagent' in ua:   # tiny 403 stub: generic challenge
            return self._send(403, 'Forbidden')
        if 'PerplexityBot' in ua:
            return self._send(200, '<html><body>tiny</body></html>')
        return self._send(200, BIG_PAGE)


class LocalServer:
    def __enter__(self):
        self.srv = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.t = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.t.start()
        self.base = f'http://127.0.0.1:{self.srv.server_address[1]}'
        return self

    def __exit__(self, *a):
        self.srv.shutdown()
        self.srv.server_close()


def closed_port_url():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return f'http://127.0.0.1:{port}/incidents.json'


class ChallengeDetection(unittest.TestCase):
    def test_cloudflare_header_and_body(self):
        self.assertEqual(h.detect_challenge(403, {'cf-mitigated': 'challenge'},
                                            b''), 'cloudflare:cf-mitigated')
        self.assertEqual(h.detect_challenge(403, {}, CF_CHALLENGE.encode()),
                         'cloudflare:challenge-title')
        self.assertEqual(h.detect_challenge(429, {'x-vercel-mitigated': 'challenge'},
                                            b'x'), 'vercel:x-vercel-mitigated')

    def test_generic_tiny_block(self):
        self.assertEqual(h.detect_challenge(403, {}, b'Forbidden'),
                         'generic:403-tiny-body')
        self.assertIsNone(h.detect_challenge(404, {}, b'Not found'))

    def test_control_page_mentioning_access_denied_is_not_a_challenge(self):
        page = (BIG_PAGE.replace('Home</h1>',
                                 'Home</h1><p>Fixing Access Denied errors '
                                 'and the checkpoint step</p>')).encode()
        self.assertIsNone(h.detect_challenge(200, {}, page))
        # the same words on a 403 are a challenge marker
        self.assertEqual(h.detect_challenge(403, {}, b'<h1>Access Denied</h1>'
                                            + b' ' * 4000),
                         'akamai:access-denied')


class RobotsParsing(unittest.TestCase):
    def test_signals_usage_groups_and_conflicts(self):
        rep, conflicts = h.robots_report(ROBOTS)
        sig = rep['content_signals']
        self.assertEqual(len(sig), 1)
        self.assertEqual((sig[0]['scope_user_agent'], sig[0]['search'],
                          sig[0]['ai_input'], sig[0]['ai_train']),
                         ('*', 'yes', 'no', 'no'))
        self.assertEqual(rep['usage_groups'][0]['token'], '__usage_ai-training')
        self.assertEqual(rep['usage_groups'][0]['root'], 'disallow')
        pb = rep['per_bot_allowed']
        self.assertEqual(pb['GPTBot'], 'allow')
        self.assertEqual(pb['CCBot'], 'disallow')
        self.assertEqual(pb['OAI-SearchBot'], 'allow')
        self.assertEqual(rep['per_bot_source']['OAI-SearchBot'], 'wildcard')
        kinds = {c['kind'] for c in conflicts}
        self.assertIn('ai_input_no_but_bot_allowed', kinds)
        self.assertIn('usage_group_vs_bot_rules', kinds)   # GPTBot named allow
        self.assertIn('ai_train_no_but_bot_allowed', kinds)
        self.assertNotIn('ai_train_yes_but_bot_disallowed', kinds)

    def test_no_robots_is_unspecified_without_conflicts(self):
        rep, conflicts = h.robots_report('')
        self.assertEqual(set(rep['per_bot_allowed'].values()), {'unspecified'})
        self.assertEqual(conflicts, [])

    def test_ai_train_yes_vs_disallow_and_content_usage(self):
        text = ('User-agent: *\nContent-Signal: ai-train=yes\n'
                'Content-Usage: train-ai=n\nAllow: /\n\n'
                'User-agent: ClaudeBot\nDisallow: /\n\n'
                'User-agent: GPTBot\nAllow: /\n')
        rep, conflicts = h.robots_report(text)
        kinds = [c['kind'] for c in conflicts]
        self.assertIn('ai_train_yes_but_bot_disallowed', kinds)
        self.assertEqual(rep['content_usage'][0]['prefs'], {'train-ai': 'n'})


class BotProbe(unittest.TestCase):
    def test_verdicts_against_control(self):
        Handler.utm_mode = 'strip'
        with LocalServer() as s:
            res = h.cmd_bot_probe(s.base + '/', ['/pricing'], None, 'k3y')
        self.assertEqual(res['status'], 'ok')
        fetched = {f['bot'] for f in res['fetches']}
        for robots_only in ('Google-Extended', 'Applebot-Extended', 'CCBot'):
            self.assertNotIn(robots_only, fetched)
        self.assertIn('Meta-ExternalAgent', fetched)
        self.assertIn('OAI-AdsBot', fetched)
        self.assertEqual(len(res['fetches']), 2 * 11)   # 2 urls × (10 bots + control)
        v = {b['bot']: b['verdict'] for b in res['per_bot']}
        self.assertEqual(v['GPTBot'], 'challenged')
        self.assertEqual(v['ClaudeBot'], 'blocked')
        self.assertEqual(v['PerplexityBot'], 'differs')
        self.assertEqual(v['Meta-ExternalAgent'], 'challenged')
        self.assertEqual(v['OAI-SearchBot'], 'ok')
        self.assertEqual(sorted(res['cdn_waf_suspect']),
                         ['ClaudeBot', 'GPTBot', 'Meta-ExternalAgent'])
        meta = [f for f in res['fetches'] if f['bot'] == 'Meta-ExternalAgent'][0]
        self.assertEqual(meta['challenge_marker'], 'generic:403-tiny-body')
        gpt = [f for f in res['fetches'] if f['bot'] == 'GPTBot'][0]
        self.assertTrue(gpt['challenge'])
        self.assertEqual(gpt['challenge_marker'], 'cloudflare:cf-mitigated')
        ctrl = [f for f in res['fetches'] if f['bot'] == 'control'][0]
        self.assertFalse(ctrl['challenge'])
        self.assertTrue(res['robots']['present'])
        self.assertTrue(res['policy_conflicts'])
        self.assertEqual(res['utm_survival']['kept'], False)
        self.assertEqual(res['utm_survival']['hops'], 1)
        self.assertEqual(res['indexnow'], {'key_candidates': ['k3y'],
                                           'key_file_status': 200,
                                           'key_file_ok': True})

    def test_utm_survives_redirect(self):
        Handler.utm_mode = 'keep'
        try:
            with LocalServer() as s:
                res = h.cmd_bot_probe(s.base + '/')
        finally:
            Handler.utm_mode = 'strip'
        u = res['utm_survival']
        self.assertTrue(u['kept'])
        self.assertEqual(u['hops'], 1)
        self.assertIn('/home?utm_source=chatgpt.com', u['final_url'])
        self.assertEqual(res['indexnow'], {'key_candidates': [],
                                           'key_file_ok': None})

    def test_robots_file_override_and_cli_writes_out(self):
        with tempfile.TemporaryDirectory() as d, LocalServer() as s:
            rf = os.path.join(d, 'robots.txt')
            with open(rf, 'w', encoding='utf-8') as f:
                f.write('User-agent: OAI-SearchBot\nDisallow: /\n')
            out = os.path.join(d, 'sub', 'bot-probe.json')
            line = run_main(['bot-probe', '--base-url', s.base + '/',
                             '--robots-file', rf, '--out', out])
            data = load(out)
        self.assertIn('bot_probe:ok', line)
        self.assertEqual(data['robots']['per_bot_allowed']['OAI-SearchBot'],
                         'disallow')
        self.assertEqual(data['robots']['fetch_status'], 'file')

    def test_unreachable_degrades(self):
        base = closed_port_url().rsplit('/', 1)[0] + '/'
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'bp.json')
            line = run_main(['bot-probe', '--base-url', base, '--out', out])
            data = load(out)
        self.assertEqual(data['status'], 'unavailable')
        self.assertIn('bot_probe:unavailable', line)


ARTICLE = """<!doctype html><html><head><title>Guide</title>
<meta name="robots" content="index, follow">
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
 {"@type":"Article","headline":"How to Brew Coffee","author":{"@type":"Person","name":"Jane Roe"},
  "datePublished":"2026-03-05T09:00:00Z","dateModified":"2026-04-01"},
 {"@type":"Product","name":"Brewer X","offers":{"@type":"Offer","price":"1299.00","priceCurrency":"USD"}},
 {"@type":"LocalBusiness","name":"Bean Shop","telephone":"+1 (555) 123-4567",
  "address":{"@type":"PostalAddress","streetAddress":"12 Main St","addressLocality":"Springfield"}}]}
</script>
<script type="application/ld+json">{not json</script>
</head><body><nav>Menu Home About</nav><main>
<h1>How to brew coffee</h1><p>By Jane Roe · <time datetime="2026-03-05">March 5, 2026</time></p>
<p>The Brewer X costs $1,299.00. Visit Bean Shop at 12 Main St, call 555-123-4567.</p>
</main></body></html>"""


class PageAuditFields(unittest.TestCase):
    def test_jsonld_fields_dates_and_main_text(self):
        r = h.analyze_html(ARTICLE)
        self.assertEqual(r['jsonld_count'], 2)
        self.assertEqual(r['jsonld_parse_errors'], 1)
        types = [n['type'] for n in r['jsonld']]
        self.assertEqual(types, ['Article', 'Product', 'LocalBusiness'])
        art = r['jsonld'][0]['fields']
        self.assertEqual(art['author'], 'Jane Roe')
        self.assertEqual(art['datePublished'], '2026-03-05T09:00:00Z')
        prod = r['jsonld'][1]['fields']
        self.assertEqual((prod['price'], prod['priceCurrency']), ('1299.00', 'USD'))
        self.assertEqual(r['jsonld'][2]['fields']['address'],
                         '12 Main St, Springfield')
        self.assertEqual(r['robots_meta'], 'index,follow')
        self.assertEqual(r['visible_dates'], ['2026-03-05'])
        self.assertGreater(r['main_text_chars'], 50)

    def test_schema_visible_match(self):
        checks = {(c['type'], c['field']): c['in_visible_text']
                  for c in h.analyze_html(ARTICLE)['schema_visible_checks']}
        self.assertEqual(checks[('Article', 'headline')], True)
        self.assertEqual(checks[('Article', 'author')], True)
        self.assertEqual(checks[('Article', 'datePublished')], True)
        self.assertEqual(checks[('Product', 'price')], True)
        self.assertEqual(checks[('Product', 'name')], True)
        self.assertEqual(checks[('LocalBusiness', 'telephone')], True)
        self.assertEqual(checks[('LocalBusiness', 'address')], True)

    def test_schema_visible_mismatch(self):
        bad = (ARTICLE.replace('"price":"1299.00"', '"price":"999.00"')
               .replace('"name":"Jane Roe"', '"name":"Ghost Writer"')
               .replace('"datePublished":"2026-03-05T09:00:00Z"',
                        '"datePublished":"2026-06-01"'))
        checks = {(c['type'], c['field']): c['in_visible_text']
                  for c in h.analyze_html(bad)['schema_visible_checks']}
        self.assertFalse(checks[('Product', 'price')])
        self.assertFalse(checks[('Article', 'author')])
        self.assertFalse(checks[('Article', 'datePublished')])
        self.assertTrue(checks[('Article', 'headline')])

    def test_wrapper_types_not_checked(self):
        page = ('<script type="application/ld+json">[{"@type":"WebPage","name":'
                '"Site — Title"},{"@type":"Organization","name":"Acme"}]'
                '</script><body><p>Acme makes things</p></body>')
        checks = h.analyze_html(page)['schema_visible_checks']
        self.assertEqual([(c['type'], c['in_visible_text']) for c in checks],
                         [('Organization', True)])

    def test_page_audit_out_json(self):
        with tempfile.TemporaryDirectory() as d:
            t = os.path.join(d, 't.txt')
            with open(t, 'w', encoding='utf-8') as f:
                f.write('https://ex.com/a\n')
            out = os.path.join(d, 'pa.json')
            fake = mock.Mock(return_value=(200, 'https://ex.com/a',
                                           ARTICLE.encode(), 'utf-8', '', False))
            with mock.patch.object(h, '_fetch_raw_page', fake):
                text = run_main(['page-audit', t, '--out', out])
            data = load(out)
        self.assertIn('jsonld=2', text)                   # text line: count
        self.assertIn('schema_visible_mismatch=0', text)
        rec = data['pages'][0]
        for k in ('jsonld', 'jsonld_parse_errors', 'robots_meta', 'canonical',
                  'visible_dates', 'main_text_chars', 'schema_visible_checks',
                  'words', 'hijack_suspect', 'bytes'):
            self.assertIn(k, rec)


SPA_RAW = '<html><head><title>App</title></head><body><div id="root"></div></body></html>'
SPA_RENDERED = ('<html><head><title>App</title><meta name="robots" content="noindex">'
                '<link rel="canonical" href="https://ex.com/app">'
                '<script type="application/ld+json">{"@type":"Product","name":"A"}</script>'
                '</head><body><div id="root"><main><p>' + 'word ' * 400 +
                '</p></main></div></body></html>')


class RenderCompare(unittest.TestCase):
    def _run(self, raw, rendered, wrap_json=False):
        with tempfile.TemporaryDirectory() as d:
            rp, np_ = os.path.join(d, 'raw.html'), os.path.join(d, 'r.html')
            with open(rp, 'w', encoding='utf-8') as f:
                f.write(raw)
            with open(np_, 'w', encoding='utf-8') as f:
                f.write(json.dumps(rendered) if wrap_json else rendered)
            out = os.path.join(d, 'rc.json')
            line = run_main(['render-compare', '--raw', rp, '--rendered', np_,
                             '--url', 'https://ex.com/app', '--out', out])
            return line, load(out)

    def test_rendered_only_noindex_and_gaps(self):
        line, r = self._run(SPA_RAW, SPA_RENDERED)
        self.assertIn('render_compare:ok', line)
        self.assertTrue(r['rendered_only_directive'])
        kinds = {c['kind'] for c in r['directive_changes']}
        self.assertEqual(kinds, {'robots_added', 'canonical_added'})
        self.assertEqual(r['rendered']['robots_meta'], 'noindex')
        self.assertIsNone(r['raw']['robots_meta'])
        self.assertTrue(r['raw_html_gap']['jsonld'])
        self.assertTrue(r['raw_html_gap']['main_content'])

    def test_json_string_wrapped_rendered_file(self):
        _line, r = self._run(SPA_RAW, SPA_RENDERED, wrap_json=True)
        self.assertTrue(r['rendered_only_directive'])
        self.assertEqual(r['rendered']['jsonld_count'], 1)

    def test_identical_is_clean(self):
        _line, r = self._run(SPA_RENDERED, SPA_RENDERED)
        self.assertFalse(r['rendered_only_directive'])
        self.assertEqual(r['directive_changes'], [])
        self.assertEqual(r['raw_html_gap'], {'jsonld': False,
                                             'main_content': False})

    def test_raw_noindex_removed_by_js_is_a_change_not_rendered_only(self):
        raw = SPA_RAW.replace('<title>', '<meta name="robots" content="noindex"><title>')
        rendered = SPA_RAW.replace('<title>', '<meta name="robots" content="index"><title>')
        _line, r = self._run(raw, rendered)
        self.assertFalse(r['rendered_only_directive'])
        self.assertEqual(r['directive_changes'][0]['kind'], 'robots_removed')

    def test_missing_file_degrades(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'rc.json')
            line = run_main(['render-compare', '--raw', os.path.join(d, 'no'),
                             '--rendered', os.path.join(d, 'no2'),
                             '--url', 'u', '--out', out])
            self.assertEqual(load(out)['status'],
                             'unavailable')
        self.assertIn('render_compare:unavailable', line)


def qp(q, page, clicks, imps, pos):
    return {'keys': [q, page], 'clicks': clicks, 'impressions': imps,
            'position': pos}


class AioSegmentation(unittest.TestCase):
    def test_aio_prone(self):
        self.assertTrue(h.aio_prone('how to brew coffee'))
        self.assertTrue(h.aio_prone('chemex vs v60'))
        self.assertTrue(h.aio_prone('one two three four five six'))
        self.assertFalse(h.aio_prone('coffee grinder'))
        self.assertFalse(h.aio_prone('this'))            # 'is' only as a word
        self.assertTrue(h.aio_prone('kaffee wie', ('wie',)))
        self.assertFalse(h.aio_prone('how to', ('wie',)))

    def test_segments_and_compression_thresholds(self):
        prev = [qp('how to brew coffee', '/a', 100, 1000, 3.0),
                qp('coffee', '/a', 10, 200, 3.0),
                # /b: same CTR drop but position fell 3 places → not AIO
                qp('what is a burr grinder', '/b', 100, 1000, 3.0),
                # /c: CTR drop but mostly non-question queries
                qp('grinder', '/c', 100, 1000, 3.0),
                qp('why grind', '/c', 10, 200, 3.0),
                # /d: only -10% CTR → under threshold
                qp('how to descale', '/d', 100, 1000, 4.0)]
        now = [qp('how to brew coffee', '/a', 50, 1000, 3.4),
               qp('coffee', '/a', 10, 200, 3.0),
               qp('what is a burr grinder', '/b', 50, 1000, 6.0),
               qp('grinder', '/c', 50, 1000, 3.0),
               qp('why grind', '/c', 10, 200, 3.0),
               qp('how to descale', '/d', 90, 1000, 4.0)]
        seg, comp = h.ctr_segments(now, prev)
        self.assertEqual(seg['aio_prone']['impressions'], 3200)
        self.assertEqual(seg['other']['impressions'], 1200)
        self.assertAlmostEqual(seg['aio_prone']['ctr_prev'], 310 / 3200)
        self.assertAlmostEqual(seg['aio_prone']['ctr_now'], 200 / 3200)
        self.assertEqual([c['page'] for c in comp], ['/a'])
        a = comp[0]
        self.assertAlmostEqual(a['aio_share'], 1000 / 1200, places=3)
        self.assertAlmostEqual(a['ctr_delta'], (60 / 1200 - 110 / 1200) / (110 / 1200),
                               places=3)
        self.assertLessEqual(abs(a['pos_delta']), 1.0)

    def test_sa_trends_out_json(self):
        prev = [qp('how to brew coffee', '/a', 100, 1000, 3.0)]
        now = [qp('how to brew coffee', '/a', 40, 1000, 3.2)]
        calls = []

        def fake_rows(site, body, cache_dir, no_cache, creds):
            calls.append(body)
            if body['dimensions'] == ['page']:
                return [], 'hit'
            if len(calls) == 1:
                return [], 'hit'
            return (prev if len(calls) == 5 else now), 'hit'

        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, 'sa.json')
            with mock.patch.object(h, '_sa_rows', side_effect=fake_rows):
                text = run_main(['sa-trends', 'c', 'sc-domain:ex.com',
                                 '2026-11-03', '90', 'acme', '--out', out])
            data = load(out)
        self.assertEqual([(b['startDate'], b['endDate']) for b in calls[4:]],
                         [('2026-09-09', '2026-10-06'),
                          ('2026-10-07', '2026-11-03')])
        self.assertIn('ai_overview_compression:1', text)
        self.assertEqual(data['ai_overview_compression'][0]['page'], '/a')
        self.assertEqual(set(data['ctr_segments']), {'aio_prone', 'other'})
        self.assertEqual(data['status'], 'ok')


class BingExports(unittest.TestCase):
    def test_absent_dir(self):
        with tempfile.TemporaryDirectory() as d:
            r = h.cmd_bing_exports(os.path.join(d, 'nope'))
            self.assertEqual(r['status'], 'absent')
            os.makedirs(os.path.join(d, 'empty'))
            self.assertEqual(h.cmd_bing_exports(os.path.join(d, 'empty'))['status'],
                             'absent')

    def test_tolerant_headers(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'cited.csv'), 'w', encoding='utf-8-sig') as f:
                f.write('Cited Page URL,Total Citations\n'
                        'https://ex.com/a,"1,204"\nhttps://ex.com/b,7\n'
                        'https://ex.com/a,6\n')
            with open(os.path.join(d, 'grounding.csv'), 'w', encoding='utf-8') as f:
                f.write('GROUNDING QUERY;citation count\nbest crm;12\nhow to x;3\n')
            with open(os.path.join(d, 'trend.csv'), 'w', encoding='utf-16') as f:
                f.write('Date\tCitations\n10/01/2026\t5\n10/31/2026\t9\n')
            out = os.path.join(d, 'out', 'bing.json')
            line = run_main(['bing-exports', '--dir', d, '--out', out])
            r = load(out)
        self.assertIn('bing_exports:ok', line)
        self.assertEqual(r['pages'][0], {'url': 'https://ex.com/a', 'citations': 1210})
        self.assertEqual(r['queries'][0], {'query': 'best crm', 'citations': 12})
        self.assertEqual(r['total_citations'], 14)          # time series wins
        self.assertEqual(r['period'], {'start': '2026-10-01', 'end': '2026-10-31'})
        kinds = {f['name']: f['kind'] for f in r['files']}
        self.assertEqual(kinds, {'cited.csv': 'pages', 'grounding.csv': 'queries',
                                 'trend.csv': 'timeseries'})


INCIDENTS = [
    {'id': 'n1', 'begin': '2026-11-10T18:06:00+00:00',
     'external_desc': 'November 2026 core update', 'service_name': 'Ranking',
     'affected_products': [{'title': 'Ranking', 'id': 'r'}]},
    {'id': 's1', 'begin': '2026-09-24T16:15:00+00:00',
     'end': '2026-10-08T08:00:00+00:00',
     'external_desc': 'September 2026 spam update', 'service_name': 'Ranking'},
    {'id': 'x1', 'begin': '2026-02-25T03:55:00+00:00',
     'end': '2026-02-25T04:10:00+00:00',
     'external_desc': 'Serving was experiencing an issue',
     'service_name': 'Serving'},
    {'id': 'd1', 'begin': '2026-02-05T17:00:00+00:00',
     'end': '2026-02-27T10:00:00+00:00',
     'external_desc': 'February 2026 Discover update', 'service_name': 'Ranking'},
]


class JsonHandler(BaseHTTPRequestHandler):
    hits = 0

    def log_message(self, *a):
        pass

    def do_GET(self):
        JsonHandler.hits += 1
        data = json.dumps(INCIDENTS).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class UpdateWindows(unittest.TestCase):
    def test_parse_ranking_only(self):
        ups = h.parse_status_incidents(INCIDENTS)
        self.assertEqual([(u['name'], u['kind'], u['start'], u['end']) for u in ups], [
            ('November 2026 core update', 'core', '2026-11-10', None),
            ('September 2026 spam update', 'spam', '2026-09-24', '2026-10-08'),
            ('February 2026 Discover update', 'other', '2026-02-05', '2026-02-27')])

    def test_overlap(self):
        ups = h.parse_status_incidents(INCIDENTS)
        hit = h.updates_overlapping(ups, '2026-10-01', '2026-10-31',
                                    today=date(2026, 11, 20))
        self.assertEqual([u['name'] for u in hit], ['September 2026 spam update'])
        ongoing = h.updates_overlapping(ups, '2026-11-15', '2026-11-18',
                                        today=date(2026, 11, 20))
        self.assertEqual([u['kind'] for u in ongoing], ['core'])

    def test_live_then_offline_cache_then_unavailable(self):
        srv = ThreadingHTTPServer(('127.0.0.1', 0), JsonHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f'http://127.0.0.1:{srv.server_address[1]}/incidents.json'
        try:
            with tempfile.TemporaryDirectory() as d:
                cache = os.path.join(d, 'cache', 'ranking-updates.json')
                out = os.path.join(d, 'uw.json')
                with mock.patch.object(h, 'UPDATE_WINDOWS_URL', url):
                    line = run_main(['update-windows', '--cache', cache,
                                     '--out', out])
                r = load(out)
                self.assertIn('update_windows:ok', line)
                self.assertEqual((r['status'], r['source']), ('ok', url))
                self.assertEqual(len(r['updates']), 3)
                self.assertTrue(os.path.exists(cache))

                # fresh cache + --overlap → served offline (no new hit)
                hits = JsonHandler.hits
                with mock.patch.object(h, 'UPDATE_WINDOWS_URL', closed_port_url()):
                    line = run_main(['update-windows', '--cache', cache,
                                     '--overlap', '2026-10-01,2026-10-31',
                                     '--out', out])
                r = load(out)
                self.assertEqual(JsonHandler.hits, hits)
                self.assertEqual(r['source'], 'cache')
                self.assertEqual(r['overlap']['update_overlap'],
                                 ['September 2026 spam update'])
                self.assertIn('overlap=September 2026 spam update', line)

                # stale cache + offline → stale cache
                old = time.time() - 30 * 86400
                os.utime(cache, (old, old))
                with mock.patch.object(h, 'UPDATE_WINDOWS_URL', closed_port_url()):
                    run_main(['update-windows', '--cache', cache, '--out', out])
                r = load(out)
                self.assertEqual((r['status'], r['source'], r['stale']),
                                 ('ok', 'cache', True))
                self.assertEqual(len(r['updates']), 3)

                # no cache + offline → unavailable
                os.remove(cache)
                with mock.patch.object(h, 'UPDATE_WINDOWS_URL', closed_port_url()):
                    line = run_main(['update-windows', '--cache', cache,
                                     '--out', out])
                r = load(out)
                self.assertEqual(r['status'], 'unavailable')
                self.assertEqual(r['updates'], [])
                self.assertIn('update_windows:unavailable', line)
        finally:
            srv.shutdown()
            srv.server_close()

    def test_merge_keeps_history_beyond_feed(self):
        old = [{'name': 'March 2025 core update', 'kind': 'core',
                'start': '2025-03-13', 'end': '2025-03-27', 'id': 'old'}]
        new = h.parse_status_incidents(INCIDENTS)
        merged = h._merge_updates(old, new)
        self.assertEqual(len(merged), 4)
        self.assertEqual(merged[-1]['id'], 'old')


if __name__ == '__main__':
    unittest.main()
