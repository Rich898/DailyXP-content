#!/usr/bin/env python3
"""
generate_revision.py — orchestrates the dedicated generator into one session (EXAM-REVISION.md).

For each requested subject it calls the `generate` edge function with that subject's topics +
format + grounding from the blueprint, assembles the questions, spreads MC answer positions
across the whole set (E3), and writes a ready-to-validate set:
  { "day", "title", "intro", "questions": [ ... ] }

Usage:
  python3 tools/generate_revision.py --subjects Science,Geography --day day37 \
      --out set.json [--counts Science=11,Geography=9] [--recent recent_ids.txt] [--seed 7]

Then run tools/validate_revision.py on --out before loading to Supabase.
"""
import json, argparse, random, sys, urllib.request

SUPA = "https://ftknumgdmalxyjxvqlux.supabase.co"
ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ0a251bWdkbWFseHlqeHZxbHV4"
        "Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY5Mzc2MTYsImV4cCI6MjEwMjUxMzYxNn0.hynBqLOOsu8Hr7etMlFBhNMUSutZ0Hb8HXL5rpL3rDc")
DEFAULT_PER_SUBJECT = 10

def call_generate(subject, d, count, avoid):
    payload = {
        "subject": subject, "year": "Year 9",
        "allow_mc": d["exam"]["multiple_choice"],
        "sections": d["exam"]["sections"],
        "topics": d["topics"], "count": count, "avoid": avoid,
    }
    req = urllib.request.Request(
        f"{SUPA}/functions/v1/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "apikey": ANON, "Authorization": "Bearer " + ANON},
        method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    if "error" in out:
        raise SystemExit(f"generate failed for {subject}: {out}")
    return out.get("questions", [])

def balance_mc(mc_items, rng):
    k = len(mc_items)
    targets = [i % 4 for i in range(k)]; rng.shuffle(targets)
    for item, tgt in zip(mc_items, targets):
        opts = list(item["opts"]); correct = opts[item["a"]]
        others = [o for j, o in enumerate(opts) if j != item["a"]]; rng.shuffle(others)
        tgt = min(tgt, len(opts) - 1)
        new = others[:tgt] + [correct] + others[tgt:]
        item["opts"] = new; item["a"] = new.index(correct)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blueprint", default="revision/roshan.json")
    ap.add_argument("--subjects", required=True, help="comma list, e.g. Science,Geography")
    ap.add_argument("--day", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--counts", default=None, help="Science=11,Geography=9")
    ap.add_argument("--recent", default=None, help="file of recently-asked topic ids")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    bp = json.load(open(args.blueprint))
    subjects = [s.strip() for s in args.subjects.split(",") if s.strip()]
    counts = {s: DEFAULT_PER_SUBJECT for s in subjects}
    if args.counts:
        for kv in args.counts.split(","):
            k, v = kv.split("="); counts[k.strip()] = int(v)
    avoid = []
    if args.recent:
        try: avoid = [l.strip() for l in open(args.recent) if l.strip()]
        except FileNotFoundError: pass

    questions = []
    for s in subjects:
        d = bp["subjects"].get(s)
        if not d:
            print(f"  (skip {s}: not in blueprint)"); continue
        qs = call_generate(s, d, counts[s], avoid)
        # enrich each question with its topic's section (from the blueprint) for coverage + validation
        sec = {t["id"]: t.get("section", "") for t in d["topics"]}
        for q in qs:
            if q.get("src") in sec and sec[q["src"]]:
                q["section"] = sec[q["src"]]
        print(f"  {s}: generated {len(qs)}")
        questions.extend(qs)

    balance_mc([q for q in questions if q.get("t") == "mc"], rng)

    subj_label = " + ".join(subjects)
    out = {
        "day": args.day,
        "title": f"{subj_label} — exam-format practice",
        "intro": (f"Exam-format practice: {subj_label}. Built from your own Canvas material, in each "
                  f"subject's real exam shape. Write in full sentences and show your working. Your written "
                  f"answers are marked on your ideas and you get part-marks — just explain it your way. Take your time."),
        "questions": questions,
    }
    json.dump(out, open(args.out, "w"), ensure_ascii=False, indent=2)
    from collections import Counter
    print(f"Wrote {len(questions)} questions -> {args.out}")
    print("  by subject:", dict(Counter(q['s'] for q in questions)))
    print("  by type:", dict(Counter(q['t'] for q in questions)))
    print("  MC positions:", sorted(q['a'] for q in questions if q['t'] == 'mc'))

if __name__ == "__main__":
    main()
