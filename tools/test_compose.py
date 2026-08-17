#!/usr/bin/env python3
"""Integration test for the compose→validate chain across question types (v3.1).

Proves assemble() threads `type` (from the plan) and the right answer fields (options for mc,
accept for typed) from the model output, and that the assembled set PASSES validate_set — i.e.
a real quiz carrying numeric/text/cloze questions survives the publish gate.
Runnable in CI: `python3 tools/test_compose.py` (exit 0 = all pass). No names/scores.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose import assemble
from validate import validate_set

# A plan with one slot of each supported type + a teach slot.
plan = {
    "student": "y9", "date": "2026-08-20", "day": "THU", "tag": "T1",
    "slots": [
        {"slot": "S1", "phase": "speed", "subject": "Maths", "intent": "fresh", "topic": "Times tables", "fresh": True, "type": "numeric"},
        {"slot": "T1", "phase": "steady", "subject": "Geography", "intent": "confirm", "topic": "Capitals", "fresh": True},  # no type → mc
        {"slot": "T2", "phase": "steady", "subject": "History", "intent": "confirm", "topic": "Treaties", "fresh": True, "type": "text"},
        {"slot": "T3", "phase": "steady", "subject": "History", "intent": "confirm", "topic": "Dates", "fresh": False, "type": "cloze", "throwback": True},
        {"slot": "T4", "phase": "steady", "subject": "History", "intent": "confirm", "topic": "WWI to WWII timeline", "fresh": True, "type": "order"},
        {"slot": "TB", "phase": "teach", "subject": "Science", "intent": "confirm", "topic": "Respiration", "fresh": True},
    ],
    "encore": [
        {"slot": "E1", "phase": "steady", "subject": "Geography", "intent": "confirm", "topic": "Capitals of Asia", "fresh": True},  # mc bonus
        {"slot": "E2", "phase": "steady", "subject": "Maths", "intent": "confirm", "topic": "Squares", "fresh": True, "type": "numeric"},
    ],
}

# What the model would return (language only), keyed by slot id.
filled = {
    "S1": {"prompt": "What is 7 × 8?", "answer": "56", "accept": ["56"], "why": "56 — seven eights."},
    "T1": {"prompt": "Capital of France?", "options": ["Paris", "Lyon", "Nice", "Metz"], "answer": "Paris", "why": "Paris."},
    "T2": {"prompt": "Clause blaming Germany for WWI?", "answer": "War Guilt Clause", "accept": ["war guilt", "guilt clause"], "why": "Article 231."},
    "T3": {"prompt": "The Treaty of ______ was signed in 1919.", "answer": "Versailles", "accept": ["versaille"], "why": "Versailles."},
    "T4": {"prompt": "Order these (earliest first).", "sequence": ["WWI", "Versailles", "Depression", "WWII"], "why": "chronology."},
    "TB": {"prompt": "Explain respiration in your own words."},
    "E1": {"prompt": "Capital of Japan?", "options": ["Tokyo", "Osaka", "Kyoto", "Nara"], "answer": "Tokyo", "why": "Tokyo."},
    "E2": {"prompt": "What is 9 × 9?", "answer": "81", "accept": ["81"], "why": "81."},
}

s = assemble(plan, filled)
q = {x["id"]: x for x in s["questions"]}

cases = []
def check(name, cond, detail=""):
    cases.append((name, cond, detail))
    if not cond:
        print(f"  FAIL {name}  [{detail}]")

# assemble threaded the right shape per type
check("numeric slot → type numeric, accept carried, no options", q["S1"].get("type") == "numeric" and q["S1"].get("accept") == ["56"] and "options" not in q["S1"], str(q["S1"]))
check("numeric answer carried from model", q["S1"].get("answer") == "56")
check("mc slot → type stays implicit, options carried", "type" not in q["T1"] and q["T1"].get("options") == ["Paris", "Lyon", "Nice", "Metz"], str(q["T1"]))
check("text slot → type text, accept carried", q["T2"].get("type") == "text" and q["T2"].get("accept") == ["war guilt", "guilt clause"], str(q["T2"]))
check("cloze throwback → type cloze, fresh forced false, throwback true", q["T3"].get("type") == "cloze" and q["T3"].get("fresh") is False and q["T3"].get("throwback") is True, str(q["T3"]))
check("order slot → type order, sequence carried, no answer/options", q["T4"].get("type") == "order" and q["T4"].get("sequence") == ["WWI", "Versailles", "Depression", "WWII"] and "answer" not in q["T4"] and "options" not in q["T4"], str(q["T4"]))

# encore block assembled + typed correctly
enc = {x["id"]: x for x in s.get("encore", [])}
check("encore block present with 2 questions", len(s.get("encore", [])) == 2, str(list(enc)))
check("encore E1 is mc with options", enc.get("E1", {}).get("options") == ["Tokyo", "Osaka", "Kyoto", "Nara"], str(enc.get("E1")))
check("encore E2 keeps numeric type + accept", enc.get("E2", {}).get("type") == "numeric" and enc.get("E2", {}).get("accept") == ["81"], str(enc.get("E2")))
check("fresh carried from plan on mc slot", q["T1"].get("fresh") is True)
check("teach slot has no answer/options/type", "answer" not in q["TB"] and "options" not in q["TB"] and "type" not in q["TB"], str(q["TB"]))

# THE integration point: the assembled set passes the publish gate
e, w = validate_set(s)
check("assembled mixed-type set PASSES validate (no errors)", e == [], str(e))

ok = all(c for _, c, _ in cases)
print("compose→validate integration:")
for n, c, _ in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}")
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
