#!/usr/bin/env python3
"""
sweep_docx_alert.py — flag NEW assessment paperwork the sweep CANNOT read
(B6 promotion item).

The 31 Aug head-to-head found both new assessment dates of the week locked
inside attachments — a docx pinned as an HSIE module item and a docx on an
English announcement — invisible to the schedule-pass (noticeboard PDFs
only) and, that day, skipped by the manual sweep too. This pass walks each
seat's raw dump for paperwork the sweep can't open and raises a LOUD flag
so a human reads it the same day.

What counts as unreadable paperwork (Canvas strips extensions from item
titles, so extension alone is not enough):
  - module items of type "File" whose title looks like assessment paperwork
  - announcements (posted_at-bearing) with paperwork-looking titles —
    their attachments are what the sweep can't open
  - any attachment filename ending .doc/.docx that looks like paperwork
Pages/assignments are NOT flagged — the sweep reads those surfaces.

Noise control: with --prev-dump, only names ABSENT from the previous
week's dump are reported — stale Term 1/2 notifications stop crying wolf
after their first week. No previous dump = first run, everything flags.

Alert-only: never fails the run. Public logs carry codes + counts; the
actual names route to <dump>/docx-alerts.txt (private repo), per the
codes-only log law.
"""
import argparse
import json
import os
import re
import sys

ATTACH_KEYS = {"display_name", "filename"}
PAT = re.compile(r"assess|examinat|\bexam\b|notification", re.IGNORECASE)
DOC = re.compile(r"\.docx?\s*$", re.IGNORECASE)


def candidates(obj, out=None):
    """Recursively collect unreadable, assessment-looking paperwork names."""
    if out is None:
        out = set()
    if isinstance(obj, dict):
        title = obj.get("title") if isinstance(obj.get("title"), str) else None
        if title and PAT.search(title):
            if obj.get("type") == "File" or "posted_at" in obj:
                out.add(title.strip())
        for k, v in obj.items():
            if k in ATTACH_KEYS and isinstance(v, str) and DOC.search(v) \
                    and PAT.search(v):
                out.add(v.strip())
            else:
                candidates(v, out)
    elif isinstance(obj, list):
        for v in obj:
            candidates(v, out)
    return out


def seat_codes(dump_dir):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import roster
        codes = roster.students()
    except Exception:
        codes = ["y8", "y9"]
    return [c for c in codes
            if os.path.exists(os.path.join(dump_dir, c + ".json"))]


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", required=True)
    ap.add_argument("--prev-dump", default="",
                    help="previous week's dump dir; only NEW names flag")
    args = ap.parse_args()

    lines = []
    for code in seat_codes(args.dump):
        cur = candidates(_load(os.path.join(args.dump, code + ".json")))
        prev_path = os.path.join(args.prev_dump, code + ".json") \
            if args.prev_dump else ""
        if prev_path and os.path.exists(prev_path):
            new = cur - candidates(_load(prev_path))
            basis = "new vs previous dump"
        else:
            new = cur
            basis = "no previous dump — all flagged"
        if new:
            print(f"::warning::{code}: {len(new)} unreadable assessment "
                  f"paperwork item(s) ({basis}) — open manually "
                  "(names in docx-alerts.txt, private)")
            lines.append(code + f" ({basis}):")
            lines.extend("  " + n for n in sorted(new))
        else:
            print(f"{code}: no new unreadable assessment paperwork ({basis})")
    if lines:
        path = os.path.join(args.dump, "docx-alerts.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"docx alert detail -> {path} (private repo only)")


if __name__ == "__main__":
    main()
