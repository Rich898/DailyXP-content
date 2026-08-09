#!/usr/bin/env python3
"""
test_wed_checkin.py — regression tests for the merged Wednesday check-in
(pure logic, no network, no files). Run: python3 tools/test_wed_checkin.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wed_checkin import (week_windows, window_stats, momentum, fact_card,  # noqa: E402
                         attendance_phrase, pick_ask, pick_gap, validate,
                         fallback_render, render_body, plan, is_cutoff,
                         display_topic, TONIGHT_NOTE)
from datetime import date, datetime  # noqa: E402

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


def card(word="solid", direction="flat", att="kept both days so far",
         tonight="in", ask="the water cycle", gap=None, name="Kid"):
    return {"code": "y8", "name": name,
            "momentum": {"word": word, "direction": direction, "attendance": att},
            "tonight": tonight,
            "ask": {"topic": ask, "subject": "Science", "colour": ""} if ask else None,
            "gap": {"topic": gap, "subject": "Maths", "colour": ""} if gap else None}


WED = date(2026, 8, 12)     # a real Wednesday
NOW = lambda d, c, p=2: {"days_done": d, "possible": p, "comp": c}  # noqa: E731

print("— the cutoff clock (the eight-twenty-five poll is the cutoff)")
check("before cutoff", not is_cutoff(datetime(2026, 8, 12, 18, 25)))
check("at/after cutoff", is_cutoff(datetime(2026, 8, 12, 20, 25)))

print("— windows, like for like (Mon–Wed when tonight's in; Mon–Tue at cutoff)")
t3, p3 = week_windows(WED, include_today=True)
t2, p2 = week_windows(WED, include_today=False)
check("tonight in -> three days", t3 == ["2026-08-10", "2026-08-11", "2026-08-12"])
check("prev window matches length (three)", p3 == ["2026-08-03", "2026-08-04", "2026-08-05"])
check("tonight out -> two days", t2 == ["2026-08-10", "2026-08-11"])
check("prev window matches length (two)", p2 == ["2026-08-03", "2026-08-04"])

print("— window stats (best-of-replays; ratio computed, printed nowhere)")
rs = [run("y8", "2026-08-10", 1000, 2000), run("y8", "2026-08-10", 1600, 2000),
      run("y8", "2026-08-11", 1400, 2000), run("y9", "2026-08-10", 500, 2000)]
st = window_stats(rs, "y8", t2)
check("two days counted, best replay wins",
      st["days_done"] == 2 and abs(st["comp"] - 0.75) < 1e-9)
check("empty window -> zero days, comp None",
      window_stats(rs, "y8", p2) == {"days_done": 0, "possible": 2, "comp": None})

print("— attendance in words (never digits)")
check("full three-day week", attendance_phrase(NOW(3, .7, 3)) == "kept every day so far")
check("full two-day week", attendance_phrase(NOW(2, .7, 2)) == "kept both days so far")
check("two of three", attendance_phrase(NOW(2, .7, 3)) == "two runs in so far")
check("one run", attendance_phrase(NOW(1, .7, 3)) == "one run in so far")
check("none yet", attendance_phrase(NOW(0, None)) == "no runs in yet this week")

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
      momentum(NOW(3, .7, 3), NOW(2, .7, 3)) == {"word": "strong", "direction": "up"})
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

print("— display-topic sanitizer (real ledger names must become law-legal)")
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

print("— the outgoing-text law (validator; body only — the soundbyte line rides above)")
GOOD = ("Midweek read: steady week for Kid, tracking level with last week. One "
        "thing worth five minutes: he's still circling 'fractions' — get him to "
        "talk you through it. It's the one Friday's wrap will centre on.")
check("approved-shape body passes", validate(GOOD, "Kid") == (True, "ok"))
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

print("— the tonight-status law (status plus open door, never judgment)")
ni = fallback_render(card(tonight="not-in-yet"))
check("not-in-yet carries the status line", TONIGHT_NOTE in ni)
check("not-in-yet body is legal", validate(ni, "Kid")[0])
check("'in' never mentions tonight's run status",
      TONIGHT_NOTE not in fallback_render(card(tonight="in")))
check("'unverified' (our gap) never mentions tonight",
      TONIGHT_NOTE not in fallback_render(card(tonight="unverified")))

print("— fallback voices are legal by construction (word x direction x tonight x gap)")
for word, direction in [("strong", "up"), ("solid", "flat"), ("solid", "none"),
                        ("quiet", "down"), ("quiet", "none"), ("slower", "down")]:
    for tonight in ("in", "not-in-yet"):
        for gap in (None, "fractions"):
            c = card(word, direction, "kept both days so far", tonight, gap=gap)
            ok, why = validate(fallback_render(c), "Kid")
            check(f"fallback legal: {word}/{direction} tonight={tonight} gap={'y' if gap else 'n'}",
                  ok, why)

print("— render_body with AI off routes to fallback")
text, src = render_body(card(), api_key=None, use_ai=False)
check("source marked fallback(ai-off)", src == "fallback(ai-off)")
check("rendered body passes the law", validate(text, "Kid")[0])

print("— plan (shapes, soundbyte coordination, idempotency, log hygiene)")
state = {"students": {"a": {"topics": ts}, "b": {"topics": ts}, "c": {"topics": []}}}
runs2 = [run("a", "2026-08-10", 1500, 2000, name="Kid"),
         run("a", "2026-08-12", 1800, 2000, name="Kid"),
         run("b", "2026-08-12", 900, 2000, name="Pal"),
         run("c", "2026-08-11", 700, 2000, name="Moe")]
jobs, log = plan(state, runs2, {"sent": {}}, {"sent": {"b": ["2026-08-12"]}},
                 WED, ("a", "b", "c"), cutoff=False)
shapes = {j["code"]: (j["sb_facts"] is not None, j["mark_sb"], j["card"]["tonight"]) for j in jobs}
check("run in + soundbyte unsent -> MERGED, marks sb cursor",
      shapes.get("a") == (True, True, "in"))
check("run in + soundbyte already sent -> body-only, sb untouched",
      shapes.get("b") == (False, False, "in"))
check("no run before cutoff -> waiting (no job)", "c" not in shapes)
check("merged momentum includes tonight (three-day window)",
      next(j for j in jobs if j["code"] == "a")["card"]["momentum"]["attendance"]
      in ("two runs in so far", "kept every day so far"))
jobs2, log2 = plan(state, runs2, {"sent": {}}, {"sent": {}}, WED, ("c",), cutoff=True)
check("no run at cutoff -> job with tonight unresolved (main resolves published)",
      len(jobs2) == 1 and jobs2[0]["card"]["tonight"] is None and not jobs2[0]["mark_sb"])
check("cutoff momentum is the two-day like-for-like",
      jobs2[0]["card"]["momentum"]["attendance"] == "one run in so far")
jobs3, _ = plan(state, runs2, {"sent": {"a": ["2026-08-12"]}}, {"sent": {}},
                WED, ("a",), cutoff=True)
check("check-in cursor makes a kid a no-op", jobs3 == [])
joined = " ".join(log + log2)
check("log carries no names", all(n not in joined for n in ("Kid", "Pal", "Moe")))
check("log carries codes + shapes", "merged" in joined and "[a]" in joined)

print()
if FAILS:
    print(f"\u2717 {len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("\u2713 all wed-checkin tests green")
