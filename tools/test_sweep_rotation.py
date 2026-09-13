#!/usr/bin/env python3
"""Tests for the ROTATION-CHANGEOVER clause (14 Sep 2026) — the first real
rotation swap (y9 D&T -> Food Technology) held the sweep because a vanished
course had no path to an explicit removal record, and y8's accumulated
history broke the all-topics sane band.

Covers: sweep_summarise.resolve_absent_subjects (retire vs carry branches)
and sweep_validate end-to-end (removal records satisfy the carry-forward
law; the gate still bites without them; the band counts live surface only).

Runnable in CI: `python3 tools/test_sweep_rotation.py` (exit 0 = all pass).
No names/scores; topic strings are synthetic.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_summarise import resolve_absent_subjects

VALIDATE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "sweep_validate.py")

cases = []


def check(name, cond, detail=""):
    cases.append((name, cond, detail))
    if not cond:
        print(f"  FAIL {name}  [{detail}]")


def dnt_base():
    return {"D&T": {"unit": "Design portfolio", "topics": [
        {"topic": "Logo design basics", "status": "live", "fresh": False},
        {"topic": "CAD for beginners", "status": "prior_term", "fresh": False},
    ]}}


# --- resolve_absent_subjects: the retire branch --------------------------

subjects = {"Food Technology": {"unit": "Kitchen safety", "topics": [
    {"topic": "Knife skills", "status": "live", "fresh": True}]}}
chg, lines = resolve_absent_subjects(dnt_base(), subjects, fetch_errors=0)
check("changeover signature retires the absent subject",
      "D&T" in chg and chg["D&T"].get("retired") is True, str(chg))
check("every base topic gets a removal record",
      [r["topic"] for r in chg["D&T"]["removed"]] ==
      ["Logo design basics", "CAD for beginners"], str(chg))
check("removal reason names the new course",
      all("Food Technology" in r["reason"] for r in chg["D&T"]["removed"]),
      str(chg))
check("retired subject is NOT re-added to the output",
      "D&T" not in subjects, str(sorted(subjects)))
check("retirement is loudly logged",
      any("RETIRED" in ln for ln in lines), str(lines))

# --- resolve_absent_subjects: the carry branches --------------------------

# absence with NO new course (a pull glitch) -> carry verbatim, never retire
base = dnt_base()
subjects = {}  # nothing else fetched this pull
chg, lines = resolve_absent_subjects(base, subjects, fetch_errors=0)
check("absence without a new course carries the base verbatim",
      chg["D&T"].get("course_absent") is True and "removed" not in chg["D&T"],
      str(chg))
check("carried subject lands in the output with all topics",
      [t["topic"] for t in subjects["D&T"]["topics"]] ==
      ["Logo design basics", "CAD for beginners"], str(subjects))
check("carry is a copy — mutating it never touches the base",
      (subjects["D&T"]["topics"][0].update({"status": "upcoming"}) or
       base["D&T"]["topics"][0]["status"]) == "live", str(base))

# new course present BUT the fetch had errors -> too risky, carry not retire
subjects = {"Food Technology": {"unit": "x", "topics": []}}
chg, _ = resolve_absent_subjects(dnt_base(), subjects, fetch_errors=2)
check("fetch errors veto auto-retirement",
      chg["D&T"].get("course_absent") is True and "D&T" in subjects, str(chg))

# no subject absent -> pure no-op
subjects = {"D&T": {"unit": "x", "topics": []}}
chg, lines = resolve_absent_subjects(dnt_base(), subjects, fetch_errors=0)
check("nothing absent is a no-op", chg == {} and lines == [], str(chg))

# two absent subjects (an HSIE-style pair) retire together
subjects = {"Commerce": {"unit": "new", "topics": []}}
chg, _ = resolve_absent_subjects(
    {"History": {"topics": [{"topic": "T1"}]},
     "Geography": {"topics": [{"topic": "T2"}]}}, subjects, fetch_errors=0)
check("multiple absent subjects retire independently",
      chg["History"].get("retired") and chg["Geography"].get("retired"),
      str(chg))


# --- sweep_validate end-to-end: the gate honours removal records ----------

def topics(n, status="live"):
    return [{"topic": f"Topic {status} {i}", "status": status, "fresh": False}
            for i in range(n)]


def run_validate(targets, dump_seats, base=None, seat_dumps=None):
    """Write a scratch dump/base/manual layout, run the real gate, return
    (exit_code, stdout)."""
    with tempfile.TemporaryDirectory() as d:
        dump = os.path.join(d, "dump")
        os.makedirs(dump)
        json.dump({"seats": dump_seats}, open(os.path.join(
            dump, "manifest.json"), "w"))
        for seat, courses in (seat_dumps or {}).items():
            json.dump({"courses": courses, "errors": []},
                      open(os.path.join(dump, f"{seat}.json"), "w"))
        manual_dir = os.path.join(d, "targets")
        os.makedirs(manual_dir)
        cmd_base = []
        if base is not None:
            base_p = os.path.join(manual_dir, "2026-09-07.json")
            json.dump(base, open(base_p, "w"))
            cmd_base = ["--base", base_p]
        t_p = os.path.join(d, "targets-shadow.json")
        json.dump(targets, open(t_p, "w"))
        r = subprocess.run(
            [sys.executable, VALIDATE, "--targets", t_p, "--dump", dump,
             "--manual-dir", manual_dir] + cmd_base,
            capture_output=True, text=True)
        return r.returncode, r.stdout


BASE = {"students": {"y9": {"subjects": dnt_base()}}}
RETIRED_TARGETS = {
    "status_legend": "x", "fresh_flag_legend": "x",
    "students": {"y9": {"subjects": {
        "Food Technology": {"unit": "Kitchen safety", "topics": topics(4)}}}},
    "sweep_update": {"seats": {"y9": {"D&T": {
        "removed": [{"topic": "Logo design basics", "reason": "changeover"},
                    {"topic": "CAD for beginners", "reason": "changeover"}],
        "retired": True}}}},
}
DUMP_SEATS = {"y9": {"courses": 1, "errors": 0}}
Y9_COURSES = [{"name": "Year 9 Food Technology 2026"}]

code, out = run_validate(RETIRED_TARGETS, DUMP_SEATS, BASE,
                         {"y9": Y9_COURSES})
check("gate PASSES a retired subject backed by removal records",
      code == 0 and "RESULT: PASS" in out, f"exit={code} out={out!r}")
check("the drop still surfaces as the drift warning",
      "subjects in manual but not machine" in out, out)

no_records = copy.deepcopy(RETIRED_TARGETS)
no_records["sweep_update"]["seats"]["y9"] = {}
code, out = run_validate(no_records, DUMP_SEATS, BASE, {"y9": Y9_COURSES})
check("gate still FAILS the same drop without removal records",
      code == 2 and "CARRY-FORWARD VIOLATION" in out, f"exit={code}")

# --- sweep_validate: the band measures the live surface only --------------

fat_history = {
    "status_legend": "x", "fresh_flag_legend": "x",
    "students": {"y8": {"subjects": {
        "Maths": {"unit": "x", "topics": topics(60) + topics(45, "prior_term")},
    }}},
}
code, out = run_validate(fat_history, {}, None)
check("105 total but 60 live passes the band",
      code == 0 and "RESULT: PASS" in out, f"exit={code} out={out!r}")

exploded = {
    "status_legend": "x", "fresh_flag_legend": "x",
    "students": {"y8": {"subjects": {
        "Maths": {"unit": "x", "topics": topics(91)},
    }}},
}
code, out = run_validate(exploded, {}, None)
check("91 live topics still trips the band",
      code == 2 and "non-prior topics outside sane band" in out,
      f"exit={code} out={out!r}")

ok = all(c for _, c, _ in cases)
print("sweep rotation-changeover:")
for n, c, _ in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}")
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
