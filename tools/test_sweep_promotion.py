"""Tests for the B6 promotion trio: overrides, promote, docx alert."""
import json
import os
import sys
import tempfile

import sweep_docx_alert as sda
import sweep_overrides as so
import sweep_promote as sp


def _targets():
    return {
        "students": {
            "y8": {"subjects": {
                "Technology": {"topics": [
                    {"topic": "CO2 Cars / engineering design", "status": "live", "fresh": True},
                    {"topic": "Digital Technology — Python coding", "status": "live", "fresh": False},
                    {"topic": "Food Technology — kitchen safety", "status": "prior_term", "fresh": False},
                    {"topic": "Timber Spice Rack — design portfolio", "status": "prior_term", "fresh": False},
                    {"topic": "Something unrelated", "status": "upcoming", "fresh": True},
                ]},
                "Music": {"topics": [
                    {"topic": "Four-chord progression", "status": "live", "fresh": False},
                ]},
            }},
        },
    }


OVR = {
    "_": "doc line, ignored",
    "y8": {"Technology": {
        "live": "timber spice rack",
        "strands": ["CO2 Car", "Digital Technology", "Food Technology",
                    "Timber Spice Rack"],
    }},
    "y9": {"Science": {"live": "whatever", "strands": []}},
}


# ------------------------------------------------------------- overrides --

def test_override_flips_live_strand_and_parks_others():
    t = _targets()
    changed = so.apply(t, OVR)
    tech = {x["topic"]: x["status"]
            for x in t["students"]["y8"]["subjects"]["Technology"]["topics"]}
    assert tech["Timber Spice Rack — design portfolio"] == "live"
    assert tech["CO2 Cars / engineering design"] == "prior_term"
    assert tech["Digital Technology — Python coding"] == "prior_term"
    assert tech["Food Technology — kitchen safety"] == "prior_term"
    assert tech["Something unrelated"] == "upcoming"          # untouched
    assert changed[("y8", "Technology")] == (1, 2)            # only real flips counted


def test_override_never_touches_other_subjects_or_fresh_flags():
    t = _targets()
    so.apply(t, OVR)
    music = t["students"]["y8"]["subjects"]["Music"]["topics"][0]
    assert music["status"] == "live"
    tech = t["students"]["y8"]["subjects"]["Technology"]["topics"]
    assert [x["fresh"] for x in tech] == [True, False, False, False, True]
    assert len(tech) == 5                                     # never adds/removes


def test_override_missing_seat_or_empty_is_noop():
    t = _targets()
    assert so.apply(t, {"y9": {"Science": {"live": "x", "strands": []}}}) == {}
    assert so.apply(t, {}) == {}
    assert so.apply(t, None) == {}


# --------------------------------------------------------------- promote --

def test_school_week_bumps_on_consecutive_mondays():
    assert sp.bump_school_week("Term 3", "2026-08-31", "Term 3, Week 7",
                               "2026-09-07") == "Term 3, Week 8"


def test_school_week_keeps_summariser_value_on_gap_or_no_week():
    assert sp.bump_school_week("Term 3", "2026-08-24", "Term 3, Week 6",
                               "2026-09-07") == "Term 3"      # 14-day gap
    assert sp.bump_school_week("Term 3", "2026-08-31", "Term 3",
                               "2026-09-07") == "Term 3"      # no Week N
    assert sp.bump_school_week("Term 3", None, None, "2026-09-07") == "Term 3"


def test_relabel_strips_shadow_and_stamps_week():
    shadow = {"week_of": "2026-08-31", "school_week": "Term 3",
              "source": "Automated Canvas API sweep (SHADOW) — student tokens"}
    prev = {"week_of": "2026-08-31", "school_week": "Term 3, Week 7"}
    sp.relabel(shadow, "2026-09-07", prev)
    assert shadow["week_of"] == "2026-09-07"
    assert "(SHADOW)" not in shadow["source"]
    assert "PROMOTED to targets/2026-09-07.json" in shadow["source"]
    assert shadow["school_week"] == "Term 3, Week 8"


def test_promote_refuses_overwrite_without_force():
    with tempfile.TemporaryDirectory() as d:
        tdir = os.path.join(d, "targets")
        os.makedirs(tdir)
        existing = os.path.join(tdir, "2026-09-07.json")
        json.dump({"week_of": "2026-09-07", "marker": "manual"},
                  open(existing, "w"))
        shadow_path = os.path.join(d, "shadow.json")
        json.dump({"week_of": "2026-09-07", "source": "x", "students": {}},
                  open(shadow_path, "w"))
        argv = sys.argv
        sys.argv = ["sweep_promote.py", "--shadow", shadow_path,
                    "--targets-dir", tdir, "--week", "2026-09-07"]
        try:
            sp.main()
        finally:
            sys.argv = argv
        kept = json.load(open(existing))
        assert kept.get("marker") == "manual"                 # untouched


def test_promote_writes_when_absent_and_with_force():
    with tempfile.TemporaryDirectory() as d:
        tdir = os.path.join(d, "targets")
        os.makedirs(tdir)
        json.dump({"week_of": "2026-08-31", "school_week": "Term 3, Week 7"},
                  open(os.path.join(tdir, "2026-08-31.json"), "w"))
        shadow_path = os.path.join(d, "shadow.json")
        json.dump({"week_of": "2026-09-07", "school_week": "Term 3",
                   "source": "sweep (SHADOW) — x",
                   "students": {"y8": {"subjects": {"Maths": {"topics": [
                       {"topic": "Probability", "status": "live",
                        "fresh": False}]}}}}},
                  open(shadow_path, "w"))
        argv = sys.argv
        sys.argv = ["sweep_promote.py", "--shadow", shadow_path,
                    "--targets-dir", tdir, "--week", "2026-09-07"]
        try:
            sp.main()
        finally:
            sys.argv = argv
        out = json.load(open(os.path.join(tdir, "2026-09-07.json")))
        assert out["school_week"] == "Term 3, Week 8"
        assert out["week_of"] == "2026-09-07"
        # force path replaces
        json.dump({"week_of": "2026-09-07", "school_week": "Term 3",
                   "source": "sweep (SHADOW) — y", "students": {}},
                  open(shadow_path, "w"))
        sys.argv = ["sweep_promote.py", "--shadow", shadow_path,
                    "--targets-dir", tdir, "--week", "2026-09-07", "--force"]
        try:
            sp.main()
        finally:
            sys.argv = argv
        out = json.load(open(os.path.join(tdir, "2026-09-07.json")))
        assert "— y" in out["source"]


# ------------------------------------------------------------ docx alert --

def test_docx_candidates_catch_extensionless_items_and_announcements():
    dump = {
        "courses": [
            {"modules": [{"items": [
                # module item: Canvas strips the extension from the title
                {"title": "Medieval History Year 8 2026 Assessment Notification",
                 "type": "File"},
                {"title": "Week 6 slides", "type": "File"},        # no PAT match
                {"title": "Shogunate Japan intro", "type": "Page"},
            ]}]},
            {"announcements": [
                {"title": "Term 3 Assessment Task Notification",
                 "posted_at": "2026-08-26T09:00:00Z",
                 "attachments": [
                     {"filename": "Year 8 2026 Term 3 Assessment Task Notification.docx"},
                     {"filename": "revision_sheet.pdf"},           # not doc
                     {"display_name": "holiday photo.docx"},       # no PAT match
                 ]},
            ]},
            # a PAGE with a paperwork title is READABLE — must not flag
            {"pages": [{"title": "Term 3 Year 8 Assessment Notification",
                        "url": "term-3-year-8-assessment-notification"}]},
        ],
    }
    found = sda.candidates(dump)
    assert found == {
        "Medieval History Year 8 2026 Assessment Notification",
        "Term 3 Assessment Task Notification",
        "Year 8 2026 Term 3 Assessment Task Notification.docx",
    }


def test_docx_new_vs_prev_is_set_difference():
    cur = {"A Notification", "B Assessment"}
    prev_dump = {"modules": [{"items": [{"title": "A Notification",
                                         "type": "File"}]}]}
    assert cur - sda.candidates(prev_dump) == {"B Assessment"}


def test_docx_candidates_empty_on_clean_dump():
    assert sda.candidates({"a": [{"title": "notes.pdf"}],
                           "b": "exam.docx mentioned in text only"}) == set()
