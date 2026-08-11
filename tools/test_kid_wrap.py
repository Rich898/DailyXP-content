#!/usr/bin/env python3
"""test_kid_wrap.py — the kid wrap's load-bearing guarantees.

Locks the doctrine that is easy to break silently (KID-REPORT.md):
  * THE TRANSPARENCY LAW — every gap the parent report names appears on the
    kid page as a target; the week-word is the same word; the kid page adds,
    never subtracts.
  * THE INTEGRITY EXCEPTION — quarantined teach-back text never renders, and
    neither does any vocabulary a kid could infer it from.
  * THE LANGUAGE LAWS — person-praise, rung-as-label, guilt, comparison and
    parent-speak are banned constructions; render() refuses to ship them.
  * Week 1 is a start line (no trend), the page is self-contained + noindex,
    and rendering is deterministic (same inputs -> byte-identical page).
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import friday_report as fr          # noqa: E402
import kid_wrap as kw               # noqa: E402
import report_page as rpage         # noqa: E402


def t(name, cond):
    assert cond, f"FAIL: {name}"
    print(f"  [PASS] {name}")


# --------------------------------------------------------------------------- #
# fixtures — one kid-week with every gap surface the parent page can name

CARD = {
    "code": "y8", "name": "Harrison", "baseline": True,
    "week_word": {"word": "solid", "direction": "none"},
    "activity": {"days_done": 2, "possible": 5, "events": 1,
                 "topics_practised": 9, "best_day": {"pts": 1585, "day": "Mon"}},
    "standing": {"overall": "mostly", "exceptions": [("Maths", "Linear equations")]},
    "standing_detail": {},
    "movement": {"net": 0, "up": [], "down": []},
    "win": {"kind": "badge", "badge": "Clean Run", "label": ""},
    "radar": {"task": "Science in-class assessment", "date": "2026-08-20",
              "days": 9, "subject": "Science", "readiness": "building",
              "focus": "Global Patterns / reproduction", "covered": 3},
    "action": {"kind": "repair", "topic": "Angles on parallel lines"},
    "snapshot": {"rows": [], "strongest": "Crusades"},
    "xp_total": 6860, "week_of": "2026-08-10",
}
STORIES = [
    {"status": "TO CLOSE", "topic": "Classifying triangles & quadrilaterals",
     "subject": "Maths", "state": "shaky", "weight": 40,
     "trace": [{"day": "Mon", "ok": False}, {"day": "Tue", "ok": False}],
     "misconception": {"picked": "Rectangle", "correct": "Rhombus",
                       "why": "A rhombus has four equal sides; a rectangle has "
                              "four equal angles."},
     "next": "re-tested next week"},
    {"status": "RESOLVED", "topic": "Crusades", "subject": "History",
     "state": "solid", "weight": 104, "next": "stays once more",
     "trace": [{"day": "Mon", "ok": False}, {"day": "Tue", "ok": True},
               {"day": "Wed", "ok": True}]},
    {"status": "DEEPENED", "topic": "Variables (independent/dependent/controlled)",
     "subject": "Science", "from": "lists", "to": "connects",
     "evidence": "because I changed it", "trace": [], "weight": 90, "next": "aims higher"},
    {"status": "WATCHING", "topic": None, "subject": None, "trace": [],
     "count": 2, "of": 5, "weight": 50, "next": "no intervention"},
]
QUOTE = {"text": "If I practice basketball for longer the practice time is the "
                 "independent variable because I changed it.",
         "subject": "Science", "secs": 120, "depth": "connects", "score": 2232}
QUARANTINED_TEXT = ("The student's response correctly symbolized the theme of "
                    "individualism and the author's behavior throughout.")
GAME = {
    "days": [{"day": "Mon", "date": "2026-08-10", "pts": 1585, "event": None},
             {"day": "Tue", "date": "2026-08-11", "pts": 1358, "event": None},
             {"day": "Wed", "date": "2026-08-12", "pts": None, "event": None},
             {"day": "Thu", "date": "2026-08-13", "pts": None, "event": None},
             {"day": "Fri", "date": "2026-08-14", "pts": None, "event": None}],
    "streak": 2, "events": [], "season_total": 6860,
    "level": {"n": 3, "into": 2460, "need": 2800},
    "accuracy": {"pct": 62, "right": 13, "asked": 21},
    "badges": [{"badge": "Clean Run", "date": "2026-08-10"}],
}


print("the level curve — deterministic, front-loaded, retunable in one place:")
t("level 1 at zero XP", kw.level_for(0) == (1, 0, 2000))
t("first level lands at 2000", kw.level_for(2000)[0] == 2)
t("costs step up by LEVEL_STEP", kw.level_for(4400)[0] == 3 and kw.level_for(4399)[0] == 2)
t("season total 6860 -> level 3, 340 to next",
  kw.level_for(6860) == (3, 2460, 2800))

print("\nlanguage laws — the validator catches the banned constructions:")
t("person-level praise is caught", kw.violations("wow, you're so clever!"))
t("rung-as-label-for-the-child is caught",
  kw.violations("you're a can list it kid now"))
t("guilt is caught", kw.violations("you should have studied more"))
t("sibling comparison is caught", kw.violations("your brother got more right"))
t("speaking for parents is caught", kw.violations("your mum will be pleased"))
t("integrity vocabulary is caught", kw.violations("that one didn't count"))
t("clean player-card copy passes",
  not kw.violations("Crusades — you can connect it now. The set bit hard; "
                    "you kept showing up."))

print("\nthe transparency law — every parent-named gap arrives as a target:")
targets = kw.targets_from(CARD, STORIES)
names = {x["topic"] for x in targets}
t("TO CLOSE story topic is a target", "Classifying triangles & quadrilaterals" in names)
t("assessment focus is a target", "Global Patterns / reproduction" in names)
t("the action's repair topic is a target", "Angles on parallel lines" in names)
t("standing 'behind' exception is a target", "Linear equations" in names)
t("no duplicates", len(names) == len(targets))

page = kw.render(CARD, stories=STORIES, quote=QUOTE, game=GAME)
parent = rpage.render(CARD, stories=STORIES, quote=QUOTE,
                      accuracy={"Maths": {"right": 5, "asked": 9}})
for topic in names:
    t(f"target renders on the page: {topic[:34]}…", topic.replace("&", "&amp;") in page
      or topic in page)
t("same week-word as the parent page — same engine, same word",
  ">Solid</h1>" in page and ">Solid</h1>" in parent)
t("the misconception diagnosis travels (same facts, kid dressing)",
  "Rhombus" in page and "four equal sides" in page)
t("the confident-wrong tendency travels (WATCHING -> sure-check)",
  "2 of 5" in page)
t("the quote is the same quote", QUOTE["text"][:40] in page)
t("the XP total is the parent page's number", "6,860" in page)

print("\nthe integrity exception — a quarantined row is invisible, not implied:")
t("quarantined text never renders", QUARANTINED_TEXT[:30] not in page)
for w in ("didn't count", "quarantin", "integrity", "flagged", "cheat"):
    t(f"vocabulary absent: '{w}'", w not in page.lower())

print("\nweek 1 is a start line, not an empty dashboard:")
t("start-line kicker renders", "THE START LINE" in page)
t("no trend language on a baseline week", "last week" not in page.lower())
b2 = dict(CARD, baseline=False, week_word={"word": "strong", "direction": "up"})
page2 = kw.render(b2, stories=STORIES, quote=QUOTE, game=GAME)
t("direction tail appears once a prior exists", "climbing on last week" in page2)

print("\nprivacy + self-containment (the report_page model):")
t("noindex", 'name="robots" content="noindex' in page)
t("brand marker for deploy verify", "XPDAILY" in page[:4000].upper())
t("no fetch calls, no scripts", "<script" not in page and "fetch(" not in page)
t("only the shared font import leaves the page",
  page.count("http") == page.count("fonts.googleapis") + page.count("fonts.gstatic"))

print("\ndeterminism — same inputs, byte-identical page:")
t("render is deterministic",
  kw.render(CARD, stories=STORIES, quote=QUOTE, game=GAME) == page)

print("\nrender refuses to ship a law breach:")
bad = dict(CARD, name="Kid")
bad["action"] = {"kind": "ask", "topic": "you're so clever"}   # hostile data
try:
    kw.render(bad, stories=[], quote=None, game=GAME)
    t("ValueError raised on a breaching page", False)
except ValueError:
    t("ValueError raised on a breaching page", True)

print("\ngame_facts — additive layer reads scores and dates, never text:")
runs = [
    {"student": "y8", "run_date": "2026-08-10", "tag": "H3.1", "score": 1585,
     "max_score": 2780, "name": "Harrison", "canonical": True,
     "questions": [{"phase": "speed", "ok": True, "secs": 8}]},
    {"student": "y8", "run_date": "2026-08-11", "tag": "H3.2 · BLITZ", "score": 1358,
     "max_score": 2780, "name": "Harrison", "canonical": True,
     "questions": [{"phase": "speed", "ok": True, "secs": 8},
                   {"phase": "speed", "ok": False, "secs": 8},
                   {"phase": "teach", "ok": True, "secs": 90, "text": "x"}]},
]
days = ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14"]
g = kw.game_facts(runs, "y8", days, [], date(2026, 8, 14),
                  season_total=2943, accuracy={"Maths": {"right": 6, "asked": 11}})
t("five day slots, blanks are None (no shame mark)",
  len(g["days"]) == 5 and g["days"][2]["pts"] is None)
t("best-of-day points fill the bars", g["days"][0]["pts"] == 1585)
t("the Blitz day carries its event mark", g["days"][1]["event"]["label"] == "Blitz")
t("streak anchors on the last PLAYED day (wrap before tonight's ingest never "
  "zeroes an honest streak)", g["streak"] == 2)
t("events list carries the blitz", g["events"][0]["label"] == "Blitz")
t("accuracy shows at >=10 scored questions", g["accuracy"]["pct"] == 55)
g2 = kw.game_facts(runs, "y8", days, [], date(2026, 8, 14),
                   season_total=100, accuracy={"Maths": {"right": 3, "asked": 5}})
t("accuracy withheld under the 10-question floor", g2["accuracy"] is None)

print("\nempty states — a thin week renders as a start line, never a verdict:")
empty_card = dict(CARD, radar=None, action={"kind": "none"},
                  standing={"overall": "on", "exceptions": []},
                  movement={"net": 0, "up": [], "down": []})
empty_game = dict(GAME, days=[dict(d, pts=None, event=None) for d in GAME["days"]],
                  streak=0, badges=[], accuracy=None, events=[])
page3 = kw.render(empty_card, stories=[], quote=None, game=empty_game)
t("empty beat-list says list-not-verdict", "a list, not a verdict" in page3)
t("empty week carries no debt", "no debt" in page3)
t("empty stalk-list renders the clear-board line", "board is clear" in page3)

print("\ngrade_teachback — the deterministic integrity pass:")
import grade_teachback as gt        # noqa: E402
fast_paste = {"student": "y9", "run_date": "2026-08-04", "tag": "R2.1",
              "canonical": True, "is_test": False,
              "questions": [{"phase": "teach", "subject": "English",
                             "text": QUARANTINED_TEXT, "chars": 640, "secs": 110}]}
own_words = {"student": "y9", "run_date": "2026-08-10", "tag": "R3.1",
             "canonical": True, "is_test": False,
             "questions": [{"phase": "teach", "subject": "Science",
                            "text": "its kinda like the moon pulls the water so "
                                    "the tide goes up becuase of gravity",
                            "chars": 84, "secs": 95}]}
n, log = gt.attach_integrity([fast_paste, own_words])
t("both rows annotated", n == 2)
t("the pasted register quarantines",
  fast_paste["questions"][0]["tb_integrity"]["verdict"] == "quarantine")
t("the kid's own informal answer passes",
  own_words["questions"][0]["tb_integrity"]["verdict"] == "ok")
t("idempotent — second pass annotates nothing",
  gt.attach_integrity([fast_paste, own_words])[0] == 0)

print("\nall kid-wrap laws hold.")
