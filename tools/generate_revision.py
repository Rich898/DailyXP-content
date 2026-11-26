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

def fetch_coverage(student, recent_hours=36):
    """Read the coverage ledger (LAW E9). Returns (recent_ids:set, weak_ids:set)."""
    url = (f"{SUPA}/rest/v1/revision_coverage?student=eq.{student}"
           "&select=topic_id,last_asked,avg_score")
    req = urllib.request.Request(url, headers={"apikey": ANON, "Authorization": "Bearer " + ANON})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            rows = json.load(r)
    except Exception as e:
        print(f"  (coverage unavailable, steering off: {e})"); return set(), set()
    import datetime
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=recent_hours)
    recent, weak = set(), set()
    for row in rows:
        la = row.get("last_asked")
        try:
            t = datetime.datetime.fromisoformat(la.replace("Z", "+00:00")) if la else None
        except Exception:
            t = None
        if t and t >= cutoff:
            recent.add(row["topic_id"])
        if row.get("avg_score") is not None and float(row["avg_score"]) < 0.5:
            weak.add(row["topic_id"])
    return recent, weak

def call_generate(subject, d, topics, count, avoid):
    payload = {
        "subject": subject, "year": "Year 9",
        "allow_mc": d["exam"]["multiple_choice"],
        "sections": d["exam"]["sections"],
        "topics": topics, "count": count, "avoid": avoid,
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
    ap.add_argument("--order", choices=["interleave", "block"], default="interleave",
                    help="interleave=vary subject question-to-question (default); block=all of one subject then the next")
    ap.add_argument("--no-steer", action="store_true", help="ignore the coverage ledger (no skip/prioritise)")
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

    recent_ids, weak_ids = (set(), set())
    if not args.no_steer:
        recent_ids, weak_ids = fetch_coverage(bp["student"])
        print(f"  ledger: skip {len(recent_ids)} recently-asked, prioritise {len(weak_ids)} weak")

    by_subject = {}   # subject -> its generated questions, in subject order
    for s in subjects:
        d = bp["subjects"].get(s)
        if not d:
            print(f"  (skip {s}: not in blueprint)"); continue
        avail = [t for t in d["topics"] if t["id"] not in recent_ids]
        if len(avail) < max(3, counts[s] // 2):   # not enough fresh topics -> allow recent back in
            avail = list(d["topics"])
        avail.sort(key=lambda t: 0 if t["id"] in weak_ids else 1)   # weak topics first
        qs = call_generate(s, d, avail, counts[s], avoid)
        # enrich each question with its topic's section (from the blueprint) for coverage + validation
        sec = {t["id"]: t.get("section", "") for t in d["topics"]}
        for q in qs:
            if q.get("src") in sec and sec[q["src"]]:
                q["section"] = sec[q["src"]]
        print(f"  {s}: generated {len(qs)}")
        by_subject[s] = qs

    if args.order == "interleave":
        # Round-robin across subjects so it varies question-to-question (no subject chunks).
        # Each subject's internal order (weak-first) is preserved within its own slots.
        cursors = {s: iter(by_subject.get(s, [])) for s in subjects}
        active = [s for s in subjects if by_subject.get(s)]
        questions = []
        last = None
        while active:
            # rotate the subject order each round so the lead subject changes, and never
            # start a round with the same subject that just went (avoids an accidental pair)
            round_order = [s for s in active]
            if last is not None and len(round_order) > 1 and round_order[0] == last:
                round_order = round_order[1:] + round_order[:1]
            progressed = []
            for s in round_order:
                nxt = next(cursors[s], None)
                if nxt is None:
                    continue
                questions.append(nxt); last = s; progressed.append(s)
            active = [s for s in active if s in progressed]
    else:  # block
        questions = []
        for s in subjects:
            questions.extend(by_subject.get(s, []))

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
