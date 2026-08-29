#!/usr/bin/env python3
"""
friday_report_run.py — the Friday job. One entry point, mirroring the shape of
the other comms runners: build deterministic facts -> render page -> deploy ->
compose SMS (AI + law validator + deterministic fallback) -> send -> advance
cursor -> snapshot state for NEXT week's trajectory.

ORDER MATTERS. The page is deployed and VERIFIED LIVE before the SMS is sent —
a text linking to a 404 is worse than no text. If deploy fails, the SMS still
goes (the SMS is the tier-1 report by doctrine) but without the link.

CURSOR: one send per kid per week. Re-running is a no-op for anyone already
sent, so a manual re-dispatch after a partial failure is always safe.

WEEKLY SNAPSHOT: writes this week's per-topic states to
work/report_snapshots/<week_of>.json. That file IS what makes next Friday's
trajectory and depth-movement computable — week 1 has no prior precisely
because no snapshot exists yet.

Usage:
  python tools/friday_report_run.py --private-dir ../DailyXP-private [--dry-run]
                                    [--student y8] [--date 2026-08-14]
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import friday_report as fr          # noqa: E402
import friday_sms as fsms           # noqa: E402
import kid_wrap as kw               # noqa: E402
import report_page as rpage         # noqa: E402
import report_stories as rst        # noqa: E402
import netlify_deploy as deploy     # noqa: E402
import notify                       # noqa: E402
import roster                       # noqa: E402
from planner import load_targets_for  # noqa: E402

CURSOR = os.path.join("work", "friday_report_cursor.json")
SNAPDIR = os.path.join("work", "report_snapshots")
SLUGS = os.path.join("work", "report_slugs.json")


def load_json(p, default=None):
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return default


def week_of(d):
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def slugs_for(private_dir, codes):
    """Stable per-kid unguessable path segments. Generated once, then reused so
    a parent's bookmark keeps working; stored private, never in the public repo.

    New slugs are token_hex — naturally lowercase (72 bits) — because Netlify's
    paths are case-normalised and mixed-case slugs caused the 28 Aug stale-page
    collision (see netlify_deploy.url_for). Existing mixed-case slugs keep
    working: every layer lowercases them at use, and mixed-case links 301."""
    import secrets
    p = os.path.join(private_dir, SLUGS)
    data = load_json(p, {}) or {}
    changed = False
    for c in codes:
        if c not in data:
            data[c] = {"report": secrets.token_hex(9), "wrap": secrets.token_hex(9)}
            changed = True
    if changed:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(data, open(p, "w"), indent=2)
    return data


def plans_for(private_dir, code):
    out = {}
    for f in glob.glob(os.path.join(private_dir, "plans", code, "*.json")):
        p = load_json(f)
        if p and p.get("set_date"):
            out[p["set_date"]] = p
    return out


def newest_targets(private_dir):
    files = sorted(glob.glob(os.path.join(private_dir, "targets", "*.json")))
    return load_json(files[-1], {}) if files else {}


def build_for(code, asof, private_dir, runs, state, targets, prev_snapshot):
    """Everything one kid's Friday needs: fact card, stories, quote, accuracy."""
    topics = state["students"][code]["topics"]
    tmap, subjects_block = load_targets_for(code, targets)
    plans = plans_for(private_dir, code)
    days, _ = fr.week_days(asof)
    baseline = not prev_snapshot
    prev_states = (prev_snapshot or {}).get(code, {})

    earned = load_json(os.path.join(private_dir, "work", "achievements_earned.json"), {}) or {}
    mine = (earned.get(code) or {}).get("earned", [])
    this_week = [b for b in mine if (b.get("date") or "") in days]

    # Completion record: lets the activity row and week-word excuse days the
    # pipeline didn't publish or the seat was recorded absent (either location;
    # absent file = excuse nothing, the pre-fix behaviour).
    schedule = (load_json(os.path.join(private_dir, "schedule.json"))
                or load_json(os.path.join(private_dir, "work", "schedule.json")))

    card = fr.build_card(code, runs, topics, tmap, asof,
                         prev_states=prev_states,
                         earned_this_week=this_week, baseline=baseline,
                         schedule=schedule)
    stories = rst.build_stories(private_dir, runs, plans, code, days, topics,
                                depth_before=(prev_snapshot or {}).get(code + "_depth", {}))
    # The subject spine (V2 §3): reorganises the same facts by subject. traces =
    # what his sets actually worked this week (never intent); fluency = the
    # held-promotion safeguard, narrated when it fired.
    traces = rst.topic_traces(runs, plans, code, days)
    subjects = rst.subject_blocks(topics, subjects_block, stories, traces, prev_states)
    fluency = rst.fluency_catch(runs, plans, code, days)
    quote = rst.pick_quote(runs, code, days)
    acc = rst.subject_accuracy(runs, code, days)
    _, prev_days = fr.week_days(asof)
    speed = rst.speed_shift(runs, code, days, prev_days)
    wow = rst.week_over_week(runs, code, days, prev_days, topics,
                             (prev_snapshot or {}).get(code + "_depth", {}),
                             baseline=baseline)

    notes = []
    held = any((q.get("tb_integrity") or {}).get("verdict") == "quarantine"
               for r in runs if r.get("student") == code
               for q in r.get("questions", []))
    if held:
        notes.append("One written answer this week was left out of the figures: it "
                     "didn't read as this student's own writing, so it isn't counted "
                     "or quoted here.")
    return card, stories, quote, acc, notes, speed, wow, subjects, fluency


def build_wrap(code, card, stories, quote, acc, asof, priv, runs, state, api_key):
    """The kid's wrap HTML (KID-REPORT.md surface C), built from the SAME card /
    stories / quote objects the parent report uses — the transparency law made
    executable: the wrap re-dresses those facts and ADDS the game layer
    (game_facts) + coaching; it never computes its own week facts and never
    subtracts one. Returns the HTML, or None if a fact is missing or render()
    refuses the page on a language-law breach — a missing wrap must never block
    the parent report, which is the tier-1 surface."""
    try:
        days, _ = fr.week_days(asof)
        earned = load_json(os.path.join(priv, "work", "achievements_earned.json"), {}) or {}
        mine = (earned.get(code) or {}).get("earned", [])
        this_week = [b for b in mine if (b.get("date") or "") in days]
        topics = state.get("students", {}).get(code, {}).get("topics", [])
        game = kw.game_facts(runs, code, days, this_week, asof,
                             season_total=card.get("xp_total", 0),
                             accuracy=acc, earned_all=mine, topics=topics)
        targets = kw.targets_from(card, stories)
        coaching, _src = kw.compose_coaching(targets, api_key=api_key)
        return kw.render(card, stories=stories, quote=quote, game=game, coaching=coaching)
    except (ValueError, KeyError, TypeError) as e:
        # codes only in the public log
        print(f"  wrap skipped ({type(e).__name__}) — report sends without it.")
        return None


def _send_and_mark(code, body, cursor, wk, sent, skipped):
    """Send one parent report and advance the weekly cursor ONLY on real success.

    send_sms returns (ok, detail): ok is False on a transport failure OR a
    per-message rejection inside a 2xx body. Gating on ok is the fix — a
    non-empty tuple is always truthy, so the old `if notify.send_sms(...)`
    advanced the cursor even on a hard failure, marking a silently-unsent
    report as sent and skipping retry. detail can echo the number/message, so
    only a coarse, PII-free reason reaches the public Actions log.
    """
    ok, detail = notify.send_sms(f"parents:{code}", body)
    if ok:
        cursor[code] = wk
        sent.append(code)
        print("  SENT ✓")
        return True
    reason = (detail or "unknown").splitlines()[0].split(":", 1)[0][:48]
    print(f"  SEND FAILED ({reason}) — cursor not advanced, safe to re-run.")
    skipped.append(code)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--student", help="one player (default: all active)")
    ap.add_argument("--dry-run", action="store_true", help="build + render, no deploy, no SMS")
    ap.add_argument("--no-sms", action="store_true", help="deploy but don't text")
    ap.add_argument("--redeploy", action="store_true",
                    help="re-render + re-deploy the pages for an ALREADY-SENT week: "
                         "ignores the sent-cursor no-op, forces --no-sms, and touches "
                         "no private state (no cursor, no snapshot). The recovery "
                         "button for a bad/stale live page after the texts went out.")
    a = ap.parse_args()
    if a.redeploy:
        a.no_sms = True

    asof = dt.date.fromisoformat(a.date)
    priv = a.private_dir
    codes = [a.student] if a.student else roster.active()
    wk = week_of(asof)

    runs = (load_json(os.path.join(priv, "work", "runs.json"), {}) or {}).get("runs", [])
    state = load_json(os.path.join(priv, "work", "state.json"), {}) or {}
    targets = newest_targets(priv)

    # prior snapshot = trajectory source. Absent -> week 1 baseline.
    snaps = sorted(glob.glob(os.path.join(priv, SNAPDIR, "*.json")))
    prev_snapshot = load_json(snaps[-1]) if snaps else None
    if prev_snapshot and prev_snapshot.get("week_of") == wk:
        prev_snapshot = load_json(snaps[-2]) if len(snaps) > 1 else None

    cursor = load_json(os.path.join(priv, CURSOR), {}) or {}
    slugs = slugs_for(priv, codes)
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    sent, skipped = [], []
    for code in codes:
        if cursor.get(code) == wk and not a.redeploy:
            print(f"[{code}] already sent for week {wk} — no-op.")
            skipped.append(code)
            continue
        if code not in state.get("students", {}):
            print(f"[{code}] no ledger — skipped.")
            continue

        card, stories, quote, acc, notes, speed, wow, subjects, fluency = build_for(
            code, asof, priv, runs, state, targets, prev_snapshot)
        # PUBLIC LOG: codes only. This repo is public, so Actions logs are too —
        # first names and per-kid report URLs are PII/access and never print here
        # (the pre-29-Aug format leaked both; those slugs rotate as follow-up).
        print(f"[{code}] week-word={card['week_word']['word']} "
              f"stories={len(stories)} quote={'y' if quote else 'n'} "
              f"baseline={card['baseline']}")

        wrap_url = deploy.url_for(slugs[code]["wrap"], kind="w")
        report_url = deploy.url_for(slugs[code]["report"], kind="r")
        wrap_html = build_wrap(code, card, stories, quote, acc, asof,
                               priv, runs, state, api_key)

        if a.dry_run:
            # Wrap preview FIRST (KID-REPORT surface), collected by the workflow's
            # widened preview_* artifact. The report preview links nothing live.
            if wrap_html:
                wp = os.path.join(priv, "work", f"preview_wrap_{code}.html")
                open(wp, "w").write(wrap_html)
                print(f"  DRY-RUN wrap -> {wp}")
            html = rpage.render(card, stories=stories, quote=quote, accuracy=acc,
                                kid_wrap_url=None, extra_notes=notes, speed=speed,
                                wow=wow, subjects=subjects, fluency=fluency)
            out = os.path.join(priv, "work", f"preview_report_{code}.html")
            open(out, "w").write(html)
            body, src = fsms.render_body(card, report_url, api_key=api_key,
                                         use_ai=bool(api_key))
            # Body carries the kid's name + report URL — it goes to a preview
            # file (collected by the workflow's dry-run artifact), never the log.
            out_sms = os.path.join(priv, "work", f"preview_report_{code}.sms.txt")
            open(out_sms, "w").write(body)
            print(f"  DRY-RUN page -> {out}")
            print(f"  DRY-RUN sms  [{src}] {len(body)} chars -> {out_sms}")
            continue

        # LIVE: publish the wrap BEFORE the report and link it only if it
        # verified live (publish demands the wrap's own build stamp back from
        # the URL) — a report must never point at a 404 wrap.
        kid_wrap_url = None
        if wrap_html:
            if deploy.publish(slugs[code]["wrap"], wrap_html, kind="w"):
                kid_wrap_url = wrap_url
                print("  wrap LIVE ✓ (per-kid URL withheld from public log)")
            else:
                print("  wrap deploy FAILED — report sends without the wrap link.")
        html = rpage.render(card, stories=stories, quote=quote, accuracy=acc,
                            kid_wrap_url=kid_wrap_url, extra_notes=notes,
                            speed=speed, wow=wow, subjects=subjects, fluency=fluency)
        live = deploy.publish(slugs[code]["report"], html, kind="r")
        if live:
            print("  page LIVE ✓ (per-kid URL withheld from public log)")
        else:
            print("  page deploy FAILED — sending SMS without the link "
                  "(the SMS is the tier-1 report).")
            report_url = None

        body, src = fsms.render_body(card, report_url, api_key=api_key,
                                     use_ai=bool(api_key))
        ok, why = fsms.validate(body, card["name"], report_url)
        if not ok:
            print(f"  ABORT {code}: body failed the law ({why}) — nothing sent.")
            continue
        print(f"  sms [{src}] {len(body)} chars")
        # SAFETY: this job texts PARENTS. If the parent seat is unresolved we
        # abort rather than let notify fall through to any other recipient — a
        # parent report landing on the kid's phone would be a serious breach of
        # the no-ammunition law (he'd read the gaps written for an adult).
        seat = f"parents:{code}"
        if not notify._recipients(seat):
            print(f"  ABORT {code}: no number configured for {seat} "
                  f"(set MOBILE_MESSAGE_PARENTS_{code.upper()}) — nothing sent.")
            continue
        if a.no_sms:
            print("  --no-sms: not sending.")
            continue
        _send_and_mark(code, body, cursor, wk, sent, skipped)

    if not a.dry_run and not a.redeploy:
        cp = os.path.join(priv, CURSOR)
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        json.dump(cursor, open(cp, "w"), indent=2)

        # THE SNAPSHOT: this is what makes next Friday's trajectory possible.
        snap = {"week_of": wk, "written": dt.datetime.utcnow().isoformat() + "Z"}
        for code in state.get("students", {}):
            tops = state["students"][code]["topics"]
            snap[code] = {t.get("topic"): t.get("state") for t in tops}
            snap[code + "_depth"] = {t.get("topic"): t.get("depth") for t in tops
                                     if t.get("depth")}
        sp = os.path.join(priv, SNAPDIR, f"{wk}.json")
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        json.dump(snap, open(sp, "w"), indent=2)
        print(f"\nsnapshot written: {os.path.relpath(sp, priv)} "
              f"(next Friday's trajectory source)")

    print(f"\n=== sent {len(sent)} · skipped {len(skipped)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
