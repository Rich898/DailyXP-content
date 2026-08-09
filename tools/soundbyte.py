#!/usr/bin/env python3
"""
soundbyte.py — the daily parent soundbyte (REPORTING.md, touchpoint 1: REASSURE).

Runs in the EVENING (its own workflow, evening-soundbyte.yml), separate from the
2pm pipeline: polls the results Sheet, and when today's run has landed for a boy
and no soundbyte has been sent yet, texts the parents ONE line — done + XP +
streak. Nothing else. That is the whole job.

Design laws (all enforced here, by construction):
  * NO AI. The line is a deterministic template filled from three facts
    (name, points, streak). Tone cannot drift; the evening path has zero
    API dependency. (The architecture law — "AI only does language" — and
    this line has so little language that code owns even that.)
  * NO AMMUNITION. Only additive facts go in: points and streak. Never
    ratios (a "6/7" whispers *there was a miss*), never misses, never
    subjects. A 1-day streak is NOT mentioned (saying "1-day streak"
    whispers *the streak broke* — same law, quieter edge).
  * SILENCE IS THE ONLY "NOT DONE" SIGNAL. If no run lands, no text is
    sent — ever, at any hour. Absence of the text is soft by design.
  * IDEMPOTENT. A cursor (private repo, work/soundbyte_cursor.json)
    records (student, date) pairs already sent. Polls finding nothing new
    are silent no-ops. The send is attempted BEFORE the cursor advances,
    so a failed send retries on the next poll.
  * PUBLIC-LOG HYGIENE. This runs in the public repo's Actions, whose logs
    are public. stdout NEVER carries names, scores, or message text — only
    y8/y9 and safe status lines. Full error detail, if any, is written to
    the PRIVATE repo (work/soundbyte_last_error.txt), never printed.
  * THE LEDGER IS NOT TOUCHED. This job reads runs.json (via the proven
    ingestion) and writes only its own cursor. The 2pm pipeline remains
    the sole owner of state.json transitions.

Facts:
  points = best score across today's completed runs (replays count the best).
  streak = consecutive SCHOOL-days ending today with a completed run;
           weekends are skipped, not broken (Fri -> Mon continues) — the
           same school-day semantics as the achievements engine.

Usage:
  python3 tools/soundbyte.py --private-dir ../DailyXP-private            # live
  python3 tools/soundbyte.py --private-dir ../DailyXP-private --dry-run  # no send, no cursor write
  python3 tools/soundbyte.py --private-dir ../DailyXP-private --date 2026-08-10
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:                                    # pragma: no cover
    ZoneInfo = None

STUDENTS = ("y8", "y9")
CURSOR_FILE = os.path.join("work", "soundbyte_cursor.json")
ERROR_FILE = os.path.join("work", "soundbyte_last_error.txt")

# Three rotating phrasings so the nightly text doesn't feel stamped out by a
# machine (even though it is). Picked deterministically from the date, so a
# given evening always renders the same line. {streak} is "" when streak < 2.
TEMPLATES = (
    "{name} \u2705 tonight's XP Daily run is done \u2014 {pts} XP{streak}.",
    "XP Daily: {name} finished tonight's run \u2014 {pts} XP{streak} \u2705",
    "{name} done \u2705 {pts} XP tonight{streak}.",
)


# --------------------------------------------------------------------------- #
# Pure logic (everything below main() is testable without network or files)

def sydney_today():
    if ZoneInfo is None:
        return date.today()
    from datetime import datetime
    return datetime.now(ZoneInfo("Australia/Sydney")).date()


def current_school_streak(present_dates, today):
    """Consecutive school-days ending at `today` with a run present.

    Weekends are transparent (Fri -> Mon continues); a missed school-day
    breaks the count. Mirrors the achievements engine's school-day
    semantics — one definition of a streak everywhere.
    """
    if today.isoformat() not in present_dates:
        return 0
    n, d = 0, today
    while True:
        if d.weekday() < 5:                    # Mon–Fri
            if d.isoformat() in present_dates:
                n += 1
            else:
                break
        d -= timedelta(days=1)
        if n > 400:                            # safety valve
            break
    return n


def facts_for(runs, student, today_iso):
    """(name, best_points, streak) for today's completed runs, else None."""
    todays = [r for r in runs
              if r.get("student") == student and r.get("run_date") == today_iso]
    if not todays:
        return None
    present = {r.get("run_date") for r in runs if r.get("student") == student}
    name = todays[0].get("name") or student.upper()
    pts = max(int(r.get("score") or 0) for r in todays)
    streak = current_school_streak(present, date.fromisoformat(today_iso))
    return {"student": student, "name": name, "pts": pts, "streak": streak}


def render_line(f, today_iso):
    """One deterministic line from the facts. streak < 2 is silently omitted."""
    t = TEMPLATES[sum(today_iso.encode()) % len(TEMPLATES)]
    streak_bit = f" \u00b7 {f['streak']}-day streak" if f["streak"] >= 2 else ""
    return t.format(name=f["name"], pts=f"{f['pts']:,}", streak=streak_bit)


def plan(runs, cursor, today_iso):
    """Decide what (if anything) to send tonight.

    Returns (message_text_or_None, safe_log_lines, new_cursor).
    safe_log_lines are guaranteed name/score-free (they're what Actions prints).
    """
    sent = cursor.get("sent", {})
    log, lines, new_cursor = [], [], {"sent": {k: list(v) for k, v in sent.items()}}
    for s in STUDENTS:
        if today_iso in sent.get(s, []):
            log.append(f"[{s}] already sent for {today_iso} \u2014 no-op.")
            continue
        f = facts_for(runs, s, today_iso)
        if not f:
            log.append(f"[{s}] no run for {today_iso} yet \u2014 silent.")
            continue
        log.append(f"[{s}] run found for {today_iso} \u2014 soundbyte queued.")
        lines.append(render_line(f, today_iso))
        new_cursor["sent"].setdefault(s, []).append(today_iso)
    text = "\n".join(lines) if lines else None
    return text, log, new_cursor


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--date", default=None, help="Override Sydney date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true",
                    help="plan only \u2014 no send, no cursor write")
    a = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import notify

    today_iso = a.date or sydney_today().isoformat()
    priv = a.private_dir

    # Refresh runs.json from the Sheet (same gating as run_daily: skip offline).
    if os.environ.get("RESULTS_URL") and os.environ.get("RESULTS_KEY"):
        try:
            import ingest_results
            summary, errs = ingest_results.ingest(
                priv, os.environ["RESULTS_URL"], os.environ["RESULTS_KEY"])
            print(f"ingest: {summary}")
            for e in errs:
                print(f"  \u26a0 {e}")
        except BaseException as e:
            print(f"\u26a0 ingest failed ({type(e).__name__}) \u2014 using committed runs.json.")
    else:
        print("ingest skipped (no RESULTS_URL/KEY) \u2014 using committed runs.json.")

    runs = json.load(open(os.path.join(priv, "work", "runs.json"))).get("runs", [])
    cpath = os.path.join(priv, CURSOR_FILE)
    cursor = json.load(open(cpath)) if os.path.exists(cpath) else {"sent": {}}

    text, log, new_cursor = plan(runs, cursor, today_iso)
    for line in log:
        print(line)

    if not text:
        print("nothing to send.")
        return

    if a.dry_run:
        print("DRY-RUN \u2014 send + cursor write suppressed.")
        return

    # Send first, advance the cursor only on success — a failed send retries
    # on the next evening poll. NOTE: `detail` may echo message content, so it
    # is never printed; failures land in the private repo instead.
    ok, detail = notify.send_sms("parents", text, ref=f"xpd-sb-{today_iso}",
                                 dry_run=False)
    if ok:
        with open(cpath, "w") as fh:
            json.dump(new_cursor, fh, indent=1)
            fh.write("\n")
        print("soundbyte sent \u2713 cursor advanced.")
    else:
        with open(os.path.join(priv, ERROR_FILE), "w") as fh:
            fh.write(f"{today_iso}: {detail}\n")
        print("\u26a0 send FAILED \u2014 cursor NOT advanced (will retry next poll); "
              "detail in private work/soundbyte_last_error.txt")


if __name__ == "__main__":
    main()
