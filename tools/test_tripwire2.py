#!/usr/bin/env python3
"""Regression test for tripwire2.checks_for — the drift-proof question picker.

The 1 Sep 2026 incident: GitHub's best-effort cron ran the 18:15 AEST rung at
02:08 the NEXT morning; the checker asked "did today's runs happen?" about a
day whose windows hadn't opened and texted a false "scheduler/dispatch may be
down" while pg_cron was firing every job to the second. checks_for derives the
question from the clock so that whenever the rung actually lands, it asks a
question that has an answer.

Runnable in CI: `python3 tools/test_tripwire2.py` (exit 0 = all pass).
"""
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tripwire2 import checks_for  # noqa: E402

cases = []
def check(name, cond, detail=""):
    cases.append((name, cond))
    if not cond:
        print(f"  FAIL {name}  [{detail}]")

def at(y, m, d, hh, mm):
    return dt.datetime(y, m, d, hh, mm)

MON, TUE, FRI, SAT, SUN = (dt.date(2026, 8, 31), dt.date(2026, 9, 1),
                           dt.date(2026, 8, 28), dt.date(2026, 8, 29),
                           dt.date(2026, 8, 30))

# on-time evening rung: both windows closed today
target, jobs = checks_for(at(2026, 8, 31, 18, 15))
check("Mon 18:15 -> checks Monday, both jobs", target == MON and len(jobs) == 2, f"{target} {jobs}")

# THE INCIDENT: rung drifted past midnight — must check the PREVIOUS school day
target, jobs = checks_for(at(2026, 9, 1, 2, 8))
check("Tue 02:08 -> checks Monday, both jobs (the 1 Sep false alarm)",
      target == MON and len(jobs) == 2, f"{target} {jobs}")

# mid-afternoon: quiz window closed, nudge window still open
target, jobs = checks_for(at(2026, 9, 1, 16, 0))
check("Tue 16:00 -> checks Tuesday, quiz only",
      target == TUE and [w for w, _ in jobs] == ["daily-quiz.yml"], f"{target} {jobs}")

# early Monday: previous school day is FRIDAY, never the weekend
target, jobs = checks_for(at(2026, 8, 31, 2, 0))
check("Mon 02:00 -> checks Friday, both jobs", target == FRI and len(jobs) == 2, f"{target} {jobs}")

# weekend drift: Saturday morning checks Friday
target, jobs = checks_for(at(2026, 8, 29, 6, 0))
check("Sat 06:00 -> checks Friday, both jobs", target == FRI and len(jobs) == 2, f"{target} {jobs}")

# deep weekend: Sunday evening still checks Friday
target, jobs = checks_for(at(2026, 8, 30, 18, 0))
check("Sun 18:00 -> checks Friday, both jobs", target == FRI and len(jobs) == 2, f"{target} {jobs}")

# exactly at a window close counts as closed
target, jobs = checks_for(at(2026, 9, 1, 15, 30))
check("Tue 15:30 sharp -> quiz window just closed",
      target == TUE and [w for w, _ in jobs] == ["daily-quiz.yml"], f"{target} {jobs}")

ok = all(c for _, c in cases)
print("tripwire2 windows:")
for n, c in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}")
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
