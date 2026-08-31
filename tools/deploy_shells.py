#!/usr/bin/env python3
"""
deploy_shells.py — deploy the stamped quiz shells to the three per-kid Netlify sites
via the Netlify API (no drag-and-drop). Run by .github/workflows/deploy-shells.yml,
runnable locally too. Zero third-party deps (urllib only), house style.

Why this exists: the kid sites serve STATIC STAMPED COPIES of shell/template_v3.html —
a repo fix reaches nobody until every site is re-deployed (the 31 Aug Scrub-It lesson).
The manual path (tools/stamp_shell.py + drag-deploy) still works; this is the same
build, delivered by API so a session/workflow can do it end-to-end.

DEPLOY METHOD IS THE DIGEST API, NEVER THE ZIP API (31 Aug 2026 incident): the first
version of this script used Netlify's application/zip deploy; the deploy went "ready"
and the page CONTENT verified, but the site served index.html with a non-HTML content
type — every kid site showed raw source instead of a playable page. The digest method
(POST a {path: sha1} manifest, then PUT the bytes — same as tools/netlify_deploy.py,
which has served rendering pages for weeks) is the proven path. And because "content
matched but the page didn't render" is exactly the failure a body-grep can't see,
verify() now also asserts the LIVE response's Content-Type is text/html.

NAME SAFETY (the reason for the fetch step): kids' display names never live in this
public repo, so each seat's name is read out of the CURRENTLY LIVE page's CONFIG and
re-stamped unchanged. Names are never printed to the log — sites, codes and shell
versions only. The STUDENT code baked into the live page is asserted against the
roster seat before anything is deployed, so a build can never land on the wrong site.

MANIFESTS ARE NOT ADDITIVE (netlify_deploy.py's 21 Aug lesson): the manifest becomes
the site's complete file list. Every already-live file is read back and carried
forward, with only /index.html replaced; if the live list can't be read, that seat is
refused rather than risk deploying a partial site.

Per seat: fetch live page -> extract NAME + STUDENT (+ old SHELL_VERSION) -> assert
STUDENT matches -> stamp template -> digest-deploy -> poll until ready -> re-fetch the
live page and assert new SHELL_VERSION + scrub/numeric markers + text/html. Any
failure aborts that seat loudly (Netlify deploys are atomic — the old page stays up)
and exits non-zero.

Usage:
  NETLIFY_AUTH_TOKEN=... python3 tools/deploy_shells.py [--only y8] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "shell", "template_v3.html")
API = "https://api.netlify.com/api/v1"

RE_NAME = re.compile(r'NAME:\s*"([^"]*)"')
RE_STUDENT = re.compile(r'STUDENT:\s*"([^"]*)"')
RE_VERSION = re.compile(r'SHELL_VERSION:\s*"([^"]*)"')


def http(url, data=None, headers=None, method=None, timeout=60):
    """Returns (body_bytes, response_headers)."""
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(), r.headers


def api(path, token, data=None, ctype="application/json", method=None, timeout=90):
    body = json.dumps(data).encode() if isinstance(data, (dict, list)) else data
    raw, _ = http(f"{API}{path}", data=body, method=method,
                  headers={"Authorization": f"Bearer {token}",
                           **({"Content-Type": ctype} if body is not None else {})},
                  timeout=timeout)
    return json.loads(raw) if raw else None


def seats():
    r = json.load(open(os.path.join(REPO, "roster.json")))
    out = []
    for s in r["students"]:
        url = s.get("play_url", "")
        m = re.match(r"https://([^/]+)/?", url)
        if not m:
            raise SystemExit(f"seat {s['code']}: no usable play_url in roster.json")
        out.append((s["code"], m.group(1)))
    return out


def live_config(domain):
    html, _ = http(f"https://{domain}/?cb={int(time.time())}", timeout=30)
    html = html.decode("utf-8", "replace")
    name = RE_NAME.search(html)
    student = RE_STUDENT.search(html)
    version = RE_VERSION.search(html)
    if not (name and student):
        raise SystemExit(f"{domain}: could not read CONFIG from the live page — aborting this seat (nothing deployed)")
    return name.group(1), student.group(1), version.group(1) if version else "?"


def build_page(code, name):
    """Stamp the template, and make every build BYTE-UNIQUE via a trailing build
    stamp. The uniqueness is load-bearing, not cosmetic: Netlify stores blobs by
    sha1 WITH the content-type recorded at first ingestion. The 31 Aug zip deploy
    ingested this page's exact bytes as text/plain, and the digest re-deploy of
    the same sha was answered "already have it" — the mistyped blob just got
    republished. A fresh sha forces a fresh PUT, which types .html correctly."""
    src = open(TEMPLATE, encoding="utf-8").read()
    built = src.replace("__STUDENT__", code).replace("__NAME__", name)
    if "__STUDENT__" in built or "__NAME__" in built:
        raise SystemExit("stamp failed: placeholders left in the build")
    # A META tag, not an HTML comment: Netlify's post-processing strips a trailing
    # comment from the served page (round 4 of this incident — the stamp never came
    # back no matter how long verify waited). report_page's xpdaily-build stamp is a
    # head meta for the same reason; mirror the proven form.
    stamp = f"{code}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{time.time_ns() % 10**9}"
    if built.count("</title>") != 1:
        raise SystemExit("stamp failed: expected exactly one </title> anchor in the template")
    built = built.replace("</title>", f'</title><meta name="xpdaily-shell-build" content="{stamp}">', 1)
    return built.encode("utf-8"), RE_VERSION.search(built).group(1), stamp


# Scoped header overrides, deployed beside the page: even a correctly-typed blob
# is one ingestion quirk away from text/plain (31 Aug incident), and _headers is
# Netlify's definitive say on what the browser receives. Single-page sites, so
# only the two paths that exist are pinned.
HEADERS_FILE = ("/\n  Content-Type: text/html; charset=utf-8\n"
                "/index.html\n  Content-Type: text/html; charset=utf-8\n").encode("utf-8")


def live_manifest(domain, token):
    """{path: sha} of the site's CURRENT published deploy — the carry-forward base.
    None = could not establish; the caller must refuse to deploy (netlify_deploy.py law)."""
    try:
        files = api(f"/sites/{domain}/files", token)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    if files is None:
        return None
    out = {}
    for f in files or []:
        p = f.get("path") or f.get("id") or ""
        sha = f.get("sha")
        if p and sha:
            out["/" + str(p).lstrip("/").lower()] = sha   # lowercase is Netlify's canonical form
    return out


def deploy(domain, page_bytes, token):
    """Digest deploy: manifest first, then upload what Netlify asks for."""
    uploads = {"/index.html": page_bytes, "/_headers": HEADERS_FILE}
    live = live_manifest(domain, token)
    if live is None:
        raise SystemExit(f"{domain}: could not read the live file list — refusing to deploy a partial site")
    manifest = dict(live)
    shas = {}
    for path, blob in uploads.items():
        shas[path] = hashlib.sha1(blob).hexdigest()
        manifest[path] = shas[path]
    dep = api(f"/sites/{domain}/deploys", token, data={"files": manifest})
    dep_id = dep["id"]
    need = set(dep.get("required") or [])
    for path, blob in uploads.items():
        if shas[path] in need:
            api(f"/deploys/{dep_id}/files{path}", token,
                data=blob, ctype="application/octet-stream", method="PUT")
            need.discard(shas[path])
    if need:
        raise SystemExit(f"{domain}: deploy {dep_id} wants {len(need)} file(s) this run does not hold — "
                         "abandoned, site unchanged")
    for _ in range(40):                      # ~2 min budget
        state = dep.get("state")
        if state == "ready":
            return dep_id
        if state in ("error", "rejected"):
            raise SystemExit(f"{domain}: deploy {dep_id} {state} on Netlify — old page stays live")
        time.sleep(3)
        dep = api(f"/deploys/{dep_id}", token, timeout=30)
    raise SystemExit(f"{domain}: deploy {dep_id} not ready after 2 min (state {dep.get('state')!r}) — check Netlify")


def verify(domain, code, want_version, want_stamp):
    """The live page must be THIS EXACT build (its own stamp back — the
    netlify_deploy.py first-run law) AND be served as renderable HTML.
    The content-type assertion exists because the zip-deploy incident passed a
    body-only check while every browser showed raw source. A "ready" deploy can
    lag a few seconds at the CDN edge (netlify_deploy.py's propagation lesson —
    round 3 of this incident failed on exactly that), so retry briefly before
    calling the deploy stale."""
    last = ""
    for attempt in range(6):
        if attempt:
            time.sleep(4)
        body, hdrs = http(f"https://{domain}/?cb={int(time.time())}", timeout=30)
        html = body.decode("utf-8", "replace")
        ctype = (hdrs.get("Content-Type") or "").lower()
        v = RE_VERSION.search(html)
        s = RE_STUDENT.search(html)
        if (v and v.group(1) == want_version and s and s.group(1) == code
                and want_stamp in html
                and "/*SCRUB-WIDGET-START*/" in html and "/*NUMERIC-WIDGET-START*/" in html
                and "text/html" in ctype):
            return ctype
        last = (f"version {v.group(1) if v else '?'}, student {s.group(1) if s else '?'}, "
                f"stamp {'present' if want_stamp in html else 'MISSING'}, content-type {ctype or '?'}")
    raise SystemExit(f"{domain}: VERIFY FAILED after {attempt + 1} tries — live page is not the expected build ({last})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="deploy a single seat code (default: every roster seat)")
    ap.add_argument("--dry-run", action="store_true", help="fetch + stamp + verify preconditions, deploy nothing")
    a = ap.parse_args()

    token = os.environ.get("NETLIFY_AUTH_TOKEN")
    if not token and not a.dry_run:
        raise SystemExit("NETLIFY_AUTH_TOKEN not set")

    targets = [(c, d) for c, d in seats() if not a.only or c == a.only]
    if not targets:
        raise SystemExit(f"--only {a.only!r} matches no roster seat")

    failed = []
    for code, domain in targets:
        try:
            name, live_student, old_v = live_config(domain)
            if live_student != code:
                raise SystemExit(f"{domain}: live page is stamped for {live_student!r}, roster says {code!r} — "
                                 "site/seat mismatch, refusing to deploy")
            page, new_v, stamp = build_page(code, name)
            if a.dry_run:
                print(f"  {code} @ {domain}: shell v{old_v} live, v{new_v} built ({len(page)//1024} KB) — dry run, not deployed")
                continue
            dep_id = deploy(domain, page, token)
            ctype = verify(domain, code, new_v, stamp)
            print(f"  {code} @ {domain}: shell v{old_v} -> v{new_v}  deploy {dep_id}  served {ctype}  VERIFIED LIVE ✓")
        except SystemExit as e:                # per-seat isolation: one bad seat never blocks the rest
            print(f"  ✗ {e}")
            failed.append(code)
    if failed:
        raise SystemExit(f"FAILED seats: {', '.join(failed)} (their old pages are untouched)")
    print("all shells deployed and verified.")


if __name__ == "__main__":
    main()
