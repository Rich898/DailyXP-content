"""
answer_length.py — deterministic answer-length integrity gate (SEASONS.md LAW 1).

Origin: the boys' beta feedback "it feels like AI because often the answer is the
longer text." Measured 17 Aug: correct MC answer was the longest option 70% of the
time (random = 25%). A child could score ~70% by tapping the longest option WITHOUT
READING — that partly invalidates the recall signal the ledger is built on.

The language layer cannot self-police this (an LLM naturally writes precise = long
correct answers and terse distractors), so it is enforced here in code.

Two checks, matching the law:

  * PER-SLOT gate:  a slot where the correct answer is the SOLE longest option by a
    meaningful margin is a violation → recompose that slot.
  * PER-RUN distribution gate:  even with no single slot failing, if the correct
    answer piles on length-rank 1 across the run (which would just teach "tap the
    longest"), the run fails the distribution target. The goal is a FLAT spread of
    the correct answer's length-rank across positions 1..N.

Pure functions, no I/O, no network. Fully unit-tested in test_answer_length.py.
"""

# ---- tunables (kept conservative; see law) ----------------------------------

# A correct answer counts as "conspicuously longest" only if it is the sole
# longest AND longer than the next option by more than this fraction of the next
# option's length. Prevents flagging a 1-char difference; catches real tells.
SOLE_LONGEST_MARGIN = 0.15  # 15% longer than the runner-up

# True/False (and any 2-option) slots are exempt from the length rule entirely —
# "False" vs "True" length is meaningless and correctness is content, not length.
MIN_OPTIONS_FOR_RULE = 3

# Per-run: at most this share of MC slots may have the correct answer as the sole
# longest option. 25% is the random baseline for 4-option questions; we allow a
# little slack for small runs. Above this, the run is a distribution violation.
MAX_RUN_LONGEST_SHARE = 0.34


def _opt_texts(slot):
    """Return the list of option strings for a slot, or None if not an MC slot."""
    opts = slot.get("options")
    if not isinstance(opts, list) or len(opts) < 2:
        return None
    return [o if isinstance(o, str) else str(o.get("text", "")) for o in opts]


def _correct_text(slot):
    """The correct option's text. Schema: answer holds the option TEXT verbatim."""
    ans = slot.get("answer")
    if ans is None:
        return None
    return ans if isinstance(ans, str) else str(ans.get("text", ""))


def slot_is_mc(slot):
    """A slot the length rule applies to: >=3 options and a resolvable answer."""
    if slot.get("phase") == "teach":
        return False
    texts = _opt_texts(slot)
    if texts is None or len(texts) < MIN_OPTIONS_FOR_RULE:
        return False
    ct = _correct_text(slot)
    return ct is not None and ct in texts


def sole_longest_violation(slot):
    """
    True iff the correct answer is the SOLE longest option and beats the runner-up
    by more than SOLE_LONGEST_MARGIN. This is the per-slot blocking condition.
    """
    if not slot_is_mc(slot):
        return False
    texts = _opt_texts(slot)
    ct = _correct_text(slot)
    lens = [len(t) for t in texts]
    cl = len(ct)
    mx = max(lens)
    if cl != mx:
        return False               # correct isn't the longest at all — fine
    if lens.count(mx) > 1:
        return False               # tie for longest — not a clean tell
    others = [l for t, l in zip(texts, lens) if not (t == ct and l == cl)]
    # remove exactly one instance of the correct length
    # (guard against duplicate-length distractors)
    runner_up = max(l for l in lens if l != cl) if any(l != cl for l in lens) else cl
    if runner_up == 0:
        return False
    return (cl - runner_up) / runner_up > SOLE_LONGEST_MARGIN


def correct_length_rank(slot):
    """
    1-based rank of the correct answer by length, 1 = longest. Ties share the best
    (lowest) rank. None for non-MC slots.
    """
    if not slot_is_mc(slot):
        return None
    texts = _opt_texts(slot)
    ct = _correct_text(slot)
    lens = sorted((len(t) for t in texts), reverse=True)
    return lens.index(len(ct)) + 1


def audit(slots):
    """
    Audit a whole run (list of slots). Returns a dict:
      {
        "mc_total": int,
        "slot_violations": [slotId, ...],        # per-slot blocking failures
        "longest_count": int,                    # correct == sole longest
        "longest_share": float,                  # longest_count / mc_total
        "rank_hist": {1: n, 2: n, ...},          # distribution of length-rank
        "run_distribution_violation": bool,      # share above MAX_RUN_LONGEST_SHARE
        "ok": bool,                              # no slot AND no run violation
      }
    Deterministic; safe on empty input.
    """
    mc = [s for s in slots if slot_is_mc(s)]
    slot_viol = [s.get("id", "?") for s in mc if sole_longest_violation(s)]
    longest_count = 0
    rank_hist = {}
    for s in mc:
        r = correct_length_rank(s)
        rank_hist[r] = rank_hist.get(r, 0) + 1
        texts = _opt_texts(s)
        ct = _correct_text(s)
        lens = [len(t) for t in texts]
        if len(ct) == max(lens) and lens.count(max(lens)) == 1:
            longest_count += 1
    total = len(mc)
    share = (longest_count / total) if total else 0.0
    run_viol = total >= 3 and share > MAX_RUN_LONGEST_SHARE
    return {
        "mc_total": total,
        "slot_violations": slot_viol,
        "longest_count": longest_count,
        "longest_share": round(share, 3),
        "rank_hist": dict(sorted(rank_hist.items())),
        "run_distribution_violation": run_viol,
        "ok": (not slot_viol) and (not run_viol),
    }


def guidance_note(slot):
    """One-line recompose instruction for a slot that failed the per-slot gate."""
    return ("ANSWER-LENGTH TELL: the correct option is the longest by a clear "
            "margin — a student could pick it without reading. Rewrite so the "
            "correct answer is NOT the longest: lengthen the distractors with "
            "specific, plausible detail (or tighten the correct answer) until all "
            "four options sit in a similar length band.")
