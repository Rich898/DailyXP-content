#!/usr/bin/env python3
"""
seed_menu.py — reconcile the scraped curriculum (the "menu") into the mastery
ledger, so every topic the kids have studied is trackable and askable.

DOCTRINE (locked 20 Aug 2026 — the outline-drives-the-quiz inversion):
  - The MENU is the whole covered curriculum: every topic that has appeared as
    status "live" in ANY weekly scrape. It only grows across a term.
  - Every scraped topic is written into the ledger as `untested` on first sight,
    stamped with `introduced_week` (the earliest week it appeared) so the planner
    can tell THIS WEEK (latest scrape) from PRIOR WEEKS (the throwback pool).
  - Seeding is ADDITIVE and idempotent: it NEVER changes an existing topic's
    mastery state — it only adds new topics and backfills the week stamp.

The planner then fills THIS-WEEK-FIRST from the full menu; the ledger only ranks,
it never caps. A player quizzes on its curriculum alias (roster.targets_alias):
e.g. the adult test seat t1 quizzes the y8 curriculum.
"""
import datetime as dt
import glob
import json
import os

W1_MONDAY = dt.date(2026, 7, 27)   # project week 1 = w/c Mon 27 Jul 2026 (mirrors run_daily)


def week_of(date_str):
    d = dt.date.fromisoformat(date_str)
    return ((d - W1_MONDAY).days // 7) + 1


def scrape_files(targets_dir):
    return sorted(glob.glob(os.path.join(targets_dir, "*.json")))


def build_menu(alias_code, targets_dir):
    """{topic: {subject, introduced_week}} across ALL scrapes for one curriculum.
    introduced_week = the EARLIEST scrape (by date) the topic was live in."""
    menu = {}
    for path in scrape_files(targets_dir):            # oldest -> newest
        date_str = os.path.basename(path)[:-5]        # strip .json
        try:
            wk = week_of(date_str)
            d = json.load(open(path))
        except Exception:
            continue
        stud = d.get("students", {}).get(alias_code)
        if not stud:
            continue
        for subj, block in stud.get("subjects", {}).items():
            for t in block.get("topics", []):
                if t.get("status") != "live":
                    continue
                name = t.get("topic")
                if not name:
                    continue
                if name not in menu:                  # first time seen = introduced week
                    menu[name] = {"subject": subj, "introduced_week": wk}
    return menu


def latest_week(targets_dir):
    files = scrape_files(targets_dir)
    return week_of(os.path.basename(files[-1])[:-5]) if files else None


def seed_player(state, player, alias_code, targets_dir):
    """Additively reconcile the menu into a player's ledger. Returns a report.
    Never mutates an existing topic's mastery — only adds topics + backfills stamps."""
    menu = build_menu(alias_code, targets_dir)
    stud = state.setdefault("students", {}).setdefault(player, {"topics": []})
    topics = stud.setdefault("topics", [])
    by_name = {t["topic"]: t for t in topics}
    added, stamped = [], 0
    for name, meta in menu.items():
        if name in by_name:
            t = by_name[name]
            if "introduced_week" not in t:            # backfill stamp, never touch mastery
                t["introduced_week"] = meta["introduced_week"]
                stamped += 1
        else:
            topics.append({
                "subject": meta["subject"], "topic": name,
                "state": "untested", "repair": False,
                "last_tested": None, "times_seen": 0, "note": "",
                "introduced_week": meta["introduced_week"],
            })
            added.append(name)
    return {
        "player": player, "alias": alias_code, "menu_size": len(menu),
        "ledger_before": len(by_name), "added": added,
        "stamped_existing": stamped, "ledger_after": len(topics),
    }
