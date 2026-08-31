#!/usr/bin/env python3
"""
sweep_promote.py — the PROMOTION step (Rich's B6 GO, 31 Aug 2026).

Runs strictly AFTER sweep_validate in the workflow, success-gated, so it
executes only on a validator PASS. It copies the validated machine summary
into targets/<monday>.json — the file the live pipeline auto-picks — with
three relabels:

  - week_of stamped to the target Monday
  - source loses its "(SHADOW)" tag and records the promotion
  - school_week bumps "…Week N" -> N+1 when the newest prior targets file
    is exactly the previous Monday (term boundaries: no guessing — keep
    the summariser's value; calendar.json (C1) owns real term arithmetic
    when it lands)

SAFETY: refuses to overwrite an existing targets file unless --force (the
workflow passes it only from the explicit overwrite_targets dispatch
input). A refusal exits 0 — a mid-week rerun for diff evidence must not
turn the run red. FAIL = HOLD lives upstream: on a validator FAIL this
never runs, the pipeline falls back to the newest existing targets file,
and staleness degrades loudly, never silently (the standing law).
"""
import argparse
import datetime as dt
import glob
import json
import os
import re


def bump_school_week(shadow_week, prev_week_of, prev_school_week, week):
    """Prev file is last Monday and carries 'Week N' -> same wording, N+1."""
    try:
        monday = dt.date.fromisoformat(week)
        prev = dt.date.fromisoformat(prev_week_of or "")
    except ValueError:
        return shadow_week
    if (monday - prev).days != 7:
        return shadow_week
    m = re.search(r"^(.*Week )(\d+)(.*)$", prev_school_week or "")
    if not m:
        return shadow_week
    return "{}{}{}".format(m.group(1), int(m.group(2)) + 1, m.group(3))


def relabel(shadow, week, prev):
    """Mutate the shadow summary into its promoted-targets identity."""
    shadow["week_of"] = week
    src = (shadow.get("source") or "").replace("(SHADOW) ", "")
    shadow["source"] = (src + " | PROMOTED to targets/" + week + ".json "
                        "behind the validator gate (B6 GO, 31 Aug 2026)")
    shadow["school_week"] = bump_school_week(
        shadow.get("school_week"), (prev or {}).get("week_of"),
        (prev or {}).get("school_week"), week)
    return shadow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shadow", required=True)
    ap.add_argument("--targets-dir", required=True)
    ap.add_argument("--week", required=True, help="Monday date YYYY-MM-DD")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    out = os.path.join(args.targets_dir, args.week + ".json")
    if os.path.exists(out) and not args.force:
        print(f"promote: {out} already exists — NOT overwriting "
              "(dispatch with overwrite_targets=true to replace)")
        return

    prior = sorted(p for p in glob.glob(os.path.join(args.targets_dir, "*.json"))
                   if os.path.abspath(p) != os.path.abspath(out))
    prev = None
    if prior:
        with open(prior[-1], encoding="utf-8") as f:
            prev = json.load(f)

    with open(args.shadow, encoding="utf-8") as f:
        shadow = json.load(f)
    relabel(shadow, args.week, prev)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(shadow, f, indent=1, ensure_ascii=False)
    seats = shadow.get("students", {})
    topics = sum(len(e.get("topics", [])) for sd in seats.values()
                 for e in (sd.get("subjects") or {}).values())
    print(f"promote: wrote {out} — {len(seats)} seat(s), {topics} topics")


if __name__ == "__main__":
    main()
