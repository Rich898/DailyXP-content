#!/usr/bin/env python3
"""
sweep_diff.py — the shadow SCOREBOARD (limb #1d). Deterministic. No LLM.

Compares a machine-summarised sweep against a manual targets file, topic by
topic, and writes the side-by-side markdown that decides promotion. The
trust-ladder rule: the scheduled sweep only replaces the manual one after
this report shows match-or-better two weekends running.

Matching is fuzzy on normalised topic names (token overlap), because the
same teaching topic worded two ways is a match, not a miss.

Buckets per seat/subject:
  MATCHED       both sweeps found it
  MANUAL-ONLY   the machine missed it   (the number that matters most)
  MACHINE-ONLY  extra finds — noise OR genuinely new content; human-judged
Plus an assessment-date agreement table.

Usage:
  python3 tools/sweep_diff.py --machine <targets-shadow.json> \
      --manual <targets/YYYY-MM-DD.json> --out <DIFF.md>
"""
import argparse
import json
import re

STOP = {"the", "a", "an", "of", "in", "and", "for", "to", "with", "on",
        "unit", "intro", "introduction"}


def toks(s):
    words = re.findall(r"[a-z0-9]+", (s or "").lower())
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
    grand = {"matched": 0, "manual_only": 0, "machine_only": 0}

    for seat in sorted(set(mn) | set(mc)):
        lines.append(f"## {seat}")
        subjects = sorted(set((mn.get(seat, {}).get("subjects") or {})) |
                          set((mc.get(seat, {}).get("subjects") or {})))
        for subj in subjects:
            man = subject_topics(mn, seat, subj)
            mac = subject_topics(mc, seat, subj)
            used = set()
            matched, manual_only = [], []
            for m in man:
                hit = next((i for i, x in enumerate(mac)
                            if i not in used and match(m, x)), None)
                if hit is None:
                    manual_only.append(m)
                else:
                    used.add(hit)
                    matched.append((m, mac[hit]))
            machine_only = [x for i, x in enumerate(mac) if i not in used]
            grand["matched"] += len(matched)
            grand["manual_only"] += len(manual_only)
            grand["machine_only"] += len(machine_only)
            lines.append(f"### {subj} — {len(matched)} matched · "
                         f"{len(manual_only)} manual-only · "
                         f"{len(machine_only)} machine-only")
            for m, x in matched:
                lines.append(f"- MATCH: `{m}` ≈ `{x}`")
            for m in manual_only:
                lines.append(f"- **MANUAL-ONLY (machine missed): `{m}`**")
            for x in machine_only:
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

    total = sum(grand.values())
    score = (f"**SCOREBOARD: {grand['matched']} matched · "
             f"{grand['manual_only']} manual-only (missed) · "
             f"{grand['machine_only']} machine-only** "
             f"({0 if not total else round(100 * grand['matched'] / max(1, grand['matched'] + grand['manual_only']))}% "
             f"of manual topics found)")
    lines.insert(2, score)
    lines.insert(3, "")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(score)


if __name__ == "__main__":
    main()
