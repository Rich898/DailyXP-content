#!/usr/bin/env python3
"""test_kid_board.py — THE BOARD's load-bearing guarantees.

Locks the doctrine (KID-WEEKLY-FRAMEWORK.md §4 + Rich's round-1 laws):
  * Every badge the board names is one achievements.py actually awards (the
    kid_wrap CABINET) — the board is a READ of the reward engine, never a
    second one.
  * Round-1 language: the daily unit is a RUN ("contract" never renders);
    "up for grabs" appears at most once; rolls-on framing only ("failed" /
    "missed" never render); no rank names, no XP promises.
  * Headlines are white (the h1 carries no accent colour class).
  * The kid Monday law: forward-only fields; kid_wrap.violations() over the
    full page; render() REFUSES a breaching page.
  * Determinism: same facts -> byte-identical page (modulo the build stamp,
    pinned here); picks are stable under input reordering.
  * The nudge appends the board link ONLY when handed one, and the Monday
    copy is otherwise byte-identical to today's.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("GITHUB_SHA", "testsha")

import kid_board as kb          # noqa: E402
import kid_wrap as kw           # noqa: E402
from kid_nudge import decide    # noqa: E402

TOPICS = [
    {"topic": "Linear equations", "subject": "Maths", "state": "developing",
     "times_seen": 9},
    {"topic": "Percentages", "subject": "Maths", "state": "developing",
     "times_seen": 4},
    {"topic": "Angles", "subject": "Maths", "state": "REPAIR", "times_seen": 7},
    {"topic": "Fractions", "subject": "Maths", "state": "solid", "times_seen": 11},
    {"topic": "Cells", "subject": "Science", "state": "solid", "times_seen": 6},
    {"topic": "Ecosystems", "subject": "Science", "state": "solid", "times_seen": 5},
    {"topic": "States of matter", "subject": "Science", "state": "solid",
     "times_seen": 7},
    {"topic": "Photosynthesis", "subject": "Science", "state": "developing",
     "times_seen": 3},
]

# --- deterministic picks ----------------------------------------------------
lock = kb.pick_lock_it(TOPICS)
assert lock["topic"] == "Linear equations"          # most-seen developing
back = kb.pick_comeback(TOPICS)
assert back["topic"] == "Angles"
fc = kb.full_clear_watch(TOPICS)
assert fc["subject"] == "Science" and fc["left"] == 1
assert kb.pick_lock_it(list(reversed(TOPICS)))["topic"] == "Linear equations"
assert kb.pick_lock_it([]) is None and kb.pick_comeback([]) is None

# --- every named badge is a real cabinet badge ------------------------------
badges = kb.week_badges(TOPICS, 6, [])
names = {b["name"] for b in badges}
assert names == {"LOCKED IT", "COMEBACK", "FULL CLEAR"}
cabinet_titles = {c.upper() for c in kw.CABINET}
for b in badges:
    assert b["name"] in cabinet_titles, b["name"]
    assert b["icon"] in kw.BADGE_ICON.values()

# --- the run strip ----------------------------------------------------------
strip = kb.run_strip(6, [])                          # streak 6 -> Silver Mon
assert len(strip["tiles"]) == 5
assert strip["streak_night"] == {"tier": "Silver", "night": 7, "day_idx": 0}
assert strip["tiles"][0]["label"] == "Silver Streak"
assert strip["tiles"][4]["icons"] == [kw.BADGE_ICON["Full Claim"],
                                      kw.BADGE_ICON["Perfect Week"]]
for t in strip["tiles"]:
    assert t["icons"], "every run tile shows a badge (round-1 law)"
mid = kb.run_strip(0, [])                            # streak 0 -> Bronze Wed
assert mid["streak_night"]["day_idx"] == 2
far = kb.run_strip(8, [{"badge": "Streak Silver"}])  # Gold at 14: not this week
assert far["streak_night"] is None

# --- render: laws over the full page ----------------------------------------
FACTS = {
    "code": "t1", "name": "Sam", "week_of": "2026-08-31",
    "brief": {"rows": [
        {"subject": "Maths", "unit": "Algebra",
         "covering": ["Solving equations with brackets", "Linear equations"],
         "new": ["Solving equations with brackets"], "hedged": False,
         "intent": ""},
        {"subject": "Science", "unit": "Body systems",
         "covering": ["How body systems work together"],
         "new": ["How body systems work together"], "hedged": False,
         "intent": ""}],
        "subjects": ["Maths", "Science"], "name": "Sam", "assessment": None},
    "radar": {"task": "Science topic test", "date": "2026-09-10", "days": 10,
              "subject": "Science", "readiness": "building",
              "focus": "How body systems work together"},
    "upcoming": [{"task": "Persuasive speech due", "date": "2026-09-18",
                  "days": 18, "subject": "English"}],
    "streak": 6,
    "runs": kb.run_strip(6, []),
    "badges": kb.week_badges(TOPICS, 6, []),
}

page = kb.render(FACTS, play_url="https://example.invalid/play")
low = page.lower()
assert "The week of <b>Monday 31 August</b> is live" in page   # Rich's sentence
assert "contract" not in low                                    # runs, not contracts
assert low.count("up for grabs") == 1                           # said once
assert "failed" not in low and "missed" not in low              # rolls on, never
assert "sergeant" not in low and "recruit" not in low           # no rank names
assert "xp" not in low.replace("xpdaily", "").replace("xp daily", "")  # no XP promises
assert "h1 class=\"word display\"" in page                      # no accent class on h1
assert 'name="xpdaily-week" content="2026-08-31"' in page       # the nudge gate meta
assert 'name="xpdaily-build"' in page and "noindex" in page
assert "Solving equations with brackets" in page and "NEW" in page
assert "BOSS APPROACHING" in page and "10 days out" in page
assert "Silver Streak" in page and "Full Claim" in page
assert kw.violations(page) == []
assert kb.render(FACTS, play_url="https://example.invalid/play") == page  # deterministic

# ground-first order (Rich's structure: ground -> runs -> radar)
assert low.index("this week's ground") < low.index("the week's runs") \
    < low.index("boss radar")

# refusal: a law-breaching line can never ship
BAD = dict(FACTS)
BAD["badges"] = [{"icon": "x", "name": "LOCKED IT",
                  "line": "you should have done this last week"}]
try:
    kb.render(BAD)
    raise AssertionError("render must refuse a language-law breach")
except ValueError:
    pass

# empty-ground fail-soft still renders (stale targets Monday)
EMPTY = dict(FACTS)
EMPTY["brief"] = {"rows": [], "subjects": [], "name": "Sam", "assessment": None}
assert "sync with what school posts" in kb.render(EMPTY)

# --- the nudge: board link only when handed one, copy untouched otherwise ---
MON = date(2026, 8, 31)
LIVE = {"date": "2026-08-31", "status": "ok"}
_, _, plain = decide(LIVE, MON, "https://play.invalid")
_, _, linked = decide(LIVE, MON, "https://play.invalid", "https://b.invalid/w/x/board/")
assert plain in linked and linked.endswith("The week's board: https://b.invalid/w/x/board/")
assert "board" in plain.lower()          # Monday copy already speaks board
_, _, tue = decide({"date": "2026-09-01", "status": "ok"}, date(2026, 9, 1),
                   "https://play.invalid", None)
assert "The week's board" not in tue

print("test_kid_board: all assertions passed")
