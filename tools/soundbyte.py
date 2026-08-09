#!/usr/bin/env python3
"""
soundbyte.py — the daily parent soundbyte (REPORTING.md, touchpoint 1: REASSURE).

Runs in the EVENING (its own workflow, evening-soundbyte.yml), separate from the
2pm pipeline: polls the results Sheet, and when today's run has landed for a boy
and no soundbyte has been sent yet, texts the parents ONE line — did it +
tonight's XP + a verdict closer. Nothing else. That is the whole job.

Design laws (all enforced here, by construction):
  * NO AI. The line is a deterministic template filled from four facts
    (name, points, band, streak). Tone cannot drift; the evening path has zero
    API dependency. (The architecture law — "AI only does language" — and
    this line has so little language that code owns even that.)
  * NO AMMUNITION, HONESTLY (final form, Rich 9 Aug 2026). The daily
    line is exactly three beats: (a) did it, (b) +XP, (c) a verdict
    closer. Lightweight, never alarming. Legal daily facts: the done
    mark, tonight's +XP, continuity (streak >= 2), and an HONEST tone
    band computed from best_score/max_score — the ratio itself printed
    NOWHERE. Never percentages, never running totals (totals belong to
    the Friday report and the portal), never misses, subjects, or
    day-vs-day. The verdict gives the score its meaning — a bare
    number means nothing to a parent. The verdict ladder is
    effort/energy language, no grade-words. ATTRIBUTION LAW: success
    belongs to the kid, difficulty belongs to the set ("the set bit
    back") — true, because the planner picks the difficulty — so even
    the floor band leaves only a praise-family move open. Band
    definitions live once in the onboarding LEGEND. A 1-day streak is
    NOT mentioned (saying "1-day streak" whispers *the streak broke*).
    Tiny sets (max < MIN_BANDED_MAX) don't band: a 4-question warm-up
    can't carry a fair tone word.
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
  band   = tone word from that best run's points/max_score (>=85% huge,
           >=70% strong, >=50% solid, else hard); None on tiny sets or
           missing max. Computed here, printed nowhere.
  total  = season bank: best-per-day points summed since SEASON_START
           (Term 3 W1 = w/c 27 Jul 2026), plus an optional approx seed
           (work/season_seed.json). COMPUTED FOR THE FRIDAY REPORT —
           the daily line never prints it.
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

CURSOR_FILE = os.path.join("work", "soundbyte_cursor.json")
ERROR_FILE = os.path.join("work", "soundbyte_last_error.txt")
SEED_FILE = os.path.join("work", "season_seed.json")

# Season bank anchor: Term 3 W1 = w/c Mon 27 Jul 2026 (schedule.json).
SEASON_START = "2026-07-27"

# Honest tone bands, computed from best_score/max_score and NEVER printed as
# a ratio. The floor band exists ("hard") because the kid saw his own end
# screen — a warm lie would teach the family the texts are fluff. The
# attribution law keeps the floor reassuring: difficulty belongs to the SET,
# showing up belongs to the KID. Tiny sets can't carry a fair tone word.
MIN_BANDED_MAX = 1500
BAND_CUTS = ((0.85, "huge"), (0.70, "strong"), (0.50, "solid"))  # else "hard"

# Two rotating phrasings PER BAND so the nightly text doesn't feel stamped
# out by a machine (even though it is). Picked deterministically from the
# date, so a given evening always renders the same line. {streak} is ""
# when streak < 2. Structure (Rich, final): (a) did it (b) +XP (c) verdict
# closer. Band keys are internal; the LADDER WORDS below are the product.
TEMPLATES = {
    "huge": (
        "{name} \u2705 did tonight's run \u2014 +{pts} XP{streak}. Flew tonight.",
        "XP Daily: {name} \u2705 tonight's run done \u2014 +{pts} XP{streak}. Absolutely flew.",
    ),
    "strong": (
        "{name} \u2705 did tonight's run \u2014 +{pts} XP{streak}. Good night's work.",
        "XP Daily: {name} \u2705 tonight's run done \u2014 +{pts} XP{streak}. A good night's work.",
    ),
    "solid": (
        "{name} \u2705 did tonight's run \u2014 +{pts} XP{streak}. Put in a shift.",
        "XP Daily: {name} \u2705 tonight's run done \u2014 +{pts} XP{streak}. Proper shift tonight.",
    ),
    "hard": (
        "{name} \u2705 did tonight's run \u2014 +{pts} XP{streak}. The set bit back \u2014 hung in there.",
        "XP Daily: {name} \u2705 tonight's run done \u2014 +{pts} XP{streak}. Tough set \u2014 stuck at it.",
    ),
    None: (
        "{name} \u2705 did tonight's run \u2014 +{pts} XP{streak}.",
        "XP Daily: {name} \u2705 tonight's run done \u2014 +{pts} XP{streak}.",
    ),
}


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


def band_for(pts, max_score):
    """Tone band from the best run's OWN max. None = no fair band exists.
    The ratio lives and dies inside this function."""
    try:
        mx = int(max_score or 0)
    except (TypeError, ValueError):
        return None
    if mx < MIN_BANDED_MAX or pts is None:
        return None
    ratio = pts / mx
    for cut, word in BAND_CUTS:
        if ratio >= cut:
            return word
    return "hard"


def season_total(student_runs, today_iso, seed=0):
    """Season bank: best-per-day points, SEASON_START..today incl., + seed."""
    best = {}
    for r in student_runs:
        d = r.get("run_date") or ""
        if SEASON_START <= d <= today_iso:
            best[d] = max(best.get(d, 0), int(r.get("score") or 0))
    return sum(best.values()) + int(seed or 0)


def facts_for(runs, student, today_iso, seed=0):
    """(name, pts, band, total, streak) for today's runs, else None."""
    todays = [r for r in runs
              if r.get("student") == student and r.get("run_date") == today_iso]
    if not todays:
        return None
    mine = [r for r in runs if r.get("student") == student]
    present = {r.get("run_date") for r in mine}
    name = todays[0].get("name") or student.upper()
    top = max(todays, key=lambda r: int(r.get("score") or 0))
    pts = int(top.get("score") or 0)
    band = band_for(pts, top.get("max_score") or top.get("maxScore"))
    streak = current_school_streak(present, date.fromisoformat(today_iso))
    total = season_total(mine, today_iso, seed)
    return {"student": student, "name": name, "pts": pts, "band": band,
            "total": total, "streak": streak}


def render_line(f, today_iso):
    """One deterministic line from the facts. streak < 2 is silently omitted."""
    options = TEMPLATES[f.get("band")]
    t = options[sum(today_iso.encode()) % len(options)]
    streak_bit = f" \u00b7 {f['streak']}-day streak" if f["streak"] >= 2 else ""
    return t.format(name=f["name"], pts=f"{f['pts']:,}", streak=streak_bit)


def plan(runs, cursor, today_iso, students, seed=None):
    """Decide what (if anything) to send tonight — PER KID, to that kid's own
    parent seat ("parents:<code>"), never a shared blast. Different kids can
    have entirely different parents; the routing enforces it.

    Returns (sends, safe_log_lines) where sends = [{code, text}].
    safe_log_lines are guaranteed name/score-free (they're what Actions prints).
    """
    sent = cursor.get("sent", {})
    log, sends = [], []
    for s in students:
        if today_iso in sent.get(s, []):
            log.append(f"[{s}] already sent for {today_iso} \u2014 no-op.")
            continue
        f = facts_for(runs, s, today_iso, (seed or {}).get(s, 0))
        if not f:
            log.append(f"[{s}] no run for {today_iso} yet \u2014 silent.")
            continue
        log.append(f"[{s}] run found for {today_iso} \u2014 soundbyte queued for parents:{s}.")
        sends.append({"code": s, "text": render_line(f, today_iso)})
    return sends, log


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
    import roster

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

    spath = os.path.join(priv, SEED_FILE)
    seed = json.load(open(spath)) if os.path.exists(spath) else {}

    sends, log = plan(runs, cursor, today_iso, roster.active(), seed)
    for line in log:
        print(line)

    if not sends:
        print("nothing to send.")
        return

    if a.dry_run:
        print(f"DRY-RUN \u2014 {len(sends)} send(s) + cursor write suppressed.")
        return

    # Send per kid to that kid's parent seat; advance ONLY that kid's cursor on
    # success — one family's failed send never blocks or repeats another's.
    # NOTE: `detail` may echo message content, so it is never printed; failures
    # land in the private repo instead.
    advanced, failed = 0, []
    for snd in sends:
        ok, detail = notify.send_sms(f"parents:{snd['code']}", snd["text"],
                                     ref=f"xpd-sb-{snd['code']}-{today_iso}", dry_run=False)
        if ok:
            cursor.setdefault("sent", {}).setdefault(snd["code"], []).append(today_iso)
            advanced += 1
            print(f"[{snd['code']}] soundbyte sent \u2713")
        else:
            failed.append((snd["code"], detail))
            print(f"[{snd['code']}] \u26a0 send FAILED \u2014 will retry next poll.")
    if advanced:
        with open(cpath, "w") as fh:
            json.dump(cursor, fh, indent=1)
            fh.write("\n")
        print(f"cursor advanced for {advanced} kid(s).")
    if failed:
        with open(os.path.join(priv, ERROR_FILE), "w") as fh:
            for code, detail in failed:
                fh.write(f"{today_iso} {code}: {detail}\n")
        print("failure detail in private work/soundbyte_last_error.txt")


if __name__ == "__main__":
    main()
