#!/usr/bin/env python3
"""
build_revision.py — the exam-revision planner (EXAM-REVISION.md §6B/§7).

Composes one Part-1 practice set FROM the blueprint bank, honouring each subject's exam
format (E2), spreading MC answer positions across A-D (E3), carrying each item's id + src
(E1/E9), and avoiding items asked recently (E9). Emits a ready-to-load set:
  { "day", "title", "intro", "questions": [ ... ] }

Usage:
  python3 tools/build_revision.py --blueprint revision/roshan.json --day day36 \
      --out set.json [--recent recent_ids.txt] [--seed 42] \
      [--counts Science=8,History=5,Geography=7]

The caller then runs validate_revision.py on --out before loading it to Supabase.
"""
import json, argparse, random, sys

DEFAULT_COUNTS = {"Science": 8, "History": 5, "Geography": 7}

def pick(bank, n, recent, rng, want_mc=None):
    """Pick up to n items from bank, skipping recent ids; want_mc True/False filters type, None = any."""
    pool = [b for b in bank if b["id"] not in recent and (want_mc is None or (b["t"] == "mc") == want_mc)]
    rng.shuffle(pool)
    return pool[:n]

def balance_mc_positions(mc_items, rng):
    """Re-order each MC's options so correct answers are spread across A-D (E3)."""
    targets = []
    k = len(mc_items)
    # cycle 0,1,2,3,0,1,... then shuffle so it isn't a predictable ABCD ladder
    for i in range(k):
        targets.append(i % 4)
    rng.shuffle(targets)
    for item, tgt in zip(mc_items, targets):
        opts = list(item["opts"])
        correct = opts[item["a"]]
        others = [o for j, o in enumerate(opts) if j != item["a"]]
        rng.shuffle(others)
        tgt = min(tgt, len(opts) - 1)
        new = others[:tgt] + [correct] + others[tgt:]
        item["opts"] = new
        item["a"] = new.index(correct)
    return mc_items

def to_question(b):
    """Project a bank item into a quiz question (keep id + src for the ledger; E9)."""
    q = {"s": b["_subject"], "t": b["t"], "q": b["ask"], "id": b["id"], "src": b["src"]}
    if b.get("section"):
        q["section"] = b["section"]
    if b["t"] == "mc":
        q["opts"] = b["opts"]; q["a"] = b["a"]; q["e"] = b.get("e", "")
    else:
        q["model"] = b["model"]
        if b.get("keys"):
            q["keys"] = b["keys"]
    return q

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blueprint", default="revision/roshan.json")
    ap.add_argument("--day", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--recent", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--counts", default=None, help="e.g. Science=8,History=5,Geography=7")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    bp = json.load(open(args.blueprint))
    recent = set()
    if args.recent:
        try:
            recent = {l.strip() for l in open(args.recent) if l.strip()}
        except FileNotFoundError:
            pass
    counts = dict(DEFAULT_COUNTS)
    if args.counts:
        for kv in args.counts.split(","):
            k, v = kv.split("="); counts[k.strip()] = int(v)

    chosen = []
    for subj, n in counts.items():
        d = bp["subjects"].get(subj)
        if not d:
            continue
        bank = [dict(b, _subject=subj) for b in d["bank"]]
        if d["exam"]["multiple_choice"]:
            # Geography-style: ~55% MC (Section I is a third of marks; a bit more in practice), rest short/tb
            n_mc = max(1, round(n * 0.55))
            items = pick(bank, n_mc, recent, rng, want_mc=True) + pick(bank, n - n_mc, recent, rng, want_mc=False)
        else:
            items = pick(bank, n, recent, rng)
        chosen.extend(items)

    # E3: spread MC answer positions across the whole set
    balance_mc_positions([c for c in chosen if c["t"] == "mc"], rng)

    questions = [to_question(b) for b in chosen]
    out = {
        "day": args.day,
        "title": "Science + History + Geography — exam-format practice",
        "intro": ("Exam-format practice across Science, History and Geography, built from your "
                  "own Canvas material. Science is written answers + a Skills section (no multiple "
                  "choice); History is short written answers; Geography has a few multiple-choice "
                  "then structured short answers. Write in full sentences, show your working. Your "
                  "written answers are marked on your ideas, and you get part-marks — just explain "
                  "it your way. Take your time."),
        "questions": questions,
    }
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=2)
    byt = {}
    for q in questions:
        byt[q["s"]] = byt.get(q["s"], 0) + 1
    print(f"Composed {len(questions)} questions -> {args.out}")
    print("  by subject:", byt)
    print("  MC positions:", sorted(q["a"] for q in questions if q["t"] == "mc"))
    print("  ids:", ", ".join(q["id"] for q in questions))

if __name__ == "__main__":
    main()
