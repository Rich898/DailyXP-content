#!/usr/bin/env python3
"""
grade_teachback.py — the teach-back QUALITY grade (the one real language judgement in ingestion).

The shell's green tick is only an EFFORT gate (enough real English words). The teach-back is
the deepest anti-fluency-illusion signal — can the student explain it in their own words? — so
its quality has to be judged, and that judgement is a language task (the LLM), not a rule.

This step is isolated on purpose:
  - It is the ONLY non-deterministic thing in the ingestion path. It reads each canonical run's
    teach-back text, asks the model for a verdict, and ANNOTATES the run with `tb_grade`.
  - The state-writer then consumes `tb_grade` DETERMINISTICALLY (state_writer.verdict_badge) and
    maps it onto the existing box model — so the ledger stays deterministic and testable, and a
    grader failure just leaves the teach-back ungraded (state-writer falls back to the old no-op).

Grade (SUBSTANCE over style — the boys are young / may be ESL, so spelling & grammar don't matter):
  solid   — correct and shows real understanding in their own words.
  partial — right track but incomplete, vague, or a notable gap/error in the core idea.
  none    — no understanding shown: wrong, empty, off-topic, just restates the question, or not
            a real explanation. A non-English answer is `none` with english:false.

Idempotent: only grades canonical, non-test runs whose teach question has text and no `tb_grade`.

Usage:
  ANTHROPIC_API_KEY=... python3 tools/grade_teachback.py --private-dir ../DailyXP-private [--dry-run]
"""
import argparse
import json
import os
import re
import sys
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("DAILYXP_GRADE_MODEL", "claude-sonnet-5")  # judgement task; strong + economical
MAX_TOKENS = 400   # a tiny JSON verdict — no headroom needed

SYSTEM = """You grade a student's TEACH-BACK: their attempt to explain a concept in their own words.
This is the deepest test of real understanding — the whole tool exists to catch the "fluency illusion",
where a student can pick the right multiple-choice answer but cannot actually explain the idea.

You are given the SUBJECT, the QUESTION they were asked, and their ANSWER. You return TWO independent
readings of that answer. They measure different things and must not be collapsed into each other.

=== READING 1: "verdict" — IS IT CORRECT? (confidence axis) ===
- "solid": correct and shows real understanding, in their own words.
- "partial": on the right track but incomplete, vague, or with a notable gap or error in the core idea.
- "none": does NOT demonstrate understanding — wrong, empty, off-topic, merely restates the question,
  or is not a real explanation.

=== READING 2: "depth" — HOW DEEPLY IS IT UNDERSTOOD? (understanding axis) ===
Judge the STRUCTURE of the explanation, not whether it is correct. Return exactly one rung:
- "not_yet": misses the point, off-topic, empty, or merely restates the question.
- "knows": states ONE relevant correct idea. A single fact or definition, nothing more.
- "lists": states SEVERAL correct parts, but holds them SEPARATELY — an enumeration. Things are
  named one after another without being joined into an explanation.
- "connects": LINKS the parts into a working explanation — cause and effect, part and whole, a
  comparison, a "because/so/which meant" chain. The answer explains HOW or WHY, not just WHAT.
- "applies": takes the idea into a context it was NOT taught in — a new example of the student's own,
  or the principle used in a different direction. RARE. Only award this on explicit evidence of
  transfer to a genuinely new context; if in doubt, use "connects".

THE MOST IMPORTANT RULE ON THIS PAGE: correctness and depth are INDEPENDENT.
A factually perfect answer that merely lists things is "lists", NOT "connects". Grading a correct
answer higher on depth BECAUSE it is correct is the single worst error you can make here — it
produces a false claim about a child's understanding. A messy, half-wrong answer that genuinely
links two ideas causally IS "connects" even while its verdict is "partial".

Rules for judging both readings:
- Judge SUBSTANCE, not style. The student is a secondary-school child and may write informally or be an
  English-as-a-second-language learner. Spelling, grammar, punctuation and phrasing DO NOT matter. Reward
  genuine understanding even when clumsily expressed.
- Do NOT reward filler, hedging, plausible-sounding non-answers, or parroting the question back.
- UNDER-CLAIM. Where the evidence is thin or you are between two rungs, return the LOWER rung. Every
  rung is a claim about a child that a parent may repeat to a teacher.
- "english": true if the answer is written in English, false otherwise. A non-English answer cannot be
  judged as understanding here — grade it "none" / "not_yet" with english:false.
- "evidence": quote the SHORT phrase from the student's own answer that justified the depth rung (a few
  words, verbatim), so the judgement is auditable. Empty string if the rung is "not_yet".

Output ONLY a JSON object, nothing else:
{"verdict": "solid" | "partial" | "none", "depth": "not_yet" | "knows" | "lists" | "connects" | "applies",
 "english": true | false, "evidence": "short quote from the answer", "reason": "one short sentence"}"""


def call_api(system, user, model, api_key):
    body = json.dumps({
        "model": model, "max_tokens": MAX_TOKENS, "system": system,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode())
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


# --------------------------------------------------------------------------- #
# The depth ladder (UNDERSTANDING.md). Order matters — index IS the rung height.
DEPTH_LADDER = ["not_yet", "knows", "lists", "connects", "applies"]

# Words that signal ideas being JOINED rather than merely listed. Used only as a
# deterministic CEILING (it can lower a model's rung, never raise it) — the
# under-claim law: an answer claimed as "connects" with no linking language
# anywhere is more likely an enumeration the model over-read.
LINK_MARKERS = (
    "because", "so ", "so,", "which meant", "which means", "which led", "led to",
    "leads to", "therefore", "thus", "as a result", "result of", "caused",
    "causes", "causing", "due to", "since", "whereas", "while", "unlike",
    "compared", "difference", "different from", "similar", "means that",
    "this shows", "shows that", "reason", "why", "if ", "then ", "in order to",
    "allows", "enables", "prevents", "affects", "impact", "influence",
    "depends", "linked", "connect", "relates", "relationship", "between",
    "but ", "however", "although", "even though", "instead",
)

# Teach-backs cannot evidence above "connects" except on explicit transfer
# (UNDERSTANDING.md §3 ceiling law + §4 promotion rules).
TEACH_CEILING = "connects"


def _has_link_language(answer):
    a = " " + (answer or "").lower() + " "
    return any(m in a for m in LINK_MARKERS)


def cap_depth(depth, answer):
    """Deterministic ceiling on the model's depth rung. LOWERS ONLY, never raises.

    Two guards, both from UNDERSTANDING.md:
      1. 'applies' from a teach-back requires explicit transfer language; without
         link language at all it cannot stand, so it falls to the teach ceiling.
      2. 'connects' claims an explanation that JOINS ideas — if the answer carries
         no linking language whatsoever, under-claim down to 'lists'.
    Returns (depth, capped_reason|None) so the adjustment is auditable.
    """
    if depth not in DEPTH_LADDER:
        return depth, None
    linked = _has_link_language(answer)
    if depth in ("connects", "applies") and not linked:
        return "lists", f"capped from {depth}: no linking language in answer"
    return depth, None


def parse_json(text):
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b != -1:
        t = t[a:b + 1]
    return json.loads(t)


def normalise(grade, answer=""):
    """Coerce a model reply into a clean verdict dict; None if it isn't usable.

    Carries BOTH axes: `verdict` (correctness — consumed unchanged by the state
    writer) and `depth` (understanding — consumed by reporting). Depth is
    validated against the ladder and passed through the deterministic ceiling.
    A missing/invalid depth degrades to None rather than failing the whole grade,
    so the confidence axis never breaks because the new axis misbehaved.
    """
    if not isinstance(grade, dict):
        return None
    v = str(grade.get("verdict", "")).strip().lower()
    if v not in ("solid", "partial", "none"):
        return None
    eng = grade.get("english", True)
    eng = bool(eng) if isinstance(eng, bool) else str(eng).strip().lower() not in ("false", "no", "0")
    if not eng:
        v = "none"   # a non-English answer can't evidence understanding here
    reason = str(grade.get("reason", "")).strip()[:200]

    d = str(grade.get("depth", "")).strip().lower()
    depth = d if d in DEPTH_LADDER else None
    capped = None
    if depth is not None:
        if not eng:
            depth, capped = "not_yet", "not English"
        else:
            depth, capped = cap_depth(depth, answer)
        # a teach-back that showed no understanding at all cannot claim a rung
        if v == "none" and depth not in ("not_yet", "knows"):
            depth, capped = "not_yet", "verdict none"
    out = {"verdict": v, "english": eng, "reason": reason}
    if depth is not None:
        out["depth"] = depth
        ev = str(grade.get("evidence", "")).strip()[:160]
        if ev:
            out["evidence"] = ev
        if capped:
            out["capped"] = capped
    return out


def grade_one(subject, question, answer, model=DEFAULT_MODEL, api_key=None):
    """Grade a single teach-back. Returns a verdict dict, or None if the model/parse failed."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    user = (f"SUBJECT: {subject}\n\nQUESTION:\n{question}\n\nSTUDENT'S ANSWER:\n{answer}\n\n"
            "Grade the answer. Output only the JSON verdict.")
    try:
        raw = call_api(SYSTEM, user, model, api_key)
        return normalise(parse_json(raw), answer)
    except Exception:
        return None


def _teach_q(run):
    for q in run.get("questions", []):
        if q.get("phase") == "teach":
            return q
    return None


def annotate_runs(private_dir, model=DEFAULT_MODEL, api_key=None, dry_run=False):
    """Grade every ungraded teach-back in canonical, non-test runs; write tb_grade back."""
    runs_path = os.path.join(private_dir, "work", "runs.json")
    blob = json.load(open(runs_path))
    runs = blob.get("runs", [])

    graded, skipped, failed = 0, 0, 0
    log = []
    for r in runs:
        if not r.get("canonical") or r.get("is_test"):
            continue
        q = _teach_q(r)
        if not q:
            continue
        text = (q.get("text") or "").strip()
        if not text:
            continue
        if q.get("tb_grade"):          # idempotent — already graded
            skipped += 1
            continue
        who = f"{r.get('student')} · {r.get('tag')} ({q.get('subject')})"
        if dry_run:
            log.append(f"  would grade: {who} — {len(text)} chars")
            continue
        g = grade_one(q.get("subject", ""), q.get("prompt", ""), text, model, api_key)
        if g is None:
            failed += 1
            log.append(f"  GRADE FAILED (left ungraded): {who}")
            continue
        q["tb_grade"] = g
        graded += 1
        log.append(f"  {who} → {g['verdict']}"
                   + (f" · depth={g['depth']}" if g.get("depth") else "")
                   + (f" [{g['capped']}]" if g.get("capped") else "")
                   + ("" if g["english"] else " (not English)")
                   + (f" — {g['reason']}" if g["reason"] else ""))

    if graded and not dry_run:
        tmp = runs_path + ".tmp"
        json.dump(blob, open(tmp, "w"), ensure_ascii=False, indent=2)
        os.replace(tmp, runs_path)
    return graded, skipped, failed, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    graded, skipped, failed, log = annotate_runs(a.private_dir, a.model, dry_run=a.dry_run)
    print("=== grade_teachback: teach-back quality ===")
    for line in log:
        print(line)
    print(f"\ngraded {graded} · already-graded {skipped} · failed {failed}")


if __name__ == "__main__":
    main()
