#!/usr/bin/env python3
"""
test_planner_reversed.py — locks the REVERSED mutator invariants.

The chapter loadout rotates by editing WEEKDAY_DIRECTIVE (run_daily + kid_nudge).
These checks make sure the plumbing behind that one-line edit keeps holding:
  1. "reversed blitz" still planner-matches blitz shape (10/2/1).
  2. The reversed doctrine block reaches composer_instructions — and ONLY when asked.
  3. The Wednesday tag carries REVERSED BLITZ with "BLITZ" intact as a substring
     (achievements' Blitz Master + the shell's event detection both key on it).
  4. run_daily and kid_nudge WEEKDAY_DIRECTIVE maps stay identical (same doctrine,
     two encodings — the comment in kid_nudge.py demands they move together).
"""
import datetime as dt
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import planner  # noqa: E402
import kid_nudge  # noqa: E402

fails = []


def check(name, ok):
    print(("  ok  " if ok else "  FAIL") + " " + name)
    if not ok:
        fails.append(name)


# Minimal state/targets: one live topic pool big enough for a blitz shape.
SUBJECTS = ["Maths", "Science", "English", "History"]
STATE = {"students": {"y8": {"status": "ACTIVE", "topics": [
    {"subject": SUBJECTS[i % 4], "topic": f"{SUBJECTS[i % 4]} Topic {i}", "state": "shaky",
     "repair": False, "last_tested": "2026-08-01", "times_seen": 2, "note": ""}
    for i in range(1, 17)
]}}}
TARGETS = {"students": {"y8": {"subjects": {
    s: {"topics": [{"topic": f"{s} Topic {i}", "status": "live"}
                   for i in range(1, 17) if SUBJECTS[i % 4] == s]}
    for s in SUBJECTS
}}}}

print("planner: reversed blitz directive")
plan = planner.plan_set("y8", "2026-08-12", "WED", "H3.3 · REVERSED BLITZ",
                        TARGETS, STATE, "reversed blitz")
rq = plan.get("requested_shape", plan["shape"])
check("directive maps to blitz 10/2/1", (rq["speed"], rq["steady"], rq["teach"]) == (10, 2, 1))
ci = plan["composer_instructions"]
check("REVERSED block present", "REVERSED" in ci)
check("declares every speed slot reversed", "EVERY SPEED SLOT" in ci)
check("carries the prompt template", "Which question is this the answer to?" in ci)
check("steady/teach stay normal", "steady and teach stay normal" in ci)

print("planner: plain blitz directive stays classic")
plan2 = planner.plan_set("y8", "2026-08-12", "WED", "H3.3 · BLITZ",
                         TARGETS, STATE, "blitz")
check("no REVERSED block on plain blitz", "REVERSED" not in plan2["composer_instructions"])
rq2 = plan2.get("requested_shape", plan2["shape"])
check("plain blitz still maps 10/2/1", (rq2["speed"], rq2["steady"], rq2["teach"]) == (10, 2, 1))

print("run_daily: Wednesday tag + directive")
spec = importlib.util.spec_from_file_location(
    "run_daily", os.path.join(REPO, "scripts", "run_daily.py"))
run_daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_daily)
tag, week, wd = run_daily.derive_tag("y8", dt.date(2026, 8, 12))  # a Wednesday
check("tag stamped REVERSED BLITZ", tag.endswith("· REVERSED BLITZ"))
check("BLITZ survives as substring (Blitz Master / shell)", "BLITZ" in tag)
check("Wed directive is reversed blitz", run_daily.WEEKDAY_DIRECTIVE[2] == "reversed blitz")

print("planner: boss -> spot-the-flaw doctrine")
plan_boss = planner.plan_set("y8", "2026-08-15", "FRI", "H3.5 \u00b7 BOSS",
                             TARGETS, STATE, "boss")
shb = plan_boss.get("requested_shape", plan_boss["shape"])
check("boss shape is 2/4/1", (shb["speed"], shb["steady"], shb["teach"]) == (2, 4, 1))
cib = plan_boss["composer_instructions"]
check("BOSS block present", "BOSS" in cib)
check("declares SPOT-THE-LIE steady", "SPOT-THE-LIE" in cib)
check("carries the 'which is false' prompt shape", "Which one is FALSE?" in cib)
check("three-true-one-false rule stated", "three are TRUE and ONE is FALSE" in cib.replace("THREE","three"))
check("speed stays warm-up recall", "SPEED slots stay NORMAL" in cib)
check("no spot-the-lie leak on a standard set",
      "SPOT-THE-LIE" not in planner.plan_set("y8","2026-08-11","MON","H3.1",TARGETS,STATE,"standard")["composer_instructions"] and
      "spread the four steady slots across the student's DIFFERENT weak subjects".lower() in cib.lower())

print("doctrine mirrors")
check("run_daily and kid_nudge WEEKDAY_DIRECTIVE identical",
      run_daily.WEEKDAY_DIRECTIVE == kid_nudge.WEEKDAY_DIRECTIVE)
check("nudge flavour exists for the Wed directive",
      kid_nudge.WEEKDAY_DIRECTIVE[2] in kid_nudge.NUDGE)
check("Wed nudge says REVERSED", "REVERSED" in kid_nudge.NUDGE[kid_nudge.WEEKDAY_DIRECTIVE[2]])

print()
if fails:
    print(f"{len(fails)} FAILURE(S): {fails}")
    sys.exit(1)
print("all green")
