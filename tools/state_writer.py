#!/usr/bin/env python3
"""
state_writer.py — the RETURN LEG of the scheduler (roadmap #2).

results_reader.py reads the Sheet and emits per-question verdicts. This takes those
verdicts and actually UPDATES state.json — the piece that makes the loop *adaptive*
instead of just *composing*. Until now a human did this by hand every morning; this
closes it.

    results (runs.json)  +  the plan (which topic each slot tested)  +  current state
        →  new state (promotions / demotions / REPAIR in&out / spacing)

It reuses results_reader's classify()/pace engine (one source of doctrine) and applies the
transition table in LEDGER-RULES.md. It is deterministic — no API, no language. The human
`note` on each topic is never overwritten (qualitative judgement stays human/LLM-authored);
the writer only moves the structured fields and appends a factual `last_result` + an audit
line.

Join: a result question carries id+subject but not topic. run_daily persists the plan to
`{private}/plans/{student}/{set_date}.json`; the writer reads it to map slot→topic.

Idempotent: only canonical, non-test runs count, each processed once (cursor). attempt>1
canonical carries a caveat → promotions capped at `developing`, never `solid`.

Usage:
  python3 tools/state_writer.py --private-dir ../DailyXP-private            # apply + write
  python3 tools/state_writer.py --private-dir ../DailyXP-private --dry-run  # preview only
"""
import argparse
import json
import os
import sys
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from results_reader import classify, relative_speed, phase_medians  # noqa: E402  (one source of doctrine)

REPAIR_EXIT_CONFIRMS = 2   # calm confident confirms needed to leave REPAIR — "one more cycle"

BOX = {"untested": 0, "shaky": 1, "REPAIR": 1, "developing": 2, "solid": 3}
IBOX = {0: "untested", 1: "shaky", 2: "developing", 3: "solid"}
# governing-badge severity (lower index wins when a topic is hit by several slots)
PREC = ["CW", "✗", "SW", "GW", "SKIP✗", "FW", "LUCKY", "TRIV✓", "TB✗", "✓_sure", "TB✓", "✓_think", "TB~", "✓_plain", "TB", "SKIP"]

# Teach-back QUALITY (graded by tools/grade_teachback.py, consumed deterministically here).
# The teach-back is the deepest anti-fluency-illusion signal, so its grade has a real ledger
# consequence — mapped onto the existing box model:
#   solid   -> TB✓  : genuine understanding; strong positive, routed like a calm confident correct.
#   partial -> TB~  : partial understanding; mild positive (a landing, never a promotion to solid).
#   none    -> TB✗  : could NOT explain it. This is the fluency-illusion catch — it is placed ABOVE
#                     the correct badges in PREC, so on a topic where the student picked the right
#                     MC answer BUT failed to explain it, TB✗ governs and BLOCKS the promotion
#                     (the topic is not truly mastered). It holds the box; it does not demote.
def verdict_badge(grade):
    """Map a teach-back grade dict (or None) to a badge. None/unrecognised -> plain 'TB' (no-op).

    INTEGRITY HOLD: a teach-back flagged by integrity.py as not plausibly the
    student's own writing gets NO ledger consequence — it degrades to the no-op
    'TB' exactly as an ungraded answer does. We do not credit (or penalise) the
    ledger on text we cannot attribute to the student. Clearing a hold is a
    human decision, made by removing the flag on the run.
    """
    if (grade or {}).get("integrity_hold"):
        return "TB"
    v = (grade or {}).get("verdict")
    return {"solid": "TB✓", "partial": "TB~", "none": "TB✗"}.get(v, "TB")


# --------------------------------------------------------------------------- #
# Join + verdict prep
# --------------------------------------------------------------------------- #

def load_plan(private_dir, student, set_date):
    p = os.path.join(private_dir, "plans", student, f"{set_date}.json")
    if not os.path.exists(p):
        return None
    plan = json.load(open(p))
    return {sl["slot"]: sl for sl in plan.get("slots", [])}


def badge_for(q, medians, student, shell_flags):
    """classify() gives the doctrine badge; split the generic '✓' by confidence/pace.
    For a teach-back, upgrade the no-op 'TB' to a graded verdict badge when one is present."""
    rel, _ = relative_speed(q, medians, student)
    if q.get("type") == "swipe":
        # a swipe is a fast 50/50 sort — deliberately weak evidence (see transition()).
        return ("SWIPE✓" if q.get("ok") else "SWIPE✗"), rel
    if q.get("type") == "numeric":
        # typed answer, no options to guess (see transition()).
        return ("NUM✓" if q.get("ok") else "NUM✗"), rel
    if q.get("type") == "order":
        # all-or-nothing sequence, no options (see transition()).
        return ("ORD✓" if q.get("ok") else "ORD✗"), rel
    badge, _impl = classify(q, rel, shell_flags)
    if badge == "✓":
        conf = (q.get("confidence") or "").lower()
        badge = "✓_sure" if conf == "sure" else "✓_think" if conf == "think so" else "✓_plain"
    elif badge == "TB":
        badge = verdict_badge(q.get("tb_grade"))   # graded teach-back gets a real consequence
    return badge, rel


def find_topic(state_student, subject, topic):
    """Tolerant (subject, topic) join into the ledger — same spirit as the planner's."""
    for t in state_student["topics"]:
        if t["subject"] == subject and t["topic"] == topic:
            return t
    # fall back to topic-string match if subject drifted
    for t in state_student["topics"]:
        if t["topic"] == topic:
            return t
    return None


# --------------------------------------------------------------------------- #
# The transition (LEDGER-RULES.md, encoded)
# --------------------------------------------------------------------------- #

def transition(t, badge, rel, spaced, caveat):
    """Mutate topic dict t for one governing badge. Return a short reason (or None for TB/SKIP)."""
    cur = t.get("state", "untested")
    repair = bool(t.get("repair"))
    confirms = int(t.get("repair_confirms", 0))
    prior_badge = (t.get("last_result") or {}).get("badge")
    calm = rel not in ("fast", "trivial")   # None counts as calm (unmeasured → benefit of doubt)

    # ---- swipe: a fast 50/50 sort. Weak evidence: it can gently RAISE a topic but NEVER reaches
    #      solid on its own (a coin-flip is not mastery), and a miss holds rather than punishes. ----
    if badge == "SWIPE✓":
        if repair:
            return "swipe-correct on REPAIR → held (a 50/50 sort can't confirm a repair)"
        if cur == "untested":
            t["state"] = "shaky"; return "swipe-correct → shaky (weak positive, gentle raise)"
        if cur == "shaky":
            t["state"] = "developing"; return "swipe-correct → developing (capped — swipe never reaches solid alone)"
        return f"swipe-correct → held at {cur} (swipe never promotes to solid alone)"
    if badge == "SWIPE✗":
        return f"swipe-wrong → held at {cur} (a 50/50 miss is weak evidence)"

    # ---- numeric: a TYPED answer, no options to guess from — strong evidence. Promotes like a clean
    #      correct but capped at developing (numeric carries no confidence wager, so solid needs deeper
    #      evidence). usedCalc is preserved on the record so the parent report shows method vs mental. ----
    if badge in ("ORD✓", "ORD✗", "NUM✓", "NUM✗"):
        ok = badge in ("ORD✓", "NUM✓")
        if repair:
            t.update(state="REPAIR", repair=True, repair_confirms=(confirms if ok else 0))
            return "numeric on REPAIR → held" + ("" if ok else " (confirms reset)")
        if ok:
            if cur in ("untested", "shaky"):
                t["state"] = "developing"
            return f"numeric-correct → {t['state']} (typed, no guessing; capped at developing)"
        t.update(state=IBOX[max(1, BOX[cur] - 1)], repair_confirms=0)
        return f"numeric-wrong → {t['state']}"

    # ---- REPAIR lane: state stays "REPAIR" until it earns out to developing ----
    if repair:
        if badge == "TB✓":                           # solid teach-back = genuine understanding → a confirm
            confirms += 1
            if confirms >= REPAIR_EXIT_CONFIRMS:
                t.update(state="developing", repair=False, repair_confirms=0)
                return f"REPAIR exit: teach-back solid, {confirms} confirms → developing"
            t.update(state="REPAIR", repair=True, repair_confirms=confirms)
            return f"REPAIR teach-back solid, confirm {confirms}/{REPAIR_EXIT_CONFIRMS} (held)"
        if badge == "TB~":                           # partial teach-back → held, confirms untouched
            t.update(state="REPAIR", repair=True, repair_confirms=confirms)
            return "partial teach-back on REPAIR → held"
        if badge in ("✓_sure", "✓_think", "✓_plain"):
            if badge == "✓_sure" and calm:
                confirms += 1
                if confirms >= REPAIR_EXIT_CONFIRMS:
                    t.update(state="developing", repair=False, repair_confirms=0)
                    return f"REPAIR exit: {confirms} calm confident confirms → developing"
                t.update(state="REPAIR", repair=True, repair_confirms=confirms)
                return f"REPAIR calm confirm {confirms}/{REPAIR_EXIT_CONFIRMS} (held)"
            t.update(state="REPAIR", repair=True, repair_confirms=confirms)
            return "correct on REPAIR but not a calm confident confirm → held"
        # any wrong / fast-wrong / lucky / trivial: hold in REPAIR, reset confirms
        t.update(state="REPAIR", repair=True, repair_confirms=0)
        label = {"CW": "confident-wrong", "✗": "considered-wrong", "SW": "slow-wrong",
                 "GW": "guessing-wrong", "FW": "fast-wrong", "LUCKY": "lucky-correct", "TB✗": "failed-teach-back",
                 "TRIV✓": "trivial-correct", "SKIP✗": "skip-on-taught"}.get(badge, badge)
        return f"{label} on REPAIR → held (confirms reset)"

    # ---- non-REPAIR topics: box model (untested/shaky/developing/solid) ----
    if badge == "CW":
        if prior_badge == "CW":
            t.update(state="REPAIR", repair=True, repair_confirms=0)
            return "2nd confident-wrong → REPAIR (chronic, self-invisible)"
        t.update(state="shaky", repair_confirms=0)
        return "confident-wrong → shaky"
    if badge in ("✗", "SW", "GW"):
        t.update(state=IBOX[max(1, BOX[cur] - 1)], repair_confirms=0)
        kind = {"✗": "considered-wrong", "SW": "slow-wrong", "GW": "guessing-wrong"}[badge]
        return f"{kind} → {t['state']}"
    if badge == "SKIP✗":                       # skipped a topic already taught → soft miss
        t.update(state=IBOX[max(1, BOX[cur] - 1)], repair_confirms=0)
        return f"skipped a taught topic (avoided) → {t['state']}"
    if badge == "FW":
        t["repair_confirms"] = 0
        return "fast-wrong → box unchanged (rush, not gap)"
    if badge in ("LUCKY", "TRIV✓"):
        t["repair_confirms"] = 0
        return ("lucky-correct" if badge == "LUCKY" else "trivially-fast-correct") + " → no promote"
    if badge in ("✓_sure", "✓_think", "✓_plain"):
        if cur == "untested":
            t["state"] = "developing"                # a clean first correct → landing
        elif badge == "✓_sure" and calm and cur == "developing" and spaced and not caveat:
            t["state"] = "solid"                     # spaced + calm + confident = the only route to solid
        elif cur == "shaky":
            t["state"] = "developing"
        # else hold: developing without a spaced Sure stays developing; solid maintains
        capped = " (caveat capped at developing)" if (caveat and badge == "✓_sure" and cur == "developing") else ""
        return f"{badge.replace('_', ' ')} → {t['state']}{capped}"

    # ---- teach-back quality (graded) → the anti-fluency-illusion consequence ----
    if badge == "TB✓":                               # explained it well: genuine understanding
        if cur == "untested":
            t["state"] = "developing"
        elif cur == "developing" and spaced and not caveat:
            t["state"] = "solid"                     # a solid spaced teach-back is calm confident evidence → solid
        elif cur == "shaky":
            t["state"] = "developing"
        capped = " (caveat capped at developing)" if (caveat and cur == "developing") else ""
        return f"teach-back solid → {t['state']}{capped}"
    if badge == "TB~":                               # partial explanation: a landing, never a promotion
        if cur == "untested":
            t["state"] = "developing"
        return f"teach-back partial → {t['state']} (no promote)"
    if badge == "TB✗":                               # could not explain it → block promotion, hold the box
        return "teach-back failed → no promote (picked it but couldn't explain it — fluency illusion)"

    return None  # TB (ungraded) / SKIP — no box change


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #

def process(private_dir, dry_run=False):
    runs_path = os.path.join(private_dir, "work", "runs.json")
    state_path = os.path.join(private_dir, "work", "state.json")
    cursor_path = os.path.join(private_dir, "work", "state_writer_cursor.json")
    log_path = os.path.join(private_dir, "work", "state_writer_log.jsonl")

    blob = json.load(open(runs_path))
    runs = blob.get("runs", [])
    state = json.load(open(state_path))
    cursor = json.load(open(cursor_path)) if os.path.exists(cursor_path) else {"processed": []}
    processed = set(cursor.get("processed", []))

    medians = phase_medians([r for r in runs if r.get("canonical")])

    todo = [r for r in runs
            if r.get("canonical") and not r.get("is_test")
            and f"{r['student']}|{r.get('ts_raw')}" not in processed]
    todo.sort(key=lambda r: r.get("ts") or "")

    lines, audit, newest = [], [], state.get("generated")
    if not todo:
        return state, ["No new canonical runs to apply — state is current."], []

    for r in todo:
        s, tag, sd = r["student"], r.get("tag"), r.get("set_date")
        slotmap = load_plan(private_dir, s, sd)
        head = f"{s} · {tag} — set {sd}, run {r.get('run_date')}"
        lines.append("\n" + head)
        lines.append("-" * min(len(head), 96))
        if slotmap is None:
            lines.append(f"  ⚠ no persisted plan at plans/{s}/{sd}.json — cannot join to topics; SKIPPED.")
            continue
        if r.get("canonical_caveat"):
            lines.append(f"  ⚠ attempt {r.get('attempt')} is canonical-by-default — promotions capped at developing.")

        st = state["students"].get(s)
        # gather governing (badge, rel, q) per topic
        per_topic = {}
        for q in r["questions"]:
            sl = slotmap.get(q["id"])
            if not sl:
                continue
            topic = sl.get("topic")
            badge, rel = badge_for(q, medians, s, r["shell_flags"])
            per_topic.setdefault((sl["subject"], topic), []).append((badge, rel, q))

        touched = 0
        for (subject, topic), hits in per_topic.items():
            gov = min(hits, key=lambda h: PREC.index(h[0]) if h[0] in PREC else 99)
            badge, rel, q = gov
            t = find_topic(st, subject, topic)
            if t is None:
                lines.append(f"  · {subject}/{topic}: not in ledger — skipped (add via targets/state)")
                continue

            tested = badge not in ("SKIP",)
            prior_state, prior_repair = t.get("state"), bool(t.get("repair"))
            prior_lt = t.get("last_tested")
            spaced = bool(prior_lt and str(prior_lt) < str(r.get("run_date")))
            reason = transition(t, badge, rel, spaced, bool(r.get("canonical_caveat")))
            if reason is None:  # TB/SKIP
                if badge == "SKIP":
                    lines.append(f"  · {subject}/{topic}: fresh-skip — benched, not tested")
                continue

            if tested:
                t["times_seen"] = int(t.get("times_seen", 0)) + 1
                t["last_tested"] = r.get("run_date")
                t["last_result"] = {"date": r.get("run_date"), "badge": badge,
                                    "ok": q.get("ok"), "confidence": q.get("confidence"),
                                    "pace": rel or "n/a", "from": tag}
            touched += 1
            arrow = ""
            if (t.get("state") != prior_state) or (bool(t.get("repair")) != prior_repair):
                flag = "  [REPAIR]" if t.get("repair") else ("  [→ out of REPAIR]" if prior_repair else "")
                arrow = f"  {prior_state}{' (REPAIR)' if prior_repair else ''} → {t.get('state')}{flag}"
            else:
                arrow = f"  {t.get('state')} (held)"
            lines.append(f"  {badge:8} {subject}/{topic}{arrow}\n            ↳ {reason}")
            audit.append({"applied": not dry_run, "student": s, "set_date": sd, "run_date": r.get("run_date"),
                          "tag": tag, "subject": subject, "topic": topic, "badge": badge,
                          "from_state": prior_state, "to_state": t.get("state"),
                          "from_repair": prior_repair, "to_repair": bool(t.get("repair")), "reason": reason})

        lines.append(f"  → {touched} topic(s) updated.")
        processed.add(f"{s}|{r.get('ts_raw')}")
        if not newest or str(r.get("run_date")) > str(newest):
            newest = r.get("run_date")

    if not dry_run:
        state["generated"] = newest
        json.dump(state, open(state_path, "w"), indent=2, ensure_ascii=False)
        cursor["processed"] = sorted(processed)
        cursor["updated"] = date.today().isoformat()
        json.dump(cursor, open(cursor_path, "w"), indent=2, ensure_ascii=False)
        with open(log_path, "a") as lf:
            for a in audit:
                lf.write(json.dumps(a, ensure_ascii=False) + "\n")
        lines.append(f"\n✓ state.json updated (generated={newest}); {len(audit)} transitions logged.")
    else:
        lines.append(f"\n(DRY RUN — nothing written; would apply {len(audit)} transitions.)")
    return state, lines, audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    _, lines, _ = process(a.private_dir, dry_run=a.dry_run)
    print("=== state-writer: results → ledger ===")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
