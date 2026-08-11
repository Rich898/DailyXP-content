#!/usr/bin/env python3
"""
weekword.py — the ONE week-word engine. Wednesday plants, Friday harvests, and
they physically cannot contradict because they compute the word HERE, together.

REPORTING.md law: "REUSE the week-word engine. Wednesday and Friday MUST use
the SAME thresholds." This module is that shared truth. Both composers import
window_stats() + momentum() from here; wed_checkin.py re-exports them for
backward compatibility so its existing tests and call sites are untouched.

The word is chosen DETERMINISTICALLY from thresholds (days completed, net
comprehension movement) — code picks it, the model only writes the sentence
around it. Sampling differs by day, the ENGINE does not:
  * Wednesday samples Mon..Wed (or Mon..Tue at the 8:25pm cutoff) vs the SAME
    days last week.
  * Friday samples Mon..Fri vs LAST week's Mon..Fri.
Same function, same COMP_DELTA, same rule order — so a "solid" on Wednesday can
never become a "slower" on Friday off the same underlying data.

The four words (REPORTING.md), framed on effort/trajectory not outcome:
  strong  high activity + forward movement            -> celebrate
  solid   steady, on pace, undramatic (most weeks)    -> keep going
  quiet   low activity / missed days (engagement dip) -> nudge the habit
  slower  showed up, but landed harder (comp. dip)    -> support the learning

Two laws encoded in rule ORDER, not comments:
  * QUIET OUTRANKS SLOWER. Sparse activity is checked before any comprehension
    judgement — thin evidence never earns a "slower". You cannot diagnose
    comprehension from days a kid didn't show up.
  * THE RATIO NEVER LEAVES. Comprehension is a mean best-run ratio computed in
    window_stats() and compared in momentum(); it is printed NOWHERE. Only the
    resulting WORD and DIRECTION are ever surfaced.
"""

COMP_DELTA = 0.12   # comprehension swing that counts as a real move (both days share it)


def window_stats(runs, student, day_isos):
    """days_done + mean comprehension ratio (best run per day) over a window.

    The ratio lives and dies in this function — callers get the word, never
    the number. 'possible' is the window length so attendance can be phrased.
    """
    best = {}
    for r in runs:
        if r.get("student") != student or r.get("run_date") not in day_isos:
            continue
        d = r["run_date"]
        sc = int(r.get("score") or 0)
        if d not in best or sc > best[d][0]:
            best[d] = (sc, r.get("max_score") or r.get("maxScore"))
    ratios = [s / int(m) for s, m in best.values() if m and int(m) > 0]
    return {"days_done": len(best), "possible": len(day_isos),
            "comp": (sum(ratios) / len(ratios)) if ratios else None}


def momentum(now, prev):
    """The week-word, from two window_stats dicts. Quiet outranks slower by
    rule order. direction: up | flat | down | none (none = no prior on file).

    Rule order IS the doctrine — do not reorder:
      1. no prior week            -> quiet if nothing done, else solid (no dir)
      2. nothing done this window -> quiet/down (engagement floor)
      3. fewer days than prior    -> quiet/down (engagement dip outranks comp.)
      4. comprehension fell >delta -> slower/down (only now, with days present)
      5. more days OR comp. rose   -> strong/up
      6. otherwise                 -> solid/flat
    """
    no_prior = prev["days_done"] == 0 and prev["comp"] is None
    if no_prior:
        word = "quiet" if now["days_done"] == 0 else "solid"
        return {"word": word, "direction": "none"}
    if now["days_done"] == 0:
        return {"word": "quiet", "direction": "down"}
    if now["days_done"] < prev["days_done"]:
        return {"word": "quiet", "direction": "down"}
    comps = now["comp"] is not None and prev["comp"] is not None
    if comps and now["comp"] <= prev["comp"] - COMP_DELTA:
        return {"word": "slower", "direction": "down"}
    if now["days_done"] > prev["days_done"] or (comps and now["comp"] >= prev["comp"] + COMP_DELTA):
        return {"word": "strong", "direction": "up"}
    return {"word": "solid", "direction": "flat"}
