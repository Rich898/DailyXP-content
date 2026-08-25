#!/usr/bin/env python3
"""
sweep_schedule.py — the SCHEDULE-PASS (limb #1d of the automated sweep).

Closes the sweep's known date gap: term assessment dates live in an
assessment-schedule PDF on the year-group noticeboard course — a course the
summariser excludes by design, in a Files area the fetcher never reads.

DECLARED SCOPE (this docstring is the public proof, same as the fetcher's):
this tool reads the FILES LIST OF EXACTLY ONE COURSE per seat — the year-group
noticeboard — and downloads ONLY assessment-schedule PDFs from it. It never
widens the fetcher's six content surfaces, never reads files on academic
courses, and never touches grades, submissions, inbox, or people.

Division of labour (doctrine): the LLM reads the PDF and transcribes
subject/task/date triples — language only, one call per seat. CODE decides
everything else: which course, which file, subject normalisation, and the
fill-and-stamp attach (ratified 25 Aug 2026):

  FILL  — a topic already carries an assessment whose task matches a PDF row:
          the PDF confirms or fixes its date (the term calendar wins).
          Exception guard: if the existing date is explicit, classroom-
          CONFIRMED and DIFFERENT, the classroom wins (teachers move tests;
          the PDF is printed once a term) and a loud date_conflict is logged
          for the weekly review.
  STAMP — a dated PDF row no topic carries: attach it to that subject's
          currently-live topics that have no assessment yet. Never overwrite
          a topic-specific assessment.

Every fill, stamp, conflict and unmatched subject lands in the changelog
(sweep_update.seats.<seat>.<subject>.schedule_pass) — editor-reviewable.

Date discipline: identical to the summariser. Only explicit calendar dates
(Australian day/month short forms count; assume 2026 when the year is
omitted). Relative phrases ("Week 6") stay out of the date field.

Shadow-safe: edits only the --targets file it is pointed at. Never targets/.
Failure is LOUD (nonzero exit -> red run) but the sweep itself has already
landed by the time this runs — a failed schedule-pass never sinks the sweep.

Env:  CANVAS_BASE_URL, CANVAS_TOKEN_<CODE>, ANTHROPIC_API_KEY (extract only)

Usage:
  # probe: list the noticeboard's files, download nothing
  python3 tools/sweep_schedule.py --dump private/shadow/sweeps/<date> --list
  # full: extract triples and attach into the shadow targets
  python3 tools/sweep_schedule.py --dump private/shadow/sweeps/<date> \
      --targets private/shadow/sweeps/<date>/targets-shadow.json [--seat y8]
"""
import argparse
import base64
import datetime as dt
import glob
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sweep_fetch import Canvas  # the one read-only Canvas client

try:
    import requests
except ImportError:
    sys.exit("sweep_schedule: `pip install requests` first")

MODEL = os.environ.get("DAILYXP_SWEEP_MODEL", "claude-sonnet-4-6")
API_URL = "https://api.anthropic.com/v1/messages"
LLM_RETRIES = 2

NOTICE_PAT = re.compile(r"year\s*group", re.I)   # how we spot the noticeboard
FILE_PAT = re.compile(r"assess", re.I)           # ...and the schedule PDF
PDF_MAX_BYTES = 15 * 1024 * 1024

# PDF subject spelling -> targets subject spelling (lowercase keys).
# Extend after the first real extract shows what the PDF actually prints.
SUBJECT_ALIASES = {
    "mathematics": "Maths",
    "maths": "Maths",
    "design and technology": "D&T",
    "d&t": "D&T",
    "science": "Science",
    "english": "English",
}
HSIE_STRANDS = ("History", "Geography")


def log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- Canvas side

def noticeboard_course(dump):
    """The dump already lists every enrollment; pick the year-group shell."""
    hits = [c for c in dump.get("courses", [])
            if NOTICE_PAT.search(c.get("name") or "")]
    return hits[0] if hits else None


def list_files(cv, course_id):
    """Files list for one course. 401/403/404 mean the Files area is hidden
    from the student token — that is a finding, not a crash."""
    try:
        return list(cv.paged(f"/api/v1/courses/{course_id}/files",
                             {"sort": "updated_at", "order": "desc"}))
    except PermissionError:
        raise
    except RuntimeError as e:
        if "403" in str(e):
            raise PermissionError("files area hidden from student token (403)")
        raise


def pick_schedule_pdf(files):
    """Newest file matching FILE_PAT with a .pdf name/content-type."""
    cands = [f for f in files
             if FILE_PAT.search(f.get("display_name") or f.get("filename") or "")
             and ((f.get("content-type") or "").endswith("pdf")
                  or (f.get("display_name") or "").lower().endswith(".pdf"))]
    cands.sort(key=lambda f: f.get("updated_at") or "", reverse=True)
    return cands


def download_pdf(url, dest):
    """Canvas hands out a signed URL; fetch it WITHOUT the auth header (the
    redirect target rejects stray bearer tokens)."""
    r = requests.get(url, timeout=60, allow_redirects=True)
    r.raise_for_status()
    if len(r.content) > PDF_MAX_BYTES:
        raise RuntimeError(f"PDF too large ({len(r.content)} bytes)")
    with open(dest, "wb") as f:
        f.write(r.content)
    return r.content


# ------------------------------------------------------------------- LLM side

def extract_prompt(seat_year_hint, today):
    return (
        "You are transcribing a school's term assessment schedule PDF for a "
        f"quiz planner. Today is {today} (Term 3, NSW Australia). "
        f"This schedule belongs to {seat_year_hint}.\n\n"
        "Return STRICT JSON only — no prose, no code fences: an array of\n"
        '[{"subject": "<exactly as printed in the PDF>", '
        '"task": "<assessment task name as printed>", '
        '"date": "YYYY-MM-DD or null", '
        '"date_confidence": "<CONFIRMED - schedule PDF | or the exact '
        'relative/range phrase when no single explicit date is printed>"}]\n\n'
        "Rules:\n"
        "- One entry per assessment task row. Transcribe; never invent.\n"
        "- DATES: only an explicit calendar date printed in the PDF. "
        "Australian short forms count: \"17/9\" or \"Thurs 17/9\" means 17 "
        "September (day/month; assume 2026 when the year is omitted); "
        "\"10th September\" is explicit too. A week range or relative phrase "
        "(\"Week 6\", \"Weeks 8-9\") is NOT a date: leave date null and put "
        "the phrase verbatim in date_confidence.\n"
        "- Keep every row, even undated ones.\n"
        "- If the PDF is not an assessment schedule, return [].")


def call_llm_pdf(system, pdf_bytes):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    body = json.dumps({
        "model": MODEL, "max_tokens": 4000, "temperature": 0,
        "system": system,
        "messages": [{"role": "user", "content": [
            {"type": "document",
             "source": {"type": "base64", "media_type": "application/pdf",
                        "data": base64.b64encode(pdf_bytes).decode()}},
            {"type": "text",
             "text": "Transcribe the assessment schedule as instructed."},
        ]}]}).encode()
    req = urllib.request.Request(API_URL, data=body, headers={
        "x-api-key": key, "anthropic-version": "2023-06-01",
        "content-type": "application/json"})
    last = None
    for attempt in range(1, LLM_RETRIES + 2):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
            text = "".join(b.get("text", "") for b in data.get("content", []))
            text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.M)
            rows, _ = json.JSONDecoder().raw_decode(text.strip())
            if not isinstance(rows, list):
                raise ValueError("expected a JSON array of rows")
            return rows
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * attempt)
    raise RuntimeError(f"LLM extract failed after retries: {last}")


def sane_row(r):
    if not isinstance(r, dict) or not r.get("subject") or not r.get("task"):
        return None
    date = r.get("date")
    if date and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
        date = None
    return {"subject": str(r["subject"]).strip(),
            "task": str(r["task"]).strip(),
            "date": date,
            "date_confidence": str(r.get("date_confidence") or "unstated")}


# ----------------------------------------------------------------- code side

def norm_subject(pdf_subject, targets_subjects):
    """PDF spelling -> targets subject name(s). Deterministic; unmatched is
    a logged finding, never a guess."""
    s = re.sub(r"\s+", " ", pdf_subject).strip().lower()
    if s == "hsie":
        return [x for x in HSIE_STRANDS if x in targets_subjects]
    alias = SUBJECT_ALIASES.get(s)
    if alias and alias in targets_subjects:
        return [alias]
    for t in targets_subjects:            # exact, case-insensitive
        if t.lower() == s:
            return [t]
    for t in targets_subjects:            # containment either way
        if t.lower() in s or s in t.lower():
            return [t]
    return []


def _tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", (s or "").lower())
            if w not in {"the", "a", "an", "of", "term", "task"}}


def task_match(a, b):
    """Deterministic fuzzy task match: containment or strong token overlap."""
    na, nb = " ".join(sorted(_tokens(a))), " ".join(sorted(_tokens(b)))
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    ta, tb = _tokens(a), _tokens(b)
    return len(ta & tb) / max(1, len(ta | tb)) >= 0.6


def attach(subjects, rows, seat_chg):
    """THE FILL-AND-STAMP ATTACH. Pure code; edits topics in place and writes
    a per-subject schedule_pass changelog. Returns totals."""
    filled = stamped = conflicts = 0
    for row in rows:
        names = norm_subject(row["subject"], list(subjects))
        if not names:
            seat_chg.setdefault("__schedule_unmatched__", []).append(
                {"subject": row["subject"], "task": row["task"],
                 "date": row["date"]})
            continue
        for name in names:
            entry = subjects.get(name) or {}
            chg = seat_chg.setdefault(name, {}).setdefault(
                "schedule_pass", {"filled": [], "stamped": [],
                                  "date_conflicts": [], "undated_rows": []})
            if not row["date"]:
                chg["undated_rows"].append(
                    {"task": row["task"], "note": row["date_confidence"]})
                continue
            hit = False
            for topic in entry.get("topics", []):
                a = topic.get("assessment")
                if not (a and a.get("task") and task_match(a["task"],
                                                           row["task"])):
                    continue
                hit = True
                old_date, old_conf = a.get("date"), a.get("date_confidence", "")
                if old_date == row["date"]:
                    continue  # already right
                if old_date and str(old_conf).upper().startswith("CONFIRMED") \
                        and "schedule PDF" not in old_conf:
                    conflicts += 1  # classroom moved it; classroom wins, loudly
                    chg["date_conflicts"].append(
                        {"topic": topic["topic"], "task": a["task"],
                         "classroom": old_date, "pdf": row["date"],
                         "kept": "classroom"})
                    continue
                a["date"] = row["date"]
                a["date_confidence"] = ("CONFIRMED — assessment schedule PDF"
                                        + (f" (was {old_date or 'null'}, "
                                           f"{old_conf})" if old_conf else ""))
                filled += 1
                chg["filled"].append({"topic": topic["topic"],
                                      "task": a["task"], "date": row["date"]})
            if not hit:
                for topic in entry.get("topics", []):
                    if topic.get("status") == "live" \
                            and not topic.get("assessment"):
                        topic["assessment"] = {
                            "task": row["task"], "date": row["date"],
                            "date_confidence": ("CONFIRMED — assessment "
                                                "schedule PDF (subject-level)")}
                        stamped += 1
                        chg["stamped"].append({"topic": topic["topic"],
                                               "task": row["task"],
                                               "date": row["date"]})
    return filled, stamped, conflicts


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--targets", help="shadow targets file to attach into "
                                      "(required unless --list)")
    ap.add_argument("--seat")
    ap.add_argument("--list", action="store_true",
                    help="probe: print the noticeboard's files, change nothing")
    args = ap.parse_args()
    if not args.list and not args.targets:
        sys.exit("sweep_schedule: --targets is required unless --list")

    base_url = os.environ.get("CANVAS_BASE_URL", "").strip()
    if not base_url:
        sys.exit("sweep_schedule: CANVAS_BASE_URL is not set")

    stamp = os.path.basename(os.path.normpath(args.dump))
    today = stamp if re.match(r"^\d{4}-\d{2}-\d{2}$", stamp) \
        else dt.date.today().isoformat()

    roster_codes = {s.get("code") for s in
                    json.load(open("roster.json", encoding="utf-8"))
                    .get("students", [])}

    targets = None
    if args.targets:
        targets = json.load(open(args.targets, encoding="utf-8"))

    processed = 0
    failures, totals = [], {"filled": 0, "stamped": 0, "conflicts": 0}
    for seat_file in sorted(glob.glob(os.path.join(args.dump, "*.json"))):
        code = os.path.splitext(os.path.basename(seat_file))[0]
        if code not in roster_codes or (args.seat and code != args.seat):
            continue
        processed += 1
        token = os.environ.get(f"CANVAS_TOKEN_{code.upper()}", "").strip()
        if not token:
            failures.append(f"{code}: no CANVAS_TOKEN_* secret")
            log(f"{code}: FAILED — no token configured")
            continue
        dump = json.load(open(seat_file, encoding="utf-8"))
        nb = noticeboard_course(dump)
        if not nb:
            failures.append(f"{code}: no course matching /{NOTICE_PAT.pattern}/")
            log(f"{code}: FAILED — no noticeboard course found in dump; "
                f"courses were: "
                f"{[c.get('name') for c in dump.get('courses', [])]}")
            continue
        cv = Canvas(base_url, token)
        try:
            files = list_files(cv, nb["id"])
        except PermissionError as e:
            failures.append(f"{code}: {e}")
            log(f"{code}: FAILED — {e}")
            continue
        except Exception as e:  # noqa: BLE001
            failures.append(f"{code}: files list: {e}")
            log(f"{code}: FAILED — files list: {e}")
            continue

        log(f"{code}: noticeboard = '{nb.get('name')}' (course {nb['id']}), "
            f"{len(files)} files")
        if args.list:
            for f in files:
                log(f"  - {f.get('display_name')}  "
                    f"[{f.get('content-type')}]  "
                    f"updated {f.get('updated_at')}  {f.get('size')} bytes")
            continue

        cands = pick_schedule_pdf(files)
        if not cands:
            failures.append(f"{code}: no file matching /{FILE_PAT.pattern}/ "
                            f"+ .pdf on the noticeboard")
            log(f"{code}: FAILED — no assessment-schedule PDF found; files "
                f"were: {[f.get('display_name') for f in files]}")
            continue
        chosen = cands[0]
        if len(cands) > 1:
            log(f"{code}: {len(cands)} candidates; using newest "
                f"'{chosen.get('display_name')}', skipped "
                f"{[c.get('display_name') for c in cands[1:]]}")
        try:
            pdf_path = os.path.join(args.dump, f"schedule-{code}.pdf")
            pdf = download_pdf(chosen.get("url"), pdf_path)
            log(f"{code}: downloaded '{chosen.get('display_name')}' "
                f"({len(pdf)} bytes) -> {pdf_path}")
            year_hint = nb.get("name") or f"seat {code}"
            rows = [r for r in (sane_row(x) for x in
                                call_llm_pdf(extract_prompt(year_hint, today),
                                             pdf)) if r]
            with open(os.path.join(args.dump, f"schedule-{code}.json"), "w",
                      encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
            dated = sum(1 for r in rows if r["date"])
            log(f"{code}: extracted {len(rows)} rows ({dated} dated)")
        except Exception as e:  # noqa: BLE001
            failures.append(f"{code}: extract: {e}")
            log(f"{code}: FAILED — extract: {e}")
            continue

        sd = (targets.get("students", {}) or {}).get(code)
        if sd is None:
            failures.append(f"{code}: swept but absent from targets file")
            continue
        seat_chg = (targets.setdefault("sweep_update", {})
                    .setdefault("seats", {}).setdefault(code, {}))
        f_, s_, c_ = attach(sd.get("subjects", {}), rows, seat_chg)
        totals["filled"] += f_
        totals["stamped"] += s_
        totals["conflicts"] += c_
        log(f"{code}: schedule-pass — {f_} filled, {s_} stamped, "
            f"{c_} date conflicts (classroom kept)")

    if targets is not None and not args.list:
        note = (f" Schedule-pass: {totals['filled']} dates filled, "
                f"{totals['stamped']} stamped subject-level, "
                f"{totals['conflicts']} conflicts kept classroom.")
        targets["fidelity_note"] = (targets.get("fidelity_note") or "") + note
        with open(args.targets, "w", encoding="utf-8") as f:
            json.dump(targets, f, ensure_ascii=False, indent=1)
        log(f"wrote {args.targets} —{note}")

    if processed == 0:
        log(f"SCHEDULE-PASS FAILED — no seat dumps found in {args.dump} "
            f"(silent no-ops are the enemy)")
        sys.exit(4)
    if failures:
        log(f"SCHEDULE-PASS FAILURES ({len(failures)}): {failures}")
        sys.exit(4)


if __name__ == "__main__":
    main()
