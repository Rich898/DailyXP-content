#!/usr/bin/env python3
"""Self-contained regression test for state_writer's transition table (LEDGER-RULES.md).

Builds a synthetic private-dir (generic topics, no names/scores) and asserts every doctrine
rule. Runnable in CI: `python3 tools/test_state_writer.py` (exit 0 = all pass).
"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import state_writer as sw

tmp = tempfile.mkdtemp(prefix="sw_regress_")
os.makedirs(f"{tmp}/work"); os.makedirs(f"{tmp}/plans/s1")

# --- synthetic ledger: one topic per rule under test ---
def T(subj, topic, state, repair=False, last="2026-07-01", seen=2, confirms=0, last_badge=None):
    d = {"subject": subj, "topic": topic, "state": state, "repair": repair,
         "last_tested": last, "times_seen": seen, "note": f"HUMAN NOTE for {topic}",
         "repair_confirms": confirms}
    if last_badge:
        d["last_result"] = {"badge": last_badge}
    return d

state = {"generated": "2026-07-01", "students": {"s1": {"ref": "s1", "status": "ACTIVE",
    "status_reason": None, "confidence_profile": "", "topics": [
        T("Sci", "repair_confirm", "REPAIR", repair=True),          # calm Sure → confirm 1/2, hold
        T("Sci", "repair_exit", "REPAIR", repair=True, confirms=1), # calm Sure → 2/2, EXIT to developing
        T("Sci", "repair_trivial", "REPAIR", repair=True, confirms=1), # trivial ✓ → held, confirms reset
        T("Mat", "fastwrong", "developing"),                        # FW → box unchanged
        T("Mat", "slowwrong", "developing"),                        # SW → demote to shaky
        T("Mat", "cw_first", "developing"),                         # 1st CW → shaky
        T("His", "cw_second", "shaky", last_badge="CW"),            # 2nd CW → REPAIR
        T("His", "promote_solid", "developing"),                    # spaced calm Sure → solid
        T("His", "think_dev", "shaky"),                             # Think so → developing
        T("Eng", "plain_hold", "developing"),                       # speed plain ✓ → hold (no solid)
        T("Eng", "solid_maintain", "solid"),                        # ✓ → maintain
        T("Eng", "fresh_skip", "untested", last=None, seen=0),      # skip → benched, times_seen stays 0
    ]}}}
json.dump(state, open(f"{tmp}/work/state.json", "w"), indent=2)

# --- plan: map slot ids → those topics ---
slots = [
    ("S1", "speed", "Sci", "repair_confirm"), ("T1", "steady", "Sci", "repair_confirm"),
    ("S2", "steady", "Sci", "repair_exit"),   ("S3", "steady", "Sci", "repair_trivial"),
    ("S4", "steady", "Mat", "fastwrong"),     ("S5", "steady", "Mat", "slowwrong"),
    ("S6", "steady", "Mat", "cw_first"),      ("S7", "steady", "His", "cw_second"),
    ("T2", "steady", "His", "promote_solid"), ("T3", "steady", "His", "think_dev"),
    ("S8", "speed", "Eng", "plain_hold"),     ("S9", "speed", "Eng", "solid_maintain"),
    ("S10", "speed", "Eng", "fresh_skip"),
]
json.dump({"student": "s1", "set_date": "2026-08-06", "tag": "X1", "day": "THU",
           "slots": [{"slot": i, "phase": p, "subject": s, "intent": "x", "topic": t} for i, p, s, t in slots]},
          open(f"{tmp}/plans/s1/2026-08-06.json", "w"), indent=2)

def Q(id, subj, phase, ok, conf=None, secs=12.0, skip=False):
    return {"id": id, "subject": subj, "phase": phase, "skipped": skip, "ok": ok, "picked": "x",
            "confidence": conf, "secs": secs, "pts": 0, "chars": None, "text": None}

# steady median will be ~12s (many 12s answers) → 3s=trivial, 4s=fast, 25s=slow
run = {"student": "s1", "name": "s1", "tag": "X1", "day": "THU", "set_date": "2026-08-06",
       "run_date": "2026-08-06", "ts": "2026-08-06T08:00:00+00:00", "ts_raw": "2026-08-06T08:00:00+00:00",
       "attempt": 1, "shell": "3.0", "score": 0, "max_score": 0, "speed": {}, "steady": {}, "teach": {},
       "shell_flags": {"skips": ["S10"], "confidentWrong": ["S6", "S7"], "slowWrong": ["S5"],
                       "fastWrong": ["S4"], "luckyGuess": []},
       "timing": {}, "is_test": False, "canonical": True, "canonical_caveat": False,
       "questions": [
           Q("S1", "Sci", "speed", True, None, 12), Q("T1", "Sci", "steady", True, "Sure", 14),  # repair_confirm
           Q("S2", "Sci", "steady", True, "Sure", 14),      # repair_exit
           Q("S3", "Sci", "steady", True, "Think so", 3),   # repair_trivial (trivial)
           Q("S4", "Mat", "steady", False, "Think so", 4),  # fastwrong
           Q("S5", "Mat", "steady", False, "Think so", 25), # slowwrong
           Q("S6", "Mat", "steady", False, "Sure", 14),     # cw_first
           Q("S7", "His", "steady", False, "Sure", 14),     # cw_second
           Q("T2", "His", "steady", True, "Sure", 14),      # promote_solid (spaced)
           Q("T3", "His", "steady", True, "Think so", 14),  # think_dev
           Q("S8", "Eng", "speed", True, None, 12),         # plain_hold
           Q("S9", "Eng", "speed", True, None, 12),         # solid_maintain
           Q("S10", "Eng", "speed", None, None, 12, skip=True),  # fresh_skip
           Q("F1", "Mat", "steady", True, None, 12), Q("F2", "Mat", "steady", True, None, 12),  # padding for baseline
       ]}
json.dump({"runs": [run]}, open(f"{tmp}/work/runs.json", "w"), indent=2)

_, lines, _ = sw.process(tmp, dry_run=False)
after = json.load(open(f"{tmp}/work/state.json"))
tp = {t["topic"]: t for t in after["students"]["s1"]["topics"]}

cases = [
    ("repair_confirm held at 1/2", tp["repair_confirm"]["state"] == "REPAIR" and tp["repair_confirm"]["repair_confirms"] == 1),
    ("repair_exit → developing, repair off", tp["repair_exit"]["state"] == "developing" and not tp["repair_exit"]["repair"]),
    ("repair_trivial held, confirms reset to 0", tp["repair_trivial"]["state"] == "REPAIR" and tp["repair_trivial"]["repair_confirms"] == 0),
    ("fast-wrong box UNCHANGED (developing)", tp["fastwrong"]["state"] == "developing"),
    ("slow-wrong demote developing→shaky", tp["slowwrong"]["state"] == "shaky"),
    ("1st CW → shaky", tp["cw_first"]["state"] == "shaky"),
    ("2nd CW → REPAIR", tp["cw_second"]["state"] == "REPAIR" and tp["cw_second"]["repair"]),
    ("spaced calm Sure developing→solid", tp["promote_solid"]["state"] == "solid"),
    ("Think so shaky→developing", tp["think_dev"]["state"] == "developing"),
    ("speed plain ✓ holds developing (no solid)", tp["plain_hold"]["state"] == "developing"),
    ("solid maintained", tp["solid_maintain"]["state"] == "solid"),
    ("fresh-skip untested, times_seen 0", tp["fresh_skip"]["state"] == "untested" and tp["fresh_skip"]["times_seen"] == 0),
    ("human note preserved", tp["repair_confirm"]["note"] == "HUMAN NOTE for repair_confirm"),
]
ok = True
print("state-writer regression:")
for d, c in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {d}"); ok = ok and c
import shutil; shutil.rmtree(tmp)
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
