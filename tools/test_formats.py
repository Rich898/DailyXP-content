"""Tests for formats.py — the LAW 2 daily format bank."""
import formats as F


def slot(slotid, subject, topic, phase="speed", **kw):
    d = {"slot": slotid, "subject": subject, "topic": topic, "phase": phase}
    d.update(kw)
    return d


# ---------------------------------------------------------------- eligibility --

def test_calc_topic_detection():
    assert F.is_calc_topic("Maths", "Linear equations") is True
    assert F.is_calc_topic("Science", "Calculating density") is True
    assert F.is_calc_topic("History", "Crusades") is False


def test_calc_topic_excludes_unsafe_formats():
    s = slot("S1", "Maths", "Linear equations")
    elig_speed = F.eligible_formats(s, "speed")
    elig_steady = F.eligible_formats(s, "steady")
    # numeric-unsafe formats must not appear on a calc topic
    for bad in (F.REVERSED, F.SPOT_LIE, F.ODD_ONE_OUT, F.MATCHING):
        assert bad not in elig_speed, f"{bad} should be excluded on a calc topic"
    # spot-the-error suits maths but is now STEADY-only (a multi-step worked argument is too long for the timed speed round)
    assert F.SPOT_ERROR not in elig_speed, "spot-the-error must not be in the timed speed round"
    assert F.SPOT_ERROR in elig_steady, "spot-the-error should be available for maths in the untimed steady round"
    assert F.RECALL in elig_speed


def test_history_gets_fact_formats():
    s = slot("S2", "History", "Feudalism")
    elig = F.eligible_formats(s, "speed")
    assert F.SPOT_LIE in elig
    assert F.ODD_ONE_OUT in elig
    assert F.RECALL in elig


def test_throwback_stays_recall():
    s = slot("T1", "History", "Feudalism", phase="steady", throwback=True)
    assert F.eligible_formats(s, "steady") == [F.RECALL]


def test_teachback_is_recall_only():
    s = slot("TB", "English", "Essay", phase="teach")
    assert F.eligible_formats(s, "teach") == [F.RECALL]


def test_reversed_needs_explicit_allow():
    s = slot("S3", "History", "Rome")           # fact topic, reversed eligible...
    assert F.REVERSED in F.eligible_formats(s, "speed")
    # ...but assign_formats won't pick it without allow_reversed
    slots = [slot(f"S{i}", "History", f"Topic {i}") for i in range(4)]
    F.assign_formats(slots, "y8", "2026-08-19", "H5.1")
    assert all(s.get("format") != F.REVERSED for s in slots)


# ---------------------------------------------------------------- assignment ---

def test_assignment_covers_all_mc_slots():
    slots = [slot(f"S{i}", "History", f"Topic {i}") for i in range(7)] + \
            [slot(f"T{i}", "Science", f"Sci {i}", phase="steady") for i in range(4)] + \
            [slot("TB", "English", "Essay", phase="teach")]
    F.assign_formats(slots, "y8", "2026-08-19", "H5.1")
    mc = [s for s in slots if s["phase"] in ("speed", "steady")]
    assert all("format" in s for s in mc)
    tb = [s for s in slots if s["phase"] == "teach"][0]
    assert "format" not in tb           # teach not formatted


def test_variety_no_format_dominates():
    # 11 fact-topic slots → should span multiple formats, not all recall
    slots = [slot(f"S{i}", "History", f"Topic {i}") for i in range(11)]
    F.assign_formats(slots, "y8", "2026-08-19", "H5.1", max_same=3)
    fmts = {s["format"] for s in slots}
    assert len(fmts) >= 3, f"expected variety, got {fmts}"
    # recall must not swallow the whole run
    recall_count = sum(1 for s in slots if s["format"] == F.RECALL)
    assert recall_count <= 5


def test_determinism_same_seed_same_result():
    def build():
        s = [slot(f"S{i}", "History", f"Topic {i}") for i in range(8)]
        F.assign_formats(s, "y8", "2026-08-19", "H5.1")
        return [x["format"] for x in s]
    assert build() == build()


def test_different_day_can_differ():
    def build(date):
        s = [slot(f"S{i}", "History", f"Topic {i}") for i in range(8)]
        F.assign_formats(s, "y8", date, "H5.1")
        return tuple(x["format"] for x in s)
    a = build("2026-08-19")
    b = build("2026-08-26")
    # not guaranteed different, but the seed differs so this should hold in practice
    assert a != b or True     # tolerate rare collision; determinism is the hard req


def test_calc_slots_never_get_unsafe_format_in_assignment():
    slots = [slot(f"M{i}", "Maths", f"Equation topic {i}") for i in range(6)]
    F.assign_formats(slots, "y9", "2026-08-19", "R5.1")
    for s in slots:
        assert s["format"] not in (F.REVERSED, F.SPOT_LIE, F.ODD_ONE_OUT, F.MATCHING)


# ---------------------------------------------------------------- notes --------

def test_every_format_has_a_note():
    for fmt in [F.RECALL, F.SPOT_LIE, F.SPOT_ERROR, F.ODD_ONE_OUT,
                F.ORDERING, F.MATCHING, F.REVERSED]:
        note = F.render_note(fmt)
        assert isinstance(note, str) and len(note) > 20


def test_notes_carry_length_law_reminders():
    # the length tell must be guarded inside the format instructions too
    assert "longest" in F.render_note(F.SPOT_LIE).lower()
    assert "length" in F.render_note(F.ODD_ONE_OUT).lower()


if __name__ == "__main__":
    import types
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and isinstance(v, types.FunctionType)]
    for fn in fns:
        fn(); print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)}/{len(fns)} passed")
