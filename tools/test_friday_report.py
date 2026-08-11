#!/usr/bin/env python3
"""test_friday_report.py — the Friday report's load-bearing guarantees.

Locks the doctrine that is easy to break silently: the shared week-word engine,
week-1 baseline behaviour, the integrity gate on quotes, the overall-not-
per-subject trend rule, and the small-sample guards.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import friday_report as fr          # noqa: E402
import friday_sms as fsms           # noqa: E402
import report_stories as rst        # noqa: E402
import report_page as rpage         # noqa: E402


def t(name, cond):
    assert cond, f"FAIL: {name}"
    print(f"  [PASS] {name}")


def run(stu, d, qs, tag="X1", score=100, mx=100):
    return {"student": stu, "run_date": d, "set_date": d, "tag": tag,
            "score": score, "max_score": mx, "name": stu.upper(), "questions": qs}


def q(ok=True, phase="speed", subject="Maths", secs=8, conf=None, text=None, qid="S1"):
    o = {"id": qid, "ok": ok, "phase": phase, "subject": subject, "secs": secs}
    if conf:
        o["confidence"] = conf
    if text is not None:
        o["text"] = text
        o["chars"] = len(text)
    return o


print("shared week-word engine — Wednesday and Friday cannot diverge:")
import weekword  # noqa: E402
import wed_checkin as wc  # noqa: E402
t("Friday and Wednesday call the SAME momentum()", wc.momentum is weekword.momentum)
t("and the SAME window_stats()", wc.window_stats is weekword.window_stats)
t("and share one threshold", wc.COMP_DELTA == weekword.COMP_DELTA)

print("\nweek windows — Friday samples Mon..Fri vs LAST week's Mon..Fri:")
this, prev = fr.week_days(date(2026, 8, 14))          # a Friday
t("this week is Mon..Fri", this == ["2026-08-10", "2026-08-11", "2026-08-12",
                                    "2026-08-13", "2026-08-14"])
t("prior is the SAME span a week back", prev[0] == "2026-08-03" and prev[-1] == "2026-08-07")
t("like-for-like window lengths", len(this) == len(prev))

print("\nweek 1 baseline — no prior means no trend, ever:")
runs = [run("y8", "2026-08-10", [q()]), run("y8", "2026-08-04", [q()])]
t("trend engine returns None under baseline (ignores the pre-go-live week)",
  rst.week_over_week(runs, "y8", this, prev, [], {}, baseline=True) is None)
t("trend engine returns None when there is genuinely no prior",
  rst.week_over_week([run("y8", "2026-08-10", [q()])], "y8", this, prev, [], {}) is None)
card = fr.build_card("y8", runs, [], {}, date(2026, 8, 14), {}, [], baseline=True)
t("baseline forces direction 'none'", card["week_word"]["direction"] == "none")
t("baseline never claims 'strong' or 'slower'",
  card["week_word"]["word"] in ("solid", "quiet"))
t("baseline empties movement", card["movement"] == {"net": 0, "up": [], "down": []})

print("\ntrend is OVERALL, never per subject (small-sample rule):")
wk = ["2026-08-10", "2026-08-11"]
pv = ["2026-08-03", "2026-08-04"]
many = [run("y8", "2026-08-10", [q(ok=True, qid=f"S{i}") for i in range(12)]),
        run("y8", "2026-08-03", [q(ok=True, qid=f"S{i}") for i in range(12)])]
rows = rst.week_over_week(many, "y8", wk, pv, [], {})
t("returns rows when both weeks have enough", rows is not None and len(rows) >= 1)
t("no row is subject-scoped",
  all("subject" not in (r.get("label", "") + r.get("note", "")).lower()
      or "all subjects" in r.get("note", "") for r in rows))
thin = [run("y8", "2026-08-10", [q() for _ in range(3)]),
        run("y8", "2026-08-03", [q() for _ in range(3)])]
rows_thin = rst.week_over_week(thin, "y8", wk, pv, [], {})
t("accuracy row is SUPPRESSED on a thin sample (<10 either week)",
  all(r["label"] != "Answered right" for r in (rows_thin or [])))

print("\nquotes are integrity-gated — unattributable text is never quoted:")
good = ("I think it works because the base times height gives you the whole "
        "rectangle first, and then you halve it to get the triangle.")
held = run("y8", "2026-08-10", [q(phase="teach", text=good, qid="TB1")])
held["questions"][0]["tb_grade"] = {"verdict": "solid", "integrity_hold": True}
held["questions"][0]["tb_integrity"] = {"verdict": "quarantine"}
t("quarantined teach-back is NOT quoted",
  rst.pick_quote([held], "y8", ["2026-08-10"]) is None)
okrun = run("y8", "2026-08-10", [q(phase="teach", text=good, qid="TB1")])
okrun["questions"][0]["tb_grade"] = {"verdict": "solid"}
okrun["questions"][0]["tb_integrity"] = {"verdict": "ok"}
t("clean teach-back IS quoted",
  (rst.pick_quote([okrun], "y8", ["2026-08-10"]) or {}).get("text") == good)

print("\nspeed only speaks when it MOVED:")
fast = [run("y8", d, [q(secs=4, qid=f"S{i}") for i in range(4)]) for d in wk]
slow = [run("y8", d, [q(secs=12, qid=f"S{i}") for i in range(4)]) for d in pv]
t("a big shift is reported", rst.speed_shift(fast + slow, "y8", wk, pv) is not None)
same = [run("y8", d, [q(secs=8, qid=f"S{i}") for i in range(4)]) for d in wk + pv]
t("a flat week is silent", rst.speed_shift(same, "y8", wk, pv) is None)

print("\nthe Friday SMS law:")
name = "Harrison"
url = "https://x.example/r/abc/"
t("percentages rejected", fsms.validate(f"{name} did well 80% " + "x" * 90, name, url)[0] is False)
t("score slashes rejected", fsms.validate(f"{name} got 8/10 " + "x" * 90, name, url)[0] is False)
t("bare 'behind' rejected",
  fsms.validate(f"{name} is behind on maths " + "x" * 90, name, url)[0] is False)
t("'a step behind' allowed",
  fsms.validate(f"{name} is a step behind on maths. {url} " + "x" * 60, name, url)[0] is True)
t("paywall language rejected",
  fsms.validate(f"{name} did well, log in to see more {url} " + "x" * 70, name, url)[0] is False)
t("missing link rejected", fsms.validate(f"{name} did well. " + "x" * 90, name, url)[0] is False)
for w in ("miss", "wrong", "fail", "lazy"):
    t(f"banned word '{w}' rejected",
      fsms.validate(f"{name} {w}ed things {url} " + "x" * 80, name, url)[0] is False)

print("\nthe page renders safely from a minimal card:")
minimal = {"name": "Harrison", "code": "y8", "baseline": True,
           "week_word": {"word": "quiet", "direction": "none"},
           "activity": {"days_done": 0, "possible": 5, "events": 0,
                        "topics_practised": 0, "best_day": None},
           "standing": {"overall": "on", "exceptions": []},
           "standing_detail": {}, "movement": {"net": 0, "up": [], "down": []},
           "win": {"kind": "none"}, "radar": None, "action": {"kind": "none"},
           "snapshot": {"rows": [], "strongest": None}, "xp_total": 0,
           "week_of": "2026-08-10"}
html = rpage.render(minimal)
t("renders with no stories, no quote, no radar", "<html" in html and "XPDAILY" in html)
t("is self-contained — no fetch", "fetch(" not in html and "XMLHttpRequest" not in html)
t("is noindex", "noindex" in html)
t("week 1 shows the empty trend state, not a blank", "week one" in html.lower())

print("\n\u2713 all friday-report tests green")
