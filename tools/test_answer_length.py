"""Tests for answer_length.py — the LAW 1 answer-length integrity gate."""
import answer_length as al


def mc(id, options, answer, phase="speed"):
    return {"id": id, "phase": phase, "options": options, "answer": answer}


# ---------------------------------------------------------------- per-slot ----

def test_sole_longest_is_flagged():
    # correct answer far longer than the three short distractors
    s = mc("S1",
           ["96°", "84°", "180°",
            "96°, because co-interior angles are supplementary and sum to 180"],
           "96°, because co-interior angles are supplementary and sum to 180")
    assert al.sole_longest_violation(s) is True


def test_balanced_band_passes():
    s = mc("S2", ["Rectangle", "Rhombus", "Trapezium", "Parallelogram"], "Rectangle")
    assert al.sole_longest_violation(s) is False


def test_correct_shortest_passes():
    s = mc("S3", ["A long wrong option here", "Another wrong one padded out",
                  "Third distractor of length", "Paris"], "Paris")
    assert al.sole_longest_violation(s) is False


def test_tie_for_longest_not_flagged():
    # correct ties another option for longest → not a clean tell
    s = mc("S4", ["x = 5 after expanding the brackets first",
                  "x = 6 after expanding the brackets first",  # same length-ish
                  "x = 4", "x = 7"],
           "x = 5 after expanding the brackets first")
    # force exact tie
    s["options"][1] = "y = 5 after expanding the brackets first"
    assert len(s["options"][0]) == len(s["options"][1])
    assert al.sole_longest_violation(s) is False


def test_small_margin_not_flagged():
    # correct longest but only by a couple of chars (< 15%) → allowed
    s = mc("S5", ["Photosynthesis", "Respiration!!", "Fermentation", "Transpiration"],
           "Photosynthesis")
    # Photosynthesis(14) vs Transpiration(13) — 1 char, under margin
    assert al.sole_longest_violation(s) is False


def test_true_false_exempt():
    s = mc("S6", ["True", "False"], "False")
    assert al.slot_is_mc(s) is False           # 2 options → rule doesn't apply
    assert al.sole_longest_violation(s) is False


def test_teachback_ignored():
    s = {"id": "T1", "phase": "teach", "prompt": "Explain...", "answer": "n/a"}
    assert al.slot_is_mc(s) is False


# --------------------------------------------------------------- per-run ------

def test_rank_computation():
    s = mc("S7", ["aaaa", "bb", "cccccc", "d"], "cccccc")   # correct is longest
    assert al.correct_length_rank(s) == 1
    s2 = mc("S8", ["aaaa", "bb", "cccccc", "d"], "bb")       # correct 2nd shortest
    assert al.correct_length_rank(s2) == 3


def test_run_distribution_violation_when_all_longest():
    # 5 slots, correct is sole-longest in all → run fails distribution
    slots = []
    for i in range(5):
        slots.append(mc(f"S{i}",
                        ["x", "yy", "zzz",
                         "the correct and much longer answer text here"],
                        "the correct and much longer answer text here"))
    a = al.audit(slots)
    assert a["mc_total"] == 5
    assert a["longest_count"] == 5
    assert a["run_distribution_violation"] is True
    assert a["ok"] is False
    assert len(a["slot_violations"]) == 5


def test_flat_run_passes():
    # correct answer sits at a different length-rank each slot, none conspicuous
    slots = [
        mc("A", ["short", "medium ok", "a bit longer here", "tiny"], "medium ok"),
        mc("B", ["alpha", "beta", "gamma", "delt"], "beta"),
        mc("C", ["one", "two", "three", "four"], "four"),
        mc("D", ["cat", "horse", "elephantine", "dog"], "cat"),
    ]
    a = al.audit(slots)
    assert a["run_distribution_violation"] is False
    assert a["slot_violations"] == []
    assert a["ok"] is True


def test_empty_is_ok():
    a = al.audit([])
    assert a["ok"] is True
    assert a["mc_total"] == 0


if __name__ == "__main__":
    import sys, types
    fns = [v for k, v in sorted(globals().items())
           if k.startswith("test_") and isinstance(v, types.FunctionType)]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
        passed += 1
    print(f"\n{passed}/{len(fns)} passed")
