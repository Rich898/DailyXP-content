#!/usr/bin/env python3
"""
sweep_summarise.py — the sweep SUMMARISER (limb #1b of the automated sweep).

Turns the raw per-seat Canvas dump (sweep_fetch.py) into a targets-format
file. The split of labour is doctrine: CODE decides structure — which courses
count, subject names, the output schema, assessment-date merging — and the
LLM writes LANGUAGE ONLY: condensing a course's current content into the
week's topic outline. The LLM never picks which courses exist and never
holds state.

Output schema = exactly targets/<monday>.json as the planner consumes it:
  students.<seat>.subjects.<Subject> = {unit: str, topics: [
    {topic, status: live|upcoming|not_yet_posted|prior_term, fresh: bool,
     assessment: null | {task, date, date_confidence}}]}
plus the standard top-level fields; legends are carried verbatim from the
newest manual targets file so the dialect never drifts.

School-dialect rules encoded here (from the manual sweeps):
  - academic course = "Year N <Subject> [class-letter] 2026"; everything else
    (Sport, Counsellor, Year Group, Beyond Bally, competitions) is a
    noticeboard shell and is EXCLUDED before the LLM ever sees it.
  - "Maths L"/"Maths I" -> Maths; "Design and Technology" -> D&T.
  - y8 "HSIE" is one Canvas course but TWO subjects in targets: the LLM tags
    each topic with a strand (History|Geography) and code splits the entry.

Shadow-safe: writes only where --out points. Never targets/.

Usage:
  python3 tools/sweep_summarise.py --dump private/shadow/sweeps/2026-08-25 \
      --out private/shadow/sweeps/2026-08-25/targets-shadow.json \
      --manual-dir private/targets [--seat y8] [--dry-run]
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

MODEL = os.environ.get("DAILYXP_SWEEP_MODEL", "claude-sonnet-4-6")
API_URL = "https://api.anthropic.com/v1/messages"
CONTENT_BUDGET_CHARS = 14000     # per-course prompt payload cap
ANNOUNCE_CAP = 12                # most-recent announcements passed per course
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
    s = re.sub(r"(?i)<li\b[^>]*>", "\n• ", s)
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
    subject = re.sub(r"\s+[A-Z]$", "", subject)          # class letter: Maths L
    subject = SUBJECT_ALIASES.get(subject, subject)
    return subject, subject.upper() == "HSIE"


def course_payload(course):
    """Assemble the text the LLM sees for one course, inside the budget."""
    parts = []
    fp = course.get("front_page")
    if fp and fp.get("body"):
        parts.append("== COURSE HOMEPAGE (week-by-week schedules often live "
                     f"here) — updated {fp.get('updated_at')} ==\n"
                     + strip_html(fp["body"]))
    fresh_pages = [p for p in course.get("pages", []) if p.get("body")]
    for p in fresh_pages:
        parts.append(f"== PAGE: {p.get('title')} (updated {p.get('updated_at')}) ==\n"
                     + strip_html(p["body"]))
    mods = course.get("modules", [])
    if mods:
        lines = []
        for m in mods:
            items = ", ".join(i.get("title") or "" for i in m.get("items", []))
            lines.append(f"- {m.get('name')}: {items}")
        parts.append("== MODULE STRUCTURE ==\n" + "\n".join(lines))
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
        parts.append("== ASSIGNMENTS (authoritative dates from Canvas) ==\n"
                     + "\n".join(lines))
    text = "\n\n".join(parts)
    truncated = len(text) > CONTENT_BUDGET_CHARS
    return text[:CONTENT_BUDGET_CHARS], truncated


def system_prompt(legends, today, hsie):
    strand_rule = (
        '\n- This course is HSIE, which the targets file splits into History '
        'and Geography: every topic MUST carry "strand": "History" or '
        '"Geography".' if hsie else "")
    return f"""You turn one school Canvas course's recent content into this week's teaching outline for a quiz planner. Today is {today} (Term 3, NSW Australia).

Return STRICT JSON only — no prose, no code fences:
{{"unit": "<2-3 sentence plain summary of where the class is up to, with dates>",
 "topics": [{{"topic": "<short quizzable topic name>",
   "status": "live|upcoming|not_yet_posted|prior_term",
   "fresh": true|false,
   "assessment": null | {{"task": "<name>", "date": "YYYY-MM-DD or null",
     "date_confidence": "<CONFIRMED/LIKELY + which surface says so>"}}{',\n   "strand": "History|Geography"' if hsie else ''}}}]}}

Status meanings (use exactly these): {json.dumps(legends.get('status_legend', {}))}
fresh flag: {json.dumps(legends.get('fresh_flag_legend', {}))}

Rules:
- Current term only: what is being taught now, just finished, or on the near horizon. Old archive content is not a topic.
- Topic granularity = one quizzable unit, like "Venn diagrams (probability)" or "Linear equations (solve for x, balance rule)". 1-6 topics typical.
- ASSIGNMENTS section dates are authoritative; homepage schedules are strong evidence; announcements support. date_confidence must name the evidence.
- NEVER invent. If the course shows no current teaching content, return {{"unit": "No current content posted.", "topics": []}}.{strand_rule}"""


def call_llm(system, user):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        sys.exit("sweep_summarise: ANTHROPIC_API_KEY not set")
    body = json.dumps({"model": MODEL, "max_tokens": 2000, "temperature": 0,
                       "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01",
        "content-type": "application/json"})
    last = None
    for attempt in range(1, LLM_RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
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
        out["assessment"] = {"task": str(a["task"]),
                             "date": date,
                             "date_confidence": str(a.get("date_confidence") or
                                                    "unstated")}
    if hsie:
        out["_strand"] = a_str = str(t.get("strand") or "").title()
        if a_str not in HSIE_STRANDS:
            out["_strand"] = "History"  # default strand; validator surfaces it
    return out


def newest_manual(manual_dir):
    files = sorted(glob.glob(os.path.join(manual_dir, "*.json")))
    return files[-1] if files else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--manual-dir", default="private/targets",
                    help="where manual targets live (legends are copied)")
    ap.add_argument("--seat")
    ap.add_argument("--dry-run", action="store_true",
                    help="no LLM: structure + classification only")
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

    out = {
        "week_of": week_of,
        "school_week": school_week,
        "source": (f"Automated Canvas API sweep (SHADOW) — student tokens, six "
                   f"content surfaces; dump {stamp}, summarised "
                   f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}"),
        "fidelity_note": "",
        "layer": ("TARGETING ONLY. This file = what is live in class + when "
                  "it's assessed (the sweep's job)."),
        **legends,
        "students": {},
    }

    excluded, failed, truncs, llm_calls = [], [], 0, 0
    for seat_file in sorted(glob.glob(os.path.join(args.dump, "*.json"))):
        code = os.path.splitext(os.path.basename(seat_file))[0]
        if code == "manifest" or (args.seat and code != args.seat):
            continue
        dump = json.load(open(seat_file, encoding="utf-8"))
        subjects = {}
        for course in dump.get("courses", []):
            subject, hsie = classify(course.get("name"))
            if subject is None:
                excluded.append(course.get("name"))
                continue
            payload, cut = course_payload(course)
            truncs += cut
            if args.dry_run:
                subjects.setdefault(subject, {"unit": "(dry-run)",
                                              "topics": []})
                continue
            try:
                llm_calls += 1
                res = call_llm(system_prompt(legends, today, hsie), payload)
            except Exception as e:  # noqa: BLE001
                failed.append(f"{code}/{course.get('name')}: {e}")
                subjects[subject] = {"unit": f"SWEEP FAILED: {e}", "topics": []}
                continue
            topics = [t for t in (sane_topic(x, hsie)
                                  for x in res.get("topics", [])) if t]
            if hsie:
                for strand in HSIE_STRANDS:
                    st = [{k: v for k, v in t.items() if k != "_strand"}
                          for t in topics if t["_strand"] == strand]
                    if st or strand == "History":
                        subjects[strand] = {"unit": res.get("unit", ""),
                                            "topics": st}
            else:
                subjects[subject] = {"unit": str(res.get("unit", "")).strip(),
                                     "topics": topics}
            log(f"{code}/{subject}: {len(topics)} topics")
        out["students"][code] = {"subjects": subjects}

    out["fidelity_note"] = (
        f"Automated shadow sweep: {llm_calls} academic courses summarised, "
        f"{len(failed)} failed, {truncs} truncated to budget. Noticeboard "
        f"shells excluded: {sorted(set(excluded))}."
        + (f" FAILURES: {failed}" if failed else ""))

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    log(f"wrote {args.out}"
        f" — seats: {', '.join(out['students'])} | excluded shells: "
        f"{len(set(excluded))} | failures: {len(failed)}")
    if failed:
        sys.exit(3)


if __name__ == "__main__":
    main()
