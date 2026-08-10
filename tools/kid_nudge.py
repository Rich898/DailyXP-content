#!/usr/bin/env python3
"""
kid_nudge.py — the daily kid text: "XP Daily is up" (REPORTING.md, kid-facing).

Runs at 4:00pm Sydney (kid-nudge.yml), DECOUPLED from the 2pm publish on
purpose. The pipeline publishes at 2pm; kids get texted at 4pm, when school's
out and phones are back in hands — and only after this job VERIFIES the live
set really is today's. That two-hour gap is the safety margin: if the review
gate HOLDs a set (yesterday's stays live), no kid gets texted a promise the
pipeline didn't keep.

Rules:
  * VERIFY BEFORE TEXT. Fetch the same raw URL the shell fetches (publish.py's
    VERIFY pattern). Nudge only if live date == today and it's not a
    placeholder. Stale or frozen → silent suppression, loud in the log.
  * FLAVOURED BY THE WEEKLY SKELETON. Wed = blitz, Fri = boss (the locked
    skeleton from SEASONS.md — same mapping run_daily plans with).
  * STATELESS. Reads the live URL, sends, writes nothing — no private repo,
    no cursor. The cron fires once a day; a re-dispatch is a human choice.
  * PUBLIC-LOG SAFE. Prints y8/y9 + status only. Nudge text carries no
    names or scores by design.

Usage:
  python3 tools/kid_nudge.py                # live (needs MOBILE_MESSAGE_*)
  python3 tools/kid_nudge.py --dry-run      # verify + decide only, no send
  python3 tools/kid_nudge.py --date 2026-08-10 --student y8
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:                                    # pragma: no cover
    ZoneInfo = None

RAW = "https://raw.githubusercontent.com/Rich898/DailyXP-content/main/{student}.json"

# The locked weekly skeleton (SEASONS.md): Wed = blitz, Fri = boss. Mirrors
# WEEKDAY_DIRECTIVE in scripts/run_daily.py — if the skeleton ever changes,
# change BOTH (they encode the same doctrine).
WEEKDAY_DIRECTIVE = {0: "standard", 1: "standard", 2: "reversed blitz", 3: "standard", 4: "boss"}
NUDGE = {
    "standard": "XP Daily is up \U0001f44a",
    "reversed blitz": "\u26a1 REVERSED BLITZ \u2014 you get the answers, find the questions. Double XP is live. XP Daily is up \U0001f44a",
    "boss": "\U0001f409 BOSS day \u2014 XP Daily is up. Go get it \U0001f44a",
}


def sydney_today():
    if ZoneInfo is None:
        from datetime import date
        return date.today()
    return datetime.now(ZoneInfo("Australia/Sydney")).date()


def decide(live_set, today):
    """Pure decision: (send?, reason, text). Testable without network."""
    if not isinstance(live_set, dict):
        return False, "live set unreadable", None
    if live_set.get("status") == "placeholder":
        return False, "live set is a placeholder (frozen/held) \u2014 nudge suppressed", None
    if live_set.get("date") != today.isoformat():
        return False, (f"live set is {live_set.get('date')!r}, not today "
                       f"\u2014 nudge suppressed (never text a promise not kept)"), None
    directive = WEEKDAY_DIRECTIVE.get(today.weekday())
    if directive is None:
        return False, "weekend \u2014 no nudge", None
    return True, f"live set verified for today ({directive})", NUDGE[directive]


def fetch_live(student):
    url = RAW.format(student=student) + f"?cb={int(time.time())}"
    return json.loads(urllib.request.urlopen(url, timeout=15).read().decode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="Override Sydney date (YYYY-MM-DD)")
    ap.add_argument("--student", default="all", help='a roster code, or "all" (default)')
    ap.add_argument("--dry-run", action="store_true", help="verify + decide only, no send")
    a = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import notify
    import roster

    from datetime import date as _d
    today = _d.fromisoformat(a.date) if a.date else sydney_today()
    targets = roster.active() if a.student == "all" else (a.student,)

    any_fail = False
    for s in targets:
        try:
            live = fetch_live(s)
        except Exception as e:
            print(f"[{s}] \u26a0 could not read live URL ({type(e).__name__}) \u2014 no nudge.")
            any_fail = True
            continue
        send, reason, text = decide(live, today)
        print(f"[{s}] {reason}")
        if not send:
            continue
        if a.dry_run:
            print(f"[{s}] DRY-RUN \u2014 send suppressed.")
            continue
        ok, detail = notify.send_sms(s, text, ref=f"xpd-nudge-{today.isoformat()}",
                                     dry_run=False)
        if not ok and "no recipient configured" in (detail or ""):
            # A kid without a number (e.g. the US-phone gap) is a known state,
            # not an error — the icon is his channel until the fallback lands.
            print(f"[{s}] no number configured \u2014 skipped (icon is his channel).")
            continue
        print(f"[{s}] nudge {'sent \u2713' if ok else 'FAILED \u2717'}")
        if not ok:
            any_fail = True

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
