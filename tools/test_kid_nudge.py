#!/usr/bin/env python3
"""test_kid_nudge.py — pure-logic tests for the 4pm nudge decision."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kid_nudge import decide  # noqa: E402
from datetime import date  # noqa: E402

FAILS = []
def check(name, cond):
    print(f"  {'✓' if cond else '✗ FAIL'} {name}")
    if not cond: FAILS.append(name)

MON, WED, FRI, SAT = date(2026,8,10), date(2026,8,12), date(2026,8,14), date(2026,8,15)
def live(d, placeholder=False):
    s = {"student":"y8","date":d,"day":"","tag":"T","title":"DailyXP"}
    if placeholder: s["status"]="placeholder"
    return s

print("— verify-before-text")
send,_,text = decide(live("2026-08-10"), MON)
check("today's live set -> send, standard flavour", send and text == "XP Daily is up 👊")
send,r,_ = decide(live("2026-08-09"), MON)
check("stale live set -> suppressed (never text a promise not kept)", not send and "not today" in r)
send,_,_ = decide(live("2026-08-10", placeholder=True), MON)
check("placeholder (frozen/held) -> suppressed", not send)
send,_,_ = decide("garbage", MON)
check("unreadable live set -> suppressed", not send)

print("— weekly skeleton flavour")
_,_,t = decide(live("2026-08-12"), WED)
check("Wednesday -> blitz flavour", "BLITZ" in t)
_,_,t = decide(live("2026-08-14"), FRI)
check("Friday -> boss flavour", "BOSS" in t)
send,_,_ = decide(live("2026-08-15"), SAT)
check("weekend -> no nudge", not send)

print()
if FAILS:
    print(f"✗ {len(FAILS)} FAILED: {FAILS}"); sys.exit(1)
print("✓ all kid-nudge tests green")
