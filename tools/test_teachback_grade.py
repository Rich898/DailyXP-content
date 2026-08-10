#!/usr/bin/env python3
"""
Regression test for the teach-back QUALITY consequence in the ledger.

Two layers:
  1. transition() — per-verdict box movement (TB✓ / TB~ / TB✗), including the REPAIR lane.
  2. process()    — the headline FLUENCY-ILLUSION CATCH: a topic where the student picked the
     right MC answer (✓_sure) BUT failed the teach-back (TB✗) must NOT promote — TB✗ governs.
Runnable in CI: `python3 tools/test_teachback_grade.py` (exit 0 = all pass).
"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_writer as sw

fails = 0
def check(name, ok):
    global fails
    print(("  [PASS] " if ok else "  [FAIL] ") + name)
    if not ok: fails += 1

def topic(state, repair=False, confirms=0):
    return {"subject": "X", "topic": "t", "state": state, "repair": repair,
            "repair_confirms": confirms, "times_seen": 2, "last_tested": "2026-07-01", "note": "n"}

# ── precedence property: TB✗ must outrank (govern over) the correct badges ──
print("precedence:")
check("TB✗ governs over ✓_sure (blocks promotion)", sw.PREC.index("TB✗") < sw.PREC.index("✓_sure"))
check("TB✓ sits among the correct badges (not a wrong)", sw.PREC.index("TB✓") > sw.PREC.index("TRIV✓"))

# ── transition(): per-verdict movement (spaced=True, calm via rel=None) ──
print("transition — solid teach-back (TB✓):")
t = topic("untested"); sw.transition(t, "TB✓", None, True, False); check("untested → developing", t["state"] == "developing")
t = topic("developing"); sw.transition(t, "TB✓", None, True, False); check("developing + spaced → solid", t["state"] == "solid")
t = topic("developing"); sw.transition(t, "TB✓", None, False, False); check("developing + NOT spaced → holds developing", t["state"] == "developing")
t = topic("shaky"); sw.transition(t, "TB✓", None, True, False); check("shaky → developing", t["state"] == "developing")
t = topic("solid"); sw.transition(t, "TB✓", None, True, False); check("solid maintained", t["state"] == "solid")

print("transition — partial teach-back (TB~):")
t = topic("untested"); sw.transition(t, "TB~", None, True, False); check("untested → developing (a landing)", t["state"] == "developing")
t = topic("developing"); sw.transition(t, "TB~", None, True, False); check("developing holds (never promotes to solid)", t["state"] == "developing")

print("transition — failed teach-back (TB✗):")
t = topic("developing"); r = sw.transition(t, "TB✗", None, True, False); check("developing holds (blocked, not demoted)", t["state"] == "developing")
check("reason names the fluency illusion", "fluency illusion" in (r or ""))
t = topic("untested"); sw.transition(t, "TB✗", None, True, False); check("untested holds", t["state"] == "untested")

print("transition — REPAIR lane:")
t = topic("REPAIR", repair=True, confirms=0); sw.transition(t, "TB✓", None, True, False)
check("TB✓ on REPAIR → confirm 1/2, held", t["state"] == "REPAIR" and t["repair_confirms"] == 1)
t = topic("REPAIR", repair=True, confirms=1); sw.transition(t, "TB✓", None, True, False)
check("TB✓ reaching 2/2 → EXIT to developing", t["state"] == "developing" and not t["repair"])
t = topic("REPAIR", repair=True, confirms=1); sw.transition(t, "TB✗", None, True, False)
check("TB✗ on REPAIR → held, confirms reset", t["state"] == "REPAIR" and t["repair_confirms"] == 0)
t = topic("REPAIR", repair=True, confirms=1); sw.transition(t, "TB~", None, True, False)
check("TB~ on REPAIR → held, confirms untouched", t["state"] == "REPAIR" and t["repair_confirms"] == 1)

# ── process(): the fluency-illusion catch, end-to-end ──
print("process — fluency-illusion catch (right answer + failed explanation):")
tmp = tempfile.mkdtemp(prefix="tb_catch_")
os.makedirs(f"{tmp}/work"); os.makedirs(f"{tmp}/plans/s1")
state = {"generated": "2026-07-01", "students": {"s1": {"ref": "s1", "status": "ACTIVE",
    "status_reason": None, "confidence_profile": "", "topics": [
        {"subject": "Sci", "topic": "illusion", "state": "developing", "repair": False,
         "last_tested": "2026-07-01", "times_seen": 3, "note": "n", "repair_confirms": 0},
        {"subject": "Sci", "topic": "genuine", "state": "developing", "repair": False,
         "last_tested": "2026-07-01", "times_seen": 3, "note": "n", "repair_confirms": 0},
    ]}}}
json.dump(state, open(f"{tmp}/work/state.json", "w"), indent=2)
# both topics get a correct Sure steady; illusion also gets a FAILED teach-back, genuine a SOLID one
slots = [("A1", "steady", "Sci", "illusion"), ("A2", "teach", "Sci", "illusion"),
         ("B1", "steady", "Sci", "genuine"),  ("B2", "teach", "Sci", "genuine"),
         ("P1", "steady", "Sci", "genuine"),  ("P2", "steady", "Sci", "illusion")]
json.dump({"student": "s1", "set_date": "2026-08-06", "tag": "X1", "day": "THU",
           "slots": [{"slot": i, "phase": p, "subject": s, "intent": "x", "topic": t} for i, p, s, t in slots]},
          open(f"{tmp}/plans/s1/2026-08-06.json", "w"), indent=2)

def Q(id, phase, ok, conf=None, secs=13.0, grade=None):
    q = {"id": id, "subject": "Sci", "phase": phase, "skipped": False, "ok": ok, "picked": "x",
         "confidence": conf, "secs": secs, "pts": 0, "chars": (120 if phase == "teach" else None),
         "text": ("an explanation" if phase == "teach" else None)}
    if grade: q["tb_grade"] = grade
    return q

run = {"student": "s1", "name": "s1", "tag": "X1", "day": "THU", "set_date": "2026-08-06",
       "run_date": "2026-08-06", "ts": "2026-08-06T08:00:00+00:00", "ts_raw": "2026-08-06T08:00:00+00:00",
       "attempt": 1, "shell": "3.0", "score": 0, "max_score": 0, "speed": {}, "steady": {}, "teach": {},
       "shell_flags": {"skips": [], "confidentWrong": [], "slowWrong": [], "fastWrong": [], "luckyGuess": []},
       "timing": {}, "is_test": False, "canonical": True, "canonical_caveat": False,
       "questions": [
           Q("A1", "steady", True, "Sure", 13),                                  # illusion: right answer, Sure
           Q("A2", "teach", True, None, None, grade={"verdict": "none", "english": True, "reason": "x"}),   # ...but FAILED explanation
           Q("B1", "steady", True, "Sure", 13),                                  # genuine: right answer, Sure
           Q("B2", "teach", True, None, None, grade={"verdict": "solid", "english": True, "reason": "x"}),  # ...and SOLID explanation
           Q("P1", "steady", True, None, 13), Q("P2", "steady", True, None, 13), # padding for a stable median
           Q("P3", "steady", True, None, 13), Q("P4", "steady", True, None, 13),
       ]}
json.dump({"runs": [run]}, open(f"{tmp}/work/runs.json", "w"), indent=2)

sw.process(tmp, dry_run=False)
after = {t["topic"]: t for t in json.load(open(f"{tmp}/work/state.json"))["students"]["s1"]["topics"]}
check("illusion topic BLOCKED at developing (right answer, couldn't explain → no promote)", after["illusion"]["state"] == "developing")
check("genuine topic PROMOTED to solid (right answer + solid explanation)", after["genuine"]["state"] == "solid")
import shutil; shutil.rmtree(tmp)

print("")
if fails: print(f"{fails} FAILED"); sys.exit(1)
print("teach-back consequence: all green")
