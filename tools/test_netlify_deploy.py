#!/usr/bin/env python3
"""
Tests for netlify_deploy — with the regression test for the 2026-08-21 outage
front and centre: a deploy must carry forward every already-live page, never
publish a manifest containing only the page it is deploying.

Authored fresh (the original patch's test file was lost); it exercises the
behaviour of the committed netlify_deploy.py, not a copy of that patch.
"""
import hashlib
import os
import unittest
from unittest import mock

import netlify_deploy as nd


def _sha1(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class BaseUrlTests(unittest.TestCase):
    def test_explicit_base_wins_and_trailing_slash_stripped(self):
        with mock.patch.dict(os.environ, {"DAILYXP_REPORTS_BASE": "https://x.example/"}, clear=True):
            self.assertEqual(nd.base_url(), "https://x.example")

    def test_falls_back_to_site_name(self):
        with mock.patch.dict(os.environ, {"NETLIFY_SITE_NAME": "somesite"}, clear=True):
            self.assertEqual(nd.base_url(), "https://somesite.netlify.app")

    def test_url_for_kinds(self):
        with mock.patch.dict(os.environ, {"DAILYXP_REPORTS_BASE": "https://x.example"}, clear=True):
            self.assertEqual(nd.url_for("abc", "r"), "https://x.example/r/abc/")
            self.assertEqual(nd.url_for("abc", "w"), "https://x.example/w/abc/")


class PublishGuardTests(unittest.TestCase):
    def test_no_credentials_returns_false(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertFalse(nd.publish("slug", "<html>XPDAILY</html>"))

    def test_refuses_when_live_manifest_unreadable(self):
        # The critical safety property: if we cannot read the live file list we
        # must NOT deploy (a partial manifest would delete the archive), and we
        # must never reach the POST.
        env = {"NETLIFY_AUTH_TOKEN": "t", "NETLIFY_SITE_ID": "s"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(nd, "_live_manifest", return_value=None), \
             mock.patch.object(nd, "_req") as req:
            self.assertFalse(nd.publish("slug", "<html>XPDAILY</html>"))
            req.assert_not_called()


class ManifestCarryForwardTests(unittest.TestCase):
    """The regression test for the outage."""

    def setUp(self):
        nd._session.clear()   # module-level cache — isolate tests from each other

    def _run_publish(self, live_files, extra_env=None, verify_ok=True):
        html = "<html>XPDAILY page</html>"
        new_sha = _sha1(html)
        captured = {}

        def fake_req(method, path, token, data=None, ctype="application/json", raw=False):
            if method == "GET" and path.endswith("/files"):
                return live_files
            if method == "POST" and path.endswith("/deploys"):
                captured["manifest"] = dict(data["files"])
                return {"id": "dep1", "required": [new_sha]}
            if method == "PUT":
                captured["put"] = path
                return None
            if method == "GET" and "/deploys/" in path:
                return {"state": "ready"}
            raise AssertionError(f"unexpected request {method} {path}")

        env = {"NETLIFY_AUTH_TOKEN": "t", "NETLIFY_SITE_ID": "s"}
        env.update(extra_env or {})
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(nd, "_req", side_effect=fake_req), \
             mock.patch.object(nd, "verify", return_value=verify_ok), \
             mock.patch.object(nd.time, "sleep", return_value=None):
            result = nd.publish("newkid", html, kind="r")
        return result, captured, new_sha

    def test_deploy_includes_every_already_live_page(self):
        live = [
            {"path": "/r/alice/index.html", "sha": "aaa"},
            {"path": "/r/bob/index.html", "sha": "bbb"},
        ]
        result, captured, new_sha = self._run_publish(live)
        self.assertTrue(result)
        manifest = captured["manifest"]
        # every pre-existing page survives...
        self.assertEqual(manifest["/r/alice/index.html"], "aaa")
        self.assertEqual(manifest["/r/bob/index.html"], "bbb")
        # ...and the new page is added, not substituted
        self.assertEqual(manifest["/r/newkid/index.html"], new_sha)
        self.assertEqual(len(manifest), 3)

    def test_new_file_is_uploaded_when_required(self):
        result, captured, new_sha = self._run_publish([])
        self.assertTrue(result)
        self.assertIn("/r/newkid/index.html", captured["put"])

    def test_failed_verify_returns_false(self):
        result, _, _ = self._run_publish(
            [{"path": "/r/alice/index.html", "sha": "aaa"}], verify_ok=False
        )
        self.assertFalse(result)


class SessionCacheTests(unittest.TestCase):
    def setUp(self):
        nd._session.clear()

    def tearDown(self):
        nd._session.clear()

    def test_session_pages_carried_forward_within_a_run(self):
        # Netlify's read-back can lag; a page published earlier this process
        # must be re-listed even if the live read does not show it yet.
        nd._session["/r/earlier/index.html"] = "eee"
        html = "<html>XPDAILY</html>"
        new_sha = _sha1(html)
        captured = {}

        def fake_req(method, path, token, data=None, ctype="application/json", raw=False):
            if method == "GET" and path.endswith("/files"):
                return []  # live read shows nothing yet
            if method == "POST" and path.endswith("/deploys"):
                captured["manifest"] = dict(data["files"])
                return {"id": "d", "required": []}
            if method == "GET" and "/deploys/" in path:
                return {"state": "ready"}
            raise AssertionError(f"unexpected {method} {path}")

        env = {"NETLIFY_AUTH_TOKEN": "t", "NETLIFY_SITE_ID": "s"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(nd, "_req", side_effect=fake_req), \
             mock.patch.object(nd, "verify", return_value=True), \
             mock.patch.object(nd.time, "sleep", return_value=None):
            self.assertTrue(nd.publish("newkid", html))
        self.assertEqual(captured["manifest"]["/r/earlier/index.html"], "eee")
        self.assertEqual(captured["manifest"]["/r/newkid/index.html"], new_sha)


class CaseNormalisationTests(unittest.TestCase):
    """28 Aug 2026 root cause: Netlify lowercases paths, our slugs were
    mixed-case. The carry-forward manifest re-listed the live page under its
    lowercase path while publish() added the replacement under a MIXED-case
    path — two entries, one normalised path, and the stale one won. Pages
    only ever landed when NEW to the site."""

    def setUp(self):
        nd._session.clear()   # module-level cache — isolate tests from each other

    def _capture_publish(self, slug, live_files):
        html = "<html>XPDAILY page</html>"
        new_sha = _sha1(html)
        captured = {}

        def fake_req(method, path, token, data=None, ctype="application/json", raw=False):
            if method == "GET" and path.endswith("/files"):
                return live_files
            if method == "POST" and path.endswith("/deploys"):
                captured["manifest"] = dict(data["files"])
                return {"id": "dep1", "required": [new_sha]}
            if method == "PUT":
                captured["put"] = path
                return None
            if method == "GET" and "/deploys/" in path:
                return {"state": "ready"}
            raise AssertionError(f"unexpected request {method} {path}")

        env = {"NETLIFY_AUTH_TOKEN": "t", "NETLIFY_SITE_ID": "s"}
        with mock.patch.dict(os.environ, env, clear=True), \
             mock.patch.object(nd, "_req", side_effect=fake_req), \
             mock.patch.object(nd, "verify", return_value=True), \
             mock.patch.object(nd.time, "sleep", return_value=None):
            result = nd.publish(slug, html, kind="r")
        return result, captured, new_sha

    def test_mixed_case_slug_replaces_its_live_lowercase_page(self):
        # The exact Friday shape: t1's live page listed lowercase, publish
        # called with the mixed-case slug. The manifest must contain exactly
        # ONE entry for that page — lowercase, carrying the NEW sha.
        live = [{"path": "/r/akqqibfftbrt/index.html", "sha": "old_light_sha"}]
        result, captured, new_sha = self._capture_publish("AKqqiBFftBrt", live)
        self.assertTrue(result)
        manifest = captured["manifest"]
        self.assertEqual(manifest["/r/akqqibfftbrt/index.html"], new_sha)
        self.assertNotIn("/r/AKqqiBFftBrt/index.html", manifest)
        self.assertEqual(len(manifest), 1)

    def test_live_manifest_keys_are_lowercased(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             mock.patch.object(nd, "_req", return_value=[
                 {"path": "/r/MiXeD/index.html", "sha": "abc"}]):
            self.assertEqual(nd._live_manifest("s", "t"),
                             {"/r/mixed/index.html": "abc"})

    def test_url_for_is_lowercase(self):
        with mock.patch.dict(os.environ, {"DAILYXP_REPORTS_BASE": "https://x.example"}, clear=True):
            self.assertEqual(nd.url_for("AKqqiBFftBrt", "r"),
                             "https://x.example/r/akqqibfftbrt/")


class BuildStampVerifyTests(unittest.TestCase):
    """28 Aug 2026 regression: deploys went 'ready' while the site served a
    stale locked deploy, and verify() — checking only 200 + the brand string —
    waved the stale page through. verify(expect=<stamp>) closes that hole."""

    STAMPED = ('<html><head><meta charset="UTF-8" />\n'
               '<meta name="xpdaily-build" content="abc123def 2026-08-29T01:00:00Z" />'
               '</head><body>XPDAILY</body></html>')

    def test_stamp_extracted_from_payload(self):
        self.assertEqual(nd._stamp_of(self.STAMPED),
                         "abc123def 2026-08-29T01:00:00Z")

    def test_no_stamp_is_none(self):
        self.assertIsNone(nd._stamp_of("<html>XPDAILY</html>"))

    def _fetched(self, body):
        resp = mock.MagicMock()
        resp.status = 200
        resp.read.return_value = body.encode()
        resp.__enter__ = lambda s: resp
        resp.__exit__ = lambda s, *a: False
        return resp

    def test_verify_demands_the_exact_stamp(self):
        stale = "<html><body>XPDAILY (last week's page)</body></html>"
        with mock.patch.object(nd.urllib.request, "urlopen",
                               return_value=self._fetched(stale)):
            self.assertFalse(nd.verify("https://x/r/a/",
                                       expect="abc123def 2026-08-29T01:00:00Z"))

    def test_verify_passes_on_the_fresh_render(self):
        with mock.patch.object(nd.urllib.request, "urlopen",
                               return_value=self._fetched(self.STAMPED)):
            self.assertTrue(nd.verify("https://x/r/a/",
                                      expect="abc123def 2026-08-29T01:00:00Z"))

    def test_verify_without_stamp_keeps_brand_check(self):
        with mock.patch.object(nd.urllib.request, "urlopen",
                               return_value=self._fetched("<html>XPDAILY</html>")):
            self.assertTrue(nd.verify("https://x/r/a/"))


if __name__ == "__main__":
    unittest.main()
