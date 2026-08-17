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
    a parent's bookmark keeps working; stored private, never in the public repo."""
    import secrets
    p = os.path.join(private_dir, SLUGS)
    data = load_json(p, {}) or {}
    changed = False
    for c in codes:
        if c not in data:
            data[c] = {"report": secrets.token_urlsafe(9), "wrap": secrets.token_urlsafe(9)}
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
    tmap, _ = load_targets_for(code, targets)
    days, _ = fr.week_days(asof)
    baseline = not prev_snapshot

    earned = load_json(os.path.join(private_dir, "work", "achievements_earned.json"), {}) or {}
    mine = (earned.get(code) or {}).get("earned", [])
    this_week = [b for b in mine if (b.get("date") or "") in days]

    card = fr.build_card(code, runs, topics, tmap, asof,
                         prev_states=(prev_snapshot or {}).get(code, {}),
                         earned_this_week=this_week, baseline=baseline)
    stories = rst.build_stories(private_dir, runs, plans_for(private_dir, code),
                                code, days, topics,
                                depth_before=(prev_snapshot or {}).get(code + "_depth", {}))
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
    return card, stories, quote, acc, notes, speed, wow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--date", default=dt.date.today().isoformat())
    ap.add_argument("--student", help="one player (default: all active)")
    ap.add_argument("--dry-run", action="store_true", help="build + render, no deploy, no SMS")
    ap.add_argument("--no-sms", action="store_true", help="deploy but don't text")
    a = ap.parse_args()

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
        if cursor.get(code) == wk:
            print(f"[{code}] already sent for week {wk} — no-op.")
            skipped.append(code)
            continue
        if code not in state.get("students", {}):
            print(f"[{code}] no ledger — skipped.")
            continue

        card, stories, quote, acc, notes, speed, wow = build_for(
            code, asof, priv, runs, state, targets, prev_snapshot)
        print(f"[{code}] {card['name']}: week-word={card['week_word']['word']} "
              f"stories={len(stories)} quote={'y' if quote else 'n'} "
              f"baseline={card['baseline']}")

        wrap_url = deploy.url_for(slugs[code]["wrap"], kind="w")
        html = rpage.render(card, stories=stories, quote=quote, accuracy=acc,
                            kid_wrap_url=None, extra_notes=notes, speed=speed, wow=wow)
        report_url = deploy.url_for(slugs[code]["report"], kind="r")

        if a.dry_run:
            out = os.path.join(priv, "work", f"preview_report_{code}.html")
            open(out, "w").write(html)
            body, src = fsms.render_body(card, report_url, api_key=api_key,
                                         use_ai=bool(api_key))
            print(f"  DRY-RUN page -> {out}")
            print(f"  DRY-RUN sms  [{src}] {len(body)} chars:\n    {body}\n")
            continue

        live = deploy.publish(slugs[code]["report"], html, kind="r")
        if live:
            print(f"  page LIVE: {report_url}")
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
        if notify.send_sms(f"parents:{code}", body):
            cursor[code] = wk
            sent.append(code)
            print("  SENT ✓")
        else:
            print("  SEND FAILED — cursor not advanced, safe to re-run.")

    if not a.dry_run:
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
