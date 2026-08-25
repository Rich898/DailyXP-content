#!/usr/bin/env python3
"""test_planner_scrub.py — locks Scrub It's planner stage (stage 3, ratified 25 Aug 2026).

The invariants:
  1. T1 GATE — on a standard day, t1's speed round ends with a Scrub It block
     (swipe → recall → scrub, the order approved in the staging play-through);
     y8 and y9 plans contain NO scrub anywhere, in any field. Same rollout law
     as every mechanic before it.
  2. IDENTITY — scrub slots carry the ratified block object (Scrub It · #B18CFF ·
     ⌫ · "Rub out the wrong answers with your finger") and mode:'scrub';
     type stays MC (the ledger never learns the delivery mode).
  3. CONTAINMENT — the reversed directive deals no scrub; blocks stay coherent.
  4. CHAIN — a real t1 plan flows through build_user (mode reaches the model),
     assemble, and validate_set with ZERO errors: planner output is composable
     and publishable as-is (the LLM's language stubbed, everything else real).

Runnable in CI: `python3 tools/test_planner_scrub.py` (exit 0 = all pass). No names/scores.
"""
import os, sys, tempfile, json
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import planner
from compose import build_user, assemble
from validate import validate_set

fails = []
def check(name, ok, d=""):
    print(("  ok  " if ok else "  FAIL") + " " + name + (f"  [{d}]" if (d and not ok) else ""))
    if not ok:
        fails.append(name)

# 8 subjects, like a real seat — the planner's global per-subject cap means a
# 4-subject pool can never fill 12/6/1 (learned building this test).
SUBJECTS = ["Maths", "Science", "English", "History", "Geography", "French", "Music", "PDHPE"]
def fixtures(student):
    state = {"students": {student: {"status": "ACTIVE", "topics": [
        {"subject": SUBJECTS[i % 8], "topic": f"{SUBJECTS[i % 8]} Topic {i}", "state": "shaky",
         "repair": False, "last_tested": "2026-08-01", "times_seen": 2, "note": ""}
        for i in range(1, 33)
    ]}}}
    targets = {"students": {student: {"subjects": {
        s: {"topics": [{"topic": f"{s} Topic {i}", "status": "live"}
                       for i in range(1, 33) if SUBJECTS[i % 8] == s]}
        for s in SUBJECTS
    }}}}
    return state, targets

def plan_for(student, directive="standard"):
    state, targets = fixtures(student)
    return planner.plan_set(student, "2026-08-25", "TUE", "T5", targets, state, directive)

RAT = {"label": "Scrub It", "hue": "#B18CFF", "icon": "\u232b",
       "sub": "Rub out the wrong answers with your finger", "cta": "Start scrubbing \u2192"}

# ---- 1+2: t1 gets the block, with the ratified identity ---------------------
p = plan_for("t1")
speed = [x for x in p["slots"] if x["phase"] == "speed"]
scrubs = [x for x in speed if x.get("mech") == "scrub"]
check("t1 standard day deals a Scrub It block", len(scrubs) == 3, f"got {len(scrubs)}")
check("scrub is the FINAL speed block (approved staging order)",
      [x.get("mech") for x in speed[-3:]] == ["scrub"] * 3 and speed[0].get("mech") == "swipe")
check("swipe 4 / recall / scrub 3 partition",
      [x.get("mech") for x in speed[:4]] == ["swipe"] * 4 and
      all(x.get("mech") == "recall" for x in speed[4:-3]))
check("every scrub slot carries mode:'scrub'", all(x.get("mode") == "scrub" for x in scrubs))
check("scrub slots stay MC — no 'type' (ledger never learns the mode)",
      all("type" not in x for x in scrubs))
check("ratified block identity on every scrub slot",
      all(x.get("block") == RAT for x in scrubs))
check("blocks stay coherent (no mechanic mixing inside a block run)",
      all(a.get("mech") == b.get("mech") or True for a, b in zip(speed, speed[1:])) and
      [x.get("mech") for x in speed] == ["swipe"] * 4 + ["recall"] * (len(speed) - 7) + ["scrub"] * 3)
check("steady mechanics untouched (numeric/order/text by subject)",
      all(x.get("mech") in ("numeric", "order", "text", None) for x in p["slots"] if x["phase"] == "steady"))

# ---- 1: the boys get NOTHING -------------------------------------------------
for kid in ("y8", "y9"):
    pk = plan_for(kid)
    flat = json.dumps(pk)
    check(f"{kid} plan contains no scrub in any field", "scrub" not in flat.lower(), flat[:80])

# ---- 3: reversed directive unchanged ----------------------------------------
pr = plan_for("t1", "reversed")
check("reversed-directive day deals NO scrub (contained reversed block preserved)",
      "scrub" not in json.dumps(pr).lower())

# ---- 4: full deterministic chain — plan -> compose -> validate ---------------
user = build_user(p, set())
check("build_user passes mode:'scrub' to the model for t1", '"mode": "scrub"' in user)

def synth_fill(slots):
    """Valid synthetic language for every slot — the LLM stubbed, all structure real."""
    filled = {}
    for i, s in enumerate(slots):
        sid, mech, typ = s["slot"], s.get("mech"), s.get("type")
        if s["phase"] == "teach":
            filled[sid] = {"prompt": f"Explain sample concept {i} in your own words."}
        elif typ == "swipe":
            filled[sid] = {"prompt": f"Sample statement {i}", "left": "True", "right": "False",
                           "answer": "True" if i % 2 else "False", "why": f"Because of fact {i}."}
        elif typ == "numeric":
            filled[sid] = {"prompt": f"What is {i} + {i}?", "answer": i + i, "calc": False,
                           "pre": "", "post": "", "why": f"{i}+{i}."}
        elif typ == "order":
            filled[sid] = {"prompt": f"Order the sample steps for item {i}",
                           "sequence": [f"Step A{i}", f"Step B{i}", f"Step C{i}", f"Step D{i}"],
                           "top": "First", "bot": "Last", "why": "A then B then C then D."}
        elif typ == "text":
            filled[sid] = {"prompt": f"Name the sample term for item {i}",
                           "accept": [f"term{i}"], "why": f"It is term{i}."}
        else:  # MC — recall and scrub alike (scrub content obeys the ratified gates)
            filled[sid] = {"prompt": f"Which sample option belongs to set {i}?",
                           "options": [f"Optiona{i}", f"Optionb{i}", f"Optionc{i}", f"Optiond{i}"],
                           "answer": f"Optionb{i}", "why": f"Optionb{i} is the one."}
    return filled

candidate = assemble(p, synth_fill(p["slots"]))
qs = {q["id"]: q for q in candidate["questions"]}
sq = [q for q in candidate["questions"] if q.get("mode") == "scrub"]
check("assembled set carries 3 scrub questions with block + mode", len(sq) == 3 and
      all(q.get("block") == RAT and "type" not in q for q in sq))
e, w = validate_set(candidate, tempfile.mkdtemp())
check("planner output validates for publish with ZERO errors", e == [], str(e[:3]))

print()
print("ALL PASS \u2713" if not fails else f"FAILURES \u2717 {fails}")
sys.exit(0 if not fails else 1)
