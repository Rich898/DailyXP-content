#!/usr/bin/env python3
"""
validate.py — hard gate before any set is published.

Checks (ERROR = blocks publish, WARN = surfaced but allowed):
  ERROR  malformed schema (missing student/date/day/tag/questions)
  ERROR  question missing id/phase/subject/prompt
  ERROR  mc missing options(>=2) or answer-not-in-options; numeric/text/cloze missing a string answer; any Q missing why
  ERROR  unknown question type (expected mc|numeric|text|cloze)
  ERROR  answer not exactly one of options
  ERROR  speed/steady missing boolean `fresh` (true=newly-introduced, false=established); throwback must be fresh:false
  ERROR  duplicate id within the set
  ERROR  prompt repeats one already seen by this student (history/ archive)
  WARN   run shape != a known template (7/4/1 standard, 10/2/1 blitz, boss chain)

Placeholder sets (status=="placeholder", empty questions) are valid by design.

Usage:
  python3 tools/validate.py <set.json>
  from tools.validate import validate_set  ->  (errors:list, warns:list)
"""
import json
import re
import sys
import glob
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _norm(p: str) -> str:
    """Normalise a prompt for repeat detection: lowercase, collapse whitespace,
    strip trailing punctuation. Catches re-asks that differ only cosmetically."""
    p = (p or "").lower().strip()
    p = re.sub(r"\s+", " ", p)
    p = re.sub(r"[?.!:;,\s]+$", "", p)
    return p


def seen_prompts(student: str, history_dir: str = None) -> set:
    """All prompts this student has already been served, from the archive."""
    history_dir = history_dir or os.path.join(REPO, "history")
    out = set()
    for f in glob.glob(os.path.join(history_dir, student, "*.json")):
        try:
            for q in json.load(open(f)).get("questions", []):
                n = _norm(q.get("prompt", ""))
                if n:
                    out.add(n)
        except Exception:
            pass
    return out


KNOWN_SHAPES = {
    (7, 4, 1): "standard",
    (10, 2, 1): "blitz",
}


def _check_ss_answer(q, qid, errors, warns):
    """Validate the answer shape of one speed/steady question (multiple-choice, or swipe)."""
    if q.get("type") == "swipe":
        left, right, ans = q.get("left"), q.get("right"), q.get("answer")
        if not left or not right:
            errors.append(f"[{qid}] swipe needs both 'left' and 'right' bucket labels")
        if ans is None or ans not in (left, right):
            errors.append(f"[{qid}] swipe answer {ans!r} must be exactly the 'left' ({left!r}) or 'right' ({right!r}) label")
        if not q.get("why"):
            errors.append(f"[{qid}] missing 'why' (every Q must re-teach)")
        if not isinstance(q.get("fresh"), bool):
            errors.append(f"[{qid}] swipe must carry a boolean 'fresh'")
        return
    if q.get("type") == "text":
        acc = q.get("accept")
        if not isinstance(acc, list) or len(acc) < 1 or not all(isinstance(x, str) and x.strip() for x in acc):
            errors.append(f"[{qid}] text needs an 'accept' list of >=1 non-empty strings (accept[0]=canonical)")
        if not q.get("why"):
            errors.append(f"[{qid}] missing 'why' (every Q must re-teach)")
        if not isinstance(q.get("fresh"), bool):
            errors.append(f"[{qid}] text must carry a boolean 'fresh'")
        return
    if q.get("type") == "order":
        seq = q.get("sequence")
        if not isinstance(seq, list) or len(seq) < 2:
            errors.append(f"[{qid}] order needs a 'sequence' list of >=2 items")
        elif len({str(x) for x in seq}) != len(seq):
            errors.append(f"[{qid}] order sequence has duplicate items")
        if not q.get("why"):
            errors.append(f"[{qid}] missing 'why' (every Q must re-teach)")
        if not isinstance(q.get("fresh"), bool):
            errors.append(f"[{qid}] order must carry a boolean 'fresh'")
        return
    if q.get("type") == "numeric":
        ans = q.get("answer")
        if isinstance(ans, bool) or not isinstance(ans, (int, float)):
            errors.append(f"[{qid}] numeric answer must be a number, got {ans!r}")
        if not isinstance(q.get("calc"), bool):
            errors.append(f"[{qid}] numeric must carry a boolean 'calc' (method vs mental)")
        if not q.get("why"):
            errors.append(f"[{qid}] missing 'why' (every Q must re-teach)")
        if not isinstance(q.get("fresh"), bool):
            errors.append(f"[{qid}] numeric must carry a boolean 'fresh'")
        return
    ans = q.get("answer")
    opts = q.get("options")
    if not isinstance(opts, list) or len(opts) < 2:
        errors.append(f"[{qid}] question needs an options list (>=2)")
        opts = opts if isinstance(opts, list) else []
    if ans is None:
        errors.append(f"[{qid}] missing 'answer'")
    elif opts and ans not in opts:
        errors.append(f"[{qid}] answer {ans!r} is not one of options {opts}")
    if not q.get("why"):
        errors.append(f"[{qid}] missing 'why' (every Q must re-teach)")
    fr = q.get("fresh")
    if not isinstance(fr, bool):
        errors.append(f"[{qid}] speed/steady must carry a boolean 'fresh' "
                      "(true = newly introduced this week → benign skip; "
                      "false = established → a skip is a soft miss)")
    elif q.get("throwback") and fr is not False:
        errors.append(f"[{qid}] throwback must be fresh:false — a revisit is never newly introduced")


def validate_set(s: dict, history_dir: str = None) -> tuple:
    errors, warns = [], []

    student = s.get("student")
    import roster
    if student not in roster.students():
        errors.append(f"student must be one of {roster.students()}, got {student!r}")
    if "questions" not in s or not isinstance(s["questions"], list):
        errors.append("missing/invalid 'questions' list")
        return errors, warns

    # placeholder = valid empty set (no tag/day required — the shell shows 'no quiz')
    if s.get("status") == "placeholder":
        if s["questions"]:
            warns.append("placeholder set has questions — shell will still show 'no quiz'")
        return errors, warns

    # real sets require the scheduling metadata
    for k in ("date", "day", "tag"):
        if k not in s:
            errors.append(f"missing top-level '{k}'")

    qs = s["questions"]
    ids = [q.get("id") for q in qs]
    dupe_ids = {i for i in ids if ids.count(i) > 1}
    if dupe_ids:
        errors.append(f"duplicate question id(s): {sorted(dupe_ids)}")

    counts = {"speed": 0, "steady": 0, "teach": 0}
    seen = seen_prompts(student, history_dir) if student else set()

    for q in qs:
        qid = q.get("id", "?")
        phase = q.get("phase")
        for k in ("id", "phase", "subject", "prompt"):
            if not q.get(k):
                errors.append(f"[{qid}] missing '{k}'")
        if phase not in ("speed", "steady", "teach"):
            errors.append(f"[{qid}] phase must be speed|steady|teach, got {phase!r}")
            continue
        counts[phase] += 1

        # no-repeat (all phases with a prompt)
        n = _norm(q.get("prompt", ""))
        if n and n in seen:
            errors.append(f"[{qid}] prompt REPEATS one this student has seen: {q.get('prompt','')[:60]!r}")

        if phase in ("speed", "steady"):
            _check_ss_answer(q, qid, errors, warns)

    shape = (counts["speed"], counts["steady"], counts["teach"])

    if counts["teach"] != 1:
        errors.append(f"exactly ONE teach question required (got {counts['teach']}) — "
                      "shell v3.0 unconditionally enters the teach-back screen after steady "
                      "and crashes without one (learned the hard way, 9 Aug: no end screen, "
                      "no submit)")
    if shape not in KNOWN_SHAPES:
        # boss chains and encores legitimately vary — warn, don't block
        warns.append(f"run shape {shape} is non-standard (known: 7/4/1 standard, 10/2/1 blitz) — intended?")

    return errors, warns


def main():
    if len(sys.argv) < 2:
        print("usage: validate.py <set.json>")
        sys.exit(2)
    s = json.load(open(sys.argv[1]))
    errors, warns = validate_set(s)
    tag = s.get("tag", "?")
    print(f"Validating {sys.argv[1]}  (tag {tag}, {len(s.get('questions',[]))} Qs)")
    for w in warns:
        print(f"  WARN  {w}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        print(f"FAIL — {len(errors)} error(s), will NOT publish.")
        sys.exit(1)
    print(f"PASS{' with ' + str(len(warns)) + ' warning(s)' if warns else ''} — safe to publish.")


if __name__ == "__main__":
    main()
