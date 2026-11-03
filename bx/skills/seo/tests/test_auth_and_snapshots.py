"""Regression tests for gsc-parse-helper: mint-failure classification and
snapshot retention (S68).

Run: python -I bx/skills/seo/tests/test_auth_and_snapshots.py
Stdlib only; no network (urlopen is patched)."""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import date
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, '..', 'references', 'gsc-parse-helper.py')

spec = importlib.util.spec_from_file_location('gsc_helper', HELPER)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)


def http_error(code, body):
    return urllib.error.HTTPError(
        h.OAUTH_TOKEN_ENDPOINT, code, 'err', {},
        io.BytesIO(json.dumps(body).encode()))


ADC = {'type': 'authorized_user', 'client_id': 'c', 'client_secret': 's',
       'refresh_token': 'r'}


class MintClassification(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cred = os.path.join(self.tmp.name, 'adc.json')
        with open(self.cred, 'w') as f:
            json.dump(ADC, f)
        self.env = mock.patch.dict(os.environ, {
            'GOOGLE_APPLICATION_CREDENTIALS': self.cred,
            'GCLOUD_TOKEN': '', 'GCLOUD_QUOTA_PROJECT': ''})
        self.env.start()
        self.sleep = mock.patch.object(h.time, 'sleep')
        self.sleep.start()

    def tearDown(self):
        self.sleep.stop()
        self.env.stop()
        self.tmp.cleanup()

    def mint(self, side_effect):
        with mock.patch.object(h.urllib.request, 'urlopen',
                               side_effect=side_effect) as m:
            with self.assertRaises(h.CredentialError) as cm:
                h.resolve_credentials()
        return cm.exception, m.call_count

    def test_invalid_grant_is_token_revoked_and_not_retried(self):
        e, calls = self.mint(lambda *a, **k: (_ for _ in ()).throw(http_error(
            400, {'error': 'invalid_grant',
                  'error_description': 'Token has been expired or revoked.'})))
        self.assertEqual(e.reason, 'token_revoked')
        self.assertIn('expired or revoked', e.detail)
        self.assertEqual(calls, 1)

    def test_rapt_is_reauth_required(self):
        e, _ = self.mint(lambda *a, **k: (_ for _ in ()).throw(http_error(
            400, {'error': 'invalid_grant', 'error_subtype': 'invalid_rapt',
                  'error_description': 'reauth related error (invalid_rapt)'})))
        self.assertEqual(e.reason, 'reauth_required')

    def test_invalid_client(self):
        e, _ = self.mint(lambda *a, **k: (_ for _ in ()).throw(http_error(
            401, {'error': 'invalid_client'})))
        self.assertEqual(e.reason, 'client_invalid')

    def test_network_retried_then_network_reason(self):
        e, calls = self.mint(urllib.error.URLError('getaddrinfo failed'))
        self.assertEqual(e.reason, 'network')
        self.assertEqual(calls, h.TOKEN_REFRESH_ATTEMPTS)
        self.assertNotIn('Re-auth', str(e))

    def test_5xx_retried_then_succeeds(self):
        ok = mock.MagicMock()
        ok.__enter__.return_value.read.return_value = b'{"access_token":"T"}'
        seq = [http_error(503, {}), ok]
        with mock.patch.object(h.urllib.request, 'urlopen', side_effect=seq):
            with mock.patch.dict(os.environ, {'GCLOUD_QUOTA_PROJECT': 'qp'}):
                tok, qp = h.resolve_credentials()
        self.assertEqual((tok, qp), ('T', 'qp'))

    def test_default_path_revoked_skips_gcloud_fallback(self):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = ''
        with mock.patch.object(h, '_default_adc_path', return_value=self.cred), \
             mock.patch.object(h, '_read_skill_config', return_value={}), \
             mock.patch.object(h, '_gcloud_token') as g:
            e, _ = self.mint(lambda *a, **k: (_ for _ in ()).throw(http_error(
                400, {'error': 'invalid_grant'})))
        self.assertEqual(e.reason, 'token_revoked')
        g.assert_not_called()

    def test_auth_token_prints_detail_line(self):
        out = io.StringIO()
        with mock.patch.object(h.urllib.request, 'urlopen',
                               side_effect=http_error(400, {
                                   'error': 'invalid_grant',
                                   'error_description': 'Bad Request'})), \
             mock.patch('sys.stdout', out), mock.patch('sys.stderr', io.StringIO()):
            with self.assertRaises(SystemExit):
                h.cmd_auth_token()
        lines = out.getvalue().splitlines()
        self.assertEqual(lines[0], 'AUTH_ERROR:token_revoked')
        self.assertTrue(lines[1].startswith('AUTH_DETAIL:HTTP 400 invalid_grant'))


def snap(d, day, sha='abc1234'):
    p = os.path.join(d, f'{day}T120000-{sha}.json')
    with open(p, 'w') as f:
        f.write('{}')
    return p


class SnapshotRetention(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_s68_month_old_baseline_survives(self):
        # The S68 failure: a 31-day-old baseline. Old rule deleted it.
        snap(self.d, '2026-10-02')
        removed, kept = h.snapshot_prune(self.d, today=date(2026, 11, 2))
        self.assertEqual((removed, kept), (0, 1))

    def test_newest_five_kept_regardless_of_age(self):
        for m in range(1, 8):  # 7 snapshots, all > 180 days old
            snap(self.d, f'2025-0{m}-01')
        removed, kept = h.snapshot_prune(self.d, today=date(2026, 11, 2))
        self.assertEqual((removed, kept), (2, 5))
        self.assertNotIn('2025-01-01T120000-abc1234.json', os.listdir(self.d))

    def test_recent_beyond_five_kept(self):
        for day in range(1, 10):
            snap(self.d, f'2026-10-0{day}')
        self.assertEqual(h.snapshot_prune(self.d, today=date(2026, 11, 2)),
                         (0, 9))

    def test_foreign_files_untouched(self):
        for m in range(1, 8):
            snap(self.d, f'2025-0{m}-01')
        open(os.path.join(self.d, 'notes.txt'), 'w').close()
        h.snapshot_prune(self.d, today=date(2026, 11, 2))
        self.assertIn('notes.txt', os.listdir(self.d))

    def run_cli(self, cache):
        out = os.path.join(self.d, 'snaps', '2026-11-02T120000-abc1234.json')
        r = subprocess.run([sys.executable, '-I', HELPER, 'snapshot-write',
                            cache, '2026-11-02T120000', 'abc1234',
                            'sc-domain:x.com', out],
                           capture_output=True, text=True)
        return r, out

    def test_empty_cache_refuses_and_prunes_nothing(self):
        cache = os.path.join(self.d, 'cache')
        os.makedirs(cache)
        os.makedirs(os.path.join(self.d, 'snaps'))
        old = snap(os.path.join(self.d, 'snaps'), '2024-01-01')
        r, out = self.run_cli(cache)
        self.assertEqual(r.returncode, 1)
        self.assertIn('snapshot_write_failed:no_inspections_in_cache', r.stdout)
        self.assertFalse(os.path.exists(out))
        self.assertTrue(os.path.exists(old))

    def test_write_then_prune_reports_counts(self):
        cache = os.path.join(self.d, 'cache')
        os.makedirs(cache)
        with open(os.path.join(cache, 'ui-1.json'), 'w') as f:
            json.dump({'inspectionUrl': 'https://x.com/a', 'inspectionResult': {
                'indexStatusResult': {'coverageState': 'Submitted and indexed'}}}, f)
        snaps = os.path.join(self.d, 'snaps')
        os.makedirs(snaps)
        for m in range(1, 7):  # 6 old + new one = 7; newest 5 kept
            snap(snaps, f'2024-0{m}-01')
        r, out = self.run_cli(cache)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('snapshots_pruned:2', r.stdout)
        self.assertIn('snapshots_retained:5', r.stdout)
        self.assertTrue(os.path.exists(out))


def ui_entry(cache, site, url, state):
    with open(h._ui_cache_path(cache, site, url), 'w') as f:
        json.dump({'inspectionUrl': url, 'inspectionResult': {
            'indexStatusResult': {'coverageState': state}}}, f)


class RunScoping(unittest.TestCase):
    SITE = 'sc-domain:x.com'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_only_includes_manifest_urls(self):
        ui_entry(self.cache, self.SITE, 'https://x.com/now', 'Submitted and indexed')
        ui_entry(self.cache, self.SITE, 'https://x.com/stale', 'Not found (404)')
        h._atomic_write_json(os.path.join(self.cache, h.RUN_MANIFEST_NAME),
                             {'site_url': self.SITE, 'urls': ['https://x.com/now']})
        out = os.path.join(self.cache, 's', '2026-11-02T120000-abc1234.json')
        with mock.patch('sys.stdout', io.StringIO()):
            h.snapshot_write(self.cache, '2026-11-02T120000', 'abc1234',
                             self.SITE, out)
        with open(out) as f:
            self.assertEqual(list(json.load(f)['inspections']),
                             ['https://x.com/now'])

    def test_no_manifest_falls_back_to_all(self):
        ui_entry(self.cache, self.SITE, 'https://x.com/a', 'Submitted and indexed')
        ui_entry(self.cache, self.SITE, 'https://x.com/b', 'Submitted and indexed')
        files, scoped = h._run_ui_files(self.cache)
        self.assertEqual((len(files), scoped), (2, False))

    def test_dropped_from_sitemap_is_not_a_deindex(self):
        prev = os.path.join(self.cache, 'p.json')
        cur = os.path.join(self.cache, 'c.json')
        for p, st in ((prev, 'Submitted and indexed'),
                      (cur, 'Indexed, not submitted in sitemap')):
            with open(p, 'w') as f:
                json.dump({'inspections': {'https://x.com/a': st},
                           'run_timestamp': '2026-11-02T120000',
                           'commit_sha': 'abc'}, f)
        out = io.StringIO()
        with mock.patch('sys.stdout', out):
            h.regression(cur, prev)
        self.assertIn('transitions_total:0', out.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
