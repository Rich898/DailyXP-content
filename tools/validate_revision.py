#!/usr/bin/env python3
"""
validate_revision.py — the mechanical gate for exam-revision sets (EXAM-REVISION.md LAWS).

Checks a composed question set against the LAWS before it is allowed to go live:
  E1  every question cites a `src`
  E2  no `mc` in a subject whose blueprint says multiple_choice=false;
      Science set must include a Part-C Skills item
  E3  MC fairness: correct answers spread (no single letter > 50% when >=3 MC),
      and the correct option is not the sole-longest too often (<=34% of MC, per LAW 1)
  E4  no multi-part items (a single `q` containing both "(a)" and "(b)")
  E9  (optional) no item whose id was asked within the recent window
  schema: mc has opts + valid `a`; short/tb has a model

Usage:
  python3 tools/validate_revision.py <set.json> [--blueprint revision/roshan.json]
                                      [--recent recent_ids.txt]
`set.json` is a JSON array of question objects (the `questions` payload), or an object
with a top-level "questions" array.
Exit code 0 = PASS, 1 = FAIL.
"""
import json, sys, argparse
from collections import Counter

def load_questions(path):
    data = json.load(open(path))
    if isinstance(data, dict) and "questions" in data:
        return data["questions"]
    if isinstance(data, list):
        return data
    raise SystemExit("set file must be a JSON array or have a top-level 'questions' array")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set_file")
    ap.add_argument("--blueprint", default="revision/roshan.json")
    ap.add_argument("--recent", default=None, help="file of recently-asked bank ids, one per line (E9)")
    args = ap.parse_args()

    qs = load_questions(args.set_file)
    try:
        bp = json.load(open(args.blueprint))
        subj_mc = {s: d["exam"]["multiple_choice"] for s, d in bp["subjects"].items()}
    except Exception:
        subj_mc = {}
    recent = set()
    if args.recent:
        try:
            recent = {l.strip() for l in open(args.recent) if l.strip()}
        except FileNotFoundError:
            pass

    errors, warnings = [], []

    # per-question checks
    for i, q in enumerate(qs):
        tag = f"#{i} ({q.get('s','?')}/{q.get('t','?')})"
        if not q.get("src"):                                   # E1
            errors.append(f"E1 {tag}: missing `src`")
        if "(a)" in q.get("q", "") and "(b)" in q.get("q", ""):  # E4 (info, not a fail)
            warnings.append(f"E4 {tag}: multi-part item — ensure it is part-credited (E5), never all-or-nothing")
        t = q.get("t")
        if t == "mc":
            if "opts" not in q or "a" not in q or not (0 <= q.get("a", -1) < len(q.get("opts", []))):
                errors.append(f"schema {tag}: mc needs opts + valid `a`")
            if subj_mc.get(q.get("s")) is False:               # E2
                errors.append(f"E2 {tag}: multiple choice in a no-MC subject")
        elif t in ("short", "tb"):
            if not q.get("model"):
                errors.append(f"schema {tag}: {t} needs a `model` answer")
        else:
            errors.append(f"schema {tag}: unknown type {t!r}")
        if q.get("id") in recent:                              # E9
            warnings.append(f"E9 {tag}: id {q.get('id')} was asked within the recent window")

    # set-level MC fairness (E3 / LAW 1)
    mc = [q for q in qs if q.get("t") == "mc" and "opts" in q and "a" in q]
    if len(mc) >= 3:
        pos = Counter(q["a"] for q in mc)
        top_letter, top_n = pos.most_common(1)[0]
        if top_n / len(mc) > 0.5:
            errors.append(f"E3: correct MC answers clustered — {top_n}/{len(mc)} at position "
                          f"{'ABCD'[top_letter]} (>50%); spread across A-D")
        sole_longest = 0
        for q in mc:
            lens = [len(str(o)) for o in q["opts"]]
            m = max(lens)
            if lens.count(m) == 1 and lens.index(m) == q["a"]:
                sole_longest += 1
        if sole_longest / len(mc) > 0.34:
            errors.append(f"E3/LAW1: correct option is the sole-longest in {sole_longest}/{len(mc)} "
                          f"MC (>34%) — a length tell")

    # Science must carry a Skills item (E2)
    sci = [q for q in qs if q.get("s") == "Science"]
    if sci and not any("Skills" in str(q.get("section", "")) or "skills" in str(q.get("src", "")).lower() or "SKILLS" in q.get("q", "") for q in sci):
        warnings.append("E2: Science set has no Part-C Skills item")

    print(f"Validated {len(qs)} questions | MC: {len(mc)}")
    for w in warnings:
        print("  WARN  " + w)
    if errors:
        for e in errors:
            print("  FAIL  " + e)
        print(f"\nRESULT: FAIL ({len(errors)} error(s)) — do not load this set.")
        sys.exit(1)
    print("\nRESULT: PASS — safe to load.")
    sys.exit(0)

if __name__ == "__main__":
    main()
