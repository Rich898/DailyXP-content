"""Tests for throwback.py — the LAW 3 continuous throwback selector."""
import datetime as dt
import throwback as tb

REF = dt.date(2026, 8, 20)   # a Thursday, well after the 3 Aug go-live


def topic(subject, name, state, last_tested, times_seen=5, repair=False):
    return {"subject": subject, "topic": name, "state": state,
            "last_tested": last_tested, "times_seen": times_seen, "repair": repair}


def student(topics):
    return {"ref": "y8", "topics": topics}


# ---------------------------------------------------------------- eligibility --

def test_aged_solid_is_eligible():
    t = topic("Maths", "Area", "solid", "2026-08-05")   # 15 days old
    assert tb.is_eligible(t, REF) is True


def test_recent_solid_not_eligible():
    t = topic("Maths", "Area", "solid", "2026-08-18")   # 2 days old
    assert tb.is_eligible(t, REF) is False


def test_shaky_not_eligible_even_if_old():
    t = topic("Maths", "Linear equations", "shaky", "2026-07-20")
    assert tb.is_eligible(t, REF) is False


def test_untested_not_eligible():
    t = topic("Maths", "Composite area", "untested", None)
    assert tb.is_eligible(t, REF) is False


def test_repair_thread_excluded():
    t = topic("Maths", "Variables", "solid", "2026-08-01", repair=True)
    assert tb.is_eligible(t, REF) is False


def test_no_last_tested_not_eligible():
    t = topic("History", "Rome", "solid", None)
    assert tb.is_eligible(t, REF) is False


# ---------------------------------------------------------------- ordering -----

def test_older_scores_higher():
    old = topic("Maths", "Area", "solid", "2026-07-25")       # 26 days
    newer = topic("History", "Crusades", "solid", "2026-08-06")  # 14 days
    s = student([newer, old])
    assert tb.pick(s, REF)["topic"] == "Area"


def test_solid_beats_developing_at_same_age():
    a = topic("Maths", "Area", "solid", "2026-08-05")
    b = topic("Science", "Cells", "developing", "2026-08-05")
    s = student([b, a])
    assert tb.pick(s, REF)["topic"] == "Area"    # mastery bonus breaks the tie


def test_exclude_prevents_double_booking():
    a = topic("Maths", "Area", "solid", "2026-07-25")
    b = topic("History", "Crusades", "solid", "2026-08-06")
    s = student([a, b])
    # Area already slotted elsewhere in the run → next best is Crusades
    assert tb.pick(s, REF, exclude_topics={"Area"})["topic"] == "Crusades"


def test_empty_ledger_returns_none():
    s = student([topic("Maths", "Area", "shaky", "2026-07-01")])  # nothing eligible
    assert tb.pick(s, REF) is None
    assert tb.candidates(s, REF) == []


def test_determinism_on_full_tie():
    # identical score/age → subject then topic alpha decides, stably
    a = topic("Science", "Zebra topic", "solid", "2026-08-05", times_seen=5)
    b = topic("History", "Alpha topic", "solid", "2026-08-05", times_seen=5)
    s = student([a, b])
    first = tb.pick(s, REF)["topic"]
    assert first == tb.pick(s, REF)["topic"]      # stable
    assert first == "Alpha topic"                 # History < Science alpha


# ---------------------------------------------------------------- framing ------

def test_composer_note_is_neutral_and_scoped():
    n = tb.composer_note("Area", "Maths", 15)
    assert "retention check" in n.lower()
    assert "never imply" in n.lower()             # no fail-state framing
    assert "2 weeks" in n                          # 15 days ≈ 2 weeks


if __name__ == "__main__":
    import types
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and isinstance(v, types.FunctionType)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} passed")
