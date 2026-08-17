"""
formats.py — the daily question-format bank (SEASONS.md LAW 2).

"Same every day" is structural when every slot is plain 4-option recall MC. This
bank gives the planner a set of MC-family formats to rotate across a run, so Mon/
Tue stop being 11 identical taps. Novelty from ROTATION across a bank, not constant
invention (the SEASONS content-economics principle).

EVERY format renders as four tappable options — so ZERO shell/schema cost, and the
ledger/grading are untouched (they read ok/picked only). Formats needing typed
input, dragging, or multi-select are NOT here; they are Shell v3.1 (LAW 5).

The planner calls assign_formats() to label each speed/steady slot with a format;
the composer reads formats.render_note(fmt) to get the per-format instruction. Pure
functions, deterministic (seeded by student+date+tag so a run is stable on re-plan
but varies day to day). Fully unit-tested in test_formats.py.
"""

import hashlib

# ---- the bank ---------------------------------------------------------------
# Each entry: which phases it suits, which subjects it fits best, and the
# composer instruction. "recall" is the plain baseline (today's default).

RECALL = "recall"
SPOT_LIE = "spot_the_lie"
SPOT_ERROR = "spot_the_error"
ODD_ONE_OUT = "odd_one_out"
ORDERING = "ordering"
MATCHING = "matching"
# reversed already exists as a mutator; represented here so it can join rotation
REVERSED = "reversed"

# subjects where a format lands especially well (soft preference, not a hard gate)
_FIT = {
    RECALL:      {"any"},
    SPOT_LIE:    {"History", "Science", "Geography", "English", "Commerce"},
    SPOT_ERROR:  {"Maths", "Science"},                 # worked-solution errors
    ODD_ONE_OUT: {"Science", "History", "Geography", "English", "Commerce"},
    ORDERING:    {"History", "Science", "Maths"},       # chronology / method / steps
    MATCHING:    {"Geography", "Science", "Commerce", "English"},
    REVERSED:    {"History", "Science", "Geography", "English", "Commerce"},  # fact-based
}

# formats that must NOT be used on calculation topics (numeric answers collide or
# the format doesn't apply). Mirrors the reversed-mutator numeric rule.
_CALC_UNSAFE = {REVERSED, SPOT_LIE, ODD_ONE_OUT, MATCHING}

# calculation topic detection (same spirit as the reversed exemption)
_CALC_HINTS = ("equation", "angle", "area", "volume", "percent", "perimeter",
               "mean", "median", "mode", "ratio", "fraction", "calculat",
               "surds", "index", "indices", "algebra", "solve", "simultaneous")


def is_calc_topic(subject, topic):
    t = (topic or "").lower()
    if subject == "Maths":
        return True                       # treat all Maths as calc-leaning by default
    return any(h in t for h in _CALC_HINTS)


def _rng(seed_parts):
    """Deterministic 0..1 float from string parts."""
    h = hashlib.sha256("|".join(map(str, seed_parts)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def eligible_formats(slot, phase):
    """Formats allowed for this slot, given subject/topic constraints."""
    subj = slot.get("subject", "")
    topic = slot.get("topic", "")
    calc = is_calc_topic(subj, topic)
    # a throwback slot stays PLAIN recall — it is a like-for-like retention check;
    # changing the format would change the difficulty and defeat the comparison.
    if slot.get("throwback"):
        return [RECALL]
    # teach-back has no options — never formatted here
    if phase == "teach":
        return [RECALL]
    out = []
    for fmt, fits in _FIT.items():
        if calc and fmt in _CALC_UNSAFE:
            continue
        if fmt == SPOT_ERROR and not calc and subj not in _FIT[SPOT_ERROR]:
            continue
        if "any" in fits or subj in fits:
            out.append(fmt)
    # spot-the-error is calc/science only; ensure it's offered for calc topics
    if calc and SPOT_ERROR not in out:
        out.append(SPOT_ERROR)
    # MATCHING and ORDERING are cognitively heavy — multi-item mappings/sequences with long options.
    # They belong in the UNTIMED steady round, never the timed speed round (a kid has seconds there).
    if phase == "speed":
        out = [f for f in out if f not in (MATCHING, ORDERING)]
    # RECALL is always a valid fallback
    if RECALL not in out:
        out.append(RECALL)
    return out


def assign_formats(slots, student, date_str, tag, max_same=3, exclude=None):
    """
    Assign a format to each speed/steady slot, deterministically seeded, aiming for
    VARIETY: no single non-recall format used more than `max_same` times, and recall
    kept to a minority so the run doesn't collapse back to plain MC. Mutates and
    returns the slots (each gets slot['format']).

    `exclude` is a set of formats to keep OUT of this run (e.g. the planner passes
    {ORDERING} when a tap-to-order slot exists, so a run never carries both an MC
    ordering format AND the drag-order type — SEASONS/v3.1 trap-1).

    Reversed is only auto-assigned if the run's directive already declares reversed
    (handled by the caller); here we treat REVERSED as available only when present in
    a slot's eligible set AND explicitly enabled — see planner wiring. To keep this
    module self-contained and safe, assign_formats never picks REVERSED unless the
    slot already carries slot['allow_reversed'] = True.
    """
    exclude = exclude or set()
    used = {}
    for i, s in enumerate(slots):
        phase = s.get("phase")
        if phase not in ("speed", "steady"):
            continue
        if s.get("type") and s.get("type") != "mc":
            s["format"] = None                       # typed slot (numeric/text/cloze) — no MC format
            continue
        elig = [f for f in eligible_formats(s, phase)
                if (f != REVERSED or s.get("allow_reversed")) and f not in exclude]
        # rank eligible formats by (least-used-so-far, deterministic jitter)
        def rank(f):
            r = _rng([student, date_str, tag, s.get("slot", i), f])
            penalty = used.get(f, 0)
            # push recall to the back so variety wins, but keep it available
            recall_bias = 0.5 if f == RECALL else 0.0
            return (penalty + recall_bias, r)
        elig.sort(key=rank)
        # respect the per-format cap where possible
        choice = None
        for f in elig:
            if f == RECALL or used.get(f, 0) < max_same:
                choice = f
                break
        choice = choice or elig[0]
        s["format"] = choice
        used[choice] = used.get(choice, 0) + 1
    return slots


# ---- composer instructions per format --------------------------------------

_NOTES = {
    RECALL: ("FORMAT recall: a normal question with four options, exactly one correct. "
             "Straight recall or discrimination."),
    SPOT_LIE: ("FORMAT spot-the-lie: write FOUR statements about the topic — THREE true, "
               "ONE false. The prompt ends 'Which statement is FALSE?'. answer = the false "
               "statement (verbatim in options). The false one must be a real misconception, "
               "not an obvious howler, and must NOT be the longest option."),
    SPOT_ERROR: ("FORMAT spot-the-error: show a short WORKED solution/argument broken into "
                 "four labelled steps as the four options (e.g. 'Step 1: ...', 'Step 2: ...'). "
                 "Exactly ONE step contains the mistake. The prompt asks 'Which step is WRONG?'. "
                 "answer = the flawed step. The error must be the real slip a student makes on "
                 "this topic. Keep the four steps similar in length."),
    ODD_ONE_OUT: ("FORMAT odd-one-out: four items, three share a property and ONE does not. "
                  "The prompt states the category and asks 'Which does NOT belong?'. answer = "
                  "the outlier. The 'why' names the shared property. Items similar in length."),
    ORDERING: ("FORMAT ordering-as-MC: give a set of items to sequence (chronology, method "
               "steps, size order). The four options are four CANDIDATE orderings written out; "
               "exactly one is correct. answer = the correct sequence (verbatim). Distractor "
               "orderings must be plausible near-misses (one swap), similar in length."),
    MATCHING: ("FORMAT matching-as-MC: the prompt gives items to pair (term↔definition, "
               "cause↔effect, place↔feature). The four options are four candidate PAIRINGS; "
               "exactly one has every pair correct. answer = the fully-correct pairing. "
               "Distractors swap one pair. Keep options similar in length."),
    REVERSED: ("FORMAT reversed: the prompt STATES a fact/answer; the four options are candidate "
               "QUESTIONS; exactly one is genuinely answered by the stated fact. Fact-based topics "
               "only. See the reversed doctrine block for the full rule."),
}


def render_note(fmt):
    return _NOTES.get(fmt, _NOTES[RECALL])


def run_format_summary(slots):
    """Human-readable tally for plan logs, e.g. 'recall×4 spot_the_lie×3 ordering×2'."""
    counts = {}
    for s in slots:
        f = s.get("format")
        if f:
            counts[f] = counts.get(f, 0) + 1
    return " ".join(f"{k}×{v}" for k, v in sorted(counts.items()))
