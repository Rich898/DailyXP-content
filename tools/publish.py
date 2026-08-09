#!/usr/bin/env python3
"""
publish.py — limb #1.5: the ONE atomic publish operation.

Replaces hand-editing y8.json/y9.json (the path that caused the Wed 5 Aug
rollback). Every publish runs the same five steps, and step 5 is the one that
makes the rollback bug impossible to miss again:

  1. VALIDATE   tools/validate.py must pass (blocks on any error)
  2. WRITE      overwrite <student>.json
  3. ARCHIVE    copy to history/<student>/<date>_<tag>.json (feeds no-repeat)
  4. COMMIT     git add + commit + push (single-purpose commit message)
  5. VERIFY     fetch the raw URL the shell fetches and assert the LIVE tag ==
                the tag we intended. If they differ (silent overwrite, cache,
                wrong branch) -> LOUD FAIL, non-zero exit.

Also appends a line to publish_log.jsonl (private audit trail).

Usage:
  python3 tools/publish.py <set.json>            # full publish + verify
  python3 tools/publish.py <set.json> --no-push  # local dry run (validate+archive, skip git)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from validate import validate_set  # noqa: E402

# history/ moved to the private repo; point archive + no-repeat there via env in automation
HISTORY_DIR = os.environ.get("DAILYXP_HISTORY_DIR", os.path.join(REPO, "history"))

RAW = "https://raw.githubusercontent.com/Rich898/DailyXP-content/main/{student}.json"


def read_token():
    if os.environ.get("GH_TOKEN"):
        return os.environ["GH_TOKEN"].strip()
    for p in (os.path.expanduser("~/.ghtoken"), "/home/claude/.ghtoken", os.path.join(REPO, ".ghtoken")):
        if os.path.exists(p):
            return open(p).read().strip()
    return None


def slug(tag):
    return re.sub(r"[^A-Za-z0-9.]+", "-", tag).strip("-")


def sh(cmd):
    return subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)


def publish(set_path, push=True):
    s = json.load(open(set_path))
    student = s.get("student")
    import roster
    if student not in roster.students():
        print(f"ABORT: bad student {student!r}")
        return 2

    # 1) VALIDATE
    errors, warns = validate_set(s, HISTORY_DIR)
    for w in warns:
        print(f"  WARN  {w}")
    if errors:
        for e in errors:
            print(f"  ERROR {e}")
        print(f"ABORT: {len(errors)} validation error(s) — nothing published.")
        return 1
    is_placeholder = s.get("status") == "placeholder"
    intended_tag = s.get("tag") if not is_placeholder else "(placeholder)"
    print(f"VALIDATE ✓  {student} {intended_tag}  ({len(s.get('questions',[]))} Qs)")

    # 2) WRITE
    target = os.path.join(REPO, f"{student}.json")
    with open(target, "w") as f:
        json.dump(s, f, indent=2, ensure_ascii=False)
    print(f"WRITE ✓  {student}.json")

    # 3) ARCHIVE (real sets only)
    archived = None
    if not is_placeholder:
        adir = os.path.join(HISTORY_DIR, student)
        os.makedirs(adir, exist_ok=True)
        archived = os.path.join(adir, f"{s['date']}_{slug(s['tag'])}.json")
        with open(archived, "w") as f:
            json.dump(s, f, indent=2, ensure_ascii=False)
        print(f"ARCHIVE ✓  {os.path.relpath(archived, REPO)}")

    if not push:
        print("STOP: --no-push (local dry run). Validate + write + archive done; skipped git + verify.")
        return 0

    # 4) COMMIT + PUSH
    token = read_token()
    if not token:
        print("ABORT: no token (set GH_TOKEN or ~/.ghtoken)")
        return 2
    add_paths = [f"{student}.json"]
    # only include the archive in THIS (public) commit if it lives inside this repo.
    # In automation HISTORY_DIR points at the private repo — the workflow commits that separately.
    if archived and os.path.abspath(archived).startswith(os.path.abspath(REPO) + os.sep):
        add_paths.append(os.path.relpath(archived, REPO))
    sh(["git", "add"] + add_paths)
    msg = f"publish {student} {intended_tag}"
    c = sh(["git", "commit", "-q", "-m", msg])
    if c.returncode != 0 and "nothing to commit" not in (c.stdout + c.stderr):
        print(f"ABORT: commit failed: {c.stderr or c.stdout}")
        return 2
    push_url = f"https://x-access-token:{token}@github.com/Rich898/DailyXP-content.git"
    p = sh(["git", "push", "-q", push_url, "main"])
    if p.returncode != 0:
        print(f"ABORT: push failed: {p.stderr or p.stdout}")
        return 2
    head = sh(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
    print(f"COMMIT ✓  {head}  \u201c{msg}\u201d")

    # 5) VERIFY the live URL matches intent
    time.sleep(3)
    url = RAW.format(student=student) + f"?cb={int(time.time())}"
    verified = False
    try:
        live = json.loads(urllib.request.urlopen(url, timeout=15).read().decode())
        if is_placeholder:
            verified = live.get("status") == "placeholder"
            live_tag = "(placeholder)" if verified else live.get("tag")
        else:
            live_tag = live.get("tag")
            verified = (live_tag == s.get("tag"))
        if verified:
            print(f"VERIFY ✓  live {student}.json serves {live_tag} — matches intent.")
        else:
            print(f"VERIFY ✗✗  live serves {live_tag!r}, intended {intended_tag!r} — "
                  f"LIVE DOES NOT MATCH. Investigate (overwrite? cache? wrong branch?).")
    except Exception as e:
        print(f"VERIFY ?  could not read live URL ({e}) — check manually.")

    # audit log (private)
    log = os.path.join(REPO, "publish_log.jsonl")
    with open(log, "a") as f:
        f.write(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "student": student,
            "date": s.get("date"), "tag": intended_tag, "placeholder": is_placeholder,
            "commit": head, "verified": verified,
        }) + "\n")

    return 0 if verified else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set_path")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()
    sys.exit(publish(a.set_path, push=not a.no_push))


if __name__ == "__main__":
    main()
