"""Tests for gsc-parse-helper `page-audit` (raw-HTML rendering / 2 MB /
back-button hijack signals) and `sa-trends` (cannibalization + decay), 2.17.0.

Run: python -I bx/skills/seo/tests/test_page_audit_and_trends.py
Stdlib only; no network (urlopen is patched)."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, '..', 'references', 'gsc-parse-helper.py')

spec = importlib.util.spec_from_file_location('gsc_helper', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def run(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn(*args)
    return buf.getvalue()


SSR_PAGE = """<!doctype html><html lang="en"><head>
<title>Pricing &amp; Plans</title>
<link href="https://ex.com/pricing" rel="canonical">
<meta content="index, follow" name="robots">
<script type="application/ld+json">{"@type":"Product"}</script>
</head><body><h1>Pricing</h1><p>""" + ' '.join(['word'] * 120) + """</p>
<script>window.dataLayer=[];history.replaceState({}, '', '/pricing');</script>
</body></html>"""

SPA_SHELL = """<!doctype html><html><head><title>App</title></head>
<body><div id="root"></div><script src="/assets/index.js"></script></body></html>"""

HIJACK = """<html><head><title>x</title></head><body><p>hello</p><script>
history.pushState(null, '', location.href);
window.addEventListener('popstate', function () { location.href = 'https://ads.example/'; });
</script></body></html>"""

ROUTER_ONLY = """<html><body><p>hi</p><script>
document.querySelector('a').onclick = function (e) { history.pushState({}, '', '/next'); };
</script></body></html>"""


class AnalyzeHtml(unittest.TestCase):
    def test_ssr_page_facts(self):
        r = h.analyze_html(SSR_PAGE)
        self.assertEqual(r['title'], 'Pricing & Plans')
        self.assertEqual(r['canonical'], 'https://ex.com/pricing')
        self.assertEqual(r['robots'], 'index,follow')
        self.assertEqual((r['h1'], r['jsonld']), (1, 1))
        self.assertGreaterEqual(r['words'], 120)
        self.assertFalse(r['empty_root'])
        self.assertEqual(r['history_calls'], 1)
        self.assertFalse(r['hijack_suspect'])

    def test_spa_shell(self):
        r = h.analyze_html(SPA_SHELL)
        self.assertTrue(r['empty_root'])
        self.assertLess(r['words'], h.PAGE_AUDIT_THIN_WORDS)
        self.assertIsNone(r['canonical'])
        self.assertEqual(r['inline_scripts'], 0)   # src scripts are not inline

    def test_hijack_vs_router(self):
        self.assertTrue(h.analyze_html(HIJACK)['hijack_suspect'])
        r = h.analyze_html(ROUTER_ONLY)
        self.assertEqual(r['history_calls'], 1)
        self.assertFalse(r['popstate'])
        self.assertFalse(r['hijack_suspect'])


class PageAuditCmd(unittest.TestCase):
    def test_records_and_2mb_flag(self):
        big = '<html><body>' + ('x' * (h.GOOGLEBOT_HTML_LIMIT + 10)) + '</body></html>'
        pages = {'https://ex.com/': SSR_PAGE, 'https://ex.com/big': big,
                 'https://ex.com/app': SPA_SHELL}

        def fake(url):
            if url == 'https://ex.com/gone':
                return 404, url, b'', 'utf-8', '', False
            return 200, url, pages[url].encode(), 'utf-8', 'noai', False

        with tempfile.TemporaryDirectory() as d:
            t = os.path.join(d, 't.txt')
            with open(t, 'w', encoding='utf-8') as f:
                f.write('\n'.join(list(pages) + ['https://ex.com/gone',
                                                 'https://ex.com/']))
            with mock.patch.object(h, '_fetch_raw_page', side_effect=fake):
                out = run(h.cmd_page_audit, t)
        self.assertIn('pages_audited:4', out)        # duplicate dropped
        self.assertIn('over_2mb_count:1', out)
        self.assertIn('url=https://ex.com/gone status=404', out)
        self.assertIn('empty_root=yes', out)
        self.assertIn('x_robots=noai', out)
        self.assertRegex(out, r'url=https://ex.com/big .*over_2mb=yes')


class Cannibalization(unittest.TestCase):
    def test_split_brand_and_threshold(self):
        rows = [
            {'keys': ['crm pricing', 'https://ex.com/pricing'], 'impressions': 600, 'clicks': 30, 'position': 4},
            {'keys': ['crm pricing', 'https://ex.com/blog/crm-cost'], 'impressions': 300, 'clicks': 5, 'position': 9},
            {'keys': ['crm pricing', 'https://ex.com/blog/crm-cost#faq'], 'impressions': 100, 'clicks': 1, 'position': 9},
            {'keys': ['crm pricing', 'https://ex.com/x'], 'impressions': 50, 'clicks': 0, 'position': 30},
            {'keys': ['acme crm', 'https://ex.com/'], 'impressions': 900, 'clicks': 300, 'position': 1},
            {'keys': ['acme crm', 'https://ex.com/about'], 'impressions': 500, 'clicks': 20, 'position': 2},
            {'keys': ['tiny', 'https://ex.com/a'], 'impressions': 40, 'clicks': 0, 'position': 5},
            {'keys': ['tiny', 'https://ex.com/b'], 'impressions': 40, 'clicks': 0, 'position': 6},
        ]
        out = h.find_cannibalization(rows, ['Acme'])
        self.assertEqual([c['query'] for c in out], ['crm pricing'])
        c = out[0]
        self.assertEqual(c['impressions'], 1050)
        self.assertEqual(len(c['pages']), 2)          # /x is under 10%
        self.assertEqual(c['pages'][1]['url'], 'https://ex.com/blog/crm-cost')
        self.assertAlmostEqual(c['pages'][1]['share'], 400 / 1050)


class Decay(unittest.TestCase):
    def test_patterns(self):
        w1 = {'/a': (100, 5000), '/b': (100, 5000), '/c': (100, 5000),
              '/flat': (100, 5000), '/small': (20, 900), '/gone': (50, 800)}
        w2 = {'/a': (80, 4000), '/b': (80, 5000), '/c': (90, 5000),
              '/flat': (100, 5000), '/small': (10, 900), '/gone': (30, 400)}
        w3 = {'/a': (50, 3000), '/b': (60, 5100), '/c': (75, 5000),
              '/flat': (99, 5000), '/small': (2, 900)}
        got = {d['url']: d for d in h.find_decay([w1, w2, w3])}
        self.assertEqual(set(got), {'/a', '/b', '/gone'})   # /c only -25%
        self.assertEqual(got['/a']['pattern'], 'visibility_loss')
        self.assertEqual(got['/b']['pattern'], 'ctr_loss')
        self.assertEqual(got['/gone']['pattern'], 'vanished')


class SaTrendsCmd(unittest.TestCase):
    def test_cached_run_needs_no_credentials(self):
        calls = []

        def fake_rows(site, body, cache_dir, no_cache, creds):
            calls.append(body)
            if body['dimensions'] == ['query', 'page']:
                return [{'keys': ['q', '/p1'], 'impressions': 100, 'clicks': 1, 'position': 3},
                        {'keys': ['q', '/p2'], 'impressions': 100, 'clicks': 1, 'position': 5}], 'hit'
            clicks = {0: 100, 1: 60, 2: 20}[len(calls) - 2]
            return [{'keys': ['/p1'], 'clicks': clicks, 'impressions': 1000}], 'hit'

        with mock.patch.object(h, '_sa_rows', side_effect=fake_rows), \
                mock.patch.object(h, 'resolve_credentials') as rc:
            out = run(h.cmd_sa_trends, 'c', 'sc-domain:ex.com', '2026-11-03', '90')
        rc.assert_not_called()
        self.assertIn('sa_trend_calls:hit hit hit hit', out)
        self.assertIn('cannibal_queries:1', out)
        self.assertIn('decay_pages:1', out)
        self.assertIn('pattern=ctr_loss', out)
        # windows: oldest first, contiguous, 28 days each, ending at end_date
        w = [(b['startDate'], b['endDate']) for b in calls[1:]]
        self.assertEqual(w, [('2026-08-12', '2026-09-08'),
                             ('2026-09-09', '2026-10-06'),
                             ('2026-10-07', '2026-11-03')])
        self.assertEqual(calls[0]['startDate'], '2026-08-06')

    def test_cache_hit_reads_file(self):
        with tempfile.TemporaryDirectory() as d:
            body = {'dimensions': ['page']}
            key = h.hashlib.sha1(('s|' + json.dumps(body, sort_keys=True)).encode()).hexdigest()
            with open(os.path.join(d, f'sa-trend-{key}.json'), 'w', encoding='utf-8') as f:
                json.dump({'rows': [{'keys': ['/x']}]}, f)
            creds = []
            rows, st = h._sa_rows('s', body, d, False, creds)
        self.assertEqual((st, rows, creds), ('hit', [{'keys': ['/x']}], []))


if __name__ == '__main__':
    unittest.main()
