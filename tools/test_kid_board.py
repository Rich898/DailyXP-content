#!/usr/bin/env python3
"""test_kid_board.py — THE BOARD's load-bearing guarantees.

Locks the doctrine (KID-WEEKLY-FRAMEWORK.md §4 + Rich's rounds 1–2, 31 Aug):
  * Every achievement card the board shows is a badge achievements.py
    actually awards (the kid_wrap CABINET) — the board is a READ of the
    reward engine, never a second one. ON THE BOARD (4 of the 5 nightly
    runs) is a real engine badge, introduction-week guarded.
  * Round-1/2 language: "contract" never renders; "up for grabs" at most
    once; rolls-on framing only ("failed"/"missed" never render); no rank
    names, no XP promises; a "run" is the day's quiz, never a tile strip.
  * Headlines are white (the h1 carries no accent colour class).
  * Rich's order: ground → up for grabs → boss radar.
  * kid_wrap.violations() over the full page; render() refuses a breach.
  * Determinism: same facts -> byte-identical page (build stamp pinned).
  * The nudge appends the board link ONLY when handed one; the Monday copy
    is otherwise byte-identical to today's.
"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("GITHUB_SHA", "testsha")

import achievements as ach      # noqa: E402
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
assert kb.pick_lock_it(TOPICS)["topic"] == "Linear equations"
assert kb.pick_comeback(TOPICS)["topic"] == "Angles"
fc = kb.full_clear_watch(TOPICS)
assert fc["subject"] == "Science" and fc["left"] == 1
assert kb.pick_lock_it(list(reversed(TOPICS)))["topic"] == "Linear equations"
assert kb.pick_lock_it([]) is None and kb.pick_comeback([]) is None

# --- ON THE BOARD is a real engine badge (4 of 5 school-days, guarded) ------
def _runs(days):
    return [{"student": "t1", "run_date": d, "set_date": d, "score": 100,
             "speed": {"of": 5, "right": 4}, "steady": {"of": 5, "right": 4},
             "shell_flags": {}} for d in days]

got = {b for b, k, _, _ in ach.run_badges(_runs(
    ["2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03"]))}
assert "On the Board" in got, "4 distinct school-days must award On the Board"
got3 = {b for b, k, _, _ in ach.run_badges(_runs(
    ["2026-08-31", "2026-09-01", "2026-09-02"]))}
assert "On the Board" not in got3, "3 days is not on the board"
old = {b for b, k, _, _ in ach.run_badges(_runs(
    ["2026-05-04", "2026-05-05", "2026-05-06", "2026-05-07"]))}
assert "On the Board" not in old, "pre-introduction weeks never backfill"
keys = {k for b, k, _, _ in ach.run_badges(_runs(
    ["2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04"]))}
assert "On the Board|2026-W36" in keys and "Perfect Week|2026-W36" in keys, \
    "5/5 pays both — Perfect Week stays the trophy on top"
assert "On the Board" in kw.CABINET and "On the Board" in kw.BADGE_ICON \
    and "On the Board" in kw.BADGE_ACT

# --- the up-for-grabs cards -------------------------------------------------
grabs = kb.week_up_for_grabs(TOPICS, 6, [])
names = [c["name"] for c in grabs]
assert names[0] == "ON THE BOARD", "the weekly showing-up achievement leads"
assert "STREAK — SILVER" in names and "CLEAN RUN" in names
assert "LOCK IT: LINEAR EQUATIONS" in names
assert "BOUNCE BACK: ANGLES" in names and "FULL CLEAR: SCIENCE" in names
assert len(grabs) <= 6
cab_icons = set(kw.BADGE_ICON.values())
for c in grabs:
    assert c["icon"] in cab_icons, f"{c['name']} must carry a real badge icon"
# streak card timing: streak 6 -> Silver lands tonight (Monday)
silver = next(c for c in grabs if c["name"] == "STREAK — SILVER")
assert "tonight" in silver["terms"] and "walks in at 6" in silver["terms"]
# no streak card when the next tier is out of the week's reach
far = kb.week_up_for_grabs(TOPICS, 8, [{"badge": "Streak Silver"}])
assert not any(c["name"].startswith("STREAK") for c in far)

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
    "grabs": kb.week_up_for_grabs(TOPICS, 6, []),
}

page = kb.render(FACTS, play_url="https://example.invalid/play")
low = page.lower()
assert "The week of <b>Monday 31 August</b> is live" in page   # Rich's sentence
assert "contract" not in low
assert low.count("up for grabs") == 1                           # said once
assert "failed" not in low and "missed" not in low              # rolls on, never
assert "sergeant" not in low and "recruit" not in low           # no rank names
assert "xp" not in low.replace("xpdaily", "").replace("xp daily", "")  # no XP promises
assert "h1 class=\"word display\"" in page                      # no accent class on h1
assert 'name="xpdaily-week" content="2026-08-31"' in page       # the nudge gate meta
assert 'name="xpdaily-build"' in page and "noindex" in page
assert "Solving equations with brackets" in page and "NEW" in page
assert "BOSS APPROACHING" in page and "10 days out" in page
assert page.count("OPEN") >= 6                                  # every card open
assert kw.BADGE_ICON["On the Board"] in page                    # badges shown
assert kw.BADGE_ICON["Locked It"] in page
assert kw.violations(page) == []
assert kb.render(FACTS, play_url="https://example.invalid/play") == page

# Rich's order: ground -> up for grabs -> boss radar
assert low.index("this week's ground") < low.index("up for grabs this week") \
    < low.index("boss radar")

# refusal: a law-breaching line can never ship
BAD = dict(FACTS)
BAD["grabs"] = [{"icon": "x", "fam": "CRAFT", "name": "CLEAN RUN",
                 "terms": "you should have done this last week"}]
try:
    kb.render(BAD)
    raise AssertionError("render must refuse a language-law breach")
except ValueError:
    pass

# empty-ground fail-soft still renders (stale targets Monday)
EMPTY = dict(FACTS)
EMPTY["brief"] = {"rows": [], "subjects": [], "name": "Sam", "assessment": None}
assert "sync with what school posts" in kb.render(EMPTY)

# --- the RUNNER end-to-end (dry-run on a fixture private dir) ---------------
# The 31 Aug redeploy failure was a stale key in main()'s log line that no
# test exercised. The runner itself now runs in every suite pass.
import json as _json          # noqa: E402
import subprocess              # noqa: E402
import tempfile                # noqa: E402

with tempfile.TemporaryDirectory() as _priv:
    os.makedirs(os.path.join(_priv, "work"))
    os.makedirs(os.path.join(_priv, "targets"))
    _json.dump({"runs": [
        {"student": "t1", "name": "Sam T", "run_date": "2026-08-28",
         "set_date": "2026-08-28", "score": 500, "canonical": True,
         "speed": {"of": 5, "right": 4}, "steady": {"of": 5, "right": 4},
         "shell_flags": {}}]},
        open(os.path.join(_priv, "work", "runs.json"), "w"))
    _json.dump({"students": {"t1": {"topics": TOPICS}}},
               open(os.path.join(_priv, "work", "state.json"), "w"))
    _json.dump({"students": {"t1": {"subjects": {
        "Maths": {"topics": [
            {"topic": "Solving equations with brackets", "status": "live"},
            {"topic": "Linear equations", "status": "live"}]}}}}},
        open(os.path.join(_priv, "targets", "2026-08-31.json"), "w"))
    _r = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "kid_board.py"),
         "--private-dir", _priv, "--student", "t1",
         "--date", "2026-08-31", "--dry-run"],
        capture_output=True, text=True)
    assert _r.returncode == 0, f"runner dry-run failed:\n{_r.stdout}\n{_r.stderr}"
    assert "up-for-grabs=" in _r.stdout
    assert os.path.exists(os.path.join(_priv, "work", "preview_board_t1.html"))

# --- the nudge: the board is Monday's front door (Rich's copy, 31 Aug) ------
MON = date(2026, 8, 31)
LIVE = {"date": "2026-08-31", "status": "ok"}
_, _, plain = decide(LIVE, MON, "https://play.invalid")
_, _, linked = decide(LIVE, MON, "https://play.invalid", "https://b.invalid/w/x/board/")
copy_line = plain.split("\n")[0]
assert linked == (copy_line + "\nSee what's on the board this week here: "
                  "https://b.invalid/w/x/board/")
assert "play.invalid" not in linked      # one link: the board carries PLAY
assert plain.endswith("https://play.invalid")   # no verified board -> play link
_, _, tue = decide({"date": "2026-09-01", "status": "ok"}, date(2026, 9, 1),
                   "https://play.invalid", None)
assert "board this week" not in tue and tue.endswith("https://play.invalid")

print("test_kid_board: all assertions passed")
