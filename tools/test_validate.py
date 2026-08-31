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

# mc with fewer than 2 options is rejected (regression on the mc branch)
s = base(); s["questions"][0]["options"] = ["only one"]
e, w = validate_set(s)
check("mc with <2 options → error", any("needs an options list" in x for x in e), str(e))

# --- numeric 'frac' (decimal+fraction upgrade, 31 Aug 2026) ---
def numeric_q(**kw):
    q = {"id": "T3", "phase": "steady", "subject": "Maths", "prompt": "P(yellow) from 4 of 10?",
         "type": "numeric", "answer": 0.4, "calc": False, "pre": "", "post": "",
         "why": "4 out of 10.", "fresh": True}
    q.update(kw)
    return q

# 6a. numeric with a matching frac passes
s = base(); s["questions"].insert(1, numeric_q(frac="2/5"))
e, w = validate_set(s)
check("numeric frac 2/5 == 0.4 → clean", e == [], str(e))

# 6b. frac that doesn't equal the answer is REJECTED (review can't see numeric answers — §C7)
s = base(); s["questions"].insert(1, numeric_q(frac="3/8"))
e, w = validate_set(s)
check("numeric frac 3/8 != 0.4 → error", any("must equal the keyed value" in x for x in e), str(e))

# 6c. malformed frac is REJECTED
s = base(); s["questions"].insert(1, numeric_q(frac="two fifths"))
e, w = validate_set(s)
check("numeric malformed frac → error", any("must look like 'a/b'" in x for x in e), str(e))

# 6d. zero denominator is REJECTED
s = base(); s["questions"].insert(1, numeric_q(frac="4/0"))
e, w = validate_set(s)
check("numeric frac zero denominator → error", any("zero denominator" in x for x in e), str(e))

# 6e. no frac stays valid (optional field)
s = base(); s["questions"].insert(1, numeric_q())
e, w = validate_set(s)
check("numeric without frac → clean", e == [], str(e))

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
