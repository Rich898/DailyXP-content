#!/usr/bin/env python3
"""
kid_nudge.py — the daily kid text: "XPDaily is up" (REPORTING.md, kid-facing).

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
  * ONE NUDGE PER KID PER DAY, enforced by a cursor in the private repo.
    This REPLACED the original stateless design (11 Aug 2026): GitHub's cron is
    best-effort and dropped the 4pm nudge on two consecutive days, so the
    schedule is now a RETRY LADDER (16:00 / 16:20 / 16:45 / 17:15). Without a
    cursor that ladder would text each boy four times an afternoon. The cursor
    makes every repeat after a successful send a silent no-op — which is what
    makes the ladder safe, and the nudge finally dependable.
    The cursor advances ONLY on a confirmed send. A failed send leaves it
    untouched so the next rung retries.
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
    "standard": "XPDaily is up \U0001f44a",
    "reversed blitz": "\u26a1 REVERSED BLITZ \u2014 you get the answers, find the questions. Double XP is live. XPDaily is up \U0001f44a",
    "boss": "\u2694 BATTLEGROUND \u2014 win the week. XPDaily is up \U0001f44a",
}


def sydney_today():
    if ZoneInfo is None:
        from datetime import date
        return date.today()
    return datetime.now(ZoneInfo("Australia/Sydney")).date()


def decide(live_set, today, play_url=None):
    """Pure decision: (send?, reason, text). Testable without network.
    When play_url is set, the kid's permanent quiz link is appended so the Daily is one tap away."""
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
    text = NUDGE[directive]
    if play_url:
        text = f"{text}\n{play_url}"
    return True, f"live set verified for today ({directive})", text


def fetch_live(student):
    url = RAW.format(student=student) + f"?cb={int(time.time())}"
    return json.loads(urllib.request.urlopen(url, timeout=15).read().decode())


CURSOR_REL = os.path.join("work", "kid_nudge_cursor.json")


def load_cursor(private_dir):
    """{code: ISO date last successfully nudged}. Missing dir/file = empty."""
    if not private_dir:
        return {}
    try:
        return json.load(open(os.path.join(private_dir, CURSOR_REL)))
    except (OSError, ValueError):
        return {}


def save_cursor(private_dir, cursor):
    if not private_dir:
        return
    p = os.path.join(private_dir, CURSOR_REL)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(cursor, open(tmp, "w"), indent=2)
    os.replace(tmp, p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="Override Sydney date (YYYY-MM-DD)")
    ap.add_argument("--student", default="all", help='a roster code, or "all" (default)')
    ap.add_argument("--dry-run", action="store_true", help="verify + decide only, no send")
    ap.add_argument("--private-dir", default=os.environ.get("DAILYXP_PRIVATE_DIR"),
                    help="private checkout — holds the once-a-day cursor")
    ap.add_argument("--force", action="store_true",
                    help="ignore the cursor (deliberate re-send)")
    a = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import notify
    import roster

    from datetime import date as _d
    today = _d.fromisoformat(a.date) if a.date else sydney_today()
    targets = roster.active() if a.student == "all" else (a.student,)

    cursor = load_cursor(a.private_dir)
    any_fail = False
    for s in targets:
        try:
            live = fetch_live(s)
        except Exception as e:
            print(f"[{s}] \u26a0 could not read live URL ({type(e).__name__}) \u2014 no nudge.")
            any_fail = True
            continue
        send, reason, text = decide(live, today, roster.play_url(s))
        print(f"[{s}] {reason}")
        if not send:
            continue
        if not a.force and cursor.get(s) == today.isoformat():
            print(f"[{s}] already nudged today — no-op (retry ladder).")
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
        if ok:
            cursor[s] = today.isoformat()
            save_cursor(a.private_dir, cursor)
        else:
            any_fail = True

    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
