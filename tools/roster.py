#!/usr/bin/env python3
"""
roster.py — the single source of truth for WHO EXISTS (the account structure).

Reads roster.json at the repo root. Codes only, never PII: names arrive from
private runs at runtime; phone numbers live only in Actions secrets, resolved
by notify.py as MOBILE_MESSAGE_TO_<CODE> (the kid seat) and
MOBILE_MESSAGE_PARENTS_<CODE> (that kid's parent seat — per-kid on purpose:
different kids can have different parent sets, even inside one family).

Adding a player = one roster entry + two secrets + a seeded state block +
a stamped shell page. Nothing else should need to know the student list.
"""
import json
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path=None):
    return json.load(open(path or os.path.join(_ROOT, "roster.json")))


def students(path=None):
    return [s["code"] for s in load(path)["students"]]


def active(path=None):
    return [s["code"] for s in load(path)["students"] if s.get("active", True)]


def entry(code, path=None):
    for s in load(path)["students"]:
        if s["code"] == code:
            return s
    return None


def tag_initial(code, path=None):
    e = entry(code, path)
    return (e or {}).get("tag_initial", code[:1].upper())


def targets_alias(code, path=None):
    """The curriculum this player quizzes on (their own code unless aliased)."""
    e = entry(code, path)
    return (e or {}).get("targets_alias") or code


def alias_targets(targets, codes, path=None):
    """Inject each aliased player's curriculum block under their own code, so
    downstream readers (planner.load_targets_for and everything built on it)
    need no knowledge of aliasing — the scripts/run_daily.py pattern. The
    sweep SKIPS aliased seats (sweep_fetch writes them no block), so an
    aliased seat must borrow its alias's block at read time; missing this
    call is why t1's first Week Ahead page shipped empty (31 Aug 2026).
    Mutates and returns targets; {} and blockless files pass through."""
    st = (targets or {}).get("students") or {}
    for c in codes:
        al = targets_alias(c, path)
        if al != c and c not in st and al in st:
            st[c] = st[al]
    return targets


def play_url(code, path=None):
    """The kid's permanent Netlify quiz link (public). Empty string if not set."""
    e = entry(code, path)
    return ((e or {}).get("play_url") or "").strip()
