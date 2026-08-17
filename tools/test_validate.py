#!/usr/bin/env python3
"""Regression test for validate_set — focus: the fresh-flag rule (v3.1 item 8, workaround retired).

Runnable in CI: `python3 tools/test_validate.py` (exit 0 = all pass). No names/scores.
"""
import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate_set


def base():
    """A minimal set that validates clean (shape (1,0,1) is only a WARN, never an ERROR)."""
    return {
        "student": "y9", "date": "2026-08-20", "day": "THU", "tag": "T1",
        "questions": [
            {"id": "S1", "phase": "speed", "subject": "Maths", "prompt": "What is 2 + 2?",
             "options": ["3", "4"], "answer": "4", "why": "It is four.", "fresh": True},
            {"id": "TB", "phase": "teach", "subject": "Science", "prompt": "Explain photosynthesis in your own words."},
        ],
    }


def steady(fresh, throwback=False):
    q = {"id": "T2", "phase": "steady", "subject": "History", "prompt": "Which treaty ended WWI?",
         "options": ["Versailles", "Trianon"], "answer": "Versailles", "why": "The Treaty of Versailles."}
    if fresh is not None:
        q["fresh"] = fresh
    if throwback:
        q["throwback"] = True
    return q


def typed(qtype, **over):
    q = {"id": "TQ", "phase": "steady", "subject": "Maths", "type": qtype, "prompt": "Area of a 5×6 rectangle?",
         "answer": "30 cm²", "accept": ["30", "30 cm2"], "why": "30 cm².", "fresh": True}
    q.update(over)
    return q


cases = []
def check(name, cond, detail=""):
    cases.append((name, cond, detail))
    if not cond:
        print(f"  FAIL {name}  [{detail}]")


# 1. baseline (fresh:true) validates clean
e, w = validate_set(base())
check("baseline fresh:true → no errors", e == [], str(e))

# 2. THE CHANGE: fresh:false on an established topic now PASSES (previously an error)
s = base(); s["questions"][0]["fresh"] = False
e, w = validate_set(s)
check("fresh:false now valid (workaround retired)", e == [], str(e))

# 3. throwback with fresh:false passes (the legitimate carve-out preserved)
s = base(); s["questions"].insert(1, steady(fresh=False, throwback=True))
e, w = validate_set(s)
check("throwback fresh:false → no errors", e == [], str(e))

# 4. throwback with fresh:true is REJECTED (a revisit is never newly introduced)
s = base(); s["questions"].insert(1, steady(fresh=True, throwback=True))
e, w = validate_set(s)
check("throwback fresh:true → error", any("throwback must be fresh:false" in x for x in e), str(e))

# 5. missing fresh on speed/steady is REJECTED (flag must be present & boolean)
s = base(); del s["questions"][0]["fresh"]
e, w = validate_set(s)
check("absent fresh → error", any("boolean 'fresh'" in x for x in e), str(e))

# 6. non-boolean fresh (e.g. a truthy string) is REJECTED
s = base(); s["questions"][0]["fresh"] = "yes"
e, w = validate_set(s)
check("non-boolean fresh → error", any("boolean 'fresh'" in x for x in e), str(e))

# --- v3.1 typed question types ---
# 10. a valid numeric question passes with NO options (previously impossible — options were required)
s = base(); s["questions"].insert(1, typed("numeric"))
e, w = validate_set(s)
check("numeric question valid without options", e == [], str(e))

# 11. numeric answer with no digit is rejected
s = base(); s["questions"].insert(1, typed("numeric", answer="thirty"))
e, w = validate_set(s)
check("numeric answer with no digit → error", any("no digit" in x for x in e), str(e))

# 12. typed question missing answer is rejected
s = base(); s["questions"].insert(1, typed("text", answer=None))
e, w = validate_set(s)
check("typed question missing answer → error", any("non-empty string 'answer'" in x for x in e), str(e))

# 13. accept must be a list of strings
s = base(); s["questions"].insert(1, typed("text", answer="War Guilt Clause", accept="war guilt"))
e, w = validate_set(s)
check("non-list accept → error", any("'accept' must be a list" in x for x in e), str(e))

# 14. a valid cloze passes; a cloze without a blank only WARNS (never blocks)
s = base(); s["questions"].insert(1, typed("cloze", prompt="The Treaty of ______ ended WWI.", answer="Versailles", accept=["versaille"]))
e, w = validate_set(s)
check("valid cloze passes", e == [], str(e))
s = base(); s["questions"].insert(1, typed("cloze", prompt="No blank here", answer="Versailles"))
e, w = validate_set(s)
check("cloze without a blank warns, not errors", e == [] and any("no blank" in x for x in w), f"e={e} w={w}")

# 15. a typed question carrying options warns (options ignored), not errors
s = base(); s["questions"].insert(1, typed("numeric", options=["30", "40"]))
e, w = validate_set(s)
check("typed question with options → warn only", e == [] and any("ignored" in x for x in w), f"e={e} w={w}")

# 16. unknown question type is rejected
s = base(); s["questions"].insert(1, typed("dragdrop"))
e, w = validate_set(s)
check("unknown question type → error", any("unknown question type" in x for x in e), str(e))

# 17. mc with fewer than 2 options is rejected (regression on the mc branch)
s = base(); s["questions"][0]["options"] = ["only one"]
e, w = validate_set(s)
check("mc with <2 options → error", any("needs an options list" in x for x in e), str(e))

# 18. a valid order question passes with a sequence and no options/answer
s = base(); s["questions"].insert(1, {"id": "OQ", "phase": "steady", "subject": "History", "type": "order",
    "prompt": "Order these events (earliest first).", "sequence": ["WWI", "Versailles", "Depression"], "why": "chronology.", "fresh": True})
e, w = validate_set(s)
check("order question valid (sequence, no options)", e == [], str(e))

# 19. order with fewer than 2 items rejected
s = base(); s["questions"].insert(1, {"id": "OQ", "phase": "steady", "subject": "History", "type": "order",
    "prompt": "x", "sequence": ["A"], "why": "y", "fresh": True})
e, w = validate_set(s)
check("order sequence <2 → error", any("sequence" in x and ">=2" in x for x in e), str(e))

# 20. order with duplicate items rejected (can't sequence unambiguously)
s = base(); s["questions"].insert(1, {"id": "OQ", "phase": "steady", "subject": "History", "type": "order",
    "prompt": "x", "sequence": ["A", "A", "B"], "why": "y", "fresh": True})
e, w = validate_set(s)
check("order duplicate items → error", any("duplicate" in x for x in e), str(e))

# 21. one hidden double-XP (x2) question is fine
s = base(); s["questions"][0]["x2"] = True
e, w = validate_set(s)
check("one x2 question valid", e == [], str(e))

# 22. two x2 questions rejected (one per run)
s = base(); s["questions"][0]["x2"] = True
q2 = steady(fresh=True); q2["x2"] = True
s["questions"].insert(1, q2)
e, w = validate_set(s)
check("two x2 questions → error", any("double-XP" in x for x in e), str(e))

# --- regression: unrelated checks still fire (proves the edit didn't loosen the gate) ---
# 7. answer not among options
s = base(); s["questions"][0]["answer"] = "5"
e, w = validate_set(s)
check("regression: answer-not-in-options still errors", any("not one of options" in x for x in e), str(e))

# 8. exactly one teach still enforced (two teach → error)
s = base(); s["questions"].append({"id": "TB2", "phase": "teach", "subject": "Eng", "prompt": "Explain again."})
e, w = validate_set(s)
check("regression: two teach questions still errors", any("exactly ONE teach" in x for x in e), str(e))

# 9. non-standard shape is a WARN, not an ERROR (must not block)
e, w = validate_set(base())
check("regression: non-standard shape warns, not errors", e == [] and any("non-standard" in x for x in w), f"e={e} w={w}")

ok = all(c for _, c, _ in cases)
print("validate regression:")
for n, c, _ in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}")
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
