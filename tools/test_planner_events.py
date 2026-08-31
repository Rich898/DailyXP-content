#!/usr/bin/env python3
"""
test_planner_events.py — locks the WEEKDAY EVENT-MODE invariants (and throwback).

Covers the planner behaviour behind the one-line WEEKDAY_DIRECTIVE loadout edit:
  * standard days, * BATTLEGROUND (Fri, varied-format), * throwback (LAW 3),
  * the Reversed mechanic (kept intact + dormant for the daily-type build).
(Blitz was retired 20 Aug 2026 — Wednesday is a standard day; Reversed is
becoming a daily question-type mechanic, not a Wednesday event.)

These checks make sure the plumbing keeps holding:
  1. Wednesday maps to the standard shape (12/6/1); no event tag, no double-XP.
  2. The Reversed doctrine block still reaches composer_instructions when the
     "reversed" directive is given (intact for the future daily wiring).
  3. The Friday tag carries BATTLEGROUND; the Wednesday tag carries no BLITZ.
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

print("planner: Wednesday is now a standard day (Blitz retired 20 Aug 2026)")
plan = planner.plan_set("y8", "2026-08-12", "WED", "H3.3",
                        TARGETS, STATE, "standard")
rq = plan.get("requested_shape", plan["shape"])
check("Wednesday maps to standard 12/6/1", (rq["speed"], rq["steady"], rq["teach"]) == (12, 6, 1))
check("no REVERSED block on a standard Wednesday", "REVERSED" not in plan["composer_instructions"])

print("planner: the Reversed mechanic is intact (dormant, for the daily-type build)")
plan_rev = planner.plan_set("y8", "2026-08-12", "WED", "H3.3",
                            TARGETS, STATE, "reversed")
ci = plan_rev["composer_instructions"]
check("reversed directive still builds a CONTAINED reversed block", "CONTAINED Reversed block" in ci and 'mech "reversed"' in ci)
check("reversed block still exempts calculation slots (12 Aug HOLD)", "EXEMPT from reversal" in ci and "CALCULATION" in ci)
check("reversed block leaves steady/teach normal", "Steady and teach stay normal" in ci)

print("run_daily: Wednesday tag has no Blitz; Friday is Battleground")
spec = importlib.util.spec_from_file_location(
    "run_daily", os.path.join(REPO, "scripts", "run_daily.py"))
run_daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_daily)
wtag, _, _ = run_daily.derive_tag("y8", dt.date(2026, 8, 12))  # a Wednesday
check("Wednesday tag carries no BLITZ", "BLITZ" not in wtag.upper())
ftag, _, _ = run_daily.derive_tag("y8", dt.date(2026, 8, 14))  # a Friday
check("Friday tag stamped BATTLEGROUND", ftag.endswith("BATTLEGROUND"))
check("Wed directive is standard", run_daily.WEEKDAY_DIRECTIVE[2] == "standard")

print("planner: boss -> Battleground (varied-format) doctrine")
plan_boss = planner.plan_set("y8", "2026-08-15", "FRI", "H3.5 \u00b7 BOSS",
                             TARGETS, STATE, "boss")
shb = plan_boss.get("requested_shape", plan_boss["shape"])
check("boss shape is 2/7/1", (shb["speed"], shb["steady"], shb["teach"]) == (2, 7, 1))
cib = plan_boss["composer_instructions"]
check("BATTLEGROUND block present", "BATTLEGROUND" in cib)
check("frames zones as CLAIMABLE ground", "claimable zone" in cib and "claiming" in cib.lower())
check("offers the varied MC family", all(fmt in cib for fmt in ["SPOT-THE-LIE", "TRUE / FALSE", "MULTIPLE CHOICE", "SUM"]))
check("constrains to four options (no typed input yet)", "four options" in cib and "no typed" in cib.lower())
check("tells composer to VARY formats across zones", "VARY the formats" in cib)
check("spreads across DIFFERENT weak subjects", "DIFFERENT weak subjects" in cib)
check("speed stays warm-up recall", "SPEED slots stay NORMAL" in cib)
check("no Battleground leak on a standard set",
      "BATTLEGROUND" not in planner.plan_set("y8","2026-08-11","MON","H3.1",TARGETS,STATE,"standard")["composer_instructions"])

print("throwback (SEASONS.md LAW 3): woven aged-mastered slot")
# A state with a genuinely aged, mastered topic that has LEFT the live pool.
TB_STATE = {"students": {"y8": {"status": "ACTIVE", "topics": [
    # current weak topics (live) — fill the rest of the run
    {"subject": "Maths", "topic": "Linear equations", "state": "shaky",
     "repair": False, "last_tested": "2026-08-16", "times_seen": 6, "note": ""},
    {"subject": "Science", "topic": "Cells basics", "state": "developing",
     "repair": False, "last_tested": "2026-08-15", "times_seen": 3, "note": ""},
    {"subject": "English", "topic": "Essay structure", "state": "shaky",
     "repair": False, "last_tested": "2026-08-14", "times_seen": 4, "note": ""},
    {"subject": "History", "topic": "Timeline skills", "state": "developing",
     "repair": False, "last_tested": "2026-08-15", "times_seen": 3, "note": ""},
    # the throwback candidate: solid, aged 20 days, NOT live in class
    {"subject": "Geography", "topic": "Mapping conventions", "state": "solid",
     "repair": False, "last_tested": "2026-07-30", "times_seen": 6, "note": "landed"},
]}}}
# Targets mark only the current topics live; the aged Geography topic is NOT live.
TB_TARGETS = {"students": {"y8": {"subjects": {
    "Maths": {"topics": [{"topic": "Linear equations", "status": "live"}]},
    "Science": {"topics": [{"topic": "Cells basics", "status": "live"}]},
    "English": {"topics": [{"topic": "Essay structure", "status": "live"}]},
    "History": {"topics": [{"topic": "Timeline skills", "status": "live"}]},
}}}}
tb_plan = planner.plan_set("y8", "2026-08-19", "TUE", "H5.1",
                           TB_TARGETS, TB_STATE, "standard")
tb_slots = [s for s in tb_plan["slots"] if s.get("throwback")]
check("exactly one throwback slot woven in", len(tb_slots) == 1)
if tb_slots:
    ts = tb_slots[0]
    check("throwback pulls the aged-mastered topic", ts["topic"] == "Mapping conventions")
    check("throwback sits in steady phase", ts["phase"] == "steady")
    check("throwback intent labelled", ts["intent"] == "throwback")
    check("throwback flagged fresh:false (a revisit)", ts.get("fresh") is False)
    check("throwback guidance is a retention check", "retention check" in ts["guidance"].lower())
# shape must NOT inflate — the throwback never pushes steady past the shape's target (6).
# (Sparse ledger here: it fills a gap; at capacity it would displace — either way, never > 6.)
check("throwback never inflates steady past the shape (<= 6)",
      sum(1 for s in tb_plan["slots"] if s["phase"] == "steady") <= 6)
# on a set with NO aged-mastered topic, there is simply no throwback slot (not padded)
NO_TB_STATE = {"students": {"y8": {"status": "ACTIVE", "topics": [
    {"subject": "Maths", "topic": "Linear equations", "state": "shaky",
     "repair": False, "last_tested": "2026-08-16", "times_seen": 6, "note": ""},
]}}}
NO_TB_TARGETS = {"students": {"y8": {"subjects": {
    "Maths": {"topics": [{"topic": "Linear equations", "status": "live"}]}}}}}
no_tb = planner.plan_set("y8", "2026-08-19", "TUE", "H5.1",
                         NO_TB_TARGETS, NO_TB_STATE, "standard")
check("no throwback slot when ledger has none (never padded)",
      not any(s.get("throwback") for s in no_tb["slots"]))
# boss/Battleground owns its own topic logic — no throwback there
boss = planner.plan_set("y8", "2026-08-22", "FRI", "H5.5",
                        TB_TARGETS, TB_STATE, "boss")
check("no throwback slot on boss/Battleground",
      not any(s.get("throwback") for s in boss["slots"]))


check("run_daily and kid_nudge WEEKDAY_DIRECTIVE identical",
      run_daily.WEEKDAY_DIRECTIVE == kid_nudge.WEEKDAY_DIRECTIVE)
check("a nudge voice exists for every school weekday (per-day copy, 31 Aug)",
      all(d in kid_nudge.NUDGE for d in kid_nudge.WEEKDAY_DIRECTIVE))
check("no blitz nudge remains in the bank", not any("BLITZ" in v.upper() for v in kid_nudge.NUDGE.values()))

print()
if fails:
    print(f"{len(fails)} FAILURE(S): {fails}")
    sys.exit(1)
print("all green")
