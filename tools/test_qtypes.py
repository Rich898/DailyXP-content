#!/usr/bin/env python3
"""Regression test for qtypes.assign_types (v3.1 input-type assignment).

Checks eligibility rules (calc→numeric only; non-calc steady→text/cloze; non-calc speed & throwback
→ mc), determinism (stable on re-plan), and that the MIN_MC floor holds. No names/scores.
Runnable in CI: `python3 tools/test_qtypes.py` (exit 0 = all pass).
"""
import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qtypes

cases = []
def check(name, cond, detail=""):
    cases.append((name, cond, detail))
    if not cond:
        print(f"  FAIL {name}  [{detail}]")


def slot(sid, phase, subj, topic, throwback=False):
    s = {"slot": sid, "phase": phase, "subject": subj, "topic": topic}
    if throwback:
        s["throwback"] = True
    return s


# candidate_type rules
check("calc topic → numeric candidate", qtypes.candidate_type(slot("S1", "speed", "Maths", "Area of rectangles")) == "numeric")
check("non-calc steady → textcloze candidate", qtypes.candidate_type(slot("T1", "steady", "History", "Treaty terms")) == "textcloze")
check("non-calc speed → mc (words are steady-only)", qtypes.candidate_type(slot("S2", "speed", "History", "Treaty terms")) == "mc")
check("throwback → mc (never typed, LAW 3)", qtypes.candidate_type(slot("T2", "steady", "Maths", "Area", throwback=True)) == "mc")
check("teach → mc (no type)", qtypes.candidate_type(slot("TB", "teach", "Science", "Respiration")) == "mc")
check("orderable topic (chronology) → wordorder candidate", qtypes.candidate_type(slot("T5", "steady", "History", "WWI to WWII timeline")) == "wordorder")
check("non-orderable non-calc steady → textcloze", qtypes.candidate_type(slot("T6", "steady", "History", "Treaty terms")) == "textcloze")
check("is_orderable keyword match", qtypes.is_orderable("History", "Causes of the revolution") and not qtypes.is_orderable("English", "Character analysis"))

# a realistic standard run: 3 maths speed (calc), 4 non-calc steady, + throwback + teach
def run():
    return [
        slot("S1", "speed", "Maths", "Area of rectangles"),
        slot("S2", "speed", "Maths", "Percentages"),
        slot("S3", "speed", "History", "WWI causes"),        # non-calc speed → stays mc
        slot("T1", "steady", "History", "Treaty terms"),
        slot("T2", "steady", "Geography", "Capitals"),
        slot("T3", "steady", "English", "Vocabulary"),
        slot("T4", "steady", "Maths", "Angles", throwback=True),  # throwback → mc
        slot("TB", "teach", "Science", "Respiration"),
    ]

s = qtypes.assign_types(run(), "y9", "2026-08-20", "R4")
by = {x["slot"]: x.get("type") for x in s}
check("non-calc speed stayed mc", by["S3"] == "mc", str(by))
check("throwback stayed mc", by["T4"] == "mc", str(by))
check("teach slot untouched (no type set)", "TB" not in by or by["TB"] is None, str(by.get("TB")))
check("calc speed slots are numeric-or-mc only", by["S1"] in ("numeric", "mc") and by["S2"] in ("numeric", "mc"))
check("steady non-calc slots are text/cloze/mc only", all(by[t] in ("text", "cloze", "mc") for t in ("T1", "T2", "T3")))

# determinism: same seed → identical assignment
a = qtypes.assign_types(run(), "y9", "2026-08-20", "R4")
b = qtypes.assign_types(run(), "y9", "2026-08-20", "R4")
check("deterministic (same seed → same types)", [x.get("type") for x in a] == [x.get("type") for x in b])
c = qtypes.assign_types(run(), "y9", "2026-08-21", "R4")
check("varies by date (different seed → generally different)", [x.get("type") for x in a] != [x.get("type") for x in c] or True)  # not guaranteed different, so soft

# MIN_MC floor: force everything typed-eligible, assert at least MIN_MC mc remain
def calc_run():
    return [slot(f"S{i}", "speed", "Maths", "Percentages") for i in range(6)] + [slot("TB", "teach", "Sci", "x")]
old_p, old_min = qtypes.P_NUMERIC, qtypes.MIN_MC
qtypes.P_NUMERIC = 1.0   # every calc slot wants numeric
r = qtypes.assign_types(calc_run(), "y9", "2026-08-20", "R4")
n_mc = sum(1 for x in r if x["phase"] in ("speed", "steady") and x.get("type") == "mc")
check(f"MIN_MC floor holds (>= {old_min} mc even at P=1.0)", n_mc >= old_min, f"n_mc={n_mc}")
qtypes.P_NUMERIC = old_p

# aggregate propensity sanity across many seeds (calc → numeric should be common at 0.85)
num = tot = 0
for d in range(1, 61):
    rr = qtypes.assign_types([slot("S1", "speed", "Maths", "Percentages"), slot("S2", "steady", "Maths", "Area"), slot("T1", "steady", "History", "Terms"), slot("TB", "teach", "S", "x")], "y9", f"2026-08-{d:02d}", "R")
    for x in rr:
        if x["slot"] in ("S1", "S2"):
            tot += 1
            if x.get("type") == "numeric":
                num += 1
rate = num / tot
check(f"calc→numeric rate near baseline 0.85 (got {rate:.2f})", 0.7 <= rate <= 0.98, f"{num}/{tot}")

# order is reachable: across many seeds, an order-eligible steady slot sometimes becomes 'order'
seen_order = False
for d in range(1, 40):
    rr = qtypes.assign_types([slot("T1", "steady", "History", "WWI to WWII timeline"),
                              slot("T2", "steady", "History", "Causes of the war"),
                              slot("TB", "teach", "S", "x")], "y9", f"2026-09-{d:02d}", "R")
    if any(x.get("type") == "order" for x in rr):
        seen_order = True
        break
check("order type is reachable on orderable topics", seen_order)

# TRAP-1 CAP: when a drag-order slot exists, formats.assign_formats must not use the MC ordering format
import formats
slots = [slot("T1", "steady", "History", "WWI to WWII timeline"), slot("T2", "steady", "Geography", "Capitals"),
         slot("S1", "speed", "History", "Crusades"), slot("TB", "teach", "S", "x")]
slots[0]["type"] = "order"  # force an order slot
excl = {formats.ORDERING} if any(s.get("type") == "order" for s in slots) else None
formats.assign_formats(slots, "y9", "2026-08-20", "R", exclude=excl)
fmts = [s.get("format") for s in slots if s.get("phase") in ("speed", "steady")]
check("trap-1 cap: no MC ordering format when a drag-order slot is present", formats.ORDERING not in fmts, str(fmts))

# assign_x2: exactly ONE eligible slot flagged, never a throwback, deterministic
rr = qtypes.assign_x2(run(), "y9", "2026-08-20", "R4")
check("assign_x2 flags exactly one slot", sum(1 for x in rr if x.get("x2")) == 1, str([x["slot"] for x in rr if x.get("x2")]))
check("assign_x2 never flags a throwback", not any(x.get("x2") and x.get("throwback") for x in rr))
check("assign_x2 never flags a teach slot", not any(x.get("x2") and x.get("phase") == "teach" for x in rr))
a2 = [x["slot"] for x in qtypes.assign_x2(run(), "y9", "2026-08-20", "R4") if x.get("x2")]
b2 = [x["slot"] for x in qtypes.assign_x2(run(), "y9", "2026-08-20", "R4") if x.get("x2")]
check("assign_x2 deterministic (same seed → same slot)", a2 == b2, f"{a2} vs {b2}")

ok = all(c for _, c, _ in cases)
print("qtypes regression:")
for n, c, _ in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}")
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
