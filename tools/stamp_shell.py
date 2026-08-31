#!/usr/bin/env python3
"""
stamp_shell.py — build the per-student quiz shells for Netlify drag-deploy.

The kids' Netlify sites serve STAMPED COPIES of shell/template_v3.html — a repo
fix does not reach a single seat until each site is re-deployed (learned the
hard way 31 Aug 2026: Scrub It was merged and proven in the repo while the live
shells kept playing it as plain MC). This makes the redeploy one command:

  python3 tools/stamp_shell.py --names "y8=<Name>,y9=<Name>,t1=<Name>"

For every seat it writes  shell/build/<code>/index.html  and  shell/build/<code>-shell.zip
(zip holds index.html at its root — exactly what Netlify's drag-deploy wants), then
prints which site each zip belongs to (from roster.json play_url).

Names are typed at the prompt and land only in the gitignored shell/build/ —
never in the repo (shell/*/ is ignored; stamped pages carry real names).
Deploy: Netlify → that student's site → Deploys → drag the zip. URL never changes.
"""
import argparse
import json
import os
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(REPO, "shell", "template_v3.html")
DEFAULT_OUT = os.path.join(REPO, "shell", "build")


def roster_urls():
    r = json.load(open(os.path.join(REPO, "roster.json")))
    return {s["code"]: s.get("play_url", "?") for s in r["students"]}


def stamp(code, name, out_dir):
    src = open(TEMPLATE, encoding="utf-8").read()
    built = src.replace("__STUDENT__", code).replace("__NAME__", name)
    if "__STUDENT__" in built or "__NAME__" in built:
        raise SystemExit("stamp failed: placeholders left in the build")
    seat_dir = os.path.join(out_dir, code)
    os.makedirs(seat_dir, exist_ok=True)
    page = os.path.join(seat_dir, "index.html")
    with open(page, "w", encoding="utf-8") as f:
        f.write(built)
    zpath = os.path.join(out_dir, f"{code}-shell.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(page, "index.html")
    return zpath


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", required=True,
                    help='comma list code=Name, e.g. "y8=Harrison,y9=R,t1=Rich" (any subset of seats)')
    ap.add_argument("--out", default=DEFAULT_OUT, help="build dir (default shell/build — gitignored)")
    a = ap.parse_args()

    urls = roster_urls()
    pairs = []
    for part in a.names.split(","):
        if "=" not in part:
            raise SystemExit(f"bad --names entry {part!r} (want code=Name)")
        code, name = part.split("=", 1)
        code, name = code.strip(), name.strip()
        if code not in urls:
            raise SystemExit(f"unknown seat {code!r} (roster has {sorted(urls)})")
        if not name:
            raise SystemExit(f"empty name for {code}")
        pairs.append((code, name))

    print(f"stamping {len(pairs)} shell(s) from {os.path.relpath(TEMPLATE, REPO)}")
    for code, name in pairs:
        z = stamp(code, name, a.out)
        print(f"  {code}: {os.path.relpath(z, REPO)}  →  drag onto {urls[code]}  (Deploys → drag zip; URL unchanged)")
    print("done — after deploying, hard-refresh each site and spot-check: the Scrub It doorway")
    print("actually scrubs, and the mental number pad shows the '.' and a/b keys.")
    print("(Result payloads from the fixed shell stamp shell:\"3.2.0\".)")


if __name__ == "__main__":
    main()
