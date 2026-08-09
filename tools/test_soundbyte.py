#!/usr/bin/env python3
"""
test_soundbyte.py — regression tests for the evening soundbyte (pure logic,
no network, no files). Run: python3 tools/test_soundbyte.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from soundbyte import current_school_streak, facts_for, render_line, plan  # noqa: E402

FAILS = []


def check(name, cond, note=""):
    print(f"  {'\u2713' if cond else '\u2717 FAIL'} {name}" + (f" \u2014 {note}" if note and not cond else ""))
    if not cond:
        FAILS.append(name)


def run(student, rd, score=1000, name="Kid"):
    return {"student": student, "run_date": rd, "score": score, "name": name}


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
line2 = render_line({"student": "y8", "name": "Kid", "pts": 2178, "streak": 2}, TUE)
line1 = render_line({"student": "y8", "name": "Kid", "pts": 2178, "streak": 1}, TUE)
check("streak >= 2 is mentioned", "2-day streak" in line2)
check("streak == 1 is OMITTED (never whisper 'the streak broke')",
      "streak" not in line1)
check("points are formatted with a comma", "2,178" in line1)
check("deterministic: same date+facts -> same text",
      render_line({"student": "y8", "name": "Kid", "pts": 5, "streak": 3}, WED)
      == render_line({"student": "y8", "name": "Kid", "pts": 5, "streak": 3}, WED))
check("no ratios anywhere in the line", "/" not in line2)

print("— plan (idempotency, batching, silence, log hygiene)")
text, log, cur = plan(runs, {"sent": {}}, TUE)
check("both boys batched into ONE text (two lines)",
      text is not None and text.count("\n") == 1)
check("cursor advanced for both",
      TUE in cur["sent"].get("y8", []) and TUE in cur["sent"].get("y9", []))
text2, log2, _ = plan(runs, cur, TUE)
check("second poll same evening is a no-op", text2 is None)
text3, log3, cur3 = plan(runs, {"sent": {}}, WED)
check("no runs today -> silence (no 'not done' text exists)", text3 is None)
check("silent day advances no cursor", not cur3["sent"].get("y8") and not cur3["sent"].get("y9"))
joined = " ".join(log + log2 + log3)
check("safe log lines carry no names", "Kid" not in joined)
check("safe log lines carry no scores", "2178" not in joined and "2,178" not in joined)

# one boy done, one not: text sent for the done one only; the other stays open
text4, _, cur4 = plan([run("y8", THU, 800)], {"sent": {}}, THU)
check("one-done -> single line, other student's cursor stays open",
      text4 is not None and "\n" not in text4 and THU not in cur4["sent"].get("y9", []))
# ...and the late finisher gets picked up by a later poll
text5, _, _ = plan([run("y8", THU, 800), run("y9", THU, 900)], cur4, THU)
check("late finisher caught by next poll (y9 only, no y8 repeat)",
      text5 is not None and "\n" not in text5)

print()
if FAILS:
    print(f"\u2717 {len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("\u2713 all soundbyte tests green")
