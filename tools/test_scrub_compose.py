#!/usr/bin/env python3
"""Scrub It — composer + validator contract (pipeline stages 2+4, ratified 25 Aug 2026).

These land together by architecture: compose_set retries against validate_set, so the
validator's scrub gates ARE the composer's generation-time enforcement.

Locks:
  * validator ACCEPTS a rule-clean scrub question (mode:'scrub' on speed MC).
  * validator HARD-REJECTS every ratified breach: wrong option count, duplicate tiles,
    negative stems (not/except/false), all/none-of-the-above, answer-length tell
    (SEASONS LAW 1 sole-longest gate), scrub outside speed, scrub on a typed mechanic.
  * tap MC is UNTOUCHED — no scrub gate fires on a question without mode:'scrub'.
  * composer stamps mode:'scrub' from the PLAN slot only (structure is plan-owned);
    a model-emitted mode is never read.
  * full deterministic roundtrip: scrub plan + model language -> assemble -> validate clean.

Runnable in CI: `python3 tools/test_scrub_compose.py` (exit 0 = all pass). No names/scores.
"""
import os, sys, copy, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate_set
from compose import _build_q, build_user, assemble, SYSTEM

EMPTY_HIST = tempfile.mkdtemp()          # no history — repeat gate stays quiet
cases = []
def check(n, c, d=""):
    cases.append((n, bool(c), d))

def scrub_q(**over):
    q = {"id": "SC1", "phase": "speed", "subject": "Science", "mode": "scrub",
         "prompt": "Which organelle carries out photosynthesis?",
         "options": ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"],
         "answer": "Chloroplast", "why": "Chloroplasts hold the chlorophyll.", "fresh": True}
    q.update(over)
    return q

def a_set(*qs):
    return {"student": "t1", "date": "2026-08-25", "day": "TUE", "tag": "T5",
            "questions": list(qs) + [{"id": "TB", "phase": "teach", "subject": "Science",
                                      "prompt": "Explain photosynthesis in your own words."}]}

def errs(*qs):
    e, _ = validate_set(a_set(*qs), EMPTY_HIST)
    return e

# ---- validator: accepts clean scrub ----------------------------------------
check("clean scrub question validates", errs(scrub_q()) == [], str(errs(scrub_q())))

# ---- validator: hard gates ---------------------------------------------------
check("rejects 3 options", any("EXACTLY 4" in x for x in errs(scrub_q(options=["A", "B", "C"], answer="A"))))
check("rejects 5 options", any("EXACTLY 4" in x for x in errs(scrub_q(options=["A", "B", "C", "D", "E"], answer="A"))))
check("rejects duplicate tiles (case-insensitive)",
      any("unique" in x for x in errs(scrub_q(options=["Chloroplast", "chloroplast ", "Nucleus", "Ribosome"]))))
check("rejects negative stem 'NOT'",
      any("negative stem" in x for x in errs(scrub_q(prompt="Which of these is NOT an organelle?"))))
check("rejects negative stem 'except'",
      any("negative stem" in x for x in errs(scrub_q(prompt="All are organelles except which?"))))
check("rejects negative stem 'false'",
      any("negative stem" in x for x in errs(scrub_q(prompt="Which statement is false?"))))
check("rejects 'all of the above'",
      any("all/none-of-the-above" in x for x in errs(scrub_q(options=["Chloroplast", "Nucleus", "Ribosome", "All of the above"]))))
check("rejects 'None of these'",
      any("all/none-of-the-above" in x for x in errs(scrub_q(options=["Chloroplast", "Nucleus", "Ribosome", "None of these"]))))
check("rejects answer-length tell (sole longest, SEASONS LAW 1)",
      any("length tell" in x for x in errs(scrub_q(
          options=["The chloroplast organelle in plant cells", "Nucleus", "Ribosome", "Vacuole"],
          answer="The chloroplast organelle in plant cells"))))
check("rejects scrub outside speed",
      any("speed-round delivery mode" in x for x in errs(scrub_q(phase="steady"))))
check("rejects scrub on a typed mechanic",
      any("only valid on multiple-choice" in x for x in errs(scrub_q(
          type="swipe", left="True", right="False", answer="True", options=None))))

# ---- tap MC untouched --------------------------------------------------------
plain_neg = {"id": "S9", "phase": "speed", "subject": "Science",
             "prompt": "Which of these is NOT a mammal?", "options": ["Shark", "Whale"],
             "answer": "Shark", "why": "Sharks are fish.", "fresh": True}
check("tap MC without mode is untouched by scrub gates (2 options + negative stem still legal)",
      errs(plain_neg) == [], str(errs(plain_neg)))

# ---- composer: structure is plan-owned ---------------------------------------
slot = {"slot": "SC1", "phase": "speed", "subject": "Science", "topic": "Cells",
        "intent": "reinforce", "mode": "scrub", "fresh": True,
        "block": {"label": "Scrub It", "hue": "#B18CFF", "icon": "\u232b",
                  "sub": "Rub out the wrong answers with your finger", "cta": "Start scrubbing \u2192"}}
filled = {"SC1": {"prompt": "Which organelle carries out photosynthesis?",
                  "options": ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"],
                  "answer": "Chloroplast", "why": "Chloroplasts hold the chlorophyll."}}
q = _build_q(slot, filled)
check("composer stamps mode:'scrub' from the plan slot", q.get("mode") == "scrub")
check("composer carries the block identity from the plan", q.get("block", {}).get("label") == "Scrub It")

no_mode_slot = dict(slot); no_mode_slot.pop("mode")
sneaky = copy.deepcopy(filled); sneaky["SC1"]["mode"] = "scrub"   # model tries to set structure
q2 = _build_q(no_mode_slot, sneaky)
check("a model-emitted mode is IGNORED (structure is plan-owned)", "mode" not in q2)

row = None
plan = {"student": "t1", "tag": "T5", "day": "TUE", "date": "2026-08-25",
        "slots": [slot,
                  {"slot": "S9", "phase": "speed", "subject": "Geography", "topic": "Capitals",
                   "intent": "reinforce", "fresh": True},
                  {"slot": "TB", "phase": "teach", "subject": "Science", "topic": "Cells",
                   "intent": "depth"}]}
user = build_user(plan, set())
check("build_user passes the slot mode to the model", '"mode": "scrub"' in user)
check("SYSTEM prompt carries the scrub delivery-mode rules",
      'slot\'s "mode" is "scrub"' in SYSTEM and "negative stem" in SYSTEM and "EXACTLY four options" in SYSTEM)

# ---- full deterministic roundtrip: plan + language -> assemble -> validate ----
filled_all = dict(filled)
filled_all["S9"] = {"prompt": "Capital of France?", "options": ["Paris", "Lyon", "Nice", "Lille"],
                    "answer": "Paris", "why": "Paris."}
filled_all["TB"] = {"prompt": "Explain photosynthesis in your own words."}
candidate = assemble(plan, filled_all)
e, w = validate_set(candidate, EMPTY_HIST)
check("roundtrip: scrub plan + clean language validates for publish", e == [], str(e))
check("roundtrip: scrub question in the set carries mode + block",
      any(x.get("mode") == "scrub" and x.get("block", {}).get("hue") == "#B18CFF" for x in candidate["questions"]))

bad = copy.deepcopy(filled_all)
bad["SC1"]["prompt"] = "Which of these is NOT an organelle?"
e2, _ = validate_set(assemble(plan, bad), EMPTY_HIST)
check("roundtrip: a rule breach is caught (this is the retry loop's food)",
      any("negative stem" in x for x in e2))

ok = all(c for _, c, _ in cases)
print("scrub composer+validator contract:")
for n, c, d in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"  [{d}]" if (d and not c) else ""))
print("ALL PASS \u2713" if ok else "FAILURES \u2717")
sys.exit(0 if ok else 1)
