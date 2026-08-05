#!/usr/bin/env python3
"""
notify.py — SMS out via Mobile Message (mobilemessage.com.au).

Sends the short "your quiz is up" nudge to the boys, and (later) the parent
soundbytes/check-ins. AU-owned provider, clean REST/JSON, basic auth.

SECRETS (env — set in GitHub Actions secrets, never in the repo):
  MOBILE_MESSAGE_API_KEY / MOBILE_MESSAGE_API_SECRET   basic-auth pair
  MOBILE_MESSAGE_SENDER    "XP Daily" once the ACMA Sender ID is approved,
                           else the dedicated number (fine for family)

RECIPIENTS are injected, never hardcoded (phone numbers are PII):
  MOBILE_MESSAGE_TO_Y8, MOBILE_MESSAGE_TO_Y9           the boys
  MOBILE_MESSAGE_TO_PARENTS = comma-separated parent numbers

NOTE: confirm the exact request shape against Mobile Message's current API docs
(https://mobilemessage.com.au) before the first live send — the endpoint and
field names below follow their documented REST pattern but should be verified.

Usage:
  python3 tools/notify.py --to-student y8 --text "Tonight's quiz is up 👊"
  python3 tools/notify.py --to-student y8 --text "..." --dry-run
  from tools.notify import send_sms
"""
import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error

API_URL = "https://api.mobilemessage.com.au/v1/messages"


def _recipients(target):
    if target == "y8":
        n = os.environ.get("MOBILE_MESSAGE_TO_Y8")
        return [n] if n else []
    if target == "y9":
        n = os.environ.get("MOBILE_MESSAGE_TO_Y9")
        return [n] if n else []
    if target == "parents":
        raw = os.environ.get("MOBILE_MESSAGE_TO_PARENTS", "")
        return [x.strip() for x in raw.split(",") if x.strip()]
    return []


def send_sms(target, text, ref=None, dry_run=False):
    """Send `text` to a target group (y8|y9|parents). Returns (ok, detail)."""
    to = _recipients(target)
    if not to:
        return False, f"no recipient configured for {target!r} (set MOBILE_MESSAGE_TO_*)"
    sender = os.environ.get("MOBILE_MESSAGE_SENDER", "")
    messages = [{"to": n, "message": text, "sender": sender,
                 "custom_ref": ref or "dailyxp"} for n in to]

    if dry_run:
        return True, "DRY-RUN, not sent:\n" + json.dumps({"sender": sender, "messages": messages}, indent=2)

    key = os.environ.get("MOBILE_MESSAGE_API_KEY")
    secret = os.environ.get("MOBILE_MESSAGE_API_SECRET")
    if not (key and secret):
        return False, "MOBILE_MESSAGE_API_KEY/SECRET not set"
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    body = json.dumps({"messages": messages}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Authorization": f"Basic {auth}", "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return True, r.read().decode()
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return False, str(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to-student", dest="target", required=True, choices=["y8", "y9", "parents"])
    ap.add_argument("--text", required=True)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ok, detail = send_sms(a.target, a.text, ref=a.ref, dry_run=a.dry_run)
    print(("OK " if ok else "FAIL ") + detail)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
