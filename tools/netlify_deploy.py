#!/usr/bin/env python3
"""
netlify_deploy.py — put one self-contained HTML page live at an unguessable path.
Deploys to a single Netlify site (the reports site) via their API. Each page is
a complete, standalone document — no fetch calls, no data endpoint — so the only
thing that ever reaches a public host is one finished kid-week page at a random
slug. (When family #2 arrives these move behind the login wall; this module is
the no-backend-yet bridge, not the destination.)
Netlify's digest deploy: POST a manifest of {path: sha1}, Netlify replies with
the hashes it doesn't have, then PUT each missing file.
DEPLOYS ARE NOT ADDITIVE. This module used to say they were; they are not, and
that mistake took two parents' pages offline on 2026-08-21. The manifest you
POST becomes the COMPLETE file list of a new site snapshot — anything you leave
out is simply not part of that deploy, and 404s the moment it publishes. Three
seats deploying one page each in a loop meant seat 1 was killed by seat 2 and
seat 2 by seat 3; only the last page survived, and each verified fine on its way
past because at that instant it really was the whole site.
So: every deploy re-lists every page that must stay live. The live set is read
back from the site itself (_live_manifest) rather than tracked locally, so it is
self-healing and cannot drift. If that read fails we refuse to deploy rather
than publish a manifest that would take the archive down.
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
# Pages published during THIS process. Netlify's published-files view can lag a
# few seconds behind a just-ready deploy, so a run that publishes several pages
# back to back cannot rely on the read-back alone. Union of both is what ships.
_session = {}
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
def _live_manifest(site, token):
    """{path: sha} for every file in the site's CURRENT published deploy.
    Returns None if the live set could not be established — which is NOT the
    same as an empty site, and callers must treat it as fatal. Deploying a
    partial manifest is how pages get silently deleted.
    """
    try:
        files = _req("GET", f"/sites/{site}/files", token)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"  netlify: could not read live file list ({type(e).__name__})")
        return None
    if files is None:
        return None
    out = {}
    for f in files or []:
        p = f.get("path") or f.get("id") or ""
        sha = f.get("sha")
        if p and sha:
            out["/" + str(p).lstrip("/")] = sha
    return out
def publish(slug, html, kind="r", timeout=120):
    """Deploy one page, keeping every already-live page live. True only when VERIFIED."""
    token = os.environ.get("NETLIFY_AUTH_TOKEN")
    site = os.environ.get("NETLIFY_SITE_ID")
    if not token or not site:
        print("  netlify: NETLIFY_AUTH_TOKEN / NETLIFY_SITE_ID not set — skipping deploy.")
        return False
    payload = html.encode("utf-8")
    sha = hashlib.sha1(payload).hexdigest()
    path = f"/{kind}/{slug}/index.html"
    live = _live_manifest(site, token)
    if live is None:
        print("  netlify: refusing to deploy without the live file list — a "
              "partial manifest would take existing pages offline.")
        return False
    manifest = dict(live)
    manifest.update(_session)
    manifest[path] = sha
    carried = len(manifest) - 1
    try:
        dep = _req("POST", f"/sites/{site}/deploys", token, {"files": manifest})
        need = set(dep.get("required") or [])
        if sha in need:
            _req("PUT", f"{API}/deploys/{dep['id']}/files{path}", token,
                 data=payload, ctype="application/octet-stream", raw=True)
            need.discard(sha)
        if need:
            # Netlify wants bytes we do not hold (an archived page aged out of
            # its store). The deploy cannot complete; it will never publish, so
            # the current site stays intact. Fail loudly rather than hang.
            print(f"  netlify: {len(need)} archived file(s) no longer in Netlify's "
                  f"store and cannot be re-uploaded — deploy abandoned, site unchanged.")
            return False
        # wait for it to go ready
        deadline = time.time() + timeout
        while time.time() < deadline:
            d = _req("GET", f"/deploys/{dep['id']}", token)
            if d.get("state") == "ready":
                if verify(url_for(slug, kind)):
                    _session[path] = sha
                    print(f"  netlify: deploy ready ({carried} existing page(s) carried forward)")
                    return True
                return False
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
