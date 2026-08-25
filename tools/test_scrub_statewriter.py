#!/usr/bin/env python3
"""test_scrub_statewriter.py — Scrub It stage 5: VERIFY, not change (25 Aug 2026).

The law: the ledger never learns the delivery mode. A scrub record must be
INDISTINGUISHABLE from a tap-MC record carrying the same evidence
{ok, picked, confidence, secs, fresh}. We changed NOTHING in the state-writer,
depth-writer, or results-reader for scrub; this test proves that was correct by
construction — mode:'scrub' and the scrub telemetry subobject are read NOWHERE
on the record -> state path.

Proven here:
  1. DIFFERENTIAL — badge_for gives the byte-identical badge for a scrub record and
     a tap-MC twin, across correct/confident-wrong/considered-wrong. type:"mc" +
     no confidence (speed, no wager) routes scrub down the exact tap-MC classify path.
  2. TRANSITION — the same badge mutates a topic to the same state/box (the actual
     ledger consequence, not just the label).
  3. TELEMETRY-INERT — stripping or mutating the scrub subobject and mode flag changes
     NO badge and NO transition. If it were ever read, this would break.
  4. GUESS-FLOOR PARITY — a lucky/guessing scrub is capped exactly like tap MC (LUCKY),
     never promoted; a trivially-fast scrub is TRIV✓ just as tap MC. Recognition
     evidence, 25% guess floor, "knows it" ceiling — unchanged.
  5. DEPTH-BLIND — depth_writer.item_ceiling treats a scrub item exactly as tap MC
     (an unknown mech falls through to the tap-MC cap); the confidence axis and the
     depth axis stay independent (two-axes law).

Runnable in CI: `python3 tools/test_scrub_statewriter.py` (exit 0 = all pass). No names/scores.
"""
import os, sys, copy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from state_writer import badge_for, transition
import depth_writer

fails = []
def check(name, ok, d=""):
    print(("  ok  " if ok else "  FAIL") + " " + name + (f"  [{d}]" if (d and not ok) else ""))
    if not ok:
        fails.append(name)

STU = "t1"
# A trustworthy pace baseline for STU speed: median 10s, plenty of samples.
MEDIANS = {(STU, "speed"): (10.0, 12), (STU, "steady"): (30.0, 12)}
NO_FLAGS = {}

def tap(**over):
    """A tap-MC speed record as the shell writes it."""
    q = {"id": "S4", "subject": "Science", "phase": "speed", "type": "mc",
         "skipped": False, "fresh": True, "ok": True, "picked": "Chloroplast",
         "confidence": None, "secs": 6.0, "pts": 130, "text": None}
    q.update(over)
    return q

def scrub(**over):
    """The SAME evidence, but as a scrub record: type still mc, mode:'scrub',
    plus the telemetry subobject the widget produces. Nothing here is new evidence."""
    q = tap(**over)
    q["mode"] = "scrub"
    q["scrub"] = {"eliminations": [{"opt": "Mitochondrion", "startMs": 800, "commitMs": 2100},
                                   {"opt": "Ribosome", "startMs": 2400, "commitMs": 3300},
                                   {"opt": "Nucleus", "startMs": 3600, "commitMs": 4800}],
                  "longestLived": "Nucleus", "finalTwo": ["Nucleus", "Chloroplast"], "standing": []}
    return q

def topic(state="shaky"):
    return {"subject": "Science", "topic": "Cells", "state": state, "repair": False,
            "repair_confirms": 0, "last_tested": "2026-08-01", "note": "human note — must survive"}

def mutate(q, t0):
    """Run the real writer path: badge -> transition -> return (badge, new topic)."""
    t = copy.deepcopy(t0)
    badge, rel = badge_for(q, MEDIANS, STU, NO_FLAGS)
    reason = transition(t, badge, rel, spaced=True, caveat=False)
    return badge, t, reason

# ---- 1+2: differential across the three verdicts that matter ----------------
SCENARIOS = [
    ("clean correct (plain)", dict(ok=True, picked="Chloroplast", confidence=None, secs=6.0)),
    ("confident-wrong",       dict(ok=False, picked="Nucleus", confidence="sure", secs=6.0)),
    ("considered-wrong",      dict(ok=False, picked="Nucleus", confidence=None, secs=6.0)),
    ("correct, think-so",     dict(ok=True, picked="Chloroplast", confidence="think so", secs=6.0)),
]
for label, ev in SCENARIOS:
    bt, tt, _ = mutate(tap(**ev), topic())
    bs, ts, _ = mutate(scrub(**ev), topic())
    check(f"badge identical — {label}", bt == bs, f"tap={bt} scrub={bs}")
    check(f"state mutation identical — {label}",
          tt["state"] == ts["state"] and tt.get("repair") == ts.get("repair"),
          f"tap={tt['state']} scrub={ts['state']}")
    check(f"human note preserved — {label}", ts["note"] == topic()["note"])

# ---- 3: telemetry is inert — perturbing it changes nothing ------------------
base_badge, base_t, _ = mutate(scrub(), topic())
# (a) strip the scrub subobject entirely
q_no_tel = scrub(); q_no_tel.pop("scrub")
b1, t1, _ = mutate(q_no_tel, topic())
check("removing scrub telemetry changes no badge", b1 == base_badge, f"{b1} vs {base_badge}")
check("removing scrub telemetry changes no state", t1["state"] == base_t["state"])
# (b) garble the telemetry — a wildly different elimination story
q_gar = scrub(); q_gar["scrub"]["standing"] = ["Nucleus", "Ribosome", "Mitochondrion"]
q_gar["scrub"]["longestLived"] = "Ribosome"; q_gar["scrub"]["eliminations"] = []
b2, t2, _ = mutate(q_gar, topic())
check("garbling scrub telemetry changes no badge", b2 == base_badge)
check("garbling scrub telemetry changes no state", t2["state"] == base_t["state"])
# (c) drop the mode flag — still identical (mode is never read on this path)
q_nomode = scrub(); q_nomode.pop("mode")
b3, _, _ = mutate(q_nomode, topic())
check("dropping mode flag changes no badge", b3 == base_badge)

# ---- 4: guess-floor parity (recognition evidence, 25% floor, knows-it cap) ---
# lucky/guessing correct -> LUCKY for BOTH; never a promotion
lt = tap(ok=True, confidence="guessing"); ls = scrub(ok=True, confidence="guessing")
bl_t, _, _ = mutate(lt, topic()); bl_s, _, _ = mutate(ls, topic())
check("guessing-correct is LUCKY for tap", bl_t == "LUCKY", bl_t)
check("guessing-correct is LUCKY for scrub too (guess floor identical)", bl_s == "LUCKY", bl_s)
# trivially fast correct -> TRIV✓ for BOTH (secs well under TRIVIAL_FRAC*median)
tt_ = tap(ok=True, secs=2.0); ts_ = scrub(ok=True, secs=2.0)
bt_t, _, _ = mutate(tt_, topic("developing")); bt_s, _, _ = mutate(ts_, topic("developing"))
check("trivially-fast correct is TRIV✓ for tap", bt_t == "TRIV✓", bt_t)
check("trivially-fast correct is TRIV✓ for scrub too", bt_s == "TRIV✓", bt_s)

# a clean confident scrub can raise at most one box (never solid in one hit) — same as tap MC
cs = scrub(ok=True, confidence="sure", secs=6.0)
_, ct, _ = mutate(cs, topic("shaky"))
check("clean scrub promotes at most one box (shaky->developing, capped at knows-it)",
      ct["state"] in ("shaky", "developing") and ct["state"] != "solid", ct["state"])

# ---- 5: depth axis stays blind to scrub (two-axes law) ----------------------
scrub_slot = {"mech": "scrub", "phase": "speed"}
tap_slot = {"mech": "recall", "phase": "speed"}
qd = {"phase": "speed"}
# a clean-MC badge on a speed item: ceiling is the tap-MC recognition cap for BOTH
c_scrub = depth_writer.item_ceiling(scrub_slot, qd, "\u2713_plain")
c_tap = depth_writer.item_ceiling(tap_slot, qd, "\u2713_plain")
check("depth ceiling identical scrub vs tap (recognition cap)", c_scrub == c_tap, f"scrub={c_scrub} tap={c_tap}")
check("scrub is NOT a depth-bearing mechanic (never 'applies'/'connects')",
      c_scrub not in ("applies", "connects"), c_scrub)
# scrub badges are clean-MC, and depth_writer counts them exactly as tap-MC clean badges
check("depth writer treats scrub clean-correct in the tap-MC CLEAN_MC set",
      "\u2713_plain" in depth_writer.CLEAN_MC and "\u2713_sure" in depth_writer.CLEAN_MC)

print()
print("ALL PASS \u2713 — the ledger cannot tell scrub from tap MC" if not fails else f"FAILURES \u2717 {fails}")
sys.exit(0 if not fails else 1)
