#!/usr/bin/env python3
"""
netlify_deploy.py — put one self-contained HTML page live at an unguessable path.

Deploys to a single Netlify site (the reports site) via their API. Each page is
a complete, standalone document — no fetch calls, no data endpoint — so the only
thing that ever reaches a public host is one finished kid-week page at a random
slug. (When family #2 arrives these move behind the login wall; this module is
the no-backend-yet bridge, not the destination.)

Netlify's digest deploy: POST a manifest of {path: sha1}, Netlify replies with
the hashes it doesn't have, then PUT each missing file. Deploys are additive —
previous weeks stay live at their own paths, which gives the report archive for
free.

Secrets (Actions):
  NETLIFY_AUTH_TOKEN   personal access token
  NETLIFY_SITE_ID      the reports site's API id
  DAILYXP_REPORTS_BASE optional; overrides the public base URL

Env-less/no-token: publish() returns False and the caller sends SMS without a
link. Failure to deploy must never block the text.
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

API = "https://api.netlify.com/api/v1"


def base_url():
    b = os.environ.get("DAILYXP_REPORTS_BASE")
    if b:
        return b.rstrip("/")
    site = os.environ.get("NETLIFY_SITE_NAME", "xpdaily-reports")
    return f"https://{site}.netlify.app"


def url_for(slug, kind="r"):
    """kind: 'r' parent report, 'w' kid wrap."""
    return f"{base_url()}/{kind}/{slug}/"


def _req(method, path, token, data=None, ctype="application/json", raw=False):
    url = path if path.startswith("http") else f"{API}{path}"
    body = data if raw else (json.dumps(data).encode() if data is not None else None)
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", ctype)
    with urllib.request.urlopen(req, timeout=90) as r:
        txt = r.read()
    return json.loads(txt) if txt and not raw else None


def publish(slug, html, kind="r", timeout=120):
    """Deploy one page. Returns True only when it is VERIFIED live."""
    token = os.environ.get("NETLIFY_AUTH_TOKEN")
    site = os.environ.get("NETLIFY_SITE_ID")
    if not token or not site:
        print("  netlify: NETLIFY_AUTH_TOKEN / NETLIFY_SITE_ID not set — skipping deploy.")
        return False

    payload = html.encode("utf-8")
    sha = hashlib.sha1(payload).hexdigest()
    path = f"/{kind}/{slug}/index.html"
    try:
        dep = _req("POST", f"/sites/{site}/deploys", token, {"files": {path: sha}})
        need = dep.get("required") or []
        if sha in need:
            _req("PUT", f"{API}/deploys/{dep['id']}/files{path}", token,
                 data=payload, ctype="application/octet-stream", raw=True)
        # wait for it to go ready
        deadline = time.time() + timeout
        while time.time() < deadline:
            d = _req("GET", f"/deploys/{dep['id']}", token)
            if d.get("state") == "ready":
                return verify(url_for(slug, kind))
            if d.get("state") in ("error", "rejected"):
                print(f"  netlify: deploy {d.get('state')}")
                return False
            time.sleep(3)
        print("  netlify: timed out waiting for deploy")
        return False
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        print(f"  netlify: deploy failed ({type(e).__name__})")
        return False


def verify(url):
    """A green deploy is not a live page — fetch it and check (first-run law)."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=30) as r:
            ok = r.status == 200 and b"XPDAILY" in r.read(4000).upper()
        if not ok:
            print(f"  netlify: {url} did not verify")
        return ok
    except (urllib.error.URLError, OSError):
        print(f"  netlify: {url} not reachable")
        return False
