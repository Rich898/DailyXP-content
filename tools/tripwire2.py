#!/usr/bin/env python3
"""
tripwire2.py — the GitHub-side dispatch tripwire (HARDENING-BRIEF item 3).

The complement to Tripwire 1. Tripwire 1 lives in Supabase and catches a
dispatch that FAILED (a non-2xx reply) within a minute — but it is blind if
Supabase itself dies. This lives on GitHub's OWN schedule cron, with NO
dispatch token anywhere in its path, and asks the plainer question: did
today's expected runs actually HAPPEN AT ALL? A dead dispatch token, a paused
Supabase, a dropped cron — every one of them shows up here as a missing run.

The two guard each other, and that complementarity is the whole design:
  * Tripwire 1 (Supabase): sees dispatch failures in ~a minute; blind if
    Supabase is down.
  * Tripwire 2 (this one): sees missing runs each evening; blind only if
    GitHub itself is fully down — which Tripwire 1 sees as timeouts.

WHAT IT CHECKS (weekdays only — both were the 26 Aug casualties):
  daily-quiz.yml   the quiz build   (expected 14:00 AEST + ladder)
  kid-nudge.yml    the kid nudge    (expected 16:00 AEST + ladder)
"Happened" = at least one run of that workflow was CREATED today (AEST). We
ask only whether the run FIRED, not its conclusion — a green run that
published nothing is the watchdog's department (cursors), not this one's.

DEPENDENCIES, deliberately minimal — this must survive when other things don't:
  * GITHUB_TOKEN with actions:read   (the workflow grants it; ephemeral, per-run)
  * MOBILE_MESSAGE_* secrets         (the same creds the other workflows hold)
No dispatch PAT, no Supabase, no private-repo checkout.

SHADOW-FIRST: it sends nothing until armed. The arm switch is the
TRIPWIRE2_LIVE env in the workflow ("true" = live) — version-controlled, so
flipping it is a commit, not a dashboard toggle. Until armed it logs what it
WOULD text and sends nothing — the same discipline as Tripwire 1.

ALERTS GO TO RICH ONLY (seat t1) — ops never lands on a kid or parent phone.

Usage (from the workflow):  python3 tools/tripwire2.py [--dry-run]
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notify  # noqa: E402

ALERT_SEAT = "t1"                       # Rich's own handset — ops only
REPO = "Rich898/DailyXP-content"
RUNS_API = "https://api.github.com/repos/{repo}/actions/workflows/{wf}/runs?per_page=20"

# Weekday jobs whose absence today is a real incident.
EXPECTED = [
    ("daily-quiz.yml", "daily quiz build"),
    ("kid-nudge.yml",  "kid nudge"),
]


def syd_now():
    # AEST (UTC+10), matching tools/watchdog.py. NOTE: fixed offset, so it is an
    # hour out during AEDT (Oct–Apr) — a known repo-wide simplification; the
    # Supabase side uses the real Australia/Sydney zone.
    return dt.datetime.utcnow() + dt.timedelta(hours=10)


def ran_today(wf, today_aest, token):
    """True if a run of `wf` was created on today's AEST date."""
    req = urllib.request.Request(
        RUNS_API.format(repo=REPO, wf=wf),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "xpdaily-tripwire2",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        runs = json.load(r).get("workflow_runs", [])
    for run in runs:
        created = run.get("created_at")            # e.g. "2026-08-27T04:00:05Z" (UTC)
        if not created:
            continue
        c_utc = dt.datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ")
        if (c_utc + dt.timedelta(hours=10)).date() == today_aest:
            return True
    return False


def check(token, now):
    """Return a list of human-readable misses. Empty = healthy."""
    if now.weekday() >= 5:                          # weekend — nothing expected
        return []
    today = now.date()
    misses = []
    for wf, label in EXPECTED:
        try:
            if not ran_today(wf, today, token):
                misses.append(f"{label} ({wf}) has no run today")
        except Exception as e:
            # An API error is itself worth flagging, never swallowing — a
            # tripwire that fails silent is the bug we are fixing.
            misses.append(f"could not verify {label} ({wf}): {e}")
    return misses


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="check and report, never send")
    a = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("tripwire2: no GITHUB_TOKEN — cannot read the Actions API", file=sys.stderr)
        return 1

    now = syd_now()
    misses = check(token, now)
    if not misses:
        print(f"tripwire2 {now:%Y-%m-%d %H:%M} AEST — all expected runs present.")
        return 0

    body = "XP Daily tripwire-2: " + " · ".join(misses) + ". Scheduler/dispatch may be down — check."
    armed = os.environ.get("TRIPWIRE2_LIVE", "").strip().lower() == "true"

    for m in misses:
        print(f"  MISS {m}")
    if a.dry_run or not armed:
        why = "dry-run" if a.dry_run else "SHADOW — TRIPWIRE2_LIVE not set"
        print(f"tripwire2 [{why}] would send ({len(body)} chars): {body}")
        return 0

    ok, detail = notify.send_sms(ALERT_SEAT, body, ref=f"xpd-tripwire2-{now.date().isoformat()}")
    print(f"tripwire2 alert {'sent' if ok else 'FAILED: ' + str(detail)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
