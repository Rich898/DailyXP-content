#!/usr/bin/env python3
"""
depth_writer.py — the SOLO depth ladder's acting end, in SHADOW MODE.

UNDERSTANDING.md defines the second ledger axis: depth (the five-rung SOLO
ladder). grade_teachback.py measures it nightly; until now nothing acted on the
measurement. This module implements the ratified promotion/demotion rules —
deterministically, no API, no language — and in shadow mode writes ONLY to:

    {private}/work/depth_shadow.json         the shadow depth ledger
    {private}/work/depth_writer_cursor.json  which runs have been applied
    {private}/work/depth_writer_log.jsonl    an audit line per rung change

It NEVER opens state.json. That is the shadow guarantee: the confidence axis is
untouchable by construction, provable by byte-comparison. (Two-axes law: this
module never reads `state`, `repair`, or the confidence tap — depth evidence is
correctness + question identity + question type only.)

THE RULES IT IMPLEMENTS (UNDERSTANDING.md §3–§4, ratified 19–20 Aug 2026):

Ceilings — an item can only evidence the rungs it can honestly probe:
    transfer-tagged item        -> applies   (no such type exists yet; recognised
                                              here so the tag counts the day it ships)
    teach-back (graded)         -> connects  (the stricter of the doctrine's two
                                              readings — under-claim rule)
    reversed (`mech: reversed`) -> knows     (recognition in reverse, any phase)
    steady phase, clean correct -> lists     (MC and the typed steady types)
    speed phase / anything else -> knows

Evidence — only a CLEAN correct counts: lucky corrects, trivially-fast corrects,
integrity-held teach-backs and swipes (50/50 sorts) never evidence depth. The
confidence tap is ignored entirely (sure/think-so/plain are identical here).
A canonical-by-default repeat attempt (`canonical_caveat`) contributes NOTHING
except its graded teach-back — replayed picks are stale evidence; written
explanations are their own evidence.

Promotion — evidence at a rung proves everything below it, so a rung is set
directly (a first-ever teach-back graded `connects` takes the topic straight
there). `lists` by multiple-choice requires clean steady corrects on the topic
on TWO DIFFERENT SET DATES — the validator's no-repeat gate guarantees different
dates mean different prompts. A graded teach-back's rung is accepted as evidence
at that rung (capped at `connects`): the grader is the single depth instrument,
and its own caps under-claim already.

Demotion — deliberately reluctant: never on a single wrong answer, never from
REPAIR (which this module cannot even see). One rung down, only on repeated
failure at the rung's own evidence type: two consecutive graded teach-backs on a
`connects` topic coming back below `connects` demote it to `lists`, and the
counter resets (one rung per episode).

Join: same as the state writer — the persisted plan at
`{private}/plans/{student}/{set_date}.json` maps slot id -> topic. Runs with no
persisted plan are skipped, loudly. Idempotent via its own cursor; reuses
results_reader/state_writer classification so there is one source of doctrine
for what "lucky" and "trivially fast" mean.

Usage:
  python3 tools/depth_writer.py --private-dir ../DailyXP-private            # shadow apply
  python3 tools/depth_writer.py --private-dir ../DailyXP-private --dry-run  # preview only
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from results_reader import phase_medians                    # noqa: E402
from state_writer import badge_for, load_plan               # noqa: E402  (one source of doctrine)

LADDER = ["not_yet", "knows", "lists", "connects", "applies"]
RUNG = {r: i for i, r in enumerate(LADDER)}

# Clean-correct badges (state_writer's vocabulary). Confidence split is ignored
# on purpose — sure/think/plain are one and the same to the depth axis.
CLEAN_MC = {"✓_sure", "✓_think", "✓_plain"}
CLEAN_TYPED = {"NUM✓", "ORD✓", "TXT✓"}
# Never evidence: LUCKY, TRIV✓, SWIPE✓/✗, every wrong, every skip, ungraded TB.


def item_ceiling(slot, q, badge):
    """The highest rung this item could honestly evidence (UNDERSTANDING.md §3)."""
    mech = (slot.get("mech") or "").lower()
    if mech == "transfer" or slot.get("transfer") or q.get("transfer"):
        return "applies"
    if badge in ("TB✓", "TB~", "TB✗", "TB"):
        return "connects"
    if mech == "reversed":
        return "knows"
    if (q.get("phase") or slot.get("phase")) == "steady":
        return "lists"
    return "knows"


def tb_rung(grade):
    """The rung a graded teach-back evidences: the grader's own depth reading,
    capped at the teach ceiling. Held/ungraded/unrecognised -> None (no evidence)."""
    g = grade or {}
    if g.get("integrity_hold"):
        return None
    d = str(g.get("depth", "")).strip().lower()
    if d not in RUNG:
        return None
    return d if RUNG[d] <= RUNG["connects"] else "connects"


def get_topic(shadow_student, subject, topic):
    """Find-or-create the shadow entry. Absence == not_yet; entries are made
    lazily on first evidence so unevidenced topics never appear at all."""
    key_s, key_t = subject.strip(), topic.strip()
    for t in shadow_student["topics"]:
        if t["subject"] == key_s and t["topic"] == key_t:
            return t
    t = {"subject": key_s, "topic": key_t, "depth": "not_yet",
         "steady_dates": [], "tb_recent": []}
    shadow_student["topics"].append(t)
    return t


def apply_run_to_topic(t, hits, set_date, run_date, caveat):
    """Apply one run's evidence on one topic. Returns (old, new, why) or None.

    `hits` = [(badge, q, slot)] for every question that landed on this topic.
    Deterministic; reads nothing but its arguments.
    """
    old = t["depth"]
    best, why = old, None
    got_tb_grade = False

    for badge, q, slot in hits:
        ceiling = item_ceiling(slot, q, badge)

        # --- teach-back: the grader's rung is the evidence (caveat-immune) ---
        if badge in ("TB✓", "TB~", "TB✗"):
            rung = tb_rung(q.get("tb_grade"))
            if rung is None:
                continue
            got_tb_grade = True
            t["tb_recent"] = (t["tb_recent"] + [rung])[-2:]
            if RUNG[rung] > RUNG[best]:
                phrase = (q.get("tb_grade") or {}).get("evidence") or ""
                best, why = rung, f"teach-back graded '{rung}'" + (f" — \u201c{phrase}\u201d" if phrase else "")
            continue
        if badge == "TB":
            continue  # ungraded or integrity-held: no evidence, no demotion count

        # --- everything else: clean corrects only, and never on a caveat run ---
        if caveat or badge not in CLEAN_MC | CLEAN_TYPED:
            continue

        if ceiling == "applies":
            if RUNG["applies"] > RUNG[best]:
                best, why = "applies", "clean correct on a tagged transfer item"
            continue

        if ceiling == "lists":
            if set_date not in t["steady_dates"]:
                t["steady_dates"].append(set_date)
            if len(t["steady_dates"]) >= 2 and RUNG["lists"] > RUNG[best]:
                best, why = "lists", (f"clean steady corrects on {len(t['steady_dates'])} different set dates "
                                      "(no-repeat gate ⇒ different prompts)")
                continue

        if RUNG["knows"] > RUNG[best]:
            best, why = "knows", "one clean correct answer"

    # --- promotion: direct to the evidenced rung ---
    if RUNG[best] > RUNG[old]:
        t["depth"] = best
        t["depth_evidence"] = {"date": run_date, "why": why}
        return old, best, why

    # --- demotion: reluctant, one rung, teach-evidence only (v1: connects->lists) ---
    if (got_tb_grade and old == "connects" and len(t["tb_recent"]) == 2
            and all(RUNG[r] < RUNG["connects"] for r in t["tb_recent"])):
        t["depth"] = "lists"
        t["tb_recent"] = []  # one rung per episode; the count restarts
        why = "two consecutive teach-backs came back below 'connects'"
        t["depth_evidence"] = {"date": run_date, "why": why}
        return old, "lists", why

    return None


def process(private_dir, dry_run=False):
    runs_path = os.path.join(private_dir, "work", "runs.json")
    shadow_path = os.path.join(private_dir, "work", "depth_shadow.json")
    cursor_path = os.path.join(private_dir, "work", "depth_writer_cursor.json")
    log_path = os.path.join(private_dir, "work", "depth_writer_log.jsonl")

    runs = json.load(open(runs_path)).get("runs", [])
    shadow = (json.load(open(shadow_path)) if os.path.exists(shadow_path)
              else {"mode": "shadow", "students": {}})
    cursor = json.load(open(cursor_path)) if os.path.exists(cursor_path) else {"processed": []}
    processed = set(cursor.get("processed", []))

    medians = phase_medians([r for r in runs if r.get("canonical")])
    todo = [r for r in runs
            if r.get("canonical") and not r.get("is_test")
            and f"{r['student']}|{r.get('ts_raw')}" not in processed]
    todo.sort(key=lambda r: r.get("ts") or "")

    lines, audit = [], []
    if not todo:
        return shadow, ["No new canonical runs to apply — depth shadow is current."], []

    for r in todo:
        s, sd = r["student"], r.get("set_date")
        slotmap = load_plan(private_dir, s, sd)
        head = f"{s} · {r.get('tag')} — set {sd}, run {r.get('run_date')} [shadow]"
        lines.append("\n" + head)
        lines.append("-" * min(len(head), 96))
        if slotmap is None:
            lines.append(f"  ⚠ no persisted plan at plans/{s}/{sd}.json — permanently unjoinable; "
                         "its evidence is unreachable and it will not be raised again.")
            processed.add(f"{s}|{r.get('ts_raw')}")
            continue
        caveat = bool(r.get("canonical_caveat"))
        if caveat:
            lines.append("  ⚠ repeat-attempt caveat — only graded teach-backs count for depth tonight.")

        stu = shadow["students"].setdefault(s, {"topics": []})
        per_topic = {}
        for q in r["questions"]:
            sl = slotmap.get(q["id"])
            if not sl:
                continue
            badge, _rel = badge_for(q, medians, s, r.get("shell_flags") or {})
            per_topic.setdefault((sl["subject"], sl.get("topic")), []).append((badge, q, sl))

        # A teach-back with text but no grade yet: the grade may still be coming (the nightly
        # grader scans the backlog). Pre-scan and, if found, apply NOTHING from this run and
        # leave it un-cursored, so the whole run is applied exactly once — the night its grade
        # lands. (Applying the rest now and re-applying later would double-count evidence.)
        awaiting_grade = any(
            badge == "TB" and (q.get("text") or "").strip() and not q.get("tb_grade")
            and (q.get("tb_integrity") or {}).get("verdict") != "quarantine"
            for hits in per_topic.values() for badge, q, _sl in hits)
        # (Quarantined text is never sent for grading — its grade will never come, so it
        # must not park the run. It simply contributes nothing, same as the state writer.)
        if awaiting_grade:
            lines.append("  ⏳ teach-back written but not yet graded — run left unprocessed; "
                         "it will be applied in full the night its grade lands.")
            continue

        moved = 0
        for (subject, topic), hits in sorted(per_topic.items()):
            if not topic:
                continue
            t = get_topic(stu, subject, topic)
            change = apply_run_to_topic(t, hits, sd, r.get("run_date"), caveat)
            if change:
                old, new, why = change
                moved += 1
                lines.append(f"  · {subject}/{topic}: {old} → {new}  ({why})")
                audit.append({"ts": datetime.now(timezone.utc).isoformat(), "student": s,
                              "subject": subject, "topic": topic, "from": old, "to": new,
                              "run_date": r.get("run_date"), "set_date": sd, "why": why})
        if not moved:
            lines.append("  · no rung movement (depth moves in weeks by design)")
        processed.add(f"{s}|{r.get('ts_raw')}")

    if not dry_run:
        shadow["generated"] = datetime.now(timezone.utc).isoformat()
        json.dump(shadow, open(shadow_path, "w"), indent=2, ensure_ascii=False)
        json.dump({"processed": sorted(processed)}, open(cursor_path, "w"), indent=2)
        with open(log_path, "a") as f:
            for a in audit:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
    return shadow, lines, audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    _shadow, lines, audit = process(args.private_dir, dry_run=args.dry_run)
    print("\n".join(lines))
    print(f"\n{'DRY RUN — nothing written.' if args.dry_run else 'Shadow updated.'} "
          f"{len(audit)} rung change(s).")


if __name__ == "__main__":
    main()
