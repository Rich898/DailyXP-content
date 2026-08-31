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
    s = {"student":"y8","date":d,"day":"","tag":"T","title":"XPDaily"}
    if placeholder: s["status"]="placeholder"
    return s

print("— verify-before-text")
send,_,text = decide(live("2026-08-10"), MON)
check("today's live set -> send, Monday voice",
      send and text == "New week on the board. XPDaily is up 👊")
send,r,_ = decide(live("2026-08-09"), MON)
check("stale live set -> suppressed (never text a promise not kept)", not send and "not today" in r)
send,_,_ = decide(live("2026-08-10", placeholder=True), MON)
check("placeholder (frozen/held) -> suppressed", not send)
send,_,_ = decide("garbage", MON)
check("unreadable live set -> suppressed", not send)

print("— one voice per school day (Rich's copy, 31 Aug 2026)")
_,_,t = decide(live("2026-08-12"), WED)
check("Wednesday -> its own voice (still a standard day, Blitz retired)",
      t == "Halfway. XPDaily is up 👊")
_,_,t = decide(live("2026-08-14"), FRI)
check("Friday -> battleground call", "BATTLEGROUND" in t)
week = [decide(live(f"2026-08-{10+i}"), date(2026, 8, 10+i))[2] for i in range(5)]
check("five school days, five different messages", len(set(week)) == 5)
check("every day still says XPDaily is up", all("XPDaily is up" in t for t in week))
# link append: when a play URL is given, it's on its own line at the end
_,_,_wl = decide(live("2026-08-10"), MON, "https://xpdaily-y8.netlify.app")
check("play link appended on its own line", _wl.endswith("\nhttps://xpdaily-y8.netlify.app"))
_,_,_nolink = decide(live("2026-08-10"), MON)
check("no link when none configured (unchanged)", "\n" not in (_nolink or ""))
send,_,_ = decide(live("2026-08-15"), SAT)
check("weekend -> no nudge", not send)

print()
if FAILS:
    print(f"✗ {len(FAILS)} FAILED: {FAILS}"); sys.exit(1)
print("✓ all kid-nudge tests green")
