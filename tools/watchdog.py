#!/usr/bin/env python3
"""
watchdog.py — tells Rich when something that SHOULD have happened, didn't.

The problem this solves: GitHub's scheduler is best-effort. It queues under load
and silently drops runs — proven on 10 and 11 Aug 2026, when the 4pm kid nudge
missed two days running. Retry ladders reduce that risk; they do not remove it,
and nothing on GitHub's side will ever tell you a cron simply never fired.

So reliability here is TWO things, not one:
  1. RETRY  — each comms job polls on a ladder, made safe by its cursor.
  2. DETECT — this watchdog checks the CURSORS (the record of what actually
     happened) against what the day's schedule promised, and texts Rich if
     anything is still outstanding past its deadline.

CURSORS ARE THE TRUTH, NOT RUN CONCLUSIONS. A green workflow that published
nothing is the founding lesson of this system (RUNBOOK gotcha #1), so the
watchdog never looks at run status — only at the state the jobs leave behind.

DESIGN RULES:
  * ALERTS GO TO RICH ONLY — never a parent seat, never a kid. This is ops, and
    an ops message must never land on a family member's phone.
  * SILENT WHEN HEALTHY. It texts only on a real miss, so a text always means
    something. A watchdog that chats is a watchdog you learn to ignore.
  * ONE ALERT PER ITEM PER DAY, cursored like everything else, so a repeated
    check doesn't turn a missed nudge into six texts.
  * IT NEVER FIXES ANYTHING. Detection only — the fix is a human clicking Run,
    or the next rung of the ladder. A watchdog that also acts is two systems
    failing together.

Checks (each: does the cursor show today's work done, past its deadline?)
  kid nudge          weekdays, deadline 17:30 AEST
  daily publish      weekdays, deadline 15:00 AEST (live set date == today)
  evening soundbyte  weekdays, deadline 21:45 AEST — only if a run exists to report
  friday report      Fridays,  deadline 22:00 AEST

Usage:
  python3 tools/watchdog.py --private-dir private [--dry-run]
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notify      # noqa: E402
import roster      # noqa: E402

ALERT_SEAT = "t1"                       # Rich's own handset — ops only
CURSOR_REL = os.path.join("work", "watchdog_cursor.json")
RAW = "https://raw.githubusercontent.com/Rich898/DailyXP-content/main/{s}.json"


def syd_now():
    return dt.datetime.utcnow() + dt.timedelta(hours=10)      # AEST (UTC+10)


def load(private_dir, rel, default=None):
    try:
        return json.load(open(os.path.join(private_dir, rel)))
    except (OSError, ValueError):
        return default if default is not None else {}


def live_set_date(student):
    try:
        with urllib.request.urlopen(RAW.format(s=student), timeout=20) as r:
            return json.load(r).get("date")
    except Exception:
        return None


def check(private_dir, now):
    """Returns a list of human-readable misses. Empty list = healthy."""
    today = now.date().isoformat()
    weekday = now.weekday() < 5
    hhmm = now.hour * 60 + now.minute
    misses = []
    codes = roster.active()

    # 1) daily publish — the live set must be today's
    if weekday and hhmm >= 15 * 60:
        stale = [s for s in codes if live_set_date(s) != today]
        if stale:
            misses.append(("publish",
                           f"Today's set is not live for {', '.join(stale)}. "
                           f"Run daily-quiz."))

    # 2) kid nudge — cursor must show today
    if weekday and hhmm >= 17 * 60 + 30:
        cur = load(private_dir, os.path.join("work", "kid_nudge_cursor.json"))
        missing = [s for s in codes if cur.get(s) != today]
        if missing:
            misses.append(("nudge",
                           f"Kid nudge hasn't gone for {', '.join(missing)}. "
                           f"Run kid-nudge."))

    # 3) evening soundbyte — only expected if there IS a run to report on
    if weekday and hhmm >= 21 * 60 + 45:
        runs = load(private_dir, os.path.join("work", "runs.json"), {}).get("runs", [])
        played = {r.get("student") for r in runs if r.get("run_date") == today}
        cur = load(private_dir, os.path.join("work", "soundbyte_cursor.json"))
        owed = [s for s in played if cur.get(s) != today]
        if owed:
            misses.append(("soundbyte",
                           f"Played but no parent soundbyte for {', '.join(sorted(owed))}. "
                           f"Run evening-soundbyte."))

    # 4) friday report — weekly cursor must show this week
    if now.weekday() == 4 and hhmm >= 22 * 60:
        monday = (now.date() - dt.timedelta(days=now.weekday())).isoformat()
        cur = load(private_dir, os.path.join("work", "friday_report_cursor.json"))
        missing = [s for s in codes if cur.get(s) != monday]
        if missing:
            misses.append(("friday",
                           f"Weekly report hasn't gone for {', '.join(missing)}. "
                           f"Run friday-report."))
    return misses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--now", help="override AEST time, ISO, for testing")
    a = ap.parse_args()

    now = dt.datetime.fromisoformat(a.now) if a.now else syd_now()
    misses = check(a.private_dir, now)
    if not misses:
        print(f"watchdog {now:%Y-%m-%d %H:%M} AEST — all clear.")
        return 0

    cur = load(a.private_dir, CURSOR_REL)
    today = now.date().isoformat()
    fresh = [(k, m) for k, m in misses if cur.get(k) != today]
    for k, m in misses:
        print(f"  MISS [{k}] {m}" + ("" if cur.get(k) != today else "  (already alerted)"))
    if not fresh:
        print("all misses already alerted today — staying quiet.")
        return 0

    body = "XPDaily watchdog: " + " · ".join(m for _, m in fresh)
    if a.dry_run:
        print(f"DRY-RUN alert ({len(body)} chars): {body}")
        return 0
    ok, detail = notify.send_sms(ALERT_SEAT, body, ref=f"xpd-watchdog-{today}")
    print(f"alert {'sent' if ok else 'FAILED: ' + str(detail)}")
    if ok:
        for k, _ in fresh:
            cur[k] = today
        p = os.path.join(a.private_dir, CURSOR_REL)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(cur, open(p, "w"), indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
