#!/usr/bin/env python3
"""
notify.py — SMS out via Mobile Message (mobilemessage.com.au).

Sends the short "your quiz is up" nudge to the boys, and (later) the parent
soundbytes/check-ins. AU-owned provider, clean REST/JSON, basic auth.

SECRETS (env — set in GitHub Actions secrets, never in the repo):
  MOBILE_MESSAGE_API_KEY / MOBILE_MESSAGE_API_SECRET   basic-auth pair
  MOBILE_MESSAGE_SENDER    "XPDaily" once the ACMA Sender ID is approved,
                           else the dedicated number (fine for family)

RECIPIENTS are injected, never hardcoded (phone numbers are PII):
  MOBILE_MESSAGE_TO_Y8, MOBILE_MESSAGE_TO_Y9           the boys
  MOBILE_MESSAGE_TO_PARENTS = comma-separated parent numbers
A kid seat with no number may carry roster.json "kid_comms_via": "parents" —
an explicit per-seat redirect to that kid's OWN parent seat (see _recipients).

Request shape VERIFIED against Mobile Message's live API docs (Aug 2026):
POST /v1/messages, Basic auth (API username:password base64), messages[] of
{to, message, sender, custom_ref}; enable_unicode ON because every XPDaily
text carries emoji (unicode SMS = 70-char segments — our lines are short).

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


def _env(name):
    """Env var, falling back to the Actions-wide SECRETS_CONTEXT JSON blob
    (workflows pass `SECRETS_CONTEXT: ${{ toJson(secrets) }}` so adding a
    player never requires editing workflow env blocks)."""
    v = os.environ.get(name)
    if v:
        return v
    try:
        return json.loads(os.environ.get("SECRETS_CONTEXT", "{}")).get(name)
    except Exception:
        return None


def _split(raw):
    return [x.strip() for x in (raw or "").split(",") if x.strip()]


def _recipients(target):
    """Resolve a target to phone numbers (from Actions secrets, never files).

    Targets:
      "<code>"          the kid's own seat        -> MOBILE_MESSAGE_TO_<CODE>
      "parents:<code>"  that kid's parent seat    -> MOBILE_MESSAGE_PARENTS_<CODE>
                        NO fallback — a per-kid parent seat resolves to its own
                        secret or to nobody. The old silent fallback to the
                        shared legacy list meant a mistyped secret for a NEW
                        family would text that child's report to the WRONG
                        household, while looking "resolved" to every caller's
                        hard-abort check. Fail empty; senders abort loudly.
      "parents"         legacy shared group       -> MOBILE_MESSAGE_TO_PARENTS
    """
    if target.startswith("parents:"):
        code = target.split(":", 1)[1].strip()
        return _split(_env(f"MOBILE_MESSAGE_PARENTS_{code.upper()}"))
    if target == "parents":
        return _split(_env("MOBILE_MESSAGE_TO_PARENTS"))
    nums = _split(_env(f"MOBILE_MESSAGE_TO_{target.upper()}"))
    if nums:
        return nums
    # A kid seat with no number of its own can carry an EXPLICIT roster redirect
    # ("kid_comms_via": "parents") — the y9 US-phone gap, ratified 31 Aug 2026:
    # that kid's own seat has no SMS channel at all, so his nudges ride the
    # parent seat until he has a local number. Three guards keep this the
    # opposite of the old silent fallback: a real TO_<CODE> secret always wins;
    # no roster flag, no redirect (fail empty, senders abort loudly); and the
    # redirect goes to THAT kid's own parent seat, never a shared list.
    if _kid_comms_via(target) == "parents":
        return _split(_env(f"MOBILE_MESSAGE_PARENTS_{target.upper()}"))
    return []


def _kid_comms_via(code):
    """roster.json's per-seat redirect for a kid seat with no phone (see
    _recipients). Fail-closed: an unreadable roster means no redirect."""
    try:
        import roster
        return ((roster.entry(code) or {}).get("kid_comms_via") or "").strip()
    except Exception:
        return ""


# Statuses Mobile Message can report per-message inside an HTTP-2xx body. A 2xx
# means the request was ACCEPTED, not that every message was — a bad number or
# an out-of-credit account comes back 200 with a per-message rejection. We fail
# ONLY on a status we positively recognise as a rejection (denylist), so an
# unfamiliar or success status can never be mistaken for a failure and block a
# real send. True end-of-line delivery confirmation needs the delivery webhook;
# this closes the send-response hole, which is what silently advanced the cursor.
_REJECT_STATUSES = {
    "failed", "invalid", "rejected", "error", "errored", "undelivered",
    "bounced", "expired", "blocked", "unsubscribed", "opted_out", "opted-out",
    "insufficient_credit", "insufficient credit", "no_credit",
}


def _delivery_ok(raw, n_expected=None):
    """(ok, detail) from a 2xx body. Fail-OPEN: an unparseable body or a body
    with no recognisable per-message results keeps the prior 'accepted' meaning;
    we only return False when the provider explicitly reports a rejection."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return True, raw                      # 2xx we can't parse -> accepted
    results = data if isinstance(data, list) else None
    if isinstance(data, dict):
        for k in ("results", "messages", "data"):
            if isinstance(data.get(k), list):
                results = data[k]
                break
    if not results:
        return True, raw                      # no per-message detail -> accepted
    rejected = []
    for item in results:
        if isinstance(item, dict):
            status = str(item.get("status", "")).strip().lower()
            if status in _REJECT_STATUSES:
                rejected.append(status)
    if rejected:
        # summary only — never echo numbers/message text into a public log
        return False, (f"provider rejected {len(rejected)}/{len(results)} "
                       f"message(s): {sorted(set(rejected))}")
    return True, raw


def send_sms(target, text, ref=None, dry_run=False):
    """Send `text` to a target group (y8|y9|parents). Returns (ok, detail).

    `ok` reflects real acceptance: a transport failure (non-2xx / exception) OR
    a per-message rejection inside a 2xx body both return ok=False, so a caller
    that gates a cursor on `ok` never marks a silently-rejected message as sent.
    """
    to = _recipients(target)
    if not to:
        return False, f"no recipient configured for {target!r} (set MOBILE_MESSAGE_TO_*)"
    sender = os.environ.get("MOBILE_MESSAGE_SENDER", "")
    messages = [{"to": n, "message": text, "sender": sender,
                 "custom_ref": ref or "dailyxp"} for n in to]

    if dry_run:
        return True, "DRY-RUN, not sent:\n" + json.dumps({"sender": sender, "messages": messages}, indent=2)

    key = _env("MOBILE_MESSAGE_API_KEY")
    secret = _env("MOBILE_MESSAGE_API_SECRET")
    if not (key and secret):
        return False, "MOBILE_MESSAGE_API_KEY/SECRET not set"
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    body = json.dumps({"enable_unicode": True, "messages": messages}).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "Authorization": f"Basic {auth}", "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode()[:200]}"
    except Exception as e:
        return False, str(e)
    return _delivery_ok(raw, len(to))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to-student", dest="target", required=True,
                    help='a kid code (e.g. y8), "parents:<code>", or legacy "parents"')
    ap.add_argument("--text", required=True)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true",
                    help="print only OK/FAIL — for public Actions logs (detail can echo numbers/text)")
    a = ap.parse_args()
    ok, detail = send_sms(a.target, a.text, ref=a.ref, dry_run=a.dry_run)
    if a.quiet:
        print("OK sent" if ok else "FAIL (detail withheld from public log — check the Mobile Message dashboard)")
    else:
        print(("OK " if ok else "FAIL ") + detail)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
