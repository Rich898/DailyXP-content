#!/usr/bin/env python3
"""test_portal_run.py — the portal publisher's load-bearing guarantees.

Runs the real runner end-to-end (--dry-run) against a minimal fixture private
dir: four pages render, the ahead page carries the new week's targets and
UPCOMING DATES, the fail-soft weekly update never blocks the portal, the
pointer SMS passes the Monday law, and the portal slug lands in
report_slugs.json without touching the report/wrap slugs.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import monday_brief as mb       # noqa: E402


def t(name, cond):
    assert cond, f"FAIL: {name}"
    print(f"  [PASS] {name}")


def fixture(priv):
    os.makedirs(os.path.join(priv, "work"), exist_ok=True)
    os.makedirs(os.path.join(priv, "targets"), exist_ok=True)
    os.makedirs(os.path.join(priv, "work", "report_snapshots"), exist_ok=True)
    json.dump({"students": {"t1": {"topics": [
        {"topic": "Linear equations", "subject": "Maths", "state": "solid", "depth": "lists"},
        {"topic": "Solving equations with brackets", "subject": "Maths", "state": "shaky", "depth": None},
        {"topic": "The circulatory system", "subject": "Science", "state": "developing", "depth": None},
    ]}}}, open(os.path.join(priv, "work", "state.json"), "w"))
    # one named run: name_for() feeds the page/pointer (a nameless seat would
    # fall back to "T1", whose digit rightly trips the Monday law — the guard
    # that keeps a half-configured seat from texting anything odd)
    json.dump({"runs": [{"student": "t1", "name": "Sam",
                         "run_date": "2026-08-28", "questions": []}]},
              open(os.path.join(priv, "work", "runs.json"), "w"))

    def tblock(extra_maths):
        return {"students": {"t1": {"subjects": {
            "Maths": {"unit": "Algebra", "topics":
                      [{"topic": "Linear equations", "status": "live"}] + extra_maths},
            "Science": {"unit": "Body systems", "topics": [
                {"topic": "The circulatory system", "status": "live",
                 "assessment": {"task": "Science topic test", "date": "2026-09-10"}}]},
            "English": {"unit": "Persuasive writing", "topics": [
                {"topic": "Persuasive techniques", "status": "live"}]},
        }}}}
    json.dump(tblock([]), open(os.path.join(priv, "targets", "2026-08-24.json"), "w"))
    json.dump(tblock([{"topic": "Solving equations with brackets", "status": "live"}]),
              open(os.path.join(priv, "targets", "2026-08-31.json"), "w"))
    json.dump({"week_of": "2026-08-24",
               "t1": {"Linear equations": "developing"}, "t1_depth": {}},
              open(os.path.join(priv, "work", "report_snapshots", "2026-08-24.json"), "w"))
    json.dump({"t1": {"report": "aaaaaaaaaaaaaaaaaa", "wrap": "bbbbbbbbbbbbbbbbbb"}},
              open(os.path.join(priv, "work", "report_slugs.json"), "w"))


with tempfile.TemporaryDirectory() as priv:
    fixture(priv)
    print("portal_run --dry-run against the fixture private dir:")
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "portal_run.py"),
         "--private-dir", priv, "--student", "t1",
         "--date", "2026-08-31", "--dry-run"],
        capture_output=True, text=True)
    print("  " + " / ".join(l for l in r.stdout.splitlines() if l))
    t("the runner exits clean", r.returncode == 0)

    pages = {}
    for label in ("home", "ahead", "week", "picture"):
        p = os.path.join(priv, "work", f"preview_portal_t1_{label}.html")
        t(f"preview page written: {label}", os.path.exists(p))
        pages[label] = open(p).read()

    t("the ahead page carries the NEW week's targets — brackets is new",
      "Solving equations with brackets" in pages["ahead"]
      and "Moves into" in pages["ahead"])
    t("UPCOMING DATES renders from the targets' dated assessment",
      "UPCOMING DATES" in pages["ahead"] and "Science topic test" in pages["ahead"])
    t("the per-teacher hedge rides through for English",
      "treat as a guide this week" in pages["ahead"])
    t("fail-soft: the weekly update ships (real facts or the honest empty state)",
      "Weekly update" in pages["week"])
    t("the overall picture maps the ledger",
      "The overall picture" in pages["picture"]
      and "Solving equations with brackets" in pages["picture"])
    t("every page is stamped for verify()",
      all('name="xpdaily-build"' in h for h in pages.values()))
    t("no real names in the public-log stdout (codes only)",
      "t1" in r.stdout and "Linear equations" not in r.stdout)

    sms_path = os.path.join(priv, "work", "preview_portal_t1.sms.txt")
    t("the pointer SMS preview is written", os.path.exists(sms_path))
    body = open(sms_path).read()
    ok, why = mb.validate(body, "Sam", subjects=["Maths", "Science", "English"])
    t(f"the pointer passes the Monday law ({why})", ok)
    t("the kid's name stays out of the public-log stdout", "Sam" not in r.stdout)
    t("the pointer links the ahead page", "/p/" in body and "/ahead/" in body)

    slugs = json.load(open(os.path.join(priv, "work", "report_slugs.json")))
    t("a portal slug was minted, lowercase, report/wrap untouched",
      slugs["t1"]["report"] == "aaaaaaaaaaaaaaaaaa"
      and slugs["t1"]["wrap"] == "bbbbbbbbbbbbbbbbbb"
      and slugs["t1"]["portal"] == slugs["t1"]["portal"].lower()
      and len(slugs["t1"]["portal"]) >= 16)

    print("\nre-run: slug is stable (a parent's bookmark keeps working):")
    r2 = subprocess.run(
        [sys.executable, os.path.join(HERE, "portal_run.py"),
         "--private-dir", priv, "--student", "t1",
         "--date", "2026-08-31", "--dry-run"],
        capture_output=True, text=True)
    slugs2 = json.load(open(os.path.join(priv, "work", "report_slugs.json")))
    t("second run exits clean", r2.returncode == 0)
    t("the portal slug did not rotate", slugs2["t1"]["portal"] == slugs["t1"]["portal"])

print("\n✓ all portal_run tests green")
