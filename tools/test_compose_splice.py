#!/usr/bin/env python3
"""compose slot-splicing (HARDENING-BRIEF item 5 follow-up) — deterministic, no network.

The reliable fix for the deep-history t1 compose-fail: on a validation failure, recompose
ONLY the failing slot(s) and stitch them back, leaving the good questions byte-for-byte
untouched — instead of regenerating the whole set and re-rolling the dice.

Locks (call_api stubbed, so the model's replies are scripted):
  * a single bad slot is recomposed via a FOCUSED message (only that slot);
  * the OTHER slots survive UNCHANGED into the published set — the no-churn property;
  * DAILYXP_WHOLE_SET_RECOMPOSE=1 falls back to the old whole-set regenerate.

Runnable in CI: `python3 tools/test_compose_splice.py` (exit 0 = all pass). No names/scores.
"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose
from compose import compose_set

cases = []
def check(n, c, d=""):
    cases.append((n, bool(c), d))

EMPTY = tempfile.mkdtemp()                 # no history — repeat gate quiet
os.environ["ANTHROPIC_API_KEY"] = "test-key"

PLAN = {"student": "t1", "tag": "T5", "day": "TUE", "date": "2026-08-25", "slots": [
    {"slot": "S1", "phase": "speed", "subject": "Science", "topic": "Cells", "intent": "reinforce",
     "mode": "scrub", "fresh": True},
    {"slot": "S2", "phase": "speed", "subject": "Geography", "topic": "Capitals", "intent": "reinforce",
     "fresh": True},
    {"slot": "TB", "phase": "teach", "subject": "Science", "topic": "Cells", "intent": "depth"}]}

# first whole-set reply: S1 has a scrub answer-length tell (correct = sole longest); S2, TB clean
FIRST = {
    "S1": {"prompt": "Which organelle carries out photosynthesis?",
           "options": ["The chloroplast organelle found in green plant cells", "Nucleus", "Ribosome", "Vacuole"],
           "answer": "The chloroplast organelle found in green plant cells", "why": "It holds the chlorophyll."},
    "S2": {"prompt": "Capital of France?", "options": ["Paris", "Lyon", "Nice", "Lille"],
           "answer": "Paris", "why": "Paris is the capital of France."},
    "TB": {"prompt": "Explain photosynthesis in your own words."}}
# focused reply for the slot-splice path: ONLY S1, now with even-length options (no tell)
SPLICE_S1 = {"S1": {"prompt": "Which organelle carries out photosynthesis?",
                    "options": ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"],
                    "answer": "Chloroplast", "why": "It holds the chlorophyll."}}

_orig = compose.call_api

# ---- slot-splice path -------------------------------------------------------
sent = []
seq = [json.dumps(FIRST), json.dumps(SPLICE_S1)]
def stub(system, user, model, key):
    sent.append(user)
    return seq.pop(0)
compose.call_api = stub
try:
    result, _ = compose_set(PLAN, history_dir=EMPTY)
finally:
    compose.call_api = _orig

q = {x["id"]: x for x in (result["questions"] if result else [])}
check("slice converges to a valid set", result is not None)
check("the failing scrub slot S1 was rebuilt (no longer the sole-longest)",
      bool(result) and q["S1"]["options"] == ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"])
check("the GOOD slot S2 survived UNCHANGED — no churn",
      bool(result) and q["S2"]["options"] == ["Paris", "Lyon", "Nice", "Lille"]
      and q["S2"]["prompt"] == "Capital of France?")
check("the teach slot TB survived UNCHANGED",
      bool(result) and q["TB"]["prompt"] == "Explain photosynthesis in your own words.")
check("the retry was FOCUSED — asked for S1 only, not S2",
      len(sent) == 2 and '"slotId": "S1"' in sent[1]
      and '"slotId": "S2"' not in sent[1] and "rewrite_only_these_slots" in sent[1])

# ---- kill switch: whole-set fallback ----------------------------------------
WHOLE_FIX = {**FIRST, "S1": SPLICE_S1["S1"]}     # a full set with S1 fixed
sent2 = []
seq2 = [json.dumps(FIRST), json.dumps(WHOLE_FIX)]
def stub2(system, user, model, key):
    sent2.append(user)
    return seq2.pop(0)
os.environ["DAILYXP_WHOLE_SET_RECOMPOSE"] = "1"
compose.call_api = stub2
try:
    result2, _ = compose_set(PLAN, history_dir=EMPTY)
finally:
    compose.call_api = _orig
    del os.environ["DAILYXP_WHOLE_SET_RECOMPOSE"]

check("kill switch still converges", result2 is not None)
check("kill switch retry is WHOLE-set (asks for all slots incl. S2)",
      len(sent2) == 2 and '"slotId": "S2"' in sent2[1] and "rewrite_only_these_slots" not in sent2[1])

ok = all(c for _, c, _ in cases)
print("compose slot-splicing:")
for n, c, d in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"  [{d}]" if (d and not c) else ""))
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
