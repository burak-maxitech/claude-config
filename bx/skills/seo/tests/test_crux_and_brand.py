"""Tests for gsc-parse-helper `crux` and the brand/non-brand split in `brand`
(2.16.0 — site-profile intake).

Run: python -I bx/skills/seo/tests/test_crux_and_brand.py
Stdlib only; no network (urlopen is patched)."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
import urllib.error
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


class FakeResp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def crux_body(lcp, inp, cls, ttfb=600):
    m = lambda v: {'percentiles': {'p75': v}}
    return json.dumps({'record': {'metrics': {
        'largest_contentful_paint': m(lcp),
        'interaction_to_next_paint': m(inp),
        'cumulative_layout_shift': m(str(cls)),  # CrUX returns CLS as string
        'experimental_time_to_first_byte': m(ttfb)}}}).encode()


class Crux(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.targets = os.path.join(self.tmp.name, 't.txt')
        with open(self.targets, 'w', encoding='utf-8') as f:
            f.write('origin https://example.com\nurl https://example.com/p\n'
                    'garbage line here\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_no_key(self):
        with mock.patch.dict(os.environ, {'CRUX_API_KEY': ''}):
            self.assertIn('CRUX_ERROR:no_key', run(h.cmd_crux, self.targets))

    def test_rates_and_never_prints_key(self):
        def fake(req, timeout=0):
            body = json.loads(req.data)
            if body.get('url'):
                raise urllib.error.HTTPError(req.full_url, 404, 'nf', {}, None)
            if body['formFactor'] == 'PHONE':
                return FakeResp(crux_body(4500, 150, 0.12))
            return FakeResp(crux_body(1800, 90, 0.02))
        with mock.patch.dict(os.environ, {'CRUX_API_KEY': 'SECRETKEY'}), \
                mock.patch.object(h.urllib.request, 'urlopen', fake):
            out = run(h.cmd_crux, self.targets)
        self.assertNotIn('SECRETKEY', out)
        self.assertIn('crux_queries:3', out)  # origin×2 + url×1, garbage skipped
        self.assertIn('ff=PHONE status=ok lcp_p75=4500(poor) '
                      'inp_p75=150(good) cls_p75=0.120(needs_improvement)', out)
        self.assertIn('ff=DESKTOP status=ok lcp_p75=1800(good)', out)
        self.assertIn('url=https://example.com/p ff=PHONE status=no_data', out)
        self.assertIn('crux_poor_metrics:1', out)

    def test_network_error_is_not_fatal(self):
        def boom(req, timeout=0):
            raise urllib.error.URLError('down')
        with mock.patch.dict(os.environ, {'CRUX_API_KEY': 'k'}), \
                mock.patch.object(h.urllib.request, 'urlopen', boom):
            out = run(h.cmd_crux, self.targets)
        self.assertIn('status=error:network', out)
        self.assertIn('crux_poor_metrics:0', out)

    def test_boundaries(self):
        self.assertEqual(h._crux_rate(2500, 2500, 4000), 'good')
        self.assertEqual(h._crux_rate(4000, 2500, 4000), 'needs_improvement')
        self.assertEqual(h._crux_rate(4001, 2500, 4000), 'poor')
        self.assertEqual(h._crux_rate(None, 1, 2), 'n/a')


class BrandSplit(unittest.TestCase):
    def test_aliases_and_split(self):
        rows = [
            {'keys': ['acme pricing'], 'clicks': 50, 'impressions': 100,
             'ctr': 0.5, 'position': 1.0},
            {'keys': ['akme app'], 'clicks': 1, 'impressions': 40,
             'ctr': 0.025, 'position': 6.0},
            {'keys': ['invoice software'], 'clicks': 9, 'impressions': 900,
             'ctr': 0.01, 'position': 12.0},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'q1.json')
            with open(p, 'w', encoding='utf-8') as f:
                json.dump({'rows': rows}, f)
            out = run(h.detect_brand_anomaly, p, 'Acme, akme')
        self.assertIn('brand_query_matches:2', out)
        self.assertIn('brand_clicks:51', out)
        self.assertIn('nonbrand_impressions:900', out)
        self.assertIn('brand_click_share:0.8500', out)
        self.assertIn('nonbrand_ctr:0.0100', out)
        self.assertIn('brand_anomalies:1', out)  # only "akme app" (pos 6)


if __name__ == '__main__':
    unittest.main()
