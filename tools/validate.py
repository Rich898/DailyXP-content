#!/usr/bin/env python3
"""
validate.py — hard gate before any set is published.

Checks (ERROR = blocks publish, WARN = surfaced but allowed):
  ERROR  malformed schema (missing student/date/day/tag/questions)
  ERROR  question missing id/phase/subject/prompt
  ERROR  mc missing options(>=2) or answer-not-in-options; numeric/text/cloze missing a string answer; any Q missing why
  ERROR  unknown question type (expected mc|numeric|text|cloze)
  ERROR  answer not exactly one of options
  ERROR  scrub (mode=='scrub', ratified 25 Aug 2026): only on multiple-choice; speed phase only;
         EXACTLY 4 unique options; no negative stems (not/except/false); no all/none-of-the-above;
         no answer-length tell (SEASONS LAW 1 sole-longest gate, upgraded to ERROR on this surface)
  ERROR  speed/steady missing boolean `fresh` (true=newly-introduced, false=established); throwback must be fresh:false
  ERROR  duplicate id within the set
  ERROR  prompt repeats one already seen by this student (history/ archive)
  WARN   run shape != a known template (12/6/1 standard, 2/7/1 boss)

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
sys.path.insert(0, os.path.join(REPO, "tools"))
from answer_length import sole_longest_violation  # SEASONS LAW 1 — the ratified length-tell gate


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
    (12, 6, 1): "standard",
    (2, 7, 1): "boss",
}


NEG_STEM = re.compile(r"(?i)\b(not|except|false)\b")
ABOVE_OPT = re.compile(r"(?i)\b(all|none)\s+of\s+(the\s+above|these)\b")


def _check_scrub(q, qid, errors):
    """Scrub It delivery mode (ratified 25 Aug 2026): the child physically erases the
    three wrong answers, so distractor quality is load-bearing — HARD gates, not warns.
    The ledger never learns the mode; these checks protect the GESTURE, not the evidence."""
    if q.get("phase") != "speed":
        errors.append(f"[{qid}] mode:'scrub' is a speed-round delivery mode — the shell only mounts it in speed (got phase {q.get('phase')!r})")
    opts = q.get("options") if isinstance(q.get("options"), list) else []
    if len(opts) != 4:
        errors.append(f"[{qid}] scrub needs EXACTLY 4 options (the widget deals 4 tiles; 3 erases = win), got {len(opts)}")
    normed = [str(o).strip().lower() for o in opts]
    if len(set(normed)) != len(normed):
        errors.append(f"[{qid}] scrub options must be unique — a duplicate tile makes the erase ambiguous")
    if NEG_STEM.search(q.get("prompt", "") or ""):
        errors.append(f"[{qid}] scrub forbids negative stems (not/except/false) — the child ERASES wrong answers; a negative stem inverts the gesture")
    for o in opts:
        if ABOVE_OPT.search(str(o)):
            errors.append(f"[{qid}] scrub forbids all/none-of-the-above options ({o!r}) — tiles must be erasable on their own merits")
            break
    if sole_longest_violation(q):
        errors.append(f"[{qid}] scrub answer-length tell: the correct option is the sole longest by a clear margin (SEASONS LAW 1) — a child could win by erasing the three short tiles without reading")


def _check_ss_answer(q, qid, errors, warns):
    """Validate the answer shape of one speed/steady question (multiple-choice, or swipe)."""
    if q.get("mode") == "scrub" and q.get("type") in ("swipe", "numeric", "order", "text", "cloze"):
        errors.append(f"[{qid}] mode:'scrub' is only valid on multiple-choice (got type {q.get('type')!r})")
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
        # optional 'frac': the canonical fraction DISPLAY form (e.g. "2/5"), shown on the
        # reveal. Deterministically checked for equivalence — review can't see non-MC
        # answers (QUIZ-GENERATION §C7), so a wrong fraction must be caught here.
        frac = q.get("frac")
        if frac is not None:
            m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*/\s*(-?\d+(?:\.\d+)?)\s*$", str(frac))
            if not m:
                errors.append(f"[{qid}] numeric 'frac' must look like 'a/b', got {frac!r}")
            elif float(m.group(2)) == 0:
                errors.append(f"[{qid}] numeric 'frac' has a zero denominator: {frac!r}")
            elif isinstance(ans, (int, float)) and not isinstance(ans, bool) \
                    and abs(float(m.group(1)) / float(m.group(2)) - ans) > 0.01:
                errors.append(f"[{qid}] numeric 'frac' {frac!r} != answer {ans!r} — the fraction shown on the reveal must equal the keyed value")
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
    if q.get("mode") == "scrub":
        _check_scrub(q, qid, errors)
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

        # no-repeat (recall prompts only). Teach-back slots are EXEMPT: they are
        # reasoning prompts ("explain X in your own words") — re-asking one is good
        # spaced practice, not a recall repeat, and the deepest-history seats (t1)
        # otherwise compose-fail once every fresh teach-back is exhausted (HARDENING
        # item 5 follow-up, 27 Aug 2026). The composer is still fed already_seen and
        # told to prefer unseen prompts, so a repeat only surfaces when fresh runs out.
        n = _norm(q.get("prompt", ""))
        if n and n in seen and phase != "teach":
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
        warns.append(f"run shape {shape} is non-standard (known: 12/6/1 standard, 2/7/1 boss) — intended?")

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
