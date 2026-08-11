#!/usr/bin/env python3
"""test_integrity.py — teach-back authenticity signals must be conservative:
they may never condemn a real student's writing, and must catch pasted text."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integrity import (check, credits_depth, typing_rate, baseline_for,  # noqa: E402
                       third_person_about_student, us_spellings)

REAL_SCIENCE = ("If I was testing plant growth, sunlight would be the independent "
                "variable because I change it. The plant\u2019s height is the dependent "
                "variable because I measure it carefully, but common too mix them up")
REAL_MATHS = ("Whatever you do to one side of the equation, you must do to the "
              "other side.So for this you minus 4 to 19 and 4.")
REAL_LAZY = "Because X is 3. I don't know how exactly it is but I just know it is hahahahahahahah"
PASTED = ("The student missed that the conch symbolized order, democracy, and "
          "civilized discourse, and its abandonment signifies the boys' descent "
          "into savagery and the collapse of their society.")


def t(name, cond):
    assert cond, f"FAIL: {name}"
    print(f"  [PASS] {name}")


print("integrity — real student writing is never condemned:")
r = check(REAL_SCIENCE, chars=198, secs=122.8)
t("authentic science teach-back is ok", r["verdict"] == "ok")
r = check(REAL_MATHS, chars=111, secs=138.2)
t("authentic maths teach-back is ok", r["verdict"] == "ok")
r = check(REAL_LAZY, chars=84, secs=90.0)
t("a lazy honest answer is ok (integrity != quality)", r["verdict"] == "ok")

print("\nintegrity — pasted/model text is caught:")
r = check(PASTED, chars=184, secs=31.6)
t("pasted answer quarantines", r["verdict"] == "quarantine")
t("  reason: register", any("about a student" in x for x in r["reasons"]))
t("  reason: rate", any("ch/s" in x for x in r["reasons"]))
t("  reason: US spelling", any("US spelling" in x for x in r["reasons"]))
t("quarantined text cannot credit depth", credits_depth(r) is False)
t("ok text can credit depth", credits_depth(check(REAL_SCIENCE, 198, 122.8)) is True)

print("\nintegrity — single soft signals never condemn alone:")
r = check("A clean tidy answer about photosynthesis and how the leaf uses light energy properly.",
          chars=140, secs=70)     # 2.0 ch/s, polished but slow
t("polished + normal speed is at most review", r["verdict"] in ("ok", "review"))
r = check("The colors of the leaves change.", chars=32, secs=20)
t("one US spelling on a short answer never quarantines", r["verdict"] != "quarantine")

print("\nintegrity — personal baseline beats absolute thresholds:")
fast_kid = [(200, 60), (180, 55), (160, 50)]        # ~3.3 ch/s habitually
r = check("A perfectly normal answer written at this student's usual quick pace here.",
          chars=200, secs=61, history=fast_kid)
t("a habitually fast typist is not condemned for being fast", r["verdict"] != "quarantine")
slow_kid = [(100, 100), (120, 110), (90, 95)]      # ~1.0 ch/s habitually
r = check("Some text typed far faster than this student has ever typed before now ok.",
          chars=200, secs=25, history=slow_kid)
t("a sudden 2.2x jump over own baseline flags", r["verdict"] in ("review", "quarantine"))

print("\nintegrity — helpers:")
t("rate ignores very short answers", typing_rate(20, 2) is None)
t("rate ignores zero time", typing_rate(200, 0) is None)
t("baseline needs 2+ samples", baseline_for([(200, 60)]) is None)
t("baseline computes median", abs(baseline_for([(100, 100), (200, 100)]) - 1.5) < 0.01)
t("third-person register detected", third_person_about_student("The student missed that") is True)
t("first-person is fine", third_person_about_student("I think it means") is False)
t("US spelling whole-word only", us_spellings("the colour of it") == [])

print("\n\u2713 all integrity tests green")
