#!/usr/bin/env python3
"""
test_soundbyte.py — regression tests for the evening soundbyte (pure logic,
no network, no files). Run: python3 tools/test_soundbyte.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from soundbyte import (current_school_streak, facts_for, render_line, plan,  # noqa: E402
                       band_for, season_total)

FAILS = []


def check(name, cond, note=""):
    tick = "\u2713" if cond else "\u2717 FAIL"
    suffix = f" \u2014 {note}" if note and not cond else ""
    print(f"  {tick} {name}{suffix}")
    if not cond:
        FAILS.append(name)


def run(student, rd, score=1000, name="Kid", mx=None):
    return {"student": student, "run_date": rd, "score": score, "name": name,
            "max_score": mx}


# 2026-08-03 Mon ... 07 Fri, 10 Mon (weekend 08/09)
from datetime import date  # noqa: E402
MON, TUE, WED, THU, FRI, MON2 = ("2026-08-03", "2026-08-04", "2026-08-05",
                                 "2026-08-06", "2026-08-07", "2026-08-10")

print("— streak semantics (school-days; weekends transparent)")
check("contiguous Mon–Wed = 3",
      current_school_streak({MON, TUE, WED}, date(2026, 8, 5)) == 3)
check("Fri -> Mon survives the weekend (=2)",
      current_school_streak({FRI, MON2}, date(2026, 8, 10)) == 2)
check("missed school-day breaks it (Mon,Wed from Wed = 1)",
      current_school_streak({MON, WED}, date(2026, 8, 5)) == 1)
check("no run today = 0 (streak is 'ending today')",
      current_school_streak({MON, TUE}, date(2026, 8, 5)) == 0)
check("single day = 1", current_school_streak({MON}, date(2026, 8, 3)) == 1)

print("— facts")
runs = [run("y8", MON, 900), run("y8", TUE, 2178), run("y8", TUE, 1500),
        run("y9", TUE, 3000)]
f = facts_for(runs, "y8", TUE)
check("best-of-replays points", f["pts"] == 2178)
check("streak counted", f["streak"] == 2)
check("no run today -> None", facts_for(runs, "y8", WED) is None)

print("— the line (no-ammunition edges)")
F2 = {"student": "y8", "name": "Kid", "pts": 2178, "band": "strong",
      "total": 5078, "streak": 2}
line2 = render_line(F2, TUE)
line1 = render_line(dict(F2, streak=1), TUE)
check("streak >= 2 is mentioned", "2-day streak" in line2)
check("streak == 1 is OMITTED (never whisper 'the streak broke')",
      "streak" not in line1)
check("points are formatted with a comma", "2,178" in line1)
check("deterministic: same date+facts -> same text",
      render_line(F2, WED) == render_line(F2, WED))
check("no ratios anywhere in the line", "/" not in line2)

print("— plan (per-kid dispatch, idempotency, silence, log hygiene)")
KIDS = ("y8", "y9", "t1")
sends, log = plan(runs, {"sent": {}}, TUE, KIDS)
check("one send PER kid with a run (never a shared blast)",
      [x["code"] for x in sends] == ["y8", "y9"])
check("each send routes to that kid's own parent seat (log names parents:<code>)",
      any("parents:y8" in l for l in log) and any("parents:y9" in l for l in log))
cur = {"sent": {"y8": [TUE], "y9": [TUE]}}
sends2, log2 = plan(runs, cur, TUE, KIDS)
check("second poll same evening is a no-op", sends2 == [])
sends3, log3 = plan(runs, {"sent": {}}, WED, KIDS)
check("no runs today -> silence (no 'not done' text exists)", sends3 == [])
joined = " ".join(log + log2 + log3)
check("safe log lines carry no names", "Kid" not in joined)
check("safe log lines carry no scores", "2178" not in joined and "2,178" not in joined)

# one kid done, one not: only the done kid queued; the other stays open
sends4, _ = plan([run("y8", THU, 800)], {"sent": {}}, THU, KIDS)
check("one-done -> one send, others untouched",
      [x["code"] for x in sends4] == ["y8"])
# ...the late finisher is caught by a later poll; the earlier kid, once
# cursor'd (as main() does on success), does not repeat
sends5, _ = plan([run("y8", THU, 800), run("y9", THU, 900)],
                 {"sent": {"y8": [THU]}}, THU, KIDS)
check("late finisher caught by next poll (y9 only, no y8 repeat)",
      [x["code"] for x in sends5] == ["y9"])

print("— honest tone bands (ratio computed here, printed nowhere)")
check("huge at 85%", band_for(2550, 3000) == "huge")
check("strong at 70%", band_for(2100, 3000) == "strong")
check("solid at 50%", band_for(1500, 3000) == "solid")
check("hard below 50%", band_for(1200, 3000) == "hard")
check("just under a cut rounds DOWN a band", band_for(2549, 3000) == "strong")
check("tiny set never bands (warm-ups can't carry a tone word)",
      band_for(770, 830) is None)
check("missing max never bands", band_for(770, None) is None)

print("— season bank (best-per-day since Term start; seed for manual week)")
sr = [run("y8", "2026-07-20", 999),                 # pre-season: excluded
      run("y8", MON, 900), run("y8", TUE, 2178), run("y8", TUE, 1500),
      run("y9", TUE, 5000)]                          # other kid: excluded
mine = [r for r in sr if r["student"] == "y8"]
check("best-per-day summed; pre-season + other kids excluded",
      season_total(mine, TUE) == 900 + 2178)
check("approx seed (pre-webhook week) adds on top",
      season_total(mine, TUE, seed=3000) == 900 + 2178 + 3000)
fx = facts_for([run("y8", TUE, 2178, mx=2780), run("y8", MON, 900, mx=2780)],
               "y8", TUE)
check("facts carry the band of the best run's OWN max (78% -> strong)",
      fx["band"] == "strong" and fx["total"] == 900 + 2178)

print("— the line, per band (three beats: did it · +XP · verdict closer)")
base = {"student": "y8", "name": "Kid", "pts": 990, "band": "hard",
        "total": 7740, "streak": 3}
hard = render_line(base, TUE)
huge = render_line(dict(base, band="huge", pts=2410, total=9160), TUE)
strong = render_line(dict(base, band="strong", pts=2178, total=5078), TUE)
solid = render_line(dict(base, band="solid", pts=1739, total=3917), TUE)
bare = render_line(dict(base, band=None), TUE)
allr = huge + strong + solid + hard + bare
check("NO running totals in the daily layer (totals belong to Friday)",
      "banked" not in allr and "7,740" not in allr)
check("NO percentage anywhere in the daily layer (legend owns it)",
      "%" not in allr)
check("NO ratios anywhere", "/" not in allr)
check("verdict CLOSES the line, after the XP",
      huge.index("+2,410") < huge.lower().index("flew")
      and hard.index("+990") < hard.lower().index("bit back" if "bit back" in hard.lower() else "tough"))
check("floor band: difficulty belongs to the SET, not the kid",
      ("set bit back" in hard.lower()) or ("tough set" in hard.lower()))
check("floor band carries no misses vocab", "miss" not in hard.lower())
check("top band reads as flight, not a grade", "flew" in huge.lower())
check("mid band is effort language", "shift" in solid.lower())
check("band None (tiny set): three beats minus the verdict",
      "+990" in bare and all(w not in bare.lower()
                             for w in ("flew", "shift", "night's work",
                                       "bit back", "tough")))
check("all bands keep the streak law",
      "3-day streak" in hard and "3-day streak" in huge)

print()
if FAILS:
    print(f"\u2717 {len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("\u2713 all soundbyte tests green")
