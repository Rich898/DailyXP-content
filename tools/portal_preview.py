#!/usr/bin/env python3
"""
portal_preview.py — render the four portal pages with SAMPLE data, for design
review (the operator preview window, PARENT-COMMS-V2 §9.3).

Writes preview/portal/{index.html, ahead/, week/, picture/} with working
relative navigation, so the whole portal can be walked straight off a checkout
(or any static host that mirrors the directory shape). Run from anywhere:

    python3 tools/portal_preview.py

EVERYTHING HERE IS INVENTED. "Sam" is not a student; the topics are shaped on
the t1 seat's curriculum (y8 alias) so the density and vocabulary are honest,
but no ledger, run, or sweep data is read — this file must stay runnable in the
public repo with zero private inputs (codes-only law). The archive / player-card
/ full-report links are '#' placeholders: they exist to show the designed
elements, and are wired to real slugs by the (separate, later) deploy runner.

The pictured moment is a MONDAY EVENING in week 4: the Week Ahead has just
refreshed for the new week, This Week still shows the Friday just gone, and the
Running Picture holds three banked weeks — so the term-trend gate's honest
"fills in at four weeks" state is on display rather than papered over.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import monday_brief as mb       # noqa: E402
import portal_page as pp        # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "preview", "portal")

NAME = "Sam"
WEEK_OF = "2026-08-31"          # the new week (Monday evening refresh)
UPDATED = "2026-08-31"

# --- what school posted for the new week (the targets block, sweep-shaped) ---
SUBJECTS_BLOCK = {
    "Maths": {"unit": "Algebra", "topics": [
        {"topic": "Linear equations", "status": "live"},
        {"topic": "Solving equations with brackets", "status": "live"}]},
    "Science": {"unit": "Body systems", "topics": [
        {"topic": "How body systems work together", "status": "live"}]},
    "English": {"unit": "Persuasive writing", "topics": [
        {"topic": "Persuasive techniques", "status": "live"},
        {"topic": "Structuring an argument", "status": "live"}]},
    "History": {"unit": "The Crusades", "topics": [
        {"topic": "Causes of the First Crusade", "status": "live"},
        {"topic": "Primary sources", "status": "live"}]},
}
PREV_BLOCK = {
    "Maths": {"topics": [{"topic": "Linear equations", "status": "live"}]},
    "Science": {"topics": [{"topic": "The circulatory system", "status": "live"}]},
    "English": {"topics": [{"topic": "Persuasive techniques", "status": "live"},
                           {"topic": "Structuring an argument", "status": "live"}]},
    "History": {"topics": [{"topic": "Causes of the First Crusade", "status": "live"},
                           {"topic": "Key figures of the Crusades", "status": "live"}]},
}
RADAR = {"task": "Science topic test", "date": "2026-09-10", "days": 10,
         "subject": "Science"}
# every dated thing on the radar — tests, study-guide releases, due dates
UPCOMING = [
    {"task": "Science topic test", "date": "2026-09-10", "days": 10,
     "subject": "Science"},
    {"task": "Maths study guide released", "date": "2026-09-14",
     "subject": "Maths"},
    {"task": "English persuasive speech due", "date": "2026-09-18",
     "subject": "English"},
]

# --- the ledger's active topics (the Running Picture's rows) ---
TOPICS = [
    {"topic": "Linear equations", "subject": "Maths", "state": "solid", "depth": "lists"},
    {"topic": "Fractions of amounts", "subject": "Maths", "state": "solid", "depth": "connects"},
    {"topic": "Solving equations with brackets", "subject": "Maths", "state": "shaky", "depth": None},
    {"topic": "Angles on parallel lines", "subject": "Maths", "state": "REPAIR", "depth": None},
    {"topic": "The circulatory system", "subject": "Science", "state": "developing", "depth": "knows"},
    {"topic": "The respiratory system", "subject": "Science", "state": "developing", "depth": None},
    {"topic": "States of matter", "subject": "Science", "state": "solid", "depth": "connects"},
    {"topic": "Persuasive techniques", "subject": "English", "state": "developing", "depth": "knows"},
    {"topic": "Language devices", "subject": "English", "state": "untested", "depth": None},
    {"topic": "Causes of the First Crusade", "subject": "History", "state": "solid", "depth": "connects"},
    {"topic": "Key figures of the Crusades", "subject": "History", "state": "developing", "depth": "knows"},
    {"topic": "The People's Crusade", "subject": "History", "state": "REPAIR", "depth": None},
]

# --- the Friday just gone: the subject spine (report_stories.subject_blocks
#     shape, hand-set so the preview reads real without private inputs) ---
THIS_WEEK_OF = "2026-08-24"     # the Monday of the REPORTED week (Mon 24 – Fri 28)
THIS_WEEK_BLOCKS = [
    {"subject": "Maths", "unit": "Algebra",
     "worked": ["Linear equations", "Solving equations with brackets",
                "Angles on parallel lines"],
     "topics": [
         {"topic": "Linear equations", "state": "solid", "depth": "lists",
          "moved": "up", "asked": 4, "right": 3},
         {"topic": "Solving equations with brackets", "state": "shaky",
          "depth": None, "moved": "new", "asked": 3, "right": 1},
         {"topic": "Angles on parallel lines", "state": "REPAIR", "depth": None,
          "moved": None, "asked": 2, "right": 1}],
     # the Maths detail slot gets the fluency catch (folded in by the page);
     # this misconception stays as the fallback the engine would have used.
     "detail": {"picked": "x = 5", "correct": "x = 3",
                "why": "Expanding 3(x + 2) gives 3x + 6, not 3x + 2 — the bracket "
                       "multiplies both terms, and that one slip moves the whole answer."},
     "next": "Solving equations with brackets back for another look; Linear "
             "equations eases to light maintenance"},
    {"subject": "Science", "unit": "Body systems",
     "worked": ["The circulatory system", "The respiratory system"],
     "topics": [
         {"topic": "The circulatory system", "state": "developing",
          "depth": "knows", "moved": "up", "asked": 3, "right": 2},
         {"topic": "The respiratory system", "state": "developing", "depth": None,
          "moved": "new", "asked": 2, "right": 2}],
     "detail": {"picked": "The heart oxygenates the blood",
                "correct": "The lungs oxygenate the blood",
                "why": "The heart pumps blood; the oxygen itself is loaded in the "
                       "lungs' alveoli — keeping the two jobs separate is the whole idea."},
     "next": None},
    {"subject": "History", "unit": "The Crusades",
     "worked": ["Causes of the First Crusade", "Key figures of the Crusades"],
     "topics": [
         {"topic": "Causes of the First Crusade", "state": "solid",
          "depth": "connects", "moved": None, "asked": 2, "right": 2},
         {"topic": "Key figures of the Crusades", "state": "developing",
          "depth": "knows", "moved": "up", "asked": 3, "right": 2}],
     "detail": None,
     "next": "Primary sources joins the rotation"},
]

# --- three banked weekly snapshots: the honest under-four-weeks trend state ---
SNAPSHOTS = [
    {"week_of": "2026-08-10",
     "topics": {"Linear equations": "developing", "Fractions of amounts": "solid",
                "States of matter": "developing"},
     "subjects": {"Linear equations": "Maths", "Fractions of amounts": "Maths",
                  "States of matter": "Science"}},
    {"week_of": "2026-08-17",
     "topics": {"Linear equations": "developing", "Fractions of amounts": "solid",
                "States of matter": "solid",
                "Causes of the First Crusade": "developing"},
     "subjects": {"Linear equations": "Maths", "Fractions of amounts": "Maths",
                  "States of matter": "Science",
                  "Causes of the First Crusade": "History"}},
    {"week_of": "2026-08-24",
     "topics": {"Linear equations": "solid", "Fractions of amounts": "solid",
                "States of matter": "solid",
                "Causes of the First Crusade": "solid"},
     "subjects": {"Linear equations": "Maths", "Fractions of amounts": "Maths",
                  "States of matter": "Science",
                  "Causes of the First Crusade": "History"}},
]

ARCHIVE = [{"week": "2026-08-28", "url": "#"},
           {"week": "2026-08-21", "url": "#"},
           {"week": "2026-08-14", "url": "#"}]


def build():
    brief = mb.week_ahead(NAME, SUBJECTS_BLOCK, PREV_BLOCK, RADAR,
                          unverified=("English",))
    portal = pp.build_portal(
        NAME, WEEK_OF, TOPICS, SUBJECTS_BLOCK, RADAR,
        week_ahead=brief,
        this_week_blocks=THIS_WEEK_BLOCKS,
        this_week_fluency="Linear equations",
        this_week_of=THIS_WEEK_OF,
        snapshots=SNAPSHOTS,
        archive=ARCHIVE,
        updated=UPDATED,
        week_verdict={"word": "solid"},
        activity={"days_done": 4, "possible": 5, "topics_practised": 7,
                  "events": 1},
        upcoming=UPCOMING,
    )
    return pp.render_pages(portal, kid_wrap_url="#")


def write(pages, out=OUT):
    paths = {"": "index.html", "ahead": "ahead/index.html",
             "week": "week/index.html", "picture": "picture/index.html"}
    written = []
    for key, rel in paths.items():
        path = os.path.join(out, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(pages[key])
        written.append(path)
    return written


if __name__ == "__main__":
    for p in write(build()):
        print(f"  wrote {os.path.relpath(p)}")
    print("open preview/portal/index.html and walk the nav.")
