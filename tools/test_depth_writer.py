#!/usr/bin/env python3
"""Self-contained regression test for depth_writer's ladder rules (UNDERSTANDING.md §3–§4).

Builds a synthetic private-dir (generic topics, no names/scores) and asserts every ratified
doctrine rule, PLUS the shadow guarantee: state.json is byte-identical after every run.
Runnable in CI: `python3 tools/test_depth_writer.py` (exit 0 = all pass).
"""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import depth_writer as dw

tmp = tempfile.mkdtemp(prefix="dw_regress_")
os.makedirs(f"{tmp}/work"); os.makedirs(f"{tmp}/plans/s1")

# --- a decoy state.json: the shadow writer must never touch (or even open) it ---
STATE_BYTES = json.dumps({"generated": "2026-07-01", "students": {"s1": {"topics": [
    {"subject": "Sci", "topic": "anything", "state": "REPAIR", "repair": True}]}}}, indent=2)
open(f"{tmp}/work/state.json", "w").write(STATE_BYTES)

def plan(set_date, slots):
    json.dump({"student": "s1", "set_date": set_date, "tag": "X", "day": "THU",
               "slots": [{"slot": i, "phase": p, "subject": s, "topic": t, **extra}
                         for i, p, s, t, extra in slots]},
              open(f"{tmp}/plans/s1/{set_date}.json", "w"), indent=2)

def Q(id, phase, ok=True, type=None, conf=None, secs=12.0, tb=None, text=None):
    q = {"id": id, "subject": "X", "phase": phase, "ok": ok, "secs": secs,
         "timeUsed": secs, "skipped": False, "confidence": conf, "picked": "a"}
    if type: q["type"] = type
    if tb is not None: q["tb_grade"] = tb
    if text is not None: q["text"] = text
    return q

def run(set_date, run_date, ts, questions, caveat=False, flags=None):
    return {"student": "s1", "tag": "X", "set_date": set_date, "run_date": run_date,
            "ts": ts, "ts_raw": ts, "canonical": True, "is_test": False,
            "canonical_caveat": caveat, "shell_flags": flags or {}, "questions": questions}

def write_runs(runs):
    json.dump({"runs": runs}, open(f"{tmp}/work/runs.json", "w"), indent=2)

def depth_of(shadow, topic):
    for t in shadow["students"]["s1"]["topics"]:
        if t["topic"] == topic:
            return t["depth"]
    return "not_yet"   # absence == not_yet

PASS = []
def check(name, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    PASS.append(cond)

# ---------------------------------------------------------------------------
# Night 1 (set 2026-08-10): one rule per topic
# ---------------------------------------------------------------------------
plan("2026-08-10", [
    ("S1", "speed",  "Sci", "clean_speed",   {}),                       # clean speed ✓ -> knows
    ("S2", "speed",  "Sci", "lucky_guess",   {}),                       # lucky ✓ -> nothing
    ("S3", "speed",  "Sci", "trivially_fast",{}),                       # trivially fast ✓ -> nothing
    ("S4", "speed",  "Sci", "swipe_alone",   {}),                       # swipe ✓ -> nothing
    ("S5", "speed",  "Sci", "reversed_item", {"mech": "reversed"}),     # reversed ✓ -> knows, capped
    ("T1", "steady", "Mat", "two_facets",    {}),                       # steady ✓ day 1 of 2
    ("T2", "steady", "Mat", "same_day_only", {}),                       # two steady ✓ SAME day -> knows only
    ("T3", "steady", "Mat", "same_day_only", {}),
    ("T4", "steady", "Mat", "typed_counts",  {}),                       # typed steady ✓ day 1 of 2
    ("T5", "steady", "His", "transfer_tag",  {"mech": "transfer"}),     # tagged transfer ✓ -> applies
    ("B1", "teach",  "His", "tb_connects",   {}),                       # graded connects -> connects
    ("B2", "teach",  "His", "tb_applies_cap",{}),                       # graded applies -> capped at connects
    ("B3", "teach",  "His", "tb_held",       {}),                       # integrity hold -> nothing
    ("B4", "teach",  "His", "tb_none",       {}),                       # verdict none/not_yet -> no change, no demote
])
median_filler = [Q(f"M{i}", "speed", ok=True, secs=10.0) for i in range(0)]  # medians come from the set itself
night1 = run("2026-08-10", "2026-08-10", "2026-08-10T18:00:00", [
    Q("S1", "speed", ok=True, secs=9.0),
    Q("S2", "speed", ok=True, secs=9.0),                          # flagged lucky below
    Q("S3", "speed", ok=True, secs=0.5),                          # ~5% of median -> trivially fast
    Q("S4", "speed", ok=True, type="swipe", secs=3.0),
    Q("S5", "speed", ok=True, secs=9.0),
    Q("T1", "steady", ok=True, conf="sure", secs=20.0),
    Q("T2", "steady", ok=True, conf="think so", secs=20.0),
    Q("T3", "steady", ok=True, conf="sure", secs=20.0),
    Q("T4", "steady", ok=True, type="numeric", secs=20.0),
    Q("T5", "steady", ok=True, conf="sure", secs=20.0),
    Q("B1", "teach", ok=True, text="A leads to B", tb={"verdict": "solid", "depth": "connects", "evidence": "because A causes B"}),
    Q("B2", "teach", ok=True, text="x", tb={"verdict": "solid", "depth": "applies", "evidence": "used it elsewhere"}),
    Q("B3", "teach", ok=True, text="x", tb={"verdict": "solid", "depth": "connects", "integrity_hold": True}),
    Q("B4", "teach", ok=True, text="x", tb={"verdict": "none", "depth": "not_yet"}),
], flags={"luckyGuess": ["S2"]})

write_runs([night1])
shadow, lines, audit = dw.process(tmp)

print("night 1 — evidence rules")
check("clean speed correct → knows", depth_of(shadow, "clean_speed") == "knows")
check("lucky correct never evidences depth", depth_of(shadow, "lucky_guess") == "not_yet")
check("trivially-fast correct never evidences depth", depth_of(shadow, "trivially_fast") == "not_yet")
check("a swipe never evidences depth on its own", depth_of(shadow, "swipe_alone") == "not_yet")
check("reversed caps at knows (recognition in reverse)", depth_of(shadow, "reversed_item") == "knows")
check("one steady date is not yet lists", depth_of(shadow, "two_facets") == "knows")
check("two steady corrects the SAME day → knows only (dates, not prompts)", depth_of(shadow, "same_day_only") == "knows")
check("tagged transfer correct → applies (future-proof)", depth_of(shadow, "transfer_tag") == "applies")
check("teach-back graded connects → connects (direct, from not_yet)", depth_of(shadow, "tb_connects") == "connects")
check("teach-back graded applies capped at teach ceiling connects", depth_of(shadow, "tb_applies_cap") == "connects")
check("integrity hold → no ledger consequence", depth_of(shadow, "tb_held") == "not_yet")
check("verdict none → no change (never demote on one)", depth_of(shadow, "tb_none") == "not_yet")
check("shadow guarantee: state.json byte-identical", open(f"{tmp}/work/state.json").read() == STATE_BYTES)

# ---------------------------------------------------------------------------
# Night 2 (set 2026-08-12): second facet day; first low teach-back
# ---------------------------------------------------------------------------
plan("2026-08-12", [
    ("T1", "steady", "Mat", "two_facets", {}),        # steady ✓ day 2 of 2 -> lists
    ("T2", "steady", "Mat", "typed_counts", {}),      # typed steady ✓ day 2 -> lists
    ("B1", "teach",  "His", "tb_connects", {}),       # graded lists (1st below connects) -> hold
])
night2 = run("2026-08-12", "2026-08-12", "2026-08-12T18:00:00", [
    Q("T1", "steady", ok=True, conf="sure", secs=20.0),
    Q("T2", "steady", ok=True, type="text", secs=20.0),
    Q("B1", "teach", ok=True, text="x", tb={"verdict": "partial", "depth": "lists", "evidence": "listed two causes"}),
])

# Night 2b (set 2026-08-13): a repeat-attempt caveat run — steady blocked, teach counts
plan("2026-08-13", [
    ("T1", "steady", "Mat", "caveat_blocked", {}),    # caveat run: steady ✓ must NOT count
    ("B1", "teach",  "Mat", "caveat_teach", {}),      # teach on caveat run still counts
])
night2b = run("2026-08-13", "2026-08-13", "2026-08-13T18:00:00", [
    Q("T1", "steady", ok=True, conf="sure", secs=20.0),
    Q("B1", "teach", ok=True, text="A so B", tb={"verdict": "solid", "depth": "connects", "evidence": "so"}),
], caveat=True)

write_runs([night1, night2, night2b])
shadow, lines, audit = dw.process(tmp)

print("night 2 — dates, caveats, reluctance")
check("two steady dates → lists", depth_of(shadow, "two_facets") == "lists")
check("typed steady items count toward lists", depth_of(shadow, "typed_counts") == "lists")
check("caveat run: steady corrects contribute nothing", depth_of(shadow, "caveat_blocked") == "not_yet")
check("caveat run: graded teach-back STILL counts", depth_of(shadow, "caveat_teach") == "connects")
check("one below-connects teach-back does NOT demote", depth_of(shadow, "tb_connects") == "connects")

# ---------------------------------------------------------------------------
# Night 3 (set 2026-08-14): second consecutive low teach-back -> demote one rung
# ---------------------------------------------------------------------------
plan("2026-08-14", [("B1", "teach", "His", "tb_connects", {})])
night3 = run("2026-08-14", "2026-08-14", "2026-08-14T18:00:00", [
    Q("B1", "teach", ok=True, text="x", tb={"verdict": "partial", "depth": "lists", "evidence": "still listing"}),
])
write_runs([night1, night2, night2b, night3])
shadow, lines, audit = dw.process(tmp)

print("night 3 — reluctant demotion")
check("two consecutive below-connects teach-backs → demote ONE rung to lists",
      depth_of(shadow, "tb_connects") == "lists")
check("demotion resets the episode counter", shadow["students"]["s1"]["topics"][
      [i for i, t in enumerate(shadow["students"]["s1"]["topics"]) if t["topic"] == "tb_connects"][0]
      ]["tb_recent"] == [])
check("shadow guarantee still holds after three nights",
      open(f"{tmp}/work/state.json").read() == STATE_BYTES)

# ---------------------------------------------------------------------------
# Idempotence: reprocessing changes nothing
# ---------------------------------------------------------------------------
before = json.dumps(shadow, sort_keys=True)
shadow2, lines2, audit2 = dw.process(tmp)
print("idempotence")
check("cursor prevents reprocessing (no new changes)", audit2 == [] and
      json.dumps(shadow2, sort_keys=True) == before)

# ---------------------------------------------------------------------------
# Awaiting grade: an ungraded teach-back with text parks the WHOLE run un-cursored
# ---------------------------------------------------------------------------
plan("2026-08-16", [
    ("S1", "speed", "Geo", "parked_speed", {}),
    ("B1", "teach", "Geo", "parked_teach", {}),
])
night4 = run("2026-08-16", "2026-08-16", "2026-08-16T18:00:00", [
    Q("S1", "speed", ok=True, secs=9.0),
    Q("B1", "teach", ok=True, text="a real written answer, not yet graded"),   # no tb_grade
])
write_runs([night1, night2, night2b, night3, night4])
shadow, lines, audit = dw.process(tmp)
print("awaiting grade")
check("nothing from the run applies while its teach-back is ungraded",
      depth_of(shadow, "parked_speed") == "not_yet")

# ... then the grade lands (grader scanned the backlog) and the run applies in full, once
night4["questions"][1]["tb_grade"] = {"verdict": "solid", "depth": "connects", "evidence": "linked"}
write_runs([night1, night2, night2b, night3, night4])
shadow, lines, audit = dw.process(tmp)
check("once graded, the parked run applies in full", depth_of(shadow, "parked_speed") == "knows"
      and depth_of(shadow, "parked_teach") == "connects")
shadow, lines, audit = dw.process(tmp)
check("and only once (no double-count on reprocess)",
      len([a for a in audit]) == 0)

# ---------------------------------------------------------------------------
n_fail = PASS.count(False)
print(f"\ndepth ladder acting end: {'all green' if not n_fail else f'{n_fail} FAILURE(S)'}")
sys.exit(1 if n_fail else 0)
