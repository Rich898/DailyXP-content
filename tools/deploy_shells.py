#!/usr/bin/env python3
"""
deploy_shells.py — deploy the stamped quiz shells to the three per-kid Netlify sites
via the Netlify API (no drag-and-drop). Run by .github/workflows/deploy-shells.yml,
runnable locally too. Zero third-party deps (urllib only), house style.

Why this exists: the kid sites serve STATIC STAMPED COPIES of shell/template_v3.html —
a repo fix reaches nobody until every site is re-deployed (the 31 Aug Scrub-It lesson).
The manual path (tools/stamp_shell.py + drag-deploy) still works; this is the same
build, delivered by API so a session/workflow can do it end-to-end.

NAME SAFETY (the reason for the fetch step): kids' display names never live in this
public repo, so each seat's name is read out of the CURRENTLY LIVE page's CONFIG and
re-stamped unchanged. Names are never printed to the log — sites, codes and shell
versions only. The STUDENT code baked into the live page is asserted against the
roster seat before anything is deployed, so a zip can never land on the wrong site.

Per seat: fetch live page -> extract NAME + STUDENT (+ old SHELL_VERSION) -> assert
STUDENT matches -> stamp template -> zip (index.html at root) -> POST to Netlify
/api/v1/sites/<domain>/deploys -> poll until ready -> re-fetch live page and assert
the new SHELL_VERSION + the scrub widget marker are live. Any failure aborts that
seat loudly (Netlify deploys are atomic — the old page stays up) and exits non-zero.

Usage:
  NETLIFY_AUTH_TOKEN=... python3 tools/deploy_shells.py [--only y8] [--dry-run]
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "shell", "template_v3.html")
API = "https://api.netlify.com/api/v1"

RE_NAME = re.compile(r'NAME:\s*"([^"]*)"')
RE_STUDENT = re.compile(r'STUDENT:\s*"([^"]*)"')
RE_VERSION = re.compile(r'SHELL_VERSION:\s*"([^"]*)"')


def http(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


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
    html = http(f"https://{domain}/?cb={int(time.time())}", timeout=30).decode("utf-8", "replace")
    name = RE_NAME.search(html)
    student = RE_STUDENT.search(html)
    version = RE_VERSION.search(html)
    if not (name and student):
        raise SystemExit(f"{domain}: could not read CONFIG from the live page — aborting this seat (nothing deployed)")
    return name.group(1), student.group(1), version.group(1) if version else "?"


def build_zip(code, name):
    src = open(TEMPLATE, encoding="utf-8").read()
    built = src.replace("__STUDENT__", code).replace("__NAME__", name)
    if "__STUDENT__" in built or "__NAME__" in built:
        raise SystemExit("stamp failed: placeholders left in the build")
    new_version = RE_VERSION.search(built).group(1)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("index.html", built)
    return buf.getvalue(), new_version


def deploy(domain, zip_bytes, token):
    raw = http(f"{API}/sites/{domain}/deploys", data=zip_bytes,
               headers={"Authorization": f"Bearer {token}", "Content-Type": "application/zip"},
               timeout=120)
    dep = json.loads(raw)
    dep_id = dep["id"]
    for _ in range(40):                      # ~2 min budget; zip deploys are usually ready in seconds
        state = dep.get("state")
        if state == "ready":
            return dep_id
        if state == "error":
            raise SystemExit(f"{domain}: deploy {dep_id} errored on Netlify — old page stays live")
        time.sleep(3)
        dep = json.loads(http(f"{API}/deploys/{dep_id}",
                              headers={"Authorization": f"Bearer {token}"}, timeout=30))
    raise SystemExit(f"{domain}: deploy {dep_id} not ready after 2 min (state {dep.get('state')!r}) — check Netlify")


def verify(domain, code, want_version):
    html = http(f"https://{domain}/?cb={int(time.time())}", timeout=30).decode("utf-8", "replace")
    v = RE_VERSION.search(html)
    s = RE_STUDENT.search(html)
    ok = (v and v.group(1) == want_version and s and s.group(1) == code
          and "/*SCRUB-WIDGET-START*/" in html and "/*NUMERIC-WIDGET-START*/" in html)
    if not ok:
        raise SystemExit(f"{domain}: VERIFY FAILED — live page is not the expected build "
                         f"(version {v.group(1) if v else '?'}, student {s.group(1) if s else '?'})")


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
            zip_bytes, new_v = build_zip(code, name)
            if a.dry_run:
                print(f"  {code} @ {domain}: shell v{old_v} live, v{new_v} built ({len(zip_bytes)//1024} KB) — dry run, not deployed")
                continue
            dep_id = deploy(domain, zip_bytes, token)
            verify(domain, code, new_v)
            print(f"  {code} @ {domain}: shell v{old_v} -> v{new_v}  deploy {dep_id}  VERIFIED LIVE ✓")
        except SystemExit as e:                # per-seat isolation: one bad seat never blocks the rest
            print(f"  ✗ {e}")
            failed.append(code)
    if failed:
        raise SystemExit(f"FAILED seats: {', '.join(failed)} (their old pages are untouched)")
    print("all shells deployed and verified.")


if __name__ == "__main__":
    main()
