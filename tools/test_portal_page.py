#!/usr/bin/env python3
"""test_portal_page.py — the portal's load-bearing guarantees (PARENT-COMMS-V2).

The portal is the THREE-part parent report on one page: THE WEEK AHEAD (Monday,
forward), THIS WEEK (Friday, what happened), THE RUNNING PICTURE (Friday,
cumulative). This locks: the Monday law (monday_brief), the confidently-shallow
cross, the depth ceiling, the 4-week trend gate, the freshness stamps, and the
self-contained privacy model.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portal_page as pp        # noqa: E402
import monday_brief as mb       # noqa: E402
import report_stories as rst    # noqa: E402


def t(name, cond):
    assert cond, f"FAIL: {name}"
    print(f"  [PASS] {name}")


TOPICS = [
    {"topic": "Linear equations", "subject": "Maths", "state": "solid", "depth": "lists"},
    {"topic": "Fractions", "subject": "Maths", "state": "solid", "depth": "connects"},
    {"topic": "Angles on parallel lines", "subject": "Maths", "state": "REPAIR", "depth": None},
    {"topic": "The Crusades", "subject": "History", "state": "developing", "depth": None},
    {"topic": "Old topic", "subject": "History", "state": "FROZEN", "depth": None},
]
SUBJECTS_BLOCK = {
    "Maths": {"unit": "Algebra", "topics": [
        {"topic": "Solving equations with brackets", "status": "live"},
        {"topic": "Linear equations", "status": "live"}]},
    "History": {"unit": "The Crusades", "topics": [{"topic": "The Crusades", "status": "live"}]},
}
PREV_BLOCK = {"Maths": {"topics": [{"topic": "Linear equations", "status": "live"}]},
              "History": {"topics": []}}
RADAR = {"task": "Science test", "date": "2026-09-10", "days": 12, "subject": "Science"}


print("component 1 — THE WEEK AHEAD (monday_brief): forward-only, no verdicts:")
brief = mb.week_ahead("Harrison", SUBJECTS_BLOCK, PREV_BLOCK, RADAR)
maths = next(r for r in brief["rows"] if r["subject"] == "Maths")
t("new-this-week topics are flagged vs last week's targets",
  "Solving equations with brackets" in maths["new"] and "Linear equations" not in maths["new"])
t("the intent clause is a forward verb, no state word",
  maths["intent"].startswith("moves into") and "solid" not in maths["intent"])
t("the assessment rides through", brief["assessment"]["date"] == "2026-09-10")

print("\nthe Monday POINTER SMS — carries no sweep-derived claim:")
sms = mb.pointer_sms(brief, "https://x.example/p/abc/")
ok, why = mb.validate(sms, "Harrison", subjects=brief["subjects"])
t("the pointer passes the Monday law", ok)
t("the pointer names subjects and links, nothing more",
  "https://x.example/p/abc/" in sms and "Harrison" in sms)
t("a verdict word is rejected", mb.validate(
    "Harrison is solid this week. https://x.example/p/", "Harrison")[0] is False)
t("a stray digit (not a date) is rejected", mb.validate(
    "Harrison has 3 things on. https://x.example/p/", "Harrison")[0] is False)
t("an assessment date phrase is allowed", mb.validate(
    "Harrison — a test Thursday 10 September is coming. https://x.example/p/",
    "Harrison", allow_date_phrase="Thursday 10 September")[0] is True)
t("a topic that contains a standing word does NOT false-trip", mb.validate(
    "Harrison starts Building structures this week. https://x.example/p/",
    "Harrison", topics=["Building structures"])[0] is True)

print("\ncomponent 3 — the confidently-shallow cross + depth ceiling:")
t("solid x shallow fires", pp._confidently_shallow("solid", "lists"))
t("solid x no-teachback-yet fires", pp._confidently_shallow("solid", None))
t("solid x connects does NOT fire", pp._confidently_shallow("solid", "connects") is False)
cards = pp.subject_cards(TOPICS)
by = {c["subject"]: c for c in cards}
t("frozen topics excluded", all(r["topic"] != "Old topic" for c in cards for r in c["rows"]))
t("rows are weakest-first", by["Maths"]["rows"][0]["topic"] == "Angles on parallel lines")

print("\nterm trends — positions weekly, trends monthly (the 4-week gate):")
few = [{"week_of": f"w{i}", "topics": {"A": "solid"}, "subjects": {"A": "Maths"}}
       for i in range(3)]
t("under four weeks, no trend is computed", pp.term_trends(few) is None)
four = [{"week_of": f"w{i}",
         "topics": {"A": ("shaky" if i < 2 else "solid"), "B": "shaky"},
         "subjects": {"A": "Maths", "B": "Maths"}} for i in range(4)]
tr = pp.term_trends(four)
t("at four weeks the trend switches on", tr is not None and tr["weeks"] == 4)

print("\nthe page renders all three components, honestly and privately:")
blocks = rst.subject_blocks(
    [{"topic": "Solving equations with brackets", "subject": "Maths", "state": "shaky", "depth": None}],
    SUBJECTS_BLOCK,
    [{"status": "TO CLOSE", "topic": "Solving equations with brackets", "subject": "Maths",
      "state": "shaky", "misconception": {"picked": "x=5", "correct": "x=3",
      "why": "expanded the bracket wrong"}, "next": "re-tested"}],
    {"Solving equations with brackets": [{"subject": "Maths", "date": "2026-08-10",
                                          "ok": False, "phase": "steady", "id": "S1"}]},
    {})
portal = pp.build_portal("Harrison", "2026-08-10", TOPICS, SUBJECTS_BLOCK, RADAR,
                         week_ahead=brief, this_week_blocks=blocks,
                         this_week_fluency="Fractions", snapshots=few,
                         archive=[{"week": "2026-08-10",
                                   "url": "https://x.example/r/abc/2026-08-10/"}],
                         updated="2026-08-31")
html = pp.render(portal, kid_wrap_url="https://x.example/w/abc/")
t("all three components render",
  all(s in html for s in ("THE WEEK AHEAD", "THIS WEEK", "THE RUNNING PICTURE")))
t("each component shows when it refreshes",
  "updated Monday" in html and "updated Friday" in html)
t("the week-ahead names what's new, not how he did",
  "Solving equations with brackets" in html and "solid this week" not in html)
t("the this-week subject spine renders (what happened)",
  "The detail worth knowing" in html)
t("the running picture leads with a landed tally", "landed" in html)
t("the confidently-shallow note reaches the page", "Strong recall" in html)
t("evidenced depth renders its rung", "Can connect it" in html)
t("unevidenced depth renders a dash, never an inflated claim",
  "<span class='dep none'>&mdash;</span>" in html)
t("under four weeks the page SAYS trends fill in later, not fakes it",
  "four weeks of history" in html or "four weeks" in html)
t("a visible freshness stamp (updated date) is present", "updated 2026-08-31" in html)
t("the archive links the dated report path",
  "https://x.example/r/abc/2026-08-10/" in html)
t("self-contained — zero fetch", "fetch(" not in html and "XMLHttpRequest" not in html)
t("noindex", "noindex" in html)
t("build stamp inside verify()'s 4KB window",
  'name="xpdaily-build"' in html and html.index("xpdaily-build") < 3500)
t("no same-night results leak", "tonight" not in html.lower())

print("\n✓ all portal tests green")
