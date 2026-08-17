"""
throwback.py — the continuous throwback selector (SEASONS.md LAW 3).

Aged-but-mastered topics resurface every run to check retention held. This is the
spaced-repetition engine made visible, and the deliberate INVERSE of the normal
eligibility pool: the normal pool requires a topic to be live in class; a throwback
requires the opposite — a topic that has LEFT active rotation, was mastered, and
has aged past a spacing threshold.

Pure functions, no I/O, no network. Fully unit-tested in test_throwback.py.

Selection rule (deterministic):
  eligible  = state in THROWBACK_STATES  (solid / developing — genuinely learned)
              AND last_tested is set AND age >= THROWBACK_MIN_AGE_DAYS
              AND not currently a repair thread (repairs belong to the weak pool)
  score     = age_days  (older = more due)               [primary]
              + mastery_bonus (solid > developing)         [tie-break toward solid]
              + times_seen bonus (well-established > barely)[tie-break]
  pick      = highest score; ties broken by (older, then subject alpha) for
              determinism.
"""

import datetime as dt

# A topic must be at least this old (days since last_tested) to be a throwback —
# below this it's just normal recent rotation, not a "from a while back" check.
THROWBACK_MIN_AGE_DAYS = 10

# Only genuinely-learned states are eligible. A shaky/untested topic isn't a
# retention check — it's just weak, and the normal pool already handles it.
THROWBACK_STATES = {"solid", "developing"}

# Mastery tie-break: a solid topic held is a stronger signal than a developing one.
MASTERY_BONUS = {"solid": 6, "developing": 2}


def _age_days(last_tested, ref):
    if not last_tested:
        return None
    try:
        return max(0, (ref - dt.date.fromisoformat(last_tested)).days)
    except Exception:
        return None


def is_eligible(tp, ref):
    """True iff this state-topic qualifies as a throwback candidate on ref date."""
    if tp.get("repair"):
        return False
    if tp.get("state") not in THROWBACK_STATES:
        return False
    age = _age_days(tp.get("last_tested"), ref)
    return age is not None and age >= THROWBACK_MIN_AGE_DAYS


def score(tp, ref):
    """Throwback priority: older + more-mastered + better-established = more due."""
    age = _age_days(tp.get("last_tested"), ref) or 0
    seen = tp.get("times_seen", 0) or 0
    return age + MASTERY_BONUS.get(tp.get("state"), 0) + min(seen, 6)


def candidates(state_student, ref, exclude_topics=None):
    """
    All eligible throwback topics for a student, best first. `exclude_topics` is a
    set of topic names already slotted in this run (never double-book a topic).
    """
    exclude = exclude_topics or set()
    elig = [tp for tp in state_student.get("topics", [])
            if is_eligible(tp, ref) and tp.get("topic") not in exclude]
    # deterministic: score desc, then age desc, then subject/topic alpha
    elig.sort(key=lambda tp: (
        -score(tp, ref),
        -(_age_days(tp.get("last_tested"), ref) or 0),
        tp.get("subject", ""), tp.get("topic", "")))
    return elig


def pick(state_student, ref, exclude_topics=None):
    """The single best throwback topic, or None if the ledger has no aged-mastered
    topic yet (expected early in a student's history — thin, not an error)."""
    c = candidates(state_student, ref, exclude_topics)
    return c[0] if c else None


def composer_note(topic, subject, age_days):
    """One line telling the language layer this is a retention check, framed light."""
    wk = max(1, round(age_days / 7))
    span = "about a week ago" if wk == 1 else f"about {wk} weeks ago"
    return (f"THROWBACK (SEASONS.md LAW 3 — retention check, NOT new material): this "
            f"slot revisits '{topic}' ({subject}), last practised {span} and marked "
            f"mastered. Write a fair, representative question on it — the SAME "
            f"difficulty it was mastered at, no curveballs. The point is to confirm "
            f"it held. Frame neutrally as a topic 'from a while back'; never imply "
            f"failure if missed. Answer-length law still applies.")
