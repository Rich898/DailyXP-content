#!/usr/bin/env python3
"""LEDGER INVISIBILITY (v3.1 non-negotiable): the hidden double-XP flag (x2) doubles SCORE only —
it must never change any mastery outcome. Runs an identical scenario twice, once with x2:true stamped
on every record, and asserts the resulting ledger is byte-identical. Exit 0 = all pass.
"""
import json, os, sys, tempfile, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_writer as sw


def build(private_dir, x2):
    os.makedirs(f"{private_dir}/work"); os.makedirs(f"{private_dir}/plans/s1")
    state = {"generated": "2026-07-01", "students": {"s1": {"ref": "s1", "status": "ACTIVE", "status_reason": None,
        "confidence_profile": "", "topics": [
            {"subject": "Mat", "topic": "t_wrong", "state": "developing", "repair": False, "last_tested": "2026-07-01", "times_seen": 2, "note": "n", "repair_confirms": 0},
            {"subject": "Sci", "topic": "t_right", "state": "developing", "repair": False, "last_tested": "2026-07-01", "times_seen": 2, "note": "n", "repair_confirms": 0},
            {"subject": "His", "topic": "t_cw", "state": "developing", "repair": False, "last_tested": "2026-07-01", "times_seen": 2, "note": "n", "repair_confirms": 0},
        ]}}}
    json.dump(state, open(f"{private_dir}/work/state.json", "w"), indent=2)
    slots = [("S1", "steady", "Mat", "t_wrong"), ("S2", "steady", "Sci", "t_right"), ("S3", "steady", "His", "t_cw")]
    json.dump({"student": "s1", "set_date": "2026-08-06", "tag": "X", "day": "THU",
               "slots": [{"slot": i, "phase": p, "subject": s, "intent": "x", "topic": t} for i, p, s, t in slots]},
              open(f"{private_dir}/plans/s1/2026-08-06.json", "w"), indent=2)

    def Q(id, subj, ok, conf, x2flag):
        r = {"id": id, "subject": subj, "phase": "steady", "skipped": False, "ok": ok, "picked": "x",
             "confidence": conf, "secs": 14.0, "pts": 250 if ok else 0, "chars": None, "text": None}
        if x2flag:
            r["x2"] = True   # the flag under test — must be ignored by the ledger
            r["pts"] = r["pts"] * 2
        return r

    run = {"student": "s1", "name": "s1", "tag": "X", "day": "THU", "set_date": "2026-08-06",
           "run_date": "2026-08-06", "ts": "2026-08-06T08:00:00+00:00", "ts_raw": "2026-08-06T08:00:00+00:00",
           "attempt": 1, "shell": "3.1", "score": 0, "max_score": 0, "speed": {}, "steady": {}, "teach": {},
           "shell_flags": {"skips": [], "confidentWrong": ["S3"], "slowWrong": [], "fastWrong": [], "luckyGuess": []},
           "timing": {}, "is_test": False, "canonical": True, "canonical_caveat": False,
           "questions": [Q("S1", "Mat", False, "Think so", x2), Q("S2", "Sci", True, "Sure", x2), Q("S3", "His", False, "Sure", x2)]}
    json.dump({"runs": [run]}, open(f"{private_dir}/work/runs.json", "w"), indent=2)


def ledger_after(x2):
    tmp = tempfile.mkdtemp(prefix=f"x2inv_{int(x2)}_")
    build(tmp, x2)
    sw.process(tmp, dry_run=False)
    after = json.load(open(f"{tmp}/work/state.json"))
    import shutil; shutil.rmtree(tmp)
    # topic states + repair fields are the mastery outcome; ignore any score/pts echoes
    return {t["topic"]: {"state": t["state"], "repair": t.get("repair"), "repair_confirms": t.get("repair_confirms")}
            for t in after["students"]["s1"]["topics"]}


plain = ledger_after(False)
doubled = ledger_after(True)

cases = []
def check(name, cond, detail=""):
    cases.append((name, cond, detail))
    if not cond:
        print(f"  FAIL {name}  [{detail}]")

check("scenario actually moved the ledger (not a no-op)", plain["t_wrong"]["state"] == "shaky" and plain["t_cw"]["state"] == "shaky", str(plain))
check("x2 run produces the IDENTICAL ledger (mastery invisible to double-XP)", plain == doubled, f"plain={plain} doubled={doubled}")

ok = all(c for _, c, _ in cases)
print("x2 ledger-invisibility:")
for n, c, _ in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}")
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
