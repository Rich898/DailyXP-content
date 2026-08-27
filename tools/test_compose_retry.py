#!/usr/bin/env python3
"""compose retry hardening (HARDENING-BRIEF item 5) — deterministic, no network.

Locks the two fixes for the 26 Aug t1 scrub compose-fail (retries exhausted on the
answer-length tell + a repeat-prompt collision):
  * a scrub-bearing plan gets a LARGER retry budget than a plain plan;
  * the retry message is TARGETED — it names the failing slot with its specific fix
    (length tell / repeat) and tells the model to keep the OTHER slots verbatim,
    instead of dumping raw errors and asking for a blind full regenerate (the churn
    that broke a good slot while fixing a bad one).
Plus end-to-end: a length-tell on attempt 1 is recovered on attempt 2 (call_api
stubbed), proving the loop converges.

Runnable in CI: `python3 tools/test_compose_retry.py` (exit 0 = all pass). No names/scores.
"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compose
from compose import _err_slot, _retry_message, compose_set

cases = []
def check(n, c, d=""):
    cases.append((n, bool(c), d))


# ---- _err_slot: slot-scoped vs set-level -----------------------------------
check("_err_slot pulls the slot id from a slot-scoped error",
      _err_slot("[SC1] scrub answer-length tell: ...") == "SC1")
check("_err_slot returns None for a set-level error",
      _err_slot("missing top-level 'date'") is None)

# ---- _retry_message: pointed, per-slot, keep-the-rest ----------------------
m = _retry_message([
    "[SC1] scrub answer-length tell: the correct option is the sole longest by a clear margin",
    "[S9] prompt REPEATS one this student has seen: 'Capital of France?'"])
check("retry msg tells the model to keep the other slots verbatim", "keep every OTHER slot" in m)
check("retry msg gives the ratified length-tell fix, scoped to the scrub slot",
      "ANSWER-LENGTH TELL" in m and "slot SC1" in m)
check("retry msg gives a repeat-specific fix, scoped to the repeat slot",
      "GENUINELY DIFFERENT" in m and "slot S9" in m)
check("retry msg surfaces set-level errors too",
      "Set-level" in _retry_message(["exactly ONE teach question required (got 2) ..."]))


# ---- budget: scrub-bearing plans get more attempts before giving up --------
def _plan(scrub):
    slots = [{"slot": "S1", "phase": "speed", "subject": "Sci", "topic": "T", "intent": "reinforce", "fresh": True},
             {"slot": "TB", "phase": "teach", "subject": "Sci", "topic": "T", "intent": "depth"}]
    if scrub:
        slots[0]["mode"] = "scrub"
    return {"student": "t1", "tag": "T5", "day": "TUE", "date": "2026-08-25", "slots": slots}


EMPTY = tempfile.mkdtemp()                 # no history — repeat gate stays quiet
os.environ["ANTHROPIC_API_KEY"] = "test-key"   # presence check only; call_api is stubbed

# an always-invalid fill (S1 has no 'why') → never validates → exhausts the budget
BAD = {"S1": {"prompt": "Q1?", "options": ["a", "b", "c", "d"], "answer": "a"},
       "TB": {"prompt": "Explain."}}


class Counter:
    def __init__(self, payload): self.n = 0; self.payload = payload
    def __call__(self, system, user, model, key):
        self.n += 1
        return json.dumps(self.payload)


_orig = compose.call_api
try:
    c_plain = Counter(BAD); compose.call_api = c_plain
    compose_set(_plan(scrub=False), history_dir=EMPTY)
    c_scrub = Counter(BAD); compose.call_api = c_scrub
    compose_set(_plan(scrub=True), history_dir=EMPTY)

    check("plain plan uses 3 attempts (budget 2)", c_plain.n == 3, f"got {c_plain.n}")
    check("scrub plan uses 5 attempts (budget 4)", c_scrub.n == 5, f"got {c_scrub.n}")

    # ---- end-to-end: a length tell on attempt 1 is recovered on attempt 2 ----
    TELL = {"S1": {"prompt": "Which organelle carries out photosynthesis?",
                   "options": ["The chloroplast organelle found in green plant cells",
                               "Nucleus", "Ribosome", "Vacuole"],
                   "answer": "The chloroplast organelle found in green plant cells",
                   "why": "It holds the chlorophyll."},
            "TB": {"prompt": "Explain photosynthesis in your own words."}}
    GOOD = {"S1": {"prompt": "Which organelle carries out photosynthesis?",
                   "options": ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"],
                   "answer": "Chloroplast", "why": "It holds the chlorophyll."},
            "TB": {"prompt": "Explain photosynthesis in your own words."}}
    seq = [json.dumps(TELL), json.dumps(GOOD)]
    compose.call_api = lambda system, user, model, key: seq.pop(0)
    result, _ = compose_set(_plan(scrub=True), history_dir=EMPTY)
    check("length-tell on attempt 1 is recovered on retry (loop converges)", result is not None)
    check("recovered set carries the fixed, non-tell options",
          bool(result) and any(q.get("options") == ["Chloroplast", "Mitochondrion", "Nucleus", "Ribosome"]
                               for q in result["questions"]))
finally:
    compose.call_api = _orig

ok = all(c for _, c, _ in cases)
print("compose retry hardening:")
for n, c, d in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"  [{d}]" if (d and not c) else ""))
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
