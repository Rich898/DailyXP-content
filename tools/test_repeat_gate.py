#!/usr/bin/env python3
"""No-repeat gate: teach-back exemption (HARDENING-BRIEF item 5 follow-up, 27 Aug 2026).

The 26/27 Aug t1 compose-fails were partly a TEACH-BACK prompt flagged as a repeat.
But a teach-back ("explain X in your own words") is a reasoning prompt — re-asking one
is good spaced practice, not a recall repeat — so it must NOT block. Recall prompts
(speed/steady) must STILL block on repeat. Deterministic, no network.

Runnable in CI: `python3 tools/test_repeat_gate.py` (exit 0 = all pass). No names/scores.
"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from validate import validate_set

cases = []
def check(n, c, d=""):
    cases.append((n, bool(c), d))

# history with one seen recall prompt AND one seen teach-back for t1
HIST = tempfile.mkdtemp()
os.makedirs(os.path.join(HIST, "t1"))
SEEN_RECALL = "What is the capital of Japan?"
SEEN_TEACH = "Explain why memorising vocab is not enough to order food."
json.dump({"questions": [{"prompt": SEEN_RECALL}, {"prompt": SEEN_TEACH}]},
          open(os.path.join(HIST, "t1", "2026-08-01_T1.json"), "w"))


def a_set(*qs):
    return {"student": "t1", "date": "2026-08-27", "day": "THU", "tag": "T5", "questions": list(qs)}

def teach(prompt):
    return {"id": "TB", "phase": "teach", "subject": "Science", "prompt": prompt}

def speed(prompt):
    return {"id": "S1", "phase": "speed", "subject": "Science", "prompt": prompt,
            "options": ["a", "b", "c", "d"], "answer": "a", "why": "because", "fresh": True}

def errs(*qs):
    e, _ = validate_set(a_set(*qs), HIST)
    return e


# teach-back that repeats a seen teach-back → EXEMPT (no repeat error)
check("teach-back repeat is EXEMPT (no repeat error)",
      not any("REPEATS" in x for x in errs(teach(SEEN_TEACH))),
      str(errs(teach(SEEN_TEACH))))

# speed/recall prompt that repeats a seen recall prompt → STILL blocks
check("speed/recall repeat STILL blocks",
      any("REPEATS" in x for x in errs(speed(SEEN_RECALL), teach("Explain a brand-new unseen idea."))),
      str(errs(speed(SEEN_RECALL), teach("Explain a brand-new unseen idea."))))

# a fresh (unseen) teach-back → fine
check("fresh teach-back is fine",
      not any("REPEATS" in x for x in errs(teach("Explain a totally fresh concept never seen."))))

ok = all(c for _, c, _ in cases)
print("no-repeat gate (teach-back exemption):")
for n, c, d in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}" + (f"  [{d}]" if (d and not c) else ""))
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
