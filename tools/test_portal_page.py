#!/usr/bin/env python3
"""test_portal_page.py — the portal's load-bearing guarantees (PARENT-COMMS-V2 §5).

Locks the laws that are easy to break silently: the confidently-shallow cross,
the depth ceiling, positions-weekly/trends-monthly (the 4-week gate), the
freshness stamp, and the self-contained privacy model.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import portal_page as pp   # noqa: E402


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
    "Maths": {"unit": "Algebra", "topics": [{"topic": "Linear equations", "status": "live"}]},
    "History": {"unit": "The Crusades", "topics": [{"topic": "The Crusades", "status": "live"}]},
}
RADAR = {"task": "Science test", "date": "2026-09-10", "days": 12, "subject": "Science"}


print("the confidently-shallow cross — the founding insight, per topic:")
t("solid recall over a shallow rung fires", pp._confidently_shallow("solid", "lists"))
t("solid recall with no teach-back yet fires", pp._confidently_shallow("solid", None))
t("solid recall that reached connects does NOT fire",
  pp._confidently_shallow("solid", "connects") is False)
t("a non-solid topic never fires", pp._confidently_shallow("shaky", "lists") is False)

print("\nsubject cards — both axes, weakest first, archived topics excluded:")
cards = pp.subject_cards(TOPICS)
by = {c["subject"]: c for c in cards}
t("frozen/archived topics are excluded", all(
    r["topic"] != "Old topic" for c in cards for r in c["rows"]))
t("rows are ordered weakest-first (work to do reads top-down)",
  [r["topic"] for r in by["Maths"]["rows"]][0] == "Angles on parallel lines")
lin = next(r for r in by["Maths"]["rows"] if r["topic"] == "Linear equations")
t("solid x lists is flagged confidently-shallow", lin["confidently_shallow"] is True)
frac = next(r for r in by["Maths"]["rows"] if r["topic"] == "Fractions")
t("solid x connects is not flagged", frac["confidently_shallow"] is False)

print("\nterm trends — positions weekly, trends monthly (the 4-week gate):")
few = [{"week_of": f"w{i}", "topics": {"A": "solid"}, "subjects": {"A": "Maths"}}
       for i in range(3)]
t("under four weeks, no trend is computed", pp.term_trends(few) is None)
four = [{"week_of": f"w{i}",
         "topics": {"A": ("shaky" if i < 2 else "solid"), "B": "shaky"},
         "subjects": {"A": "Maths", "B": "Maths"}} for i in range(4)]
tr = pp.term_trends(four)
t("at four weeks the trend switches on", tr is not None and tr["weeks"] == 4)
t("the trend counts landed gained over the term", tr["rows"][0]["gained"] == 1)

print("\nthe page renders honestly and privately:")
portal = pp.build_portal("Harrison", "2026-08-10", TOPICS, SUBJECTS_BLOCK, RADAR,
                         this_week={"new_or_changed": ["Solving with brackets"],
                                    "intent": "his sets steer toward it"},
                         snapshots=few, archive=[{"week": "2026-08-10",
                                                  "url": "https://x.example/r/abc/2026-08-10/"}],
                         updated="2026-08-29")
html = pp.render(portal, kid_wrap_url="https://x.example/w/abc/")
t("renders the NOW, THIS WEEK, subject and trend sections",
  all(s in html for s in ("NOW", "THIS WEEK", "BY SUBJECT", "TERM TRENDS", "ARCHIVE")))
t("the confidently-shallow note reaches the page", "Strong recall" in html)
t("evidenced depth renders its rung", "Can connect it" in html)
t("unevidenced depth renders a dash, never an inflated claim",
  "<span class='dep none'>&mdash;</span>" in html)
t("under four weeks the page SAYS the trend fills in later, not fakes it",
  "four weeks of history" in html and "don" in html.lower())
t("a visible freshness stamp (updated date) is present", "updated 2026-08-29" in html)
t("the archive links the dated report path",
  "https://x.example/r/abc/2026-08-10/" in html)
t("self-contained — zero fetch", "fetch(" not in html and "XMLHttpRequest" not in html)
t("noindex", "noindex" in html)
t("carries a build stamp inside verify()'s 4KB window",
  'name="xpdaily-build"' in html and html.index("xpdaily-build") < 3500)
t("no same-night results leak — nothing is dated today's runs",
  "tonight" not in html.lower())

print("\n✓ all portal tests green")
