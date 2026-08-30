#!/usr/bin/env python3
"""test_portal_page.py — the portal's load-bearing guarantees (PARENT-PORTAL-BRIEF).

The portal is the parent's product home: a home page plus THREE designed pages —
THE WEEK AHEAD (Monday, forward), THIS WEEK (Friday, what happened), THE RUNNING
PICTURE (Friday, cumulative) — cross-linked by an app nav. This locks: the
Monday law (monday_brief), the confidently-shallow cross, the depth ceiling, the
4-week trend gate, the freshness stamps, the self-contained privacy model, AND
the course-correction itself: each component lives on ITS OWN page, never
stacked back into one scroll.
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

print("\nthe portal renders as FOUR pages — home + one per component:")
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
                         updated="2026-08-31",
                         week_verdict={"word": "solid"},
                         activity={"days_done": 4, "possible": 5,
                                   "topics_practised": 7, "events": 1})
pages = pp.render_pages(portal, kid_wrap_url="https://x.example/w/abc/",
                        report_url="https://x.example/r/abc/2026-08-10/")
t("exactly the four pages render", set(pages) == {"", "ahead", "week", "picture"})
home, ahead, week, picture = pages[""], pages["ahead"], pages["week"], pages["picture"]

print("\nthe course-correction holds — one component per page, never one scroll:")
t("home is the front door, not the report",
  "class='subj-table'" not in home and "Where it sits" not in home
  and "class='trow'" not in home)
t("the week ahead page carries no positions or verdicts",
  all(s not in ahead for s in ("Where it sits", "Strong recall", "Nearly there",
                               "landed", "class='subj-table'", "class='dot")))
t("the subject spine (worked → detail → next week) lives on THIS WEEK only",
  "class='subj'" in week and "The detail worth knowing" in week
  and "class='subj'" not in picture and "The detail worth knowing" not in picture
  and "class='subj'" not in ahead)
t("the topic map lives on THE RUNNING PICTURE only",
  "class='cshallow'" in picture and "class='cshallow'" not in week
  and "class='cshallow'" not in home)

print("\nhome — the front door:")
t("all three doorways with live teasers",
  "The week ahead" in home and "This week" in home and "The running picture" in home
  and "one date on the radar" in home)
t("the radar strip leads", "ON THE RADAR" in home and "Science test" in home)
t("the account surface stub is designed in",
  "YOUR ACCOUNT" in home and "switched off" in home and "text to Rich" in home)
t("the kid's player card is linked", "https://x.example/w/abc/" in home)

print("\nthe week ahead — Monday, forward:")
t("the ONE DATE assessment card renders",
  "ONE DATE" in ahead and "Science test" in ahead)
t("what school posted, new topics flagged",
  "Solving equations with brackets" in ahead and "new:" in ahead)
t("the loop points at Friday", "Friday" in ahead)

print("\nthis week — Friday, backward:")
t("the verdict word is the hero", ">Solid</h1>" in week)
t("the excused-aware activity strip renders", "4 of 5" in week)
t("the fluency-illusion catch is narrated",
  "Fractions" in week and "could pick the right answer" in week)
t("the misconception detail renders in the spine", "The detail worth knowing" in week)
t("the full Friday report is linked", "https://x.example/r/abc/2026-08-10/" in week)

print("\nthe running picture — Friday, cumulative:")
t("the landed tally leads", "of " in picture and "tally" in picture)
t("the confidently-shallow note reaches the page", "Strong recall" in picture)
t("evidenced depth renders its rung", "Can connect it" in picture)
t("unevidenced depth renders a dash, never an inflated claim",
  "<span class='dep none'>&mdash;</span>" in picture)
t("under four weeks the page SAYS trends fill in later, not fakes it",
  "four weeks" in picture)
t("the archive links the dated report path",
  "https://x.example/r/abc/2026-08-10/" in picture)
t("the legend is the verdict ladder's home", "HOW TO READ THIS" in picture)

print("\nnavigation — four pages, one product:")
for key, html in pages.items():
    t(f"page '{key or 'home'}' carries the app nav",
      "pnav" in html and "aria-current='page'" in html)
t("home links the three pages relatively",
  "href='ahead/'" in home and "href='week/'" in home and "href='picture/'" in home)
t("subpages link home and each other",
  "href='../'" in ahead and "href='../picture/'" in week and "href='../week/'" in picture)
navved = pp.render_pages(portal, nav={"": "https://a/", "ahead": "https://b/",
                                      "week": "https://c/", "picture": "https://d/"})
t("explicit nav URLs override on every page",
  all("https://c/" in h for h in navved.values()))

print("\nevery page: honest, private, stamped:")
for key, html in pages.items():
    label = key or "home"
    t(f"'{label}' is self-contained — zero fetch",
      "fetch(" not in html and "XMLHttpRequest" not in html)
    t(f"'{label}' is noindex", "noindex" in html)
    t(f"'{label}' build stamp inside verify()'s 4KB window",
      'name="xpdaily-build"' in html and html.index("xpdaily-build") < 3500)
    t(f"'{label}' shows the freshness date, in human form",
      "updated Mon 31 Aug" in html)
    t(f"'{label}' names the freshness contract on the page",
      "refresh Friday evening" in html and "refreshes Monday" in html)
    t(f"'{label}' carries the visible build stamp", "build " in html.split("pfoot")[-1])
    t(f"'{label}' leaks no same-night results", "tonight" not in html.lower())

print("\nempty states are honest (a Monday-only build, pre-Friday):")
bare = pp.build_portal("Harrison", "2026-08-10", TOPICS, SUBJECTS_BLOCK, RADAR,
                       week_ahead=brief, updated="2026-08-31")
bare_pages = pp.render_pages(bare)
t("this week says it lands Friday evening",
  "lands Friday evening" in bare_pages["week"])
t("no verdict word is faked pre-Friday", ">Solid</h1>" not in bare_pages["week"])
t("home teases the week page honestly",
  "lands Friday evening" in bare_pages[""])
no_wa = pp.build_portal("Harrison", "2026-08-10", TOPICS, SUBJECTS_BLOCK, None)
t("a missing week-ahead gets the honest continuation form",
  "keep working the current topics" in pp.render_pages(no_wa)["ahead"])

print("\n✓ all portal tests green")
