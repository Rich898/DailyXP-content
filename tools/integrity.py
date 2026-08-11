#!/usr/bin/env python3
"""
integrity.py — teach-back AUTHENTICITY signals. Did the student actually write this?

WHY THIS EXISTS (and why it's load-bearing):
The teach-back is the only instrument that reaches "can connect it" on the depth
ladder (UNDERSTANDING.md §3). It exists to catch the fluency illusion — the kid
who picks the right multiple choice but cannot explain the idea. If an answer can
be pasted from a model, that instrument doesn't merely get noisy, it INVERTS: the
ledger records its highest confidence in understanding exactly where the student
did the least thinking, and the parent report then reports that as depth.

So integrity is checked BEFORE depth is credited, not after.

DESIGN LAWS:
  * DETERMINISTIC. Code decides; no model judges a child's honesty. Signals are
    arithmetic on data the shell already captures (chars, secs, the text).
  * FLAG, NEVER ACCUSE. The output is a review flag with its reasons attached,
    for the adult running the system. It NEVER enters an automated parent SMS or
    a kid-facing surface. An automated "your child cheated" that is wrong is
    unrecoverable — for the family and for the product. Escalation is a human's
    job, always.
  * UNDER-CLAIM BOTH WAYS. A flagged answer does not evidence depth (we cannot
    credit understanding we cannot attribute), and equally it is not proof of
    anything — 'review' means look, not conclude.
  * PER-KID BASELINE BEATS ABSOLUTE THRESHOLDS. A student's own typing history
    is the strongest signal; a fast typist is not a cheat. Absolute thresholds
    are only the floor for when no baseline exists yet.

Verdicts: "ok" | "review" | "quarantine"
  ok         — consistent with this student writing it.
  review     — one or more signals; worth a human look. Depth still credited.
  quarantine — implausible as this student's own writing. Depth NOT credited and
               the row is excluded from reporting until a human clears it.
"""

# --- absolute thresholds (used when a student has no personal baseline yet) --- #
RATE_IMPLAUSIBLE = 4.5     # chars/sec — sustained, above a fast adult touch-typist
RATE_FAST = 3.2            # chars/sec — fast for a secondary student
MIN_CHARS_FOR_RATE = 60    # short answers give unreliable rates
CLEAN_TEXT_CHARS = 130     # long + flawless is itself a signal in this age group

# US spellings that an Australian secondary student is unlikely to produce but a
# US-trained model produces by default. Checked as whole words only.
US_SPELLINGS = (
    "symbolized", "symbolizes", "civilized", "organized", "realized", "recognized",
    "emphasized", "analyzed", "criticized", "summarized", "characterized",
    "categorized", "minimized", "maximized", "utilized", "color", "colors",
    "behavior", "behaviors", "favorite", "honor", "labor", "neighbor",
    "center", "centers", "theater", "meter", "liter", "defense", "offense",
    "traveled", "modeling", "canceled",
)

# Informal markers — evidence FOR authenticity in this cohort.
INFORMAL_MARKERS = ("dont", "doesnt", "its ", "thats", "cant", "wont", "im ",
                    "ive ", "gonna", "kinda", "yeah", "idk", "haha", "lol",
                    "  ", " i ", "alot", "becuase", "recieve", "seperate")


def typing_rate(chars, secs):
    """chars/sec, or None when it can't be computed reliably."""
    try:
        c, s = int(chars or 0), float(secs or 0)
    except (TypeError, ValueError):
        return None
    if c < MIN_CHARS_FOR_RATE or s <= 0:
        return None
    return c / s


def typo_signals(text):
    """Rough count of human-error / informality markers. Zero on a long answer
    is itself notable in this age group."""
    if not text:
        return 0
    t = " " + text.lower() + " "
    n = sum(1 for m in INFORMAL_MARKERS if m in t)
    # doubled spaces, missing space after punctuation, lowercase 'i'
    if " i " in t:
        n += 1
    for p in (".", ","):
        if p in text:
            idx = text.find(p)
            if idx != -1 and idx + 1 < len(text) and text[idx + 1].isalpha():
                n += 1        # "side.So" — human run-on
                break
    return n


def us_spellings(text):
    """Whole-word US spellings present in the text."""
    if not text:
        return []
    import re
    words = set(re.findall(r"[a-z]+", text.lower()))
    return sorted(w for w in US_SPELLINGS if w.strip() in words)


def third_person_about_student(text):
    """Register check — an answer ABOUT a student rather than BY one. This is
    the signature of pasting a model's marking/feedback output."""
    if not text:
        return False
    t = text.lower()
    return any(p in t for p in ("the student ", "the student's", "the pupil ",
                                "the learner ", "the answer should", "you should have",
                                "the correct answer is", "this response "))


def baseline_for(history):
    """Median typing rate from a student's own PRIOR clean teach-backs.
    history: list of (chars, secs) tuples. None when there isn't enough."""
    rates = [r for r in (typing_rate(c, s) for c, s in history) if r]
    if len(rates) < 2:
        return None
    rates.sort()
    mid = len(rates) // 2
    return rates[mid] if len(rates) % 2 else (rates[mid - 1] + rates[mid]) / 2


def check(text, chars=None, secs=None, history=None):
    """Deterministic integrity verdict for one teach-back.

    Returns {"verdict", "reasons": [...], "rate": float|None, "baseline": float|None}.
    Signals are additive; the verdict is a threshold on their weight so no single
    soft signal can condemn an answer on its own.
    """
    chars = chars if chars is not None else len(text or "")
    rate = typing_rate(chars, secs)
    base = baseline_for(history or [])
    reasons, weight = [], 0

    # --- register: the strongest single signal, and unambiguous ---------------
    if third_person_about_student(text):
        reasons.append("written about a student, not by one")
        weight += 3

    # --- speed, relative to the student's own history first -------------------
    if rate is not None:
        if base and rate >= base * 2.2:
            reasons.append(f"typed {rate:.1f} ch/s vs own usual {base:.1f}")
            weight += 3
        elif rate >= RATE_IMPLAUSIBLE:
            reasons.append(f"typed {rate:.1f} ch/s — implausible sustained rate")
            weight += 3
        elif rate >= RATE_FAST:
            reasons.append(f"typed {rate:.1f} ch/s — fast for this age")
            weight += 1

    # --- polish: flawless long prose is unusual in this cohort ---------------
    if chars >= CLEAN_TEXT_CHARS and typo_signals(text) == 0:
        reasons.append("long answer with no informal or error markers")
        weight += 1

    # --- register: US spelling in an Australian school context ---------------
    us = us_spellings(text)
    if us:
        reasons.append("US spelling: " + ", ".join(us[:3]))
        weight += 1

    verdict = "ok"
    if weight >= 4:
        verdict = "quarantine"
    elif weight >= 2:
        verdict = "review"
    return {"verdict": verdict, "reasons": reasons, "rate": rate, "baseline": base}


def credits_depth(integrity):
    """Whether a teach-back may evidence a depth rung. Quarantined text cannot
    — we do not credit understanding we cannot attribute to the student."""
    return (integrity or {}).get("verdict") != "quarantine"
