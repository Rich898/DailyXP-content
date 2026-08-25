#!/usr/bin/env python3
"""
sweep_summarise.py — the sweep SUMMARISER (limb #1b of the automated sweep).

CARRY-FORWARD LAW (ratified 25 Aug 2026): the first sweep creates a seat's
outline; every sweep after is an UPDATE applied to the previous file. Topics
transition (upcoming->live->prior_term), gain corrected dates, and new ones
join — but a topic NEVER leaves by omission. Absence from a pull is not
evidence of removal. Removal is only ever explicit (flagged, human-decided)
or the end-of-year rollover. The merge is enforced in CODE: any base topic
the LLM fails to echo is reinserted by the guard, and sweep_validate.py
hard-fails any output where a base topic is missing. Blank-slating is not a
mistake we avoid; it is a thing the gate refuses to ship.

Division of labour (doctrine): CODE decides structure — course
classification, subject dialect (HSIE->History/Geography split, Maths L/I ->
Maths, D&T), the schema, the merge, the changelog. The LLM writes LANGUAGE
only: condensing course content into topics and transitioning statuses. It
never holds state and is never trusted with the never-drop guarantee.

Date discipline: an assessment date is only ever an explicit calendar date
found in the source. Relative phrases ("Week 6", "Thursday") stay out of the
date field and go into date_confidence instead.

Shadow-safe: writes only where --out points. Never targets/.

Usage:
  python3 tools/sweep_summarise.py --dump private/shadow/sweeps/<date> \
      --out .../targets-shadow.json --manual-dir private/targets \
      [--base private/targets/<prev>.json] [--seat y8] [--dry-run]
"""
import argparse
import datetime as dt
import glob
import html
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_diff import match  # fuzzy topic matcher (rename detection)

MODEL = os.environ.get("DAILYXP_SWEEP_MODEL", "claude-sonnet-4-6")
API_URL = "https://api.anthropic.com/v1/messages"
CONTENT_BUDGET_CHARS = 14000
ANNOUNCE_CAP = 12
LLM_RETRIES = 2

EXCLUDE = re.compile(r"year group|sport|counsellor|wellbeing|beyond bally|"
                     r"competition|library|careers", re.I)
ACADEMIC = re.compile(r"^Year\s+(\d+)\s+(.+?)\s+2026$")
SUBJECT_ALIASES = {"Design and Technology": "D&T"}
HSIE_STRANDS = ("History", "Geography")
STATUSES = {"live", "upcoming", "not_yet_posted", "prior_term"}


def log(msg):
    print(msg, flush=True)


def strip_html(raw):
    if not raw:
        return ""
    s = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", raw)
    s = re.sub(r"(?i)<li\b[^>]*>", "\n- ", s)
    s = re.sub(r"(?i)<(br|/p|/div|/tr|/h[1-6])\b[^>]*>", "\n", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def classify(course_name):
    """-> (subject or None, is_hsie). None = noticeboard shell, excluded."""
    if EXCLUDE.search(course_name or ""):
        return None, False
    m = ACADEMIC.match((course_name or "").strip())
    if not m:
        return None, False
    subject = m.group(2).strip()
    subject = re.sub(r"\s+[A-Z]$", "", subject)
    subject = SUBJECT_ALIASES.get(subject, subject)
    return subject, subject.upper() == "HSIE"


def course_payload(course):
    parts = []
    fp = course.get("front_page")
    if fp and fp.get("body"):
        parts.append("== COURSE HOMEPAGE (week-by-week schedules often live "
                     f"here) — updated {fp.get('updated_at')} ==\n"
                     + strip_html(fp["body"]))
    for p in [p for p in course.get("pages", []) if p.get("body")]:
        parts.append(f"== PAGE: {p.get('title')} (updated {p.get('updated_at')}) ==\n"
                     + strip_html(p["body"]))
    mods = course.get("modules", [])
    if mods:
        lines = []
        for m in mods:
            items = ", ".join(i.get("title") or "" for i in m.get("items", []))
            lines.append(f"- {m.get('name')}: {items}")
        parts.append("== MODULE STRUCTURE (the unit's full arc — earlier "
                     "items were taught in past weeks) ==\n" + "\n".join(lines))
    anns = sorted(course.get("announcements", []),
                  key=lambda a: a.get("posted_at") or a.get("created_at") or "",
                  reverse=True)[:ANNOUNCE_CAP]
    if anns:
        lines = [f"- [{(a.get('posted_at') or a.get('created_at') or '')[:10]}] "
                 f"{a.get('title')}: {strip_html(a.get('message'))[:400]}"
                 for a in anns]
        parts.append("== RECENT ANNOUNCEMENTS ==\n" + "\n".join(lines))
    assigns = course.get("assignments", [])
    if assigns:
        lines = [f"- {a.get('name')} | due {a.get('due_at') or 'no date'} | "
                 f"{a.get('points_possible')} pts | "
                 f"{strip_html(a.get('description'))[:300]}"
                 for a in assigns]
        parts.append("== ASSIGNMENTS (authoritative explicit dates) ==\n"
                     + "\n".join(lines))
    text = "\n\n".join(parts)
    truncated = len(text) > CONTENT_BUDGET_CHARS
    return text[:CONTENT_BUDGET_CHARS], truncated


def base_block(base_topics, hsie):
    if not base_topics:
        return ""
    lines = []
    for strand, t in base_topics:
        row = {"topic": t.get("topic"), "status": t.get("status"),
               "fresh": t.get("fresh"), "assessment": t.get("assessment")}
        if hsie:
            row["strand"] = strand
        lines.append(json.dumps(row, ensure_ascii=False))
    return ("\n\n== EXISTING OUTLINE (carry-forward base) ==\n"
            "Every topic below MUST appear in your output with its name "
            "repeated EXACTLY, character for character. Update status/fresh/"
            "assessment where the evidence says so; statuses transition "
            "(upcoming->live when teaching starts, live->prior_term when the "
            "class moves on). prior_term topics are KEPT — they are revision "
            "threads, especially where a term assessment covers them. If you "
            "believe a base topic was a scrape error, still include it and "
            "add \"remove_reason\": \"<why>\" — never omit it.\n"
            + "\n".join(lines))


def system_prompt(legends, today, hsie, has_base):
    strand_rule = ("\n- This course is HSIE, split into History and Geography "
                   'subjects: every topic MUST carry "strand": "History" or '
                   '"Geography".' if hsie else "")
    carry_rule = ("\n- An EXISTING OUTLINE is provided: your output is an "
                  "UPDATE of it, never a fresh start. Echo every base topic "
                  "name exactly; add new topics for newly taught content."
                  if has_base else "")
    extra = ('"remove_reason": "<only to flag a scrape error>", ' if has_base
             else "")
    strand_field = ('"strand": "History|Geography", ' if hsie else "")
    return (
        f"You maintain one school Canvas course's teaching outline for a quiz "
        f"planner. Today is {today} (Term 3, NSW Australia).\n\n"
        "Return STRICT JSON only — no prose, no code fences:\n"
        '{"unit": "<2-3 sentence plain summary of where the class is up to, '
        'with dates>",\n'
        ' "topics": [{"topic": "<short quizzable topic name>", '
        '"status": "live|upcoming|not_yet_posted|prior_term", '
        '"fresh": true|false, ' + strand_field + extra +
        '"assessment": null | {"task": "<name>", "date": "YYYY-MM-DD or null", '
        '"date_confidence": "<CONFIRMED/LIKELY + which surface says so>"}}]}\n\n'
        f"Status meanings (use exactly these): "
        f"{json.dumps(legends.get('status_legend', {}))}\n"
        f"fresh flag: {json.dumps(legends.get('fresh_flag_legend', {}))}\n\n"
        "Rules:\n"
        "- Topic granularity = one quizzable unit, like \"Venn diagrams "
        "(probability)\" or \"Linear equations (solve for x, balance rule)\". "
        "Use MODULE STRUCTURE to include the unit's already-taught arc as "
        "topics (fresh=false), not just this week's edge.\n"
        "- DATES: only ever an explicit calendar date stated in the source. "
        "NEVER derive a date from relative phrases (\"Week 6\", \"Thursday\", "
        "\"next week\") — in that case leave date null and put the phrase in "
        "date_confidence. ASSIGNMENTS dates are authoritative; homepage "
        "schedules strong; announcements supporting.\n"
        "- Use this course's own year level exactly as named; never guess "
        "another.\n"
        "- NEVER invent content. No current teaching content -> "
        '{"unit": "No current content posted.", "topics": []}.'
        + carry_rule + strand_rule)


def call_llm(system, user):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        sys.exit("sweep_summarise: ANTHROPIC_API_KEY not set")
    body = json.dumps({"model": MODEL, "max_tokens": 3000, "temperature": 0,
                       "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01",
        "content-type": "application/json"})
    last = None
    for attempt in range(1, LLM_RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                data = json.loads(r.read())
            text = "".join(b.get("text", "") for b in data.get("content", []))
            text = re.sub(r"^```(json)?|```$", "", text.strip(),
                          flags=re.M).strip()
            return json.loads(text)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * attempt)
    raise RuntimeError(f"LLM failed after retries: {last}")


def sane_topic(t, hsie):
    if not isinstance(t, dict) or not t.get("topic"):
        return None
    out = {"topic": str(t["topic"]).strip(),
           "status": t.get("status") if t.get("status") in STATUSES else "live",
           "fresh": bool(t.get("fresh", False)),
           "assessment": None}
    a = t.get("assessment")
    if isinstance(a, dict) and a.get("task"):
        date = a.get("date")
        if date and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
            date = None
        out["assessment"] = {"task": str(a["task"]), "date": date,
                             "date_confidence": str(a.get("date_confidence")
                                                    or "unstated")}
    if t.get("remove_reason"):
        out["_remove_reason"] = str(t["remove_reason"])
    if hsie:
        s = str(t.get("strand") or "").title()
        out["_strand"] = s if s in HSIE_STRANDS else "History"
    return out


def merge_subject(base_topics, llm_topics):
    """THE CARRY-FORWARD GUARD. Base topics can transition; they cannot leave.
    Returns (merged topics, changelog)."""
    chg = {"added": [], "transitioned": [], "assessment_updated": [],
           "carried": 0, "guard_reinserted": [], "renamed_carry": [],
           "flagged_for_removal": []}
    base_by_name = {t["topic"]: t for t in (base_topics or [])}
    out, seen = [], set()
    for lt in llm_topics:
        lt = dict(lt)
        flag = lt.pop("_remove_reason", None)
        name = lt["topic"]
        if flag:
            chg["flagged_for_removal"].append({"topic": name, "reason": flag})
        bt = base_by_name.get(name)
        if bt is not None:
            seen.add(name)
            chg["carried"] += 1
            if lt.get("status") != bt.get("status"):
                chg["transitioned"].append({"topic": name,
                                            "from": bt.get("status"),
                                            "to": lt.get("status")})
            if (lt.get("assessment") or None) != (bt.get("assessment") or None):
                chg["assessment_updated"].append(name)
        out.append(lt)
    for name, bt in base_by_name.items():
        if name in seen:
            continue
        hit = next((t for t in out
                    if t["topic"] not in base_by_name
                    and match(name, t["topic"])), None)
        if hit is not None:  # the LLM reworded a carried topic; base name wins
            chg["renamed_carry"].append({"base": name, "llm_said": hit["topic"]})
            hit["topic"] = name
            seen.add(name)
            chg["carried"] += 1
            if hit.get("status") != bt.get("status"):
                chg["transitioned"].append({"topic": name,
                                            "from": bt.get("status"),
                                            "to": hit.get("status")})
        else:  # THE GUARD: never dropped
            out.append(dict(bt))
            chg["guard_reinserted"].append(name)
            seen.add(name)
    chg["added"] = [t["topic"] for t in out if t["topic"] not in base_by_name]
    return out, chg


def newest_manual(manual_dir):
    files = sorted(glob.glob(os.path.join(manual_dir, "*.json")))
    return files[-1] if files else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manual-dir", default="private/targets")
    ap.add_argument("--base", help="previous targets file — the carry-forward "
                                   "base this sweep UPDATES")
    ap.add_argument("--seat")
    ap.add_argument("--dry-run", action="store_true",
                    help="no LLM: base carries forward verbatim via the guard")
    args = ap.parse_args()

    stamp = os.path.basename(os.path.normpath(args.dump))
    stamp_d = dt.date.fromisoformat(stamp)
    week_of = (stamp_d - dt.timedelta(days=stamp_d.weekday())).isoformat()
    today = stamp_d.isoformat()

    legends = {}
    school_week = "Term 3"
    manual = newest_manual(args.manual_dir)
    if manual:
        md = json.load(open(manual, encoding="utf-8"))
        legends = {k: md[k] for k in ("fresh_flag_legend", "status_legend")
                   if k in md}
        if md.get("week_of") == week_of and md.get("school_week"):
            school_week = md["school_week"]

    base_students = {}
    if args.base:
        base_students = json.load(open(args.base,
                                       encoding="utf-8")).get("students", {})

    out = {
        "week_of": week_of,
        "school_week": school_week,
        "source": (f"Automated Canvas API sweep (SHADOW) — student tokens, six "
                   f"content surfaces; dump {stamp}; carry-forward base "
                   f"{os.path.basename(args.base) if args.base else 'NONE (first sweep)'}; "
                   f"summarised {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}"),
        "fidelity_note": "",
        "layer": ("TARGETING ONLY. This file = what is live in class + when "
                  "it's assessed (the sweep's job)."),
        **legends,
        "students": {},
        "sweep_update": {"base": (os.path.basename(args.base)
                                  if args.base else None), "seats": {}},
    }

    excluded, failed, truncs, llm_calls = [], [], 0, 0
    for seat_file in sorted(glob.glob(os.path.join(args.dump, "*.json"))):
        code = os.path.splitext(os.path.basename(seat_file))[0]
        if code == "manifest" or (args.seat and code != args.seat):
            continue
        dump = json.load(open(seat_file, encoding="utf-8"))
        bsubs = (base_students.get(code, {}) or {}).get("subjects", {})
        subjects, seat_chg = {}, {}
        for course in dump.get("courses", []):
            subject, hsie = classify(course.get("name"))
            if subject is None:
                excluded.append(course.get("name"))
                continue
            targets_subjects = (list(HSIE_STRANDS) if hsie else [subject])
            base_pairs = [(s, t) for s in targets_subjects
                          for t in (bsubs.get(s, {}) or {}).get("topics", [])]
            payload, cut = course_payload(course)
            truncs += cut
            payload += base_block(base_pairs, hsie)
            if args.dry_run:
                res = {"unit": "(dry-run)", "topics": []}
            else:
                try:
                    llm_calls += 1
                    res = call_llm(system_prompt(legends, today, hsie,
                                                 bool(base_pairs)), payload)
                except Exception as e:  # noqa: BLE001
                    failed.append(f"{code}/{course.get('name')}: {e}")
                    res = None
            if res is None:
                for s in targets_subjects:
                    bt = (bsubs.get(s, {}) or {}).get("topics", [])
                    subjects[s] = {"unit": (bsubs.get(s, {}) or {}).get(
                        "unit", "") + " [SWEEP FAILED — base carried "
                        "verbatim]", "topics": [dict(t) for t in bt]}
                    seat_chg[s] = {"guard_reinserted": [t["topic"]
                                                       for t in bt],
                                   "sweep_failed": True}
                continue
            topics = [t for t in (sane_topic(x, hsie)
                                  for x in res.get("topics", [])) if t]
            for s in targets_subjects:
                if hsie:
                    mine = [{k: v for k, v in t.items() if k != "_strand"}
                            for t in topics if t.get("_strand") == s]
                else:
                    mine = topics
                merged, chg = merge_subject(
                    (bsubs.get(s, {}) or {}).get("topics", []), mine)
                if merged or s in bsubs or not hsie or s == "History":
                    subjects[s] = {"unit": str(res.get("unit", "")).strip(),
                                   "topics": merged}
                    seat_chg[s] = chg
                    log(f"{code}/{s}: {len(merged)} topics "
                        f"(+{len(chg['added'])} new, "
                        f"{len(chg['transitioned'])} transitioned, "
                        f"guard reinserted {len(chg['guard_reinserted'])})")
        out["students"][code] = {"subjects": subjects}
        out["sweep_update"]["seats"][code] = seat_chg

    out["fidelity_note"] = (
        f"Automated shadow sweep: {llm_calls} academic courses summarised, "
        f"{len(failed)} failed (base carried verbatim on failure), "
        f"{truncs} truncated to budget. Noticeboard shells excluded: "
        f"{sorted(set(excluded))}."
        + (f" FAILURES: {failed}" if failed else ""))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"wrote {args.out} — seats: {', '.join(out['students'])} | "
        f"excluded shells: {len(set(excluded))} | failures: {len(failed)}")
    if failed:
        sys.exit(3)


if __name__ == "__main__":
    main()
