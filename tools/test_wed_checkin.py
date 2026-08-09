#!/usr/bin/env python3
"""
test_wed_checkin.py — regression tests for the Wednesday check-in (pure logic,
no network, no files). Run: python3 tools/test_wed_checkin.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wed_checkin import (week_windows, window_stats, momentum, fact_card,  # noqa: E402
                         pick_ask, pick_gap, validate, fallback_render,
                         plan_cards, render)
from datetime import date  # noqa: E402

FAILS = []


def check(name, cond, note=""):
    print(f"  {'\u2713' if cond else '\u2717 FAIL'} {name}" + (f" \u2014 {note}" if note and not cond else ""))
    if not cond:
        FAILS.append(name)


def run(student, rd, score=1000, mx=2000, name="Kid"):
    return {"student": student, "run_date": rd, "score": score,
            "max_score": mx, "name": name}


def topic(t, state="developing", repair=False, lt="2026-08-04", seen=3, note=""):
    return {"topic": t, "subject": "Maths", "state": state, "repair": repair,
            "last_tested": lt, "times_seen": seen, "note": note}


WED = date(2026, 8, 12)     # a real Wednesday
NOW = lambda d, c: {"days_done": d, "possible": 2, "comp": c}  # noqa: E731

print("— windows (like-for-like: Mon–Tue vs LAST week's Mon–Tue)")
this_d, prev_d = week_windows(WED)
check("this week = Mon+Tue", this_d == ["2026-08-10", "2026-08-11"])
check("prev week = last Mon+Tue", prev_d == ["2026-08-03", "2026-08-04"])

print("— window stats (best-of-replays; ratio computed, printed nowhere)")
rs = [run("y8", "2026-08-10", 1000, 2000), run("y8", "2026-08-10", 1600, 2000),
      run("y8", "2026-08-11", 1400, 2000), run("y9", "2026-08-10", 500, 2000)]
st = window_stats(rs, "y8", this_d)
check("two days counted, best replay wins",
      st["days_done"] == 2 and abs(st["comp"] - 0.75) < 1e-9)
check("empty window -> zero days, comp None",
      window_stats(rs, "y8", prev_d) == {"days_done": 0, "possible": 2, "comp": None})

print("— the week-word engine (one engine; Friday samples the same thresholds)")
check("no prior + runs -> solid/none",
      momentum(NOW(2, .7), NOW(0, None)) == {"word": "solid", "direction": "none"})
check("no prior + nothing -> quiet/none",
      momentum(NOW(0, None), NOW(0, None)) == {"word": "quiet", "direction": "none"})
check("fewer days than last week -> quiet/down",
      momentum(NOW(1, .8), NOW(2, .7)) == {"word": "quiet", "direction": "down"})
check("QUIET OUTRANKS SLOWER (fewer days + comp drop is still quiet)",
      momentum(NOW(1, .4), NOW(2, .8))["word"] == "quiet")
check("same days, comp dropped past delta -> slower/down",
      momentum(NOW(2, .55), NOW(2, .75)) == {"word": "slower", "direction": "down"})
check("extra day -> strong/up",
      momentum(NOW(2, .7), NOW(1, .7)) == {"word": "strong", "direction": "up"})
check("comp jumped past delta -> strong/up",
      momentum(NOW(2, .85), NOW(2, .65)) == {"word": "strong", "direction": "up"})
check("level -> solid/flat",
      momentum(NOW(2, .72), NOW(2, .70)) == {"word": "solid", "direction": "flat"})

print("— pickers (one ask, one gap, ranked)")
ts = [topic("A", "developing", lt="2026-08-10"),
      topic("B", "solid", lt="2026-08-04"),
      topic("C", "shaky", lt="2026-08-11"),
      topic("D", "shaky", repair=True, lt="2026-08-01"),
      topic("E", "untested", lt="")]
check("ask: solid beats fresher developing", pick_ask(ts)["topic"] == "B")
check("gap: repair-flag beats fresher shaky", pick_gap(ts)["topic"] == "D")
check("gap falls back to shaky when no repair",
      pick_gap([t for t in ts if not t["repair"]])["topic"] == "C")
check("no candidates -> None", pick_ask([topic("X", "untested")]) is None
      and pick_gap([topic("X", "solid")]) is None)

print("— the outgoing-text law (validator; applies to AI and fallback alike)")
GOOD = ("Steady week for Kid so far, tracking level with last week. One thing "
        "worth five minutes: he's still circling 'fractions' — get him to talk "
        "you through it. It's the one Friday's wrap will centre on.")
check("approved-shape text passes", validate(GOOD, "Kid") == (True, "ok"))
check("digits rejected", validate(GOOD.replace("five", "5"), "Kid")[1] == "digits")
check("percent rejected", validate(GOOD.replace("level", "80% level"), "Kid")[1] in ("digits", "ratio-chars"))
check("slash rejected", validate(GOOD.replace("level", "l/evel"), "Kid")[1] == "ratio-chars")
check("bare 'behind' rejected",
      validate(GOOD.replace("level with", "behind"), "Kid")[1] == "bare-behind")
check("'a bit behind' allowed",
      validate(GOOD.replace("tracking level with", "a bit behind"), "Kid")[0])
check("missing Friday rejected",
      validate(GOOD.replace("Friday's", "the"), "Kid")[1] == "no-friday")
check("missing name rejected", validate(GOOD, "Zoe")[1] == "no-name")
check("banned vocab rejected",
      validate(GOOD.replace("circling", "missing"), "Kid")[1].startswith("banned-word"))

print("— fallback voices are legal by construction (every word x direction)")
cases = [("strong", "up"), ("solid", "flat"), ("solid", "none"),
         ("quiet", "down"), ("quiet", "none"), ("slower", "down")]
for word, direction in cases:
    for gap in (None, {"topic": "fractions", "subject": "Maths", "colour": ""}):
        card = {"code": "y8", "name": "Kid",
                "momentum": {"word": word, "direction": direction,
                             "attendance": "kept both days so far"},
                "ask": {"topic": "the water cycle", "subject": "Science", "colour": ""},
                "gap": gap}
        ok, why = validate(fallback_render(card), "Kid")
        check(f"fallback legal: {word}/{direction} gap={'y' if gap else 'n'}", ok, why)

print("— display-topic sanitizer (real ledger names must become law-legal)")
from wed_checkin import display_topic  # noqa: E402
check("parenthetical + fraction + slash tail cut",
      display_topic("Triangle area (\u00bdbh) / area recall") == "Triangle area")
check("intrinsic slash becomes hyphen, kept when short",
      display_topic("Push/pull factors") == "Push-pull factors")
check("long slash chain cut at first segment",
      display_topic("R&J author/context/facts") == "R&J author")
check("parenthetical dropped cleanly",
      display_topic("Variables (independent/dependent/controlled)") == "Variables")
check("degenerate name falls back to subject",
      display_topic("(\u00bd)", "Maths") == "Maths")
raw = topic("Triangle area (\u00bdbh) / area recall", "shaky", lt="2026-08-11")
card_slash = {"code": "y9", "name": "Kid",
              "momentum": {"word": "solid", "direction": "flat",
                           "attendance": "kept both days so far"},
              "ask": None,
              "gap": {"topic": display_topic(raw["topic"]), "subject": "Maths",
                      "colour": ""}}
check("fallback with a slashy raw topic is still legal",
      validate(fallback_render(card_slash), "Kid")[0])

print("— render with AI off routes to fallback")
card = {"code": "y8", "name": "Kid",
        "momentum": {"word": "solid", "direction": "flat",
                     "attendance": "kept both days so far"},
        "ask": None, "gap": None}
text, src = render(card, api_key=None, use_ai=False)
check("source marked fallback(ai-off)", src == "fallback(ai-off)")
check("rendered text passes the law", validate(text, "Kid")[0])

print("— plan (per-kid cards, idempotency, log hygiene)")
state = {"students": {"y8": {"topics": ts}, "y9": {"topics": []}}}
runs2 = [run("y8", "2026-08-10", 1500, 2000, name="Kid"),
         run("y9", "2026-08-11", 900, 2000, name="Pal")]
cards, log = plan_cards(state, runs2, {"sent": {}}, WED, ("y8", "y9"))
check("one card per active kid", [c["code"] for c in cards] == ["y8", "y9"])
cards2, log2 = plan_cards(state, runs2, {"sent": {"y8": ["2026-08-12"]}}, WED, ("y8", "y9"))
check("cursor makes a kid a no-op", [c["code"] for c in cards2] == ["y9"])
joined = " ".join(log + log2)
check("log carries no names", "Kid" not in joined and "Pal" not in joined)
check("log carries codes + word only", "word=" in joined and "[y8]" in joined)

print()
if FAILS:
    print(f"\u2717 {len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("\u2713 all wed-checkin tests green")
