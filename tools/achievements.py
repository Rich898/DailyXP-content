#!/usr/bin/env python3
"""
achievements.py — badge the ledger (ACHIEVEMENTS.md). Deterministic, idempotent, no AI.

Runs right after the state-writer. Reads three event sources and awards any newly-unlocked
badges, deduped against a private earned-ledger so nothing ever fires twice:

  runs.json                 → run-shaped badges  (First Blood, Clean Run, Boss Slayer,
                              Blitz Master, Perfect Week, Streak)
  state_writer_log.jsonl    → transition badges  (Locked It, Comeback, Untouchable,
                              Calm Hands, Sure Shot)
  state.json                → snapshot badges    (Full Clear)

Same law as the state-writer: no AI, no invented state — a badge is a read of what already
happened. Public-log safe: prints student codes (y8/y9) + badge names only, never names/scores.

Badges accrue from when the state-writer went live (the log is the transition source); run-shaped
badges can see the full runs history. Earned-ledger + per-run dedup key = idempotent.

Usage:
  python3 tools/achievements.py --private-dir ../DailyXP-private [--dry-run]
"""
import argparse
import json
import os
import sys
from datetime import date, timedelta

STREAK_TIERS = [(14, "gold"), (7, "silver"), (3, "bronze")]
ACTIVE_STATES = {"shaky", "developing", "solid", "REPAIR"}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def _load_json(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def _load_log(private_dir):
    p = os.path.join(private_dir, "work", "state_writer_log.jsonl")
    out = []
    if not os.path.exists(p):
        return out
    for line in open(p):
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            if e.get("applied", True):
                out.append(e)
        except Exception:
            pass
    return out


def _iso_week(dstr):
    d = date.fromisoformat(dstr[:10])
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _longest_school_streak(present):
    """Longest run of consecutive *school-days* (Mon–Fri) that have a completed quiz."""
    if not present:
        return 0
    days = sorted(date.fromisoformat(x) for x in present)
    lo, hi = days[0], days[-1]
    longest = cur = 0
    d = lo
    while d <= hi:
        if d.weekday() < 5:                       # school day
            if d.isoformat() in present:
                cur += 1
                longest = max(longest, cur)
            else:
                cur = 0
        d += timedelta(days=1)
    return longest


# --------------------------------------------------------------------------- #
# Detectors — each yields (badge, key, date, label). key is the idempotency handle.
# --------------------------------------------------------------------------- #

def run_badges(runs):
    out = []
    if not runs:
        return out
    out.append(("First Blood", "First Blood", runs[0].get("run_date"), "Completed your first quiz."))

    blitz_best = None
    weekday_by_week, present = {}, set()
    for r in runs:
        sf = r.get("shell_flags", {}) or {}
        day = (r.get("day") or "").upper()
        tag = (r.get("tag") or "").upper()
        sd, rd = r.get("set_date"), r.get("run_date")
        sp, st = r.get("speed", {}) or {}, r.get("steady", {}) or {}
        answered = (sp.get("of") or 0) + (st.get("of") or 0)

        # Clean Run — real answers, no lucky guesses, no confident-wrongs
        if answered > 0 and not sf.get("luckyGuess") and not sf.get("confidentWrong"):
            out.append(("Clean Run", f"Clean Run|{rd}|{tag}", rd,
                        "A whole quiz with no lucky guesses and no confident-wrongs."))

        # Boss Slayer — a Friday/Boss run with every steady slot correct
        if (day == "FRI" or "BOSS" in tag) and st.get("of") and st.get("right") == st.get("of"):
            out.append(("Boss Slayer", f"Boss Slayer|{rd}", rd, "Cleared Friday's Boss."))

        # Blitz Master — a Blitz run that beats your own previous Blitz best
        if day == "WED" or "BLITZ" in tag:
            sc = r.get("score") or 0
            if blitz_best is not None and sc > blitz_best:
                out.append(("Blitz Master", f"Blitz Master|{rd}", rd, "A new Blitz personal best."))
            blitz_best = max(blitz_best or 0, sc)

        if sd:
            present.add(sd[:10])
            wd = date.fromisoformat(sd[:10]).weekday()
            if wd < 5:
                weekday_by_week.setdefault(_iso_week(sd), set()).add(wd)

    # Perfect Week — all five school-days present in one ISO week
    for wk, wds in weekday_by_week.items():
        if len(wds) == 5:
            out.append(("Perfect Week", f"Perfect Week|{wk}", None, "Completed all five school days."))

    # Streak — longest consecutive school-day run, tiered
    longest = _longest_school_streak(present)
    for n, tier in STREAK_TIERS:
        if longest >= n:
            out.append(("Streak", f"Streak|{tier}", None,
                        f"{tier.capitalize()} streak — {n} school-days in a row."))
    return out


def log_badges(log):
    out = []
    by_topic = {}
    for e in log:
        by_topic.setdefault(f"{e.get('subject')}::{e.get('topic')}", []).append(e)

    for tkey, entries in by_topic.items():
        _subj, topic = tkey.split("::", 1)
        solid_count, seen_fw, calm_done = 0, False, False
        for e in entries:
            badge, rd = e.get("badge"), e.get("run_date")
            frm, to = e.get("from_state"), e.get("to_state")
            from_rep, to_rep = e.get("from_repair"), e.get("to_repair")

            if to == "solid" and frm != "solid":
                out.append(("Locked It", f"Locked It|{tkey}", rd, f"Mastered {topic}."))
            if to == "solid":
                solid_count += 1
                if solid_count == 3:
                    out.append(("Untouchable", f"Untouchable|{tkey}", rd,
                                f"{topic} held solid across three checks."))
            if from_rep and not to_rep:
                out.append(("Comeback", f"Comeback|{tkey}", rd, f"Brought {topic} back from repair."))
            if from_rep and badge == "✓_sure":
                out.append(("Sure Shot", f"Sure Shot|{tkey}", rd,
                            f"A confident, correct answer on {topic} while in repair."))
            if badge == "FW":
                seen_fw = True
            if badge == "✓_sure" and seen_fw and not calm_done:
                out.append(("Calm Hands", f"Calm Hands|{tkey}", rd, f"Beat the rush on {topic}."))
                calm_done = True
    return out


def state_badges(student_state):
    out = []
    by_subject = {}
    for t in student_state.get("topics", []):
        if t.get("state") in ACTIVE_STATES:
            by_subject.setdefault(t["subject"], []).append(t)
    for subj, topics in by_subject.items():
        if len(topics) >= 2 and all(t.get("state") == "solid" for t in topics):
            out.append(("Full Clear", f"Full Clear|{subj}", None, f"Every active {subj} topic mastered."))
    return out


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def process(private_dir, dry_run=False):
    runs_all = _load_json(os.path.join(private_dir, "work", "runs.json"), {"runs": []}).get("runs", [])
    state = _load_json(os.path.join(private_dir, "work", "state.json"), {"students": {}})
    log = _load_log(private_dir)
    earned_path = os.path.join(private_dir, "work", "achievements_earned.json")
    earned = _load_json(earned_path, {})

    students = sorted(state.get("students", {}).keys()) or sorted({r["student"] for r in runs_all})
    lines, awarded_all = [], []

    for s in students:
        runs = [r for r in runs_all if r.get("student") == s
                and r.get("canonical") and not r.get("is_test")]
        runs.sort(key=lambda r: (r.get("run_date") or "", r.get("ts") or ""))
        latest_rd = runs[-1].get("run_date") if runs else None
        slog = [e for e in log if e.get("student") == s]
        sstate = state.get("students", {}).get(s, {})

        cands = run_badges(runs) + log_badges(slog) + state_badges(sstate)
        have = set(e["key"] for e in earned.get(s, {}).get("earned", []))
        new = []
        for badge, key, d, label in cands:
            if key in have:
                continue
            have.add(key)                                   # dedup within this pass too
            new.append({"badge": badge, "key": key, "date": d or latest_rd, "label": label})

        if new:
            earned.setdefault(s, {}).setdefault("earned", []).extend(new)
            lines.append(f"{s}: {len(new)} new badge(s) — " + ", ".join(n["badge"] for n in new))
            for n in new:
                awarded_all.append({"student": s, **n})
        else:
            lines.append(f"{s}: no new badges.")

    if not dry_run and awarded_all:
        json.dump(earned, open(earned_path, "w"), indent=2, ensure_ascii=False)
        with open(os.path.join(private_dir, "work", "achievements_log.jsonl"), "a") as lf:
            for a in awarded_all:
                lf.write(json.dumps(a, ensure_ascii=False) + "\n")
    return awarded_all, lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    awarded, lines = process(a.private_dir, dry_run=a.dry_run)
    print("=== achievements: badge the ledger ===")
    print("\n".join(lines))
    if a.dry_run and awarded:
        print("(dry run — nothing written)")


if __name__ == "__main__":
    main()
