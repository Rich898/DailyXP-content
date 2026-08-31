#!/usr/bin/env python3
"""
sweep_overrides.py — per-seat LIVE-ROTATION overrides (B6 promotion item).

Why this exists: rotation/stream membership is invisible to the automated
sweep BY DESIGN. The fetcher reads six content surfaces and never touches
grades/submissions/inbox — but which Technology rotation (or class stream)
a student is actually in is often only provable from their submissions.
The 31 Aug head-to-head showed exactly this failure shape: the machine
marked y8's live Spice Rack strand prior_term and CO2 Cars live, inverted
from reality.

So the human keeps ONE fact per rotation subject — which strand is live —
in the PRIVATE repo (overrides/rotations.json), and this pass applies it
to the summarised targets between the schedule-pass and the validator:

  { "y8": { "Technology": {
      "live": "Timber Spice Rack",
      "strands": ["CO2 Car", "Digital Technology",
                  "Food Technology", "Timber Spice Rack"] } } }

Rules (deterministic, status-only):
  - topic name contains the live strand (case-insensitive) -> "live"
  - topic name contains any OTHER listed strand            -> "prior_term"
  - anything else (incl. seats/subjects not named)         -> untouched
  - topics are never added or removed; fresh flags untouched
Missing overrides file = explicit no-op (prints so). Public logs carry
codes and counts only — never topic names (codes-only log law).
"""
import argparse
import json


def apply(targets, overrides):
    """Mutate targets in place; return {(seat, subject): (n_live, n_prior)}."""
    changed = {}
    for seat, subjects in (overrides or {}).items():
        if seat.startswith("_"):
            continue
        seat_entry = (targets.get("students") or {}).get(seat)
        if not seat_entry or not isinstance(subjects, dict):
            continue
        for subject, rule in subjects.items():
            entry = (seat_entry.get("subjects") or {}).get(subject)
            live = ((rule or {}).get("live") or "").strip()
            strands = [s for s in (rule or {}).get("strands", []) if s]
            if not entry or not live:
                continue
            n_live = n_prior = 0
            for t in entry.get("topics", []):
                name = (t.get("topic") or "").lower()
                if live.lower() in name:
                    if t.get("status") != "live":
                        n_live += 1
                    t["status"] = "live"
                elif any(s.lower() in name for s in strands):
                    if t.get("status") != "prior_term":
                        n_prior += 1
                    t["status"] = "prior_term"
            changed[(seat, subject)] = (n_live, n_prior)
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", required=True)
    ap.add_argument("--overrides", required=True)
    args = ap.parse_args()

    try:
        with open(args.overrides, encoding="utf-8") as f:
            overrides = json.load(f)
    except FileNotFoundError:
        print(f"overrides: no file at {args.overrides} — no-op")
        return

    with open(args.targets, encoding="utf-8") as f:
        targets = json.load(f)
    changed = apply(targets, overrides)
    if not changed:
        print("overrides: file present but no seat/subject matched — no-op")
        return
    with open(args.targets, "w", encoding="utf-8") as f:
        json.dump(targets, f, indent=1, ensure_ascii=False)
    for (seat, subject), (n_live, n_prior) in sorted(changed.items()):
        print(f"{seat}/{subject}: rotation override applied — "
              f"{n_live} topic(s) -> live, {n_prior} -> prior_term")


if __name__ == "__main__":
    main()
