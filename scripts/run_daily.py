#!/usr/bin/env python3
"""
run_daily.py — the daily pipeline (the cron's spine).

For a school day, for each boy: derive the tag -> PLAN (planner) -> COMPOSE
(API) -> PUBLISH (validate+write+archive+commit+VERIFY). A FROZEN boy yields a
placeholder (no API call). Weekends are skipped.

SMS lives ELSEWHERE now (comms are decoupled from publish, by design):
  kid "it's up" nudge  -> tools/kid_nudge.py, 4pm job (kid-nudge.yml) —
                          verifies the LIVE set is today's before texting, so
                          a review HOLD never texts a promise not kept.
  parent soundbyte     -> tools/soundbyte.py, evening polls (evening-soundbyte.yml).

State ingestion (reading results, updating the ledger/state) is deliberately a
STUB here — this week that stays human-reviewed: the reader's output is applied
to the private ledger/state by hand, then committed, so state.json is current
before this runs. That matches the roadmap's "reports/state human-reviewed
initially; flip to full auto once boringly reliable."

Layout (in Actions, both repos are checked out):
  public checkout  = this repo (code + live y8/y9.json + publish target)
  private checkout = ledger/state/targets/history       (--private-dir)

Env / secrets consumed downstream:
  ANTHROPIC_API_KEY            compose
  DAILYXP_TOKEN / ~/.ghtoken   publish (push both repos)
  DAILYXP_HISTORY_DIR          set here -> private history (archive + no-repeat)

Usage:
  python3 scripts/run_daily.py --private-dir ../DailyXP-private
  python3 scripts/run_daily.py --private-dir ../DailyXP-private --date 2026-08-06 \
        --student y8 --dry-run          # shadow-run one boy, no publish
"""
import argparse
import datetime as dt
import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))

W1_MONDAY = dt.date(2026, 7, 27)          # project week 1 = w/c Mon 27 Jul 2026
MAX_REVIEW_ROUNDS = 2                      # recompose a flagged slot at most twice, then HOLD (never publish a flagged set)
# Weekly skeleton: Mon–Thu standard, Fri Battleground. (Blitz retired 20 Aug 2026 —
# Reversed is becoming a daily question-type mechanic, not a Wednesday event.)
WEEKDAY_DIRECTIVE = {0: "standard", 1: "standard", 2: "standard", 3: "standard", 4: "boss"}
# (Kid nudge texts moved to tools/kid_nudge.py — the 4pm job owns them.)


def derive_tag(student, date):
    import roster
    week = ((date - W1_MONDAY).days // 7) + 1
    wd = date.weekday() + 1                 # Mon=1..Fri=5
    tag = f"{roster.tag_initial(student)}{week}.{wd}"
    if wd == 5:
        tag += " · BATTLEGROUND"
    return tag, week, wd


def run(date, students, private_dir, directives_override, dry_run, push):
    import planner
    import compose
    import review
    import publish as pub
    from validate import seen_prompts

    if date.weekday() > 4:
        print(f"{date} is a weekend — no run.")
        return 0

    # STEP 0 — INGEST: refresh runs.json from the results Sheet (headless). Gated on RESULTS_URL
    # so local/offline runs skip it and use the committed runs.json. The endpoint is a read-only
    # doGet (never the quiz webhook). Network lives in Actions, not here.
    if (os.environ.get("RESULTS_URL") and os.environ.get("RESULTS_KEY")) or (
            os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SERVICE_KEY")):
        try:
            import ingest_results
            summary, ing_errors = ingest_results.ingest(
                private_dir, os.environ.get("RESULTS_URL"), os.environ.get("RESULTS_KEY"),
                sb_url=os.environ.get("SUPABASE_URL"),
                sb_key=os.environ.get("SUPABASE_SERVICE_KEY"),
                source=os.environ.get("INGEST_SOURCE"))
            print(f"--- ingest results (sink → runs.json) ---\n{summary}")
            for e in ing_errors:
                print(f"  ⚠ {e}")
            print("------------------------------------------\n")
        except SystemExit as e:
            print(f"⚠ ingestion skipped ({e}) — using existing runs.json.\n")
        except Exception as e:
            print(f"⚠ ingestion step failed ({e}) — using existing runs.json.\n")

    # RETURN LEG (roadmap #2): bring the ledger current from results BEFORE we plan.
    # Idempotent (cursor) — a no-op when there are no new canonical runs. It needs runs.json
    # refreshed from the Sheet first; that ingestion is still manual until the Apps Script / CSV
    # job lands, so for now this applies only what's already in runs.json. Dry-run previews only.
    if os.environ.get("DAILYXP_SKIP_STATE_WRITE") != "1" and \
       os.path.exists(os.path.join(private_dir, "work", "runs.json")):
        # TEACH-BACK GRADE: the one language judgement in ingestion. Annotates runs.json with a
        # per-teach-back verdict (grade_teachback) so the state-writer's deterministic consequence
        # engine can act on it. Skipped without an API key or via DAILYXP_SKIP_TB_GRADE; on failure
        # the teach-back is simply left ungraded (state-writer falls back to the old no-op).
        if os.environ.get("DAILYXP_SKIP_TB_GRADE") != "1" and os.environ.get("ANTHROPIC_API_KEY"):
            try:
                import grade_teachback
                g, sk, fl, glog = grade_teachback.annotate_runs(private_dir, dry_run=dry_run)
                if glog:
                    print("--- teach-back grade ---")
                    print("\n".join(glog))
                    print(f"(graded {g} · already-graded {sk} · failed {fl})")
                    print("------------------------\n")
            except Exception as e:
                print(f"⚠ teach-back grade step failed ({e}) — teach-backs left ungraded.\n")
        try:
            import state_writer
            _, sw_lines, _ = state_writer.process(private_dir, dry_run=dry_run)
            print("--- results → ledger (state-writer) ---")
            print("\n".join(sw_lines))
            print("---------------------------------------\n")
        except Exception as e:
            print(f"⚠ state-writer step failed ({e}) — proceeding with state.json as-is.\n")

    # ACHIEVEMENTS: badge the ledger from the just-updated state/log (ACHIEVEMENTS.md).
    # Deterministic + idempotent; feeds the in-quiz screen and the kid dashboard. Dry-run previews.
    if os.environ.get("DAILYXP_SKIP_ACHIEVEMENTS") != "1" and \
       os.path.exists(os.path.join(private_dir, "work", "runs.json")):
        try:
            import achievements
            awarded, ach_lines = achievements.process(private_dir, dry_run=dry_run)
            print("--- achievements (badge the ledger) ---")
            print("\n".join(ach_lines))
            print("---------------------------------------\n")
        except Exception as e:
            print(f"⚠ achievements step failed ({e}) — continuing.\n")

    # point archive + no-repeat at the PRIVATE history; load private state + targets
    hist = os.path.join(private_dir, "history")
    os.environ["DAILYXP_HISTORY_DIR"] = hist
    state = json.load(open(os.path.join(private_dir, "work", "state.json")))
    # pick the newest targets file in the private repo
    tdir = os.path.join(private_dir, "targets")
    tfiles = sorted(f for f in os.listdir(tdir) if f.endswith(".json"))
    targets = json.load(open(os.path.join(tdir, tfiles[-1])))
    # Loud about staleness: a forgotten weekly sweep should be visible, never silent.
    try:
        t_age = (date - dt.date.fromisoformat(tfiles[-1][:10])).days
        print(f"targets: {tfiles[-1]}" + (f"  \u26a0 {t_age} days old \u2014 has the weekly sweep run?" if t_age > 7 else ""))
    except Exception:
        print(f"targets: {tfiles[-1]}")

    # Test/aliased players (roster targets_alias) quiz another student's
    # curriculum: inject the alias's targets block under their own code, so the
    # planner needs no knowledge of aliasing.
    import roster as _roster
    for _s in students:
        _al = _roster.targets_alias(_s)
        if _al != _s and _s not in targets.get("students", {}) and _al in targets.get("students", {}):
            targets["students"][_s] = targets["students"][_al]
            print(f"targets: {_s} aliased to {_al}'s curriculum (roster).")

    # SEED THE MENU (locked 20 Aug 2026 — outline-drives-the-quiz doctrine): write every scraped
    # topic into the ledger, stamped with the week it first appeared, so the planner fills
    # THIS-WEEK-FIRST from the whole covered curriculum instead of starving on a thin "due" list.
    # Additive + idempotent: adds new topics as `untested`, back-stamps the week, never touches mastery.
    import seed_menu as _seed
    for _s in students:
        _al = _roster.targets_alias(_s)
        _rep = _seed.seed_player(state, _s, _al, tdir)
        if _rep["added"] or _rep["stamped_existing"]:
            print(f"[{_s}] menu seed: +{len(_rep['added'])} new topics, {_rep['stamped_existing']} "
                  f"back-stamped (ledger {_rep['ledger_before']}→{_rep['ledger_after']}, menu {_rep['menu_size']}).")

    day = date.strftime("%a").upper()
    print(f"=== DailyXP run — {day} {date} {'(DRY RUN)' if dry_run else ''} ===")
    ingest_on = bool(os.environ.get("RESULTS_URL") and os.environ.get("RESULTS_KEY"))
    print("NOTE: full loop — ingest (Sheet→runs.json) → state-writer (results→ledger) → plan → "
          "compose → review → publish. Ingestion is "
          + ("ON (RESULTS_URL configured)." if ingest_on else "OFF here (no RESULTS_URL — using committed runs.json).") + "\n")

    summary = []
    for s in students:
        tag, week, wd = derive_tag(s, date)
        directive = directives_override.get(s) or WEEKDAY_DIRECTIVE.get(date.weekday(), "standard")
        plan = planner.plan_set(s, date.isoformat(), day, tag, targets, state, directive)

        # Persist the plan (slot→topic/intent/phase) into the PRIVATE repo. This is the join
        # the feedback loop needs: a result question carries id+subject but not topic; the plan
        # is the authority on which topic each slot tested. Kept private (never in the public
        # quiz file). Written for FROZEN/dry-run too, so shadow-runs and the writer stay honest.
        try:
            pdir = os.path.join(private_dir, "plans", s)
            os.makedirs(pdir, exist_ok=True)
            with open(os.path.join(pdir, f"{date.isoformat()}.json"), "w") as pf:
                json.dump({"student": s, "set_date": date.isoformat(), "tag": tag, "day": day,
                           "directive": directive, "slots": plan.get("slots", [])},
                          pf, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[{s}] ⚠ could not persist plan ({e}) — results→topic join will miss this run.")

        if plan.get("status_gate") == "FROZEN":
            print(f"[{s}] {tag}: FROZEN → placeholder (no compose).")
            cset = {"student": s, "status": "placeholder", "date": date.isoformat(),
                    "day": "", "title": "DailyXP", "questions": []}
            errs = []
        else:
            print(f"[{s}] {tag}: planning {plan['shape']} ({directive}) → composing…")
            cset, errs = compose.compose_set(plan, model=os.environ.get("DAILYXP_MODEL", compose.DEFAULT_MODEL),
                                             history_dir=hist)
            if cset is None:
                print(f"[{s}] COMPOSE FAILED — {errs}. Skipping publish (yesterday's set stays live).")
                summary.append((s, tag, "compose-failed"))
                continue

        # ---- SECOND-PASS REVIEW (roadmap #1): the gate the validator can't be ----
        # The validator proved the schema; this reads MEANING (a distractor that's also
        # true, a false `why`, off-syllabus, trivially-easy). On a BLOCK, recompose only
        # the flagged slots and re-review; if it still won't clear after MAX_REVIEW_ROUNDS,
        # HOLD (leave yesterday's set live). Two hard rules: never publish a flagged set,
        # never fail silently. Runs in dry-run too, so shadow-runs exercise the gate.
        if os.environ.get("DAILYXP_SKIP_REVIEW") == "1":
            print(f"[{s}] {tag}: ⚠ REVIEW SKIPPED (DAILYXP_SKIP_REVIEW=1) — publishing UNREVIEWED.")
        elif cset.get("status") != "placeholder" and cset.get("questions"):
            curric = review.curriculum_context(targets, s)
            base_seen = set(seen_prompts(s, hist))
            rounds = 0
            verdict, verr = review.review_set(cset, curriculum=curric)
            while verdict and not verdict["ok"] and rounds < MAX_REVIEW_ROUNDS:
                bad = verdict["blocking"]
                print(f"[{s}] {tag}: REVIEW round {rounds+1} — {len(bad)} blocking, recomposing {bad}")
                for sid, f in verdict["flags"].items():
                    print(f"        ⛔ {sid} [{','.join(f['categories'])}] {f['note']}")
                bad_set = set(bad)
                # Feed review's SPECIFIC objection back into each flagged slot's guidance, so compose
                # fixes exactly what was wrong instead of regenerating blind (a blind retry tends to
                # reproduce subtle errors — a misattributed quote, an ambiguous controlled variable).
                flags = verdict.get("flags", {})
                recompose_slots = []
                for sl in plan["slots"]:
                    if sl["slot"] in bad_set:
                        fl = flags.get(sl["slot"], {})
                        note = (fl.get("note") or "").strip()
                        cats = ",".join(fl.get("categories", []))
                        if note:
                            sl = {**sl, "guidance": (
                                (sl.get("guidance", "").strip() + " ").lstrip()
                                + f"REVIEW REJECTED the previous version [{cats}]: {note} "
                                  "Write a corrected question that fixes exactly this problem.").strip()}
                        recompose_slots.append(sl)
                # compose validates a WHOLE set (it requires exactly one teach slot, because the shell
                # unconditionally enters the teach screen). If no teach slot is among the flagged ones,
                # borrow it for context so the mini-set is valid — then swap back ONLY the flagged slots.
                if not any(sl.get("phase") == "teach" for sl in recompose_slots):
                    _teach = next((sl for sl in plan["slots"] if sl.get("phase") == "teach"), None)
                    if _teach:
                        recompose_slots = recompose_slots + [_teach]
                reduced = {**plan, "slots": recompose_slots}
                kept = {q["prompt"] for q in cset["questions"] if q["id"] not in bad_set}
                sub, serr = compose.compose_set(
                    reduced, seen=base_seen | kept,
                    model=os.environ.get("DAILYXP_MODEL", compose.DEFAULT_MODEL), history_dir=hist)
                if sub is None:
                    print(f"[{s}] recompose of {bad} FAILED: {serr}")
                    break
                repl = {q["id"]: q for q in sub["questions"] if q["id"] in bad_set}  # only the flagged slots
                cset["questions"] = [repl.get(q["id"], q) for q in cset["questions"]]
                rounds += 1
                verdict, verr = review.review_set(cset, curriculum=curric)

            if verr or verdict is None:
                # fail-safe: no verdict = unknown safety → do NOT publish (yesterday's stays live)
                print(f"[{s}] {tag}: REVIEW UNAVAILABLE ({verr}) — holding; yesterday's set stays live.")
                summary.append((s, tag, "held-review-error"))
                continue
            review.print_verdict(verdict)
            if not verdict["ok"]:
                print(f"[{s}] {tag}: REVIEW HOLD — {verdict['blocking']} still blocking after {rounds} "
                      f"recompose round(s). NOT publishing; yesterday's set stays live. Needs a human.")
                summary.append((s, tag, f"held-review:{','.join(verdict['blocking'])}"))
                continue

        if dry_run:
            if cset.get("status") == "placeholder":
                print(f"[{s}] {tag}: placeholder (nothing to compose).")
            else:
                print(f"[{s}] {tag}: composed {len(cset['questions'])} Qs (DRY RUN — not published):")
                for q in cset["questions"]:
                    line = f"    {q['id']:<4} [{q['phase']}/{q['subject']}] {q['prompt']}"
                    print(line)
                    if q.get("options"):
                        print(f"         options: {q['options']}   → answer: {q.get('answer')!r}")
                        print(f"         why: {q.get('why','')}")
            os.makedirs(os.path.join(REPO, "work"), exist_ok=True)
            json.dump(cset, open(os.path.join(REPO, "work", f"dryrun_{s}.json"), "w"), indent=2, ensure_ascii=False)
            summary.append((s, tag, "dry-run-ok"))
            continue

        # PUBLISH (validate→write→archive→commit→verify)
        tmp = os.path.join(REPO, "work", f"set_{s}.json")
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        json.dump(cset, open(tmp, "w"), indent=2, ensure_ascii=False)
        rc = pub.publish(tmp, push=push)
        if rc != 0:
            summary.append((s, tag, f"publish-rc{rc}"))
            continue

        # (No SMS here — the 4pm kid-nudge job verifies the live set, then texts.)
        summary.append((s, tag, "published"))

    print("\n=== summary ===")
    for s, tag, st in summary:
        print(f"  {s}  {tag:<16} {st}")
    # NOTE: after a real run, commit the private repo (updated history archive + any state
    # writes) back — handled by the workflow's 'commit private' step.
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True, help="path to the DailyXP-private checkout")
    ap.add_argument("--date", default=dt.date.today().isoformat())
    import roster
    _codes = roster.active()
    ap.add_argument("--student", choices=_codes, help="run a single player (default: all active)")
    for _c in _codes:
        ap.add_argument(f"--directive-{_c}", default=None)
    ap.add_argument("--dry-run", action="store_true", help="plan+compose only; no publish")
    ap.add_argument("--no-push", action="store_true", help="publish locally but don't git push")
    a = ap.parse_args()
    date = dt.date.fromisoformat(a.date)
    students = [a.student] if a.student else _codes
    overrides = {}
    for _c in _codes:
        v = getattr(a, f"directive_{_c}".replace("-", "_"), None)
        if v:
            overrides[_c] = v
    sys.exit(run(date, students, a.private_dir, overrides, dry_run=a.dry_run, push=not a.no_push))


if __name__ == "__main__":
    main()
