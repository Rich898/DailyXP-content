#!/usr/bin/env python3
"""
DailyXP Results Reader — scheduler limb #1 (assisted-manual mode).

Replaces the by-hand morning read of the results Sheet. Takes a saved dump of
the Sheet (as returned by the Drive connector's read_file_content — a markdown
table — or a CSV export with the same columns), and emits a per-student state
summary the morning "go" can act on.

What it does:
  1. Parses rows; extracts + validates each payload_json.
  2. Dedupes by (student, ts) — retry-taps post exact duplicates.
  3. Drops SYSTEM TEST rows (tag contains "SYSTEM TEST" or day == "TEST").
  4. Marks the canonical run per (student, set-date): lowest attempt, then
     earliest ts. attempt > 1 as canonical = flagged contamination caveat.
  5. Extracts every signal: score, phase splits, per-question record
     (picked / ok / secs / confidence), shell flags, timing, teach-back.
  6. Checks the timing invariant (active <= elapsed) and phase-sum sanity.
  7. Adds KID-RELATIVE speed flags (doctrine: fast/slow is relative to the
     student's OWN pace per phase, not a fixed cutoff) alongside shell flags.
  8. Emits ledger implications per the project doctrine:
     confident-wrong != guessing-wrong != slow-wrong != fast-wrong;
     lucky guesses never promote; trivially-fast-correct on a known weakness
     is UNTESTED, not mastered; fresh-skips are benched intel, never misses;
     absence is neutral (ABSENCE.md) — a quiet day is reported, not alarmed.

What it does NOT do (by design, per BUILD brief):
  - No question composing (limb #2). No cron/API (limb #3).
  - Does not write the ledger files — it emits the update; a human/Claude
    applies it.

Usage:
  python3 tools/results_reader.py work/sheet_dump.md
  python3 tools/results_reader.py work/sheet_dump.md --since 2026-08-04
  python3 tools/results_reader.py work/sheet_dump.md --student y8 --json out.json

No results data, no names, no secrets live in this file — names come from the
payload at runtime (repo law: repo files stay y9/y8).
"""

import argparse
import csv
import io
import json
import re
import statistics
import sys
from datetime import datetime, date, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    SYD = ZoneInfo("Australia/Sydney")
except Exception:  # pragma: no cover — fallback if tzdata missing
    SYD = timezone(timedelta(hours=10))

# ---- tunables (heuristics; raw seconds are always printed for human judgement)
FAST_FRAC = 0.50      # answered in <= 50% of the kid's phase median -> fast
SLOW_FRAC = 1.80      # answered in >= 180% of the kid's phase median -> slow
TRIVIAL_FRAC = 0.35   # <= 35% of phase median -> "trivially fast" evidence rule
MIN_BASELINE_N = 4    # need at least this many timed answers to trust a median


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

_MD_ESCAPE = re.compile(r"\\([\\\[\]_])")


def _unescape_md(cell: str) -> str:
    """Undo the Drive connector's markdown escaping inside cells.

    The connector escapes \\ [ ] _ for markdown rendering, which turns the
    payload's own JSON escapes (\\" and \\n) into \\\\" and \\\\n. Collapsing
    only backslash-before-{\\ [ ] _} restores valid JSON in both the escaped
    and unescaped cases, and never touches legitimate JSON escapes like
    \\n \\" \\u003e (n, ", u are not in the set).
    """
    return _MD_ESCAPE.sub(r"\1", cell)


def _extract_json(cell: str):
    """Pull the payload JSON out of a cell: first '{' to last '}'."""
    a, b = cell.find("{"), cell.rfind("}")
    if a == -1 or b == -1 or b <= a:
        raise ValueError("no JSON object found in payload cell")
    return json.loads(_unescape_md(cell[a:b + 1]))


_MD_ROW = re.compile(
    r"^\|\s*(?P<received>[^|]*?)\s*\|\s*(?P<student>[^|]*?)\s*\|\s*(?P<qdate>[^|]*?)\s*\|"
    r"\s*(?P<day>[^|]*?)\s*\|\s*(?P<attempt>[^|]*?)\s*\|\s*(?P<score>[^|]*?)\s*\|\s*(?P<rest>.*)$"
)


def load_dump(path: str):
    """Load rows from a connector markdown-table dump or a CSV export.

    Returns (rows, errors) where each row is a dict with keys:
    received_at, student, quiz_date, day, attempt, score, payload (parsed dict)
    """
    text = open(path, encoding="utf-8").read()
    rows, errors = [], []

    looks_md = any(line.lstrip().startswith("|") for line in text.splitlines()[:6])

    if looks_md:
        # Join continuation lines (a payload containing a newline) onto their row.
        joined, buf = [], None
        for line in text.splitlines():
            if line.lstrip().startswith("|"):
                if buf is not None:
                    joined.append(buf)
                buf = line
            elif buf is not None:
                buf += " " + line
        if buf is not None:
            joined.append(buf)

        for line in joined:
            if '"shell"' not in line:      # header / divider / label rows
                continue
            m = _MD_ROW.match(line.strip())
            if not m:
                errors.append(f"unparseable row: {line[:90]}…")
                continue
            try:
                payload = _extract_json(m.group("rest"))
            except Exception as e:
                errors.append(f"payload parse failed ({e}): {line[:90]}…")
                continue
            rows.append({
                "received_at": _unescape_md(m.group("received")),
                "student": _unescape_md(m.group("student")),
                "quiz_date": _unescape_md(m.group("qdate")),
                "day": _unescape_md(m.group("day")),
                "attempt": _unescape_md(m.group("attempt")),
                "score": _unescape_md(m.group("score")),
                "payload": payload,
            })
    else:
        reader = csv.DictReader(io.StringIO(text))
        for i, r in enumerate(reader, start=2):
            cell = r.get("payload_json") or ""
            try:
                payload = _extract_json(cell)
            except Exception as e:
                errors.append(f"CSV line {i}: payload parse failed ({e})")
                continue
            rows.append({
                "received_at": r.get("received_at", ""),
                "student": r.get("student", ""),
                "quiz_date": r.get("quiz_date", ""),
                "day": r.get("day", ""),
                "attempt": r.get("attempt", ""),
                "score": r.get("score", ""),
                "payload": payload,
            })

    return rows, errors


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #

def normalise(row):
    """Turn a sheet row into a run dict with merged per-question records."""
    p = row["payload"]
    ts = datetime.fromisoformat(p["ts"].replace("Z", "+00:00"))
    local = ts.astimezone(SYD)

    timing = p.get("timing", {}) or {}
    per_q_secs = {q.get("id"): q for q in timing.get("perQuestion", []) or []}

    questions = []
    for rec in p.get("records", []) or []:
        qid = rec.get("id")
        tq = per_q_secs.get(qid, {})
        questions.append({
            "id": qid,
            "subject": rec.get("subject", "?"),
            "phase": rec.get("phase", "?"),
            "skipped": bool(rec.get("skipped")),
            "ok": rec.get("ok"),
            "picked": rec.get("picked"),
            "confidence": rec.get("confidence") or tq.get("confidence"),
            "secs": tq.get("secs", rec.get("timeUsed")),
            "pts": rec.get("pts"),
            "chars": rec.get("text") and len(rec.get("text")) or tq.get("chars"),
            "text": rec.get("text"),
        })

    flags = p.get("flags", {}) or {}
    set_date = date.fromisoformat(p["date"]) if p.get("date") else None
    run_date = local.date()

    return {
        "student": p.get("student", row["student"]),
        "name": (p.get("name") or row["student"]).strip(),
        "tag": p.get("tag", ""),
        "day": p.get("day", row["day"]),
        "set_date": set_date,
        "run_date": run_date,
        "run_dt_local": local,
        "ts": ts,
        "ts_raw": p.get("ts"),
        "attempt": int(p.get("attempt", row["attempt"] or 1)),
        "attempts_all_time": p.get("attemptsAllTime"),
        "shell": p.get("shell"),
        "score": p.get("score"),
        "max_score": p.get("maxScore"),
        "speed": p.get("speed", {}),
        "steady": p.get("steady", {}),
        "teach": p.get("teach", {}),
        "shell_flags": {
            "skips": flags.get("skips", []),
            "confidentWrong": flags.get("confidentWrong", []),
            "slowWrong": flags.get("slowWrong", []),
            "fastWrong": flags.get("fastWrong", []),
            "luckyGuess": flags.get("luckyGuess", []),
        },
        "timing": {
            "elapsed": timing.get("elapsedSecs"),
            "active": timing.get("activeSecs"),
            "idle": timing.get("idleSecs"),
            "phases": timing.get("phases", {}),
        },
        "questions": questions,
        "is_test": ("SYSTEM TEST" in (p.get("tag") or "").upper()
                    or (p.get("day") or "").upper() == "TEST"),
    }


def dedupe(runs):
    """Exact duplicates: same (student, ts). Keep first, report the rest."""
    seen, kept, dropped = {}, [], []
    for r in runs:
        key = (r["student"], r["ts_raw"])
        if key in seen:
            dropped.append(r)
        else:
            seen[key] = True
            kept.append(r)
    return kept, dropped


def mark_canonical(runs):
    """Per (student, set_date): canonical = lowest attempt, then earliest ts."""
    groups = {}
    for r in runs:
        groups.setdefault((r["student"], r["set_date"]), []).append(r)
    for grp in groups.values():
        grp.sort(key=lambda r: (r["attempt"], r["ts"]))
        for i, r in enumerate(grp):
            r["canonical"] = (i == 0)
            r["canonical_caveat"] = (i == 0 and r["attempt"] > 1)
    return runs


# --------------------------------------------------------------------------- #
# Kid-relative speed baselines
# --------------------------------------------------------------------------- #

def phase_medians(runs):
    """Median answer time per (student, phase) across honest (canonical) runs."""
    times = {}
    for r in runs:
        if not r.get("canonical"):
            continue
        for q in r["questions"]:
            if q["phase"] in ("speed", "steady") and not q["skipped"] and q["secs"]:
                times.setdefault((r["student"], q["phase"]), []).append(q["secs"])
    return {k: (statistics.median(v), len(v)) for k, v in times.items()}


def relative_speed(q, medians, student):
    med = medians.get((student, q["phase"]))
    if not med or med[1] < MIN_BASELINE_N or not q["secs"]:
        return None, None
    m = med[0]
    label = None
    if q["secs"] <= TRIVIAL_FRAC * m:
        label = "trivial"
    elif q["secs"] <= FAST_FRAC * m:
        label = "fast"
    elif q["secs"] >= SLOW_FRAC * m:
        label = "slow"
    return label, m


# --------------------------------------------------------------------------- #
# Ledger implications (the doctrine, encoded)
# --------------------------------------------------------------------------- #

def classify(q, rel, shell_flags):
    """Return (badge, implication) for one question, or (badge, None)."""
    qid = q["id"]
    in_shell = lambda k: qid in shell_flags.get(k, [])
    conf = (q["confidence"] or "").lower()

    if q["skipped"]:
        return "SKIP", (f"fresh-skip ({q['subject']}) — coverage intel, never a miss; "
                        "verify against class, keep benched until confirmed taught")

    if q["phase"] == "teach":
        return "TB", None  # quality judgement is a human/LLM call, not a rule

    if q["ok"]:
        if in_shell("luckyGuess") or conf == "guessing":
            return "LUCKY", (f"{q['subject']} {qid}: correct but GUESSING — do not "
                             "promote; re-queue within days")
        if rel == "trivial":
            return "TRIV✓", (f"{q['subject']} {qid}: correct but trivially fast "
                             f"({q['secs']}s) — weak evidence; if this is a known-weak/"
                             "REPAIR topic, treat as UNTESTED, not mastered")
        if conf == "sure":
            return "✓", (f"{q['subject']} {qid}: clean confident hit — supports "
                         "promotion after a spaced confirm")
        if conf == "think so":
            return "✓", (f"{q['subject']} {qid}: correct, 'Think so' — knowledge "
                         "landing, confidence not yet; keep in rotation, praise-worthy")
        return "✓", None

    # wrong
    if in_shell("confidentWrong") or conf == "sure":
        return "CW", (f"{q['subject']} {qid}: CONFIDENT-WRONG (picked "
                      f"\u201c{q['picked']}\u201d) — fluency illusion, the "
                      "priority class; ledger -> shaky, re-teach then re-test "
                      "within days")
    if conf == "guessing":
        return "GW", (f"{q['subject']} {qid}: guessing-wrong — honest gap, "
                      "normal re-queue")
    if in_shell("fastWrong") or rel == "fast" or rel == "trivial":
        return "FW", (f"{q['subject']} {qid}: fast-wrong ({q['secs']}s vs own pace) — "
                      "rush pattern, not a knowledge gap; medicine is pacing, "
                      "not content")
    if in_shell("slowWrong") or rel == "slow":
        return "SW", (f"{q['subject']} {qid}: slow-wrong ({q['secs']}s, considered) — "
                      "genuine struggle; re-teach before re-testing")
    return "✗", (f"{q['subject']} {qid}: considered-wrong (picked "
                 f"\u201c{q['picked']}\u201d) — clean content gap; ledger -> shaky")


def cross_run_signals(runs):
    """Per student: repeat confident-wrong subjects, subject miss-streaks."""
    out = {}
    by_student = {}
    for r in runs:
        if r.get("canonical") and not r["is_test"]:
            by_student.setdefault(r["student"], []).append(r)

    for student, rs in by_student.items():
        rs.sort(key=lambda r: r["ts"])
        notes = []
        cw_by_subject, misses_by_subject = {}, {}
        for r in rs:
            for q in r["questions"]:
                if q["phase"] == "teach" or q["skipped"]:
                    continue
                if q["ok"] is False:
                    misses_by_subject.setdefault(q["subject"], []).append(r["run_date"])
                    if (q["confidence"] or "").lower() == "sure":
                        cw_by_subject.setdefault(q["subject"], []).append(r["run_date"])
        for subj, dates in cw_by_subject.items():
            if len(dates) >= 2:
                notes.append(f"REPEAT confident-wrong in {subj} "
                             f"({len(dates)}x: {', '.join(d.strftime('%a %d') for d in dates)}) "
                             "— escalate: this is a real, self-invisible gap")
        for subj, dates in misses_by_subject.items():
            if len(set(dates)) >= 2:
                notes.append(f"{subj}: misses across {len(set(dates))} separate runs — "
                             "resurface as a repair thread, consider a depth pass "
                             "(CONTENT-MODEL: ledger as drift detector)")
        out[student] = notes
    return out


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #

def fmt_mmss(secs):
    if secs is None:
        return "?"
    secs = int(round(secs))
    return f"{secs // 60}:{secs % 60:02d}"


def render_run(r, medians):
    L = []
    name = r["name"].capitalize() if r["name"].islower() else r["name"]
    late = ""
    if r["set_date"] and r["run_date"] != r["set_date"]:
        delta = (r["run_date"] - r["set_date"]).days
        late = f"  ·  ⚠ completed {delta} day{'s' if delta != 1 else ''} late (set dated {r['set_date'].strftime('%a %d %b')})"
    canon = "CANONICAL" if r["canonical"] else f"REPEAT (attempt {r['attempt']})"
    head = (f"{name} ({r['student']}) — {r['tag']} — "
            f"{r['run_dt_local'].strftime('%a %d %b %I:%M %p AEST')} — {canon}{late}")
    L.append(head)
    L.append("-" * min(len(head), 96))

    if r["canonical_caveat"]:
        L.append(f"⚠ canonical-by-default: attempt {r['attempt']} is the only run of this set "
                 "(earlier attempt missing/abandoned) — read with a contamination caveat.")

    sp, st, t = r["speed"], r["steady"], r["teach"]
    pct = round(100 * r["score"] / r["max_score"]) if r["max_score"] else "?"
    L.append(f"Score {r['score']:,}/{r['max_score']:,} ({pct}%)  ·  "
             f"Speed {sp.get('right')}/{sp.get('of')}  ·  Steady {st.get('right')}/{st.get('of')}  ·  "
             f"Teach {'✓' if t.get('done') else '✗'} ({t.get('chars', 0)} chars)")

    tm = r["timing"]
    inv_ok = (tm["active"] is not None and tm["elapsed"] is not None
              and tm["active"] <= tm["elapsed"] + 0.05)
    ph = tm.get("phases", {})
    phase_sum = sum(v for v in ph.values() if isinstance(v, (int, float)))
    L.append(f"Timing: active {fmt_mmss(tm['active'])} ≤ elapsed {fmt_mmss(tm['elapsed'])} "
             f"{'✓ invariant OK' if inv_ok else '⚠ INVARIANT VIOLATED — phase/total times unreliable'}  "
             f"(idle {fmt_mmss(tm['idle'])}; phases Σ {fmt_mmss(phase_sum)}: "
             f"speed {fmt_mmss(ph.get('speed'))} · steady {fmt_mmss(ph.get('steady'))} · "
             f"teach {fmt_mmss(ph.get('teach'))})")

    implications, teach_q = [], None
    L.append("Per-question:")
    for q in r["questions"]:
        if q["phase"] == "teach":
            teach_q = q
            continue
        rel, med = relative_speed(q, medians, r["student"])
        badge, imp = classify(q, rel, r["shell_flags"])
        if imp:
            implications.append(imp)
        mark = "—skip—" if q["skipped"] else ("✓" if q["ok"] else "✗")
        secs = f"{q['secs']}s" if q["secs"] is not None else "  ?"
        conf = f" · {q['confidence']}" if q["confidence"] else ""
        relnote = f" [{rel} vs own median {med:.0f}s]" if rel else ""
        L.append(f"  {q['id']:>4} {q['subject']:<10} {mark:<7} {secs:>6}{conf}{relnote}"
                 + (f"  · picked \u201c{q['picked']}\u201d" if (q['ok'] is False and q['picked']) else ""))

    if teach_q is not None:
        g = teach_q.get("tb_grade")
        gnote = (f"graded {g['verdict'].upper()}" + ("" if g.get("english", True) else ", not English")
                 + (f" — {g['reason']}" if g.get("reason") else "")) if g else "ungraded (grade_teachback not run)"
        L.append(f"Teach-back ({teach_q['subject']}, {fmt_mmss(teach_q['secs'])}, "
                 f"{teach_q['chars'] or 0} chars) — {gnote}:")
        L.append(f"  \u201c{(teach_q['text'] or '').strip()}\u201d")

    if r["canonical"]:
        L.append("Ledger implications:")
        for imp in implications or ["  (clean run — spaced confirms only)"]:
            L.append(f"  • {imp}")
    else:
        L.append("(repeat run — signals excluded from ledger implications; "
                 "engagement data only)")
    return "\n".join(L)


def render_report(runs, dropped, tests, errors, medians, since, student_filter):
    out = []
    honest = [r for r in runs if not r["is_test"]]
    out.append("=" * 78)
    out.append("DAILYXP MORNING READ — results reader (limb #1)")
    out.append(f"Read {len(runs) + len(dropped)} rows -> {len(honest)} honest runs kept  ·  "
               f"{len(dropped)} duplicate(s) dropped  ·  {len(tests)} system-test row(s) ignored"
               + (f"  ·  {len(errors)} parse error(s)" if errors else ""))
    for d in dropped:
        out.append(f"  duplicate dropped: {d['student']} {d['tag']} ts {d['ts_raw']}")
    for t in tests:
        out.append(f"  test row ignored: {t['student']} tag \u201c{t['tag']}\u201d")
    for e in errors:
        out.append(f"  ⚠ {e}")

    inv_bad = [r for r in honest if r["timing"]["active"] and r["timing"]["elapsed"]
               and r["timing"]["active"] > r["timing"]["elapsed"] + 0.05]
    out.append(f"Timing invariant (active ≤ elapsed): "
               + ("HOLDING on all runs ✓" if not inv_bad else
                  f"⚠ VIOLATED on {len(inv_bad)} run(s): "
                  + ", ".join(f"{r['student']} {r['tag']}" for r in inv_bad)))
    if since:
        out.append(f"Filter: showing runs on/after {since} (Sydney run date). "
                   "Absence is neutral — quiet days are context, not failures.")
    out.append("=" * 78)

    shown = [r for r in honest
             if (not student_filter or r["student"] == student_filter)
             and (not since or r["run_date"] >= since)]
    shown.sort(key=lambda r: (r["student"], r["ts"]), reverse=True)

    by_student = {}
    for r in shown:
        by_student.setdefault(r["student"], []).append(r)

    xsignals = cross_run_signals(honest)

    for student in sorted(by_student):
        rs = by_student[student]
        name = rs[0]["name"]
        out.append("")
        out.append(f"######  {name.upper()} ({student}) — {len(rs)} run(s) shown, newest first  ######")
        for r in rs:
            out.append("")
            out.append(render_run(r, medians))
        if xsignals.get(student):
            out.append("")
            out.append("Cross-run signals (all honest runs in window):")
            for n in xsignals[student]:
                out.append(f"  ‼ {n}")

    # students with no runs in the window (absence-neutral note)
    all_students = {r["student"] for r in honest}
    quiet = all_students - set(by_student)
    for s in sorted(quiet):
        nm = next(r["name"] for r in honest if r["student"] == s)
        out.append("")
        out.append(f"######  {nm.upper()} ({s}) — no runs in window  ######")
        out.append("  Absence is neutral (ABSENCE.md): nothing due back, no debt; "
                   "untested topics simply remain due.")

    return "\n".join(out)


# --------------------------------------------------------------------------- #

def main():
    ap = argparse.ArgumentParser(description="DailyXP results reader (limb #1)")
    ap.add_argument("dump", help="saved Sheet dump (connector markdown or CSV)")
    ap.add_argument("--since", help="only show runs on/after this Sydney date (YYYY-MM-DD)")
    ap.add_argument("--student", help="filter to one student (roster code)")
    ap.add_argument("--json", dest="json_out", help="also write normalised runs as JSON")
    args = ap.parse_args()

    rows, errors = load_dump(args.dump)
    runs = [normalise(r) for r in rows]
    runs, dropped = dedupe(runs)
    tests = [r for r in runs if r["is_test"]]
    runs = mark_canonical([r for r in runs if not r["is_test"]])
    medians = phase_medians(runs)

    since = date.fromisoformat(args.since) if args.since else None
    print(render_report(runs, dropped, tests, errors, medians, since, args.student))

    if args.json_out:
        def ser(o):
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            raise TypeError
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump({"runs": runs, "medians":
                       {f"{k[0]}:{k[1]}": v for k, v in medians.items()}},
                      f, default=ser, indent=2, ensure_ascii=False)
        print(f"\n[normalised JSON written -> {args.json_out}]", file=sys.stderr)


if __name__ == "__main__":
    main()
