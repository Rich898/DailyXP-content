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
t("the focus vocabulary is exactly two verbs — an all-new subject says "
  "'moves into', never 'starts'",
  next(r for r in brief["rows"] if r["subject"] == "History")
  ["intent"].startswith("moves into"))
t("a mixed subject says both — moves into AND continues",
  maths["intent"] == "moves into Solving equations with brackets "
                     "and continues Linear equations")
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
    {"Solving equations with brackets": [
        {"subject": "Maths", "date": "2026-08-10", "ok": False, "phase": "steady", "id": "S1"},
        {"subject": "Maths", "date": "2026-08-12", "ok": True, "phase": "steady", "id": "T2"}]},
    {})
portal = pp.build_portal("Harrison", "2026-08-10", TOPICS, SUBJECTS_BLOCK, RADAR,
                         week_ahead=brief, this_week_blocks=blocks,
                         this_week_fluency="Solving equations with brackets",
                         this_week_of="2026-08-10", snapshots=few,
                         archive=[{"week": "2026-08-10",
                                   "url": "https://x.example/r/abc/2026-08-10/"}],
                         updated="2026-08-31",
                         week_verdict={"word": "solid"},
                         activity={"days_done": 4, "possible": 5,
                                   "topics_practised": 7, "events": 1,
                                   "questions": 41, "right": 34},
                         accuracy={"Maths": {"asked": 16, "right": 14},
                                   "Science": {"asked": 4, "right": 3},
                                   "English": {"asked": 1, "right": 1}})
pages = pp.render_pages(portal, kid_wrap_url="https://x.example/w/abc/")
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
  "The week ahead" in home and "The weekly update" in home
  and "The overall picture" in home and "one date on the radar" in home)
t("HOW TO READ THE REPORT teaches the model — SOLO in plain words, both axes",
  "HOW TO READ THE REPORT" in home and "SOLO taxonomy" in home
  and "Where he is" in home and "Depth" in home
  and "never a fail" in home and "explain a topic out loud" in home)
t("the reading guide sits before the account admin",
  home.index("HOW TO READ THE REPORT") < home.index("YOUR ACCOUNT"))
t("pages are titled by their own names; the masthead is the product only",
  "<title>The weekly update — Harrison · XP Daily</title>" in week
  and "<title>Harrison — XP Daily</title>" in home
  and "THE FULL PICTURE" not in week
  and ">XP DAILY<" in week)
t("the radar strip leads", "ON THE RADAR" in home and "Science test" in home)
t("the account surface stub is designed in",
  "YOUR ACCOUNT" in home and "switched off" in home and "text to Rich" in home)
t("the kid's player card is linked", "https://x.example/w/abc/" in home)

print("\nthe week ahead — Monday, forward (round-1 feedback locked):")
t("UPCOMING DATES renders (plural card; the single radar still feeds it)",
  "UPCOMING DATES" in ahead and "Science test" in ahead
  and "ONE DATE" not in ahead)
t("subject rows carry the three classifications — TOPIC and FOCUS labelled",
  ">Topic</span>" in ahead and ">Focus</span>" in ahead and "Algebra" in ahead)
t("the focus line uses the two-verb vocabulary on the page",
  "Moves into Solving equations with brackets and continues Linear equations"
  in ahead and "starts" not in ahead.lower())
t("the subheader carries no 'a plan, not a verdict' line",
  "not a verdict" not in ahead)
_phero_rule = ahead.split(".phero{")[1].split("}")[0]
t("headlines are white — the accent never colours the page title",
  _phero_rule.endswith("color:var(--ink)")
  and "body.pg-week h1.word{color:var(--ink)}" in week)
t("the loop points at Friday", "Friday" in ahead)

multi = pp.build_portal(
    "Harrison", "2026-08-10", TOPICS, SUBJECTS_BLOCK, RADAR, week_ahead=brief,
    upcoming=[{"task": "Maths study guide released", "date": "2026-09-14",
               "subject": "Maths"},
              {"task": "Science test", "date": "2026-09-10", "days": 12,
               "subject": "Science"}])
mpages = pp.render_pages(multi)
t("many dates render, nearest first — tests and study guides alike",
  "Maths study guide released" in mpages["ahead"]
  and mpages["ahead"].index("Science test")
  < mpages["ahead"].index("Maths study guide released"))
t("home's radar strip carries the nearest date",
  "Science test" in mpages[""] and "ON THE RADAR" in mpages[""])

print("\nthe weekly update — Friday, backward (round-2 feedback locked):")
t("the page is the Weekly update, and names the reported week's span",
  "Weekly update" in week and "Mon 10 – Fri 14 Aug" in week)
t("the verdict word is the hero", ">Solid</h1>" in week)
t("BY THE NUMBERS is its own deliberate section",
  "BY THE NUMBERS" in week and "BY SUBJECT" in week
  and week.index("BY THE NUMBERS") < week.index("BY SUBJECT"))
t("the tiles carry nights (excused-aware), questions and overall accuracy",
  "Nights run" in week and "of 5" in week
  and "Questions answered" in week and ">41<" in week
  and "Overall accuracy" in week and "34 of 41 right" in week)
t("no game-layer tallies on the parent report — events and achievement "
  "counts stay kid-side",
  "Events cleared" not in week and "chievement" not in week)
t("accuracy by subject renders as sorted single-hue bars, n always visible",
  "Accuracy by subject" in week and "n = questions asked" in week
  and "88% <span class='n'>&middot; n16" in week
  and "75% <span class='n'>&middot; n4" in week
  and week.index(">Maths<") < week.index(">Science<"))
t("a subject below two answers stays out of the chart", "n1<" not in week)
t("the intro line is gone — the table IS the organisation",
  "This week his sets worked" not in week)
t("the fluency catch lives INSIDE its subject block as the detail worth "
  "knowing — no page-level interruption",
  "class='fluency'" not in week
  and "The detail worth knowing:</b> on <b>Solving equations with brackets</b>"
  in week)
t("the fluency detail REPLACES the misconception in that block",
  "x=5" not in week)
t("per-topic practice volume renders — asked and right",
  "<b>2</b> asked" in week and "<b>1</b> right" in week)
t("the counts carry their small-sample caveat",
  "practice volume, not a score" in week)
t("no second 'full report' link — the Weekly update IS the Friday report",
  "full Friday report" not in week and "rowlink" not in week.split("</style>")[1])
oo_blocks = [
    {"subject": "Science", "unit": "U", "worked": ["W"],
     "topics": [{"topic": "W", "state": "solid", "depth": None, "asked": 1, "right": 1}]},
    {"subject": "Maths", "unit": "U", "worked": ["V"],
     "topics": [{"topic": "V", "state": "solid", "depth": None, "asked": 1, "right": 0}]},
]
oo = pp.render_pages(pp.build_portal("Harrison", "2026-08-10", TOPICS,
                                     SUBJECTS_BLOCK, None,
                                     this_week_blocks=oo_blocks))["week"]
t("subjects render in the one canonical order, whatever order blocks arrive",
  oo.index(">MATHS<") < oo.index(">SCIENCE<")
  if ">MATHS<" in oo else oo.index("Maths") < oo.index("Science"))
t("a single question's accuracy is suppressed — volume only",
  "<b>1</b> asked" in oo and "<b>1</b> right" not in oo and "<b>0</b> right" not in oo)
t("with no runner totals the tiles sum the table; under 10 answered, "
  "overall accuracy is suppressed too",
  "Questions answered" in oo and ">2<" in oo and "Overall accuracy" not in oo)
t("no chart from single-question subjects — two real rows or nothing",
  "Accuracy by subject" not in oo)

print("\nthe overall picture — Friday, cumulative (the mastery ledger):")
t("the landed tally leads", "of " in picture and "tally" in picture)
t("each subject's bar IS its topics — band-coloured tiles, weakest first, "
  "no new vocabulary",
  "<i class='h0'></i><i class='h3'></i><i class='h3'></i>" in picture
  and "3 topics &middot; 1 to watch" in picture
  and "exactly like the rows below" in picture)
t("the landed/explained stacking is gone from the page",
  "class='deep'" not in picture and "explained" not in picture)
t("cumulative still computes explained for later use (landed AND deep depth)",
  {c["subject"]: (c["landed"], c["explained"])
   for c in portal["running"]["cumulative"]}["Maths"] == (2, 1))
t("weakest-first is named as the risk read", "revision priorities" in picture)
t("the old TERM TRENDS section is folded into the bars",
  "TERM TRENDS" not in picture)
hist = pp.topic_history(four, [{"topic": "A", "subject": "Maths",
                                "state": "solid", "depth": None}])
t("topic_history stitches banked weeks and appends now",
  hist["A"] == ["shaky", "shaky", "solid", "solid", "solid"])
p4 = pp.render_pages(pp.build_portal(
    "Harrison", "2026-08-10",
    [{"topic": "A", "subject": "Maths", "state": "solid", "depth": None}],
    SUBJECTS_BLOCK, None, snapshots=four))["picture"]
t("with four banked weeks the term line switches on, in the bars card",
  "This term:" in p4 and "Maths +1" in p4)
t("each topic wears its week-by-week strip, ending at now",
  p4.count("<i class='h") >= 5)
t("a topic with no banked history gets no one-cell strip",
  "class='hist'" not in picture)
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
