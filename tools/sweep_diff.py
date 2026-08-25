#!/usr/bin/env python3
"""
sweep_diff.py — the shadow SCOREBOARD (limb #1d). Deterministic. No LLM.

Compares a machine-summarised sweep against a manual targets file, topic by
topic — the side-by-side that decides promotion. Trust-ladder rule: the
scheduled sweep only replaces the manual one after this shows match-or-better
two weekends running.

Matching is fuzzy on normalised topic names (token overlap) with two
fairness rules learned from the first shadow run:
  - abbreviations expand before matching (R&J -> Romeo and Juliet, & -> and)
  - split credit: one manual topic covered by several machine topics (or
    vice versa) counts as FOUND, not as a miss plus noise.

Buckets per seat/subject:
  MATCHED        found (1:1 or split coverage)
  MANUAL-ONLY    the machine genuinely missed it (the number that matters)
  MACHINE-ONLY   extra finds with no manual counterpart — noise OR new; judged

Usage:
  python3 tools/sweep_diff.py --machine <targets-shadow.json> \
      --manual <targets/YYYY-MM-DD.json> --out <DIFF.md>
"""
import argparse
import json
import re

STOP = {"the", "a", "an", "of", "in", "and", "for", "to", "with", "on",
        "unit", "intro", "introduction"}
ABBREV = [("r&j", "romeo and juliet"), ("&", " and "), ("lotf", "lord of the flies")]


def toks(s):
    s = (s or "").lower()
    for a, b in ABBREV:
        s = s.replace(a, b)
    words = re.findall(r"[a-z0-9]+", s)
    return {w for w in words if w not in STOP and len(w) > 1}


def match(a, b):
    ta, tb = toks(a), toks(b)
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    return (inter / len(ta | tb) >= 0.45) or (inter / min(len(ta), len(tb)) >= 0.6)


def subject_topics(students, seat, subject):
    return [t.get("topic", "") for t in
            (students.get(seat, {}).get("subjects", {})
             .get(subject, {}) or {}).get("topics", [])]


def assessments(students, seat):
    out = {}
    for subj, entry in (students.get(seat, {}).get("subjects", {}) or {}).items():
        for t in entry.get("topics", []):
            a = t.get("assessment")
            if a and a.get("date"):
                out.setdefault(subj, set()).add((a.get("task", "")[:60], a["date"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", required=True)
    ap.add_argument("--manual", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    mc = json.load(open(args.machine, encoding="utf-8"))["students"]
    mn = json.load(open(args.manual, encoding="utf-8"))["students"]

    lines = [f"# Shadow sweep vs manual — machine `{args.machine}` "
             f"vs manual `{args.manual}`", ""]
    found = manual_total = machine_only_total = 0

    for seat in sorted(set(mn) | set(mc)):
        lines.append(f"## {seat}")
        subjects = sorted(set((mn.get(seat, {}).get("subjects") or {})) |
                          set((mc.get(seat, {}).get("subjects") or {})))
        for subj in subjects:
            man = subject_topics(mn, seat, subj)
            mac = subject_topics(mc, seat, subj)
            manual_total += len(man)
            used = set()
            pairs, misses = [], []
            for m in man:
                hit = next((i for i, x in enumerate(mac)
                            if i not in used and match(m, x)), None)
                if hit is None:
                    misses.append(m)
                else:
                    used.add(hit)
                    pairs.append((m, mac[hit], ""))
            split_found = [m for m in misses if any(match(m, x) for x in mac)]
            misses = [m for m in misses if m not in split_found]
            for m in split_found:
                pairs.append((m, next(x for x in mac if match(m, x)),
                              " (split coverage)"))
            extras = [x for i, x in enumerate(mac) if i not in used
                      and not any(match(x, m2) for m2 in man)]
            found += len(pairs)
            machine_only_total += len(extras)
            lines.append(f"### {subj} — {len(pairs)} found · "
                         f"{len(misses)} manual-only · {len(extras)} machine-only")
            for m, x, tag in pairs:
                lines.append(f"- MATCH{tag}: `{m}` ≈ `{x}`")
            for m in misses:
                lines.append(f"- **MANUAL-ONLY (machine missed): `{m}`**")
            for x in extras:
                lines.append(f"- MACHINE-ONLY (judge: noise or new?): `{x}`")
        ma, mb = assessments(mn, seat), assessments(mc, seat)
        lines.append(f"### {seat} assessment dates")
        for subj in sorted(set(ma) | set(mb)):
            a, b = ma.get(subj, set()), mb.get(subj, set())
            both = {d for _, d in a} & {d for _, d in b}
            man_only = {f"{t} {d}" for t, d in a if d not in both}
            mac_only = {f"{t} {d}" for t, d in b if d not in both}
            lines.append(f"- {subj}: {len(both)} dates agree"
                         + (f" · manual-only: {sorted(man_only)}" if man_only else "")
                         + (f" · machine-only: {sorted(mac_only)}" if mac_only else ""))
        lines.append("")

    pct = 0 if not manual_total else round(100 * found / manual_total)
    score = (f"**SCOREBOARD: {found}/{manual_total} manual topics found "
             f"({pct}%) · {manual_total - found} missed · "
             f"{machine_only_total} machine-only**")
    lines.insert(2, score)
    lines.insert(3, "")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(score)


if __name__ == "__main__":
    main()
