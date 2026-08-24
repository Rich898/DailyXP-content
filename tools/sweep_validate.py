#!/usr/bin/env python3
"""
sweep_validate.py — the sweep GATE (limb #1c). Deterministic. No LLM.

Decides whether a summarised sweep is fit to become targets. In shadow it
just passes/fails visibly; when the sweep is promoted to scheduled, FAIL =
HOLD (last week's targets stay live), same semantics as a held quiz set.

Checks:
  1. schema: loads, students present, every non-alias seat from the dump is
     in the output; legends carried.
  2. coverage: every academic course in the raw dump surfaced as a subject
     (HSIE counts via History/Geography); no "SWEEP FAILED" subjects.
  3. sanity: per-seat topic totals within band; statuses legal; fresh is
     bool; assessment dates ISO and within -30..+180 days of the stamp.
  4. collapse detector (vs newest manual targets, warn-or-fail): per-seat
     topic total under 40% of manual = FAIL; subject-set drift = WARN.

Exit 0 PASS (warnings allowed), 2 FAIL.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

BAND = (3, 90)          # sane per-seat topic totals
COLLAPSE_RATIO = 0.4


def classify_academic(name):
    if re.search(r"year group|sport|counsellor|wellbeing|beyond bally|"
                 r"competition|library|careers", name or "", re.I):
        return None
    m = re.match(r"^Year\s+\d+\s+(.+?)\s+2026$", (name or "").strip())
    if not m:
        return None
    s = re.sub(r"\s+[A-Z]$", "", m.group(1).strip())
    return {"Design and Technology": "D&T"}.get(s, s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--manual-dir", default="private/targets")
    args = ap.parse_args()

    fails, warns = [], []
    try:
        t = json.load(open(args.targets, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: targets unreadable: {e}")
        sys.exit(2)

    stamp = os.path.basename(os.path.dirname(os.path.abspath(args.targets)))
    try:
        stamp_d = dt.date.fromisoformat(stamp)
    except ValueError:
        stamp_d = dt.date.today()

    students = t.get("students") or {}
    if not students:
        fails.append("no students in output")
    for k in ("status_legend", "fresh_flag_legend"):
        if k not in t:
            warns.append(f"legend missing: {k}")

    manifest_p = os.path.join(args.dump, "manifest.json")
    dumped = []
    if os.path.exists(manifest_p):
        dumped = list(json.load(open(manifest_p))["seats"].keys())
        for seat in dumped:
            if seat not in students:
                fails.append(f"seat {seat} swept but absent from output")

    for seat, sd in students.items():
        subjects = sd.get("subjects") or {}
        seat_dump = os.path.join(args.dump, f"{seat}.json")
        if os.path.exists(seat_dump):
            d = json.load(open(seat_dump, encoding="utf-8"))
            for c in d.get("courses", []):
                subj = classify_academic(c.get("name"))
                if subj is None:
                    continue
                ok = (subj in subjects or
                      (subj.upper() == "HSIE" and
                       any(s in subjects for s in ("History", "Geography"))))
                if not ok:
                    fails.append(f"{seat}: academic course "
                                 f"'{c.get('name')}' has no subject entry")
        total = 0
        for name, entry in subjects.items():
            if str(entry.get("unit", "")).startswith("SWEEP FAILED"):
                fails.append(f"{seat}/{name}: course summarisation failed")
            for topic in entry.get("topics", []):
                total += 1
                if topic.get("status") not in {"live", "upcoming",
                                               "not_yet_posted", "prior_term"}:
                    fails.append(f"{seat}/{name}: bad status "
                                 f"{topic.get('status')!r}")
                if not isinstance(topic.get("fresh"), bool):
                    fails.append(f"{seat}/{name}: fresh not bool")
                a = topic.get("assessment")
                if a and a.get("date"):
                    try:
                        d = dt.date.fromisoformat(a["date"])
                        if not (-30 <= (d - stamp_d).days <= 180):
                            warns.append(f"{seat}/{name}: assessment date "
                                         f"{a['date']} outside window")
                    except ValueError:
                        fails.append(f"{seat}/{name}: unparseable "
                                     f"assessment date {a['date']!r}")
        if not (BAND[0] <= total <= BAND[1]):
            fails.append(f"{seat}: {total} topics outside sane band {BAND}")

        manuals = sorted(glob.glob(os.path.join(args.manual_dir, "*.json")))
        if manuals:
            m = json.load(open(manuals[-1], encoding="utf-8"))
            ms = (m.get("students", {}).get(seat, {}) or {}).get("subjects", {})
            mtotal = sum(len(e.get("topics", [])) for e in ms.values())
            if mtotal and total < COLLAPSE_RATIO * mtotal:
                fails.append(f"{seat}: topic collapse — {total} vs manual "
                             f"{mtotal} ({os.path.basename(manuals[-1])})")
            drift = set(ms) - set(subjects)
            if drift:
                warns.append(f"{seat}: subjects in manual but not machine: "
                             f"{sorted(drift)}")

    for w in warns:
        print(f"WARN: {w}")
    for f_ in fails:
        print(f"FAIL: {f_}")
    print(f"RESULT: {'FAIL' if fails else 'PASS'} "
          f"({len(fails)} fails, {len(warns)} warns)")
    sys.exit(2 if fails else 0)


if __name__ == "__main__":
    main()
