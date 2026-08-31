#!/usr/bin/env python3
"""
portal_run.py — the parent-portal publisher (PARENT-PORTAL-BRIEF wiring).

Builds and publishes the FOUR portal pages for each kid —
    /p/<slug>/           home
    /p/<slug>/ahead/     the week ahead      (refreshed by the Monday run)
    /p/<slug>/week/      the weekly update   (refreshed by the Friday run)
    /p/<slug>/picture/   the overall picture (refreshed by the Friday run)
— and, on Rich's explicit say-so (--monday-sms), sends the Monday POINTER SMS.

RUN CADENCE (both runs publish all four pages; the data does the differing):
  * MONDAY (after the sweep): the ahead page picks up the new week's targets;
    the weekly update + overall picture re-render from LAST Friday's facts.
  * FRIDAY: friday_report_run remains the sender of record for the report SMS;
    dispatch THIS runner after it (--no --monday-sms) so the portal's weekly
    update + picture catch up with the fresh week. (A pg_cron slot lands here
    once Rich promotes the portal live.)

THE MONDAY POINTER (monday_brief.pointer_sms) is ungated by design: it names
subjects and links the ahead page — it carries no sweep-derived claim, so it
cannot tell a parent something false about the school week. It still only
sends with --monday-sms (shadow-first: pages ship dark, Rich fires the text),
passes the Monday law validator before sending, aborts when the parent seat is
unresolved (the friday_report_run safety), and advances a weekly cursor so
re-runs never double-text.

FAIL-SOFT: the weekly-update facts reuse the Friday build over LAST week's
window. If any of that fails (week one, missing runs), the portal still ships
with the page's honest empty state — the ahead page and the picture never
hostage to the report machinery.

SLUGS: adds a "portal" slug (token_hex, lowercase) beside report/wrap in the
private report_slugs.json — brand new, never leaked in any log, unaffected by
the B4 rotation of the burned report slugs.

Usage:
  python tools/portal_run.py --private-dir private [--dry-run] [--student t1]
                             [--date 2026-08-31] [--monday-sms]
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import friday_report as fr          # noqa: E402
import friday_report_run as frun    # noqa: E402  — slugs_for/plans/targets loaders
import monday_brief as mb           # noqa: E402
import portal_page as pp            # noqa: E402
import report_stories as rst        # noqa: E402
import netlify_deploy as deploy     # noqa: E402
import notify                       # noqa: E402
import roster                       # noqa: E402
from planner import load_targets_for, resolve_target  # noqa: E402

CURSOR = os.path.join("work", "portal_monday_cursor.json")

# Per-teacher subjects the sweep can't yet verify for this seat (V2 §4): their
# ahead rows carry the visible hedge. Replaced by real per-teacher confidence
# flags when the targets format grows them; t1 aliases y8's curriculum.
UNVERIFIED = {"y8": ("English",), "t1": ("English",),
              "y9": ("Science", "English")}

# Seats whose Monday pointer sends AUTOMATICALLY on a scheduled (input-less)
# Monday run. The pg_cron dispatcher fires workflows with NO inputs, so
# promotion lives here, in reviewed code — a seat joins by PR, the merge
# being the ratification. ALL SEATS promoted 31 Aug on Rich's directive
# ("expand to y8 and y9 immediately"). NOTE: y8 + y9 are one household —
# until the household-consolidation amendment is built (V2 §2), Monday
# brings that household one pointer PER KID, each naming only its own kid.
# --monday-sms remains the manual override for any seat a dispatch targets.
POINTER_LIVE = ("t1", "y8", "y9")

PAGE_ORDER = ("ahead", "week", "picture", "")   # home LAST — it links the rest


def portal_slugs(private_dir, codes):
    """report_slugs.json gains a 'portal' key per code (token_hex, lowercase —
    immune to the Netlify case-collision by construction). Existing report/wrap
    slugs are never touched here."""
    import secrets
    p = os.path.join(private_dir, frun.SLUGS)
    data = frun.load_json(p, {}) or {}
    changed = False
    for c in codes:
        entry = data.setdefault(c, {})
        if "portal" not in entry:
            entry["portal"] = secrets.token_hex(9)
            changed = True
    if changed:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        json.dump(data, open(p, "w"), indent=2)
    return data


def upcoming_dates(topics, tmap, asof, horizon_days=21):
    """EVERY dated assessment on live targets within the horizon, nearest
    first, deduped by (task, date) — the ahead page's UPCOMING DATES card.
    Today that means tests; study-guide releases and due dates join as the
    sweep starts carrying them."""
    seen, out = set(), []
    for tp in topics:
        tgt = resolve_target(tp.get("topic", ""), tmap)
        a = (tgt or {}).get("assessment")
        if not a or not a.get("date"):
            continue
        try:
            d = dt.date.fromisoformat(a["date"])
        except ValueError:
            continue
        days = (d - asof).days
        key = (a.get("task"), a["date"])
        if 0 <= days <= horizon_days and key not in seen:
            seen.add(key)
            out.append({"task": a.get("task", "a test"), "date": a["date"],
                        "days": days, "subject": tp.get("subject")})
    out.sort(key=lambda u: u["date"])
    return out


def snapshots_for(private_dir, code, topics):
    """The banked Friday snapshots as the portal wants them: oldest-first
    [{week_of, topics:{topic:state}, subjects:{topic:subject}}] for ONE kid.
    Subjects come from the current ledger (snapshots don't store them)."""
    subj_of = {t.get("topic"): t.get("subject") for t in topics}
    out = []
    for f in sorted(glob.glob(os.path.join(private_dir, frun.SNAPDIR, "*.json"))):
        snap = frun.load_json(f) or {}
        states = snap.get(code)
        if states:
            out.append({"week_of": snap.get("week_of"),
                        "topics": states, "subjects": subj_of})
    return out


def last_friday(asof):
    """The most recent completed school week's Friday (and its Monday)."""
    fri = asof - dt.timedelta(days=(asof.weekday() - 4) % 7 or 7)
    if asof.weekday() == 4:          # a Friday run reports its own week
        fri = asof
    return fri, fri - dt.timedelta(days=4)


def friday_facts(code, asof, priv, runs, state, targets, prev_snapshot):
    """Last week's Friday facts for the weekly-update page — the same build
    the Friday runner uses, read-only. Returns {} on ANY failure so the
    portal ships with the page's honest empty state instead of not at all."""
    try:
        fri, mon = last_friday(asof)
        (card, stories, quote, acc, notes, speed, wow,
         subjects, fluency) = frun.build_for(code, fri, priv, runs, state,
                                             targets, prev_snapshot)
        return {"blocks": subjects, "fluency": fluency,
                "week_verdict": {"word": card["week_word"]["word"]},
                "activity": card.get("activity") or {},
                "accuracy": acc, "name": card.get("name"),
                "this_week_of": mon.isoformat()}
    except Exception as e:                                    # noqa: BLE001
        print(f"  [WARN] last-Friday facts unavailable ({type(e).__name__}) "
              "— the weekly update ships its honest empty state.")
        return {}


def build_portal_for(code, asof, priv, runs, state, targets, prev_targets,
                     prev_snapshot):
    topics = state.get("students", {}).get(code, {}).get("topics", [])
    tmap, subjects_block = load_targets_for(code, targets)
    _, prev_subjects_block = load_targets_for(code, prev_targets or {})

    friday = friday_facts(code, asof, priv, runs, state, targets, prev_snapshot)
    name = friday.get("name") or fr.name_for(runs, code)

    radar = fr.assessment_radar(topics, tmap, asof)
    upcoming = upcoming_dates(topics, tmap, asof)
    brief = mb.week_ahead(name, subjects_block, prev_subjects_block, radar,
                          unverified=UNVERIFIED.get(code, ()))
    return pp.build_portal(
        name, frun.week_of(asof), topics, subjects_block, radar,
        week_ahead=brief,
        this_week_blocks=friday.get("blocks"),
        this_week_fluency=friday.get("fluency"),
        this_week_of=friday.get("this_week_of"),
        snapshots=snapshots_for(priv, code, topics),
        archive=[],                       # dated /r/<slug>/<week>/ paths: V2 §5 follow-up
        week_verdict=friday.get("week_verdict"),
        activity=friday.get("activity"),
        accuracy=friday.get("accuracy"),
        upcoming=upcoming,
    ), brief


def publish_pages(slug, pages):
    """All four pages to /p/<slug>/…, each stamp-verified by netlify_deploy.
    Home goes LAST so its doorways never precede their destinations. Returns
    {key: live_bool}."""
    live = {}
    for key in PAGE_ORDER:
        path = slug if key == "" else f"{slug}/{key}"
        live[key] = deploy.publish(path, pages[key], kind="p")
        label = key or "home"
        print(f"  {label}: {'LIVE ✓' if live[key] else 'DEPLOY FAILED'} "
              "(per-kid URL withheld from public log)")
    return live


def _sydney_today():
    from zoneinfo import ZoneInfo
    return dt.datetime.now(ZoneInfo("Australia/Sydney")).date()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--date", default=None,
                    help="ISO date (default: today in Australia/Sydney — the "
                         "runner's clock is the family's, not the CI box's)")
    ap.add_argument("--student", help="one player (default: all active)")
    ap.add_argument("--dry-run", action="store_true",
                    help="build + render to preview files; no deploy, no SMS")
    ap.add_argument("--monday-sms", action="store_true",
                    help="manual override: send the Monday pointer for every "
                         "seat this run targets, whatever the day (weekly "
                         "cursor; re-runs never double-text)")
    a = ap.parse_args()

    asof = dt.date.fromisoformat(a.date) if a.date else _sydney_today()
    priv = a.private_dir
    codes = [a.student] if a.student else roster.active()
    wk = frun.week_of(asof)

    runs = (frun.load_json(os.path.join(priv, "work", "runs.json"), {}) or {}).get("runs", [])
    state = frun.load_json(os.path.join(priv, "work", "state.json"), {}) or {}
    tfiles = sorted(glob.glob(os.path.join(priv, "targets", "*.json")))
    targets = frun.load_json(tfiles[-1], {}) if tfiles else {}
    prev_targets = frun.load_json(tfiles[-2], {}) if len(tfiles) > 1 else {}

    snaps = sorted(glob.glob(os.path.join(priv, frun.SNAPDIR, "*.json")))
    prev_snapshot = frun.load_json(snaps[-1]) if snaps else None
    fri, _ = last_friday(asof)
    if prev_snapshot and prev_snapshot.get("week_of") == frun.week_of(fri):
        # the newest snapshot IS the reported week's — trajectory needs the one before
        prev_snapshot = frun.load_json(snaps[-2]) if len(snaps) > 1 else None

    slugs = portal_slugs(priv, codes)
    cursor = frun.load_json(os.path.join(priv, CURSOR), {}) or {}

    sent, published = [], []
    for code in codes:
        if code not in state.get("students", {}):
            print(f"[{code}] no ledger — skipped.")
            continue
        portal, brief = build_portal_for(code, asof, priv, runs, state,
                                         targets, prev_targets, prev_snapshot)
        slug = slugs[code]["portal"]
        wrap_url = deploy.url_for(slugs[code].get("wrap", ""), kind="w") \
            if slugs[code].get("wrap") else None
        ahead_url = deploy.url_for(f"{slug}/ahead", kind="p")

        # the player-card door only renders when the wrap is actually live
        kid_wrap_url = None
        if wrap_url and not a.dry_run and deploy.verify(wrap_url):
            kid_wrap_url = wrap_url
        pages = pp.render_pages(portal, kid_wrap_url=kid_wrap_url)
        print(f"[{code}] ahead-subjects={len(brief.get('rows', []))} "
              f"upcoming={len(portal.get('upcoming') or [])} "
              f"weekly-update={'y' if portal['this_week']['blocks'] else 'empty'} "
              f"map-subjects={len(portal['running']['cards'])}")

        if a.dry_run:
            for key, label in (("", "home"), ("ahead", "ahead"),
                               ("week", "week"), ("picture", "picture")):
                out = os.path.join(priv, "work", f"preview_portal_{code}_{label}.html")
                open(out, "w").write(pages[key])
            body = mb.pointer_sms(brief, ahead_url)
            open(os.path.join(priv, "work",
                              f"preview_portal_{code}.sms.txt"), "w").write(body)
            print(f"  DRY-RUN -> work/preview_portal_{code}_*.html + .sms.txt")
            continue

        live = publish_pages(slug, pages)
        if all(live.values()):
            published.append(code)

        # THE POINTER. A scheduled (input-less) dispatch sends it only on a
        # Monday and only for POINTER_LIVE seats; --monday-sms is the manual
        # override for whatever this run targets. Everything below the gate is
        # identical either way: cursor, live-pages check, the Monday law, the
        # parent-seat guard.
        want_pointer = a.monday_sms or (asof.weekday() == 0 and code in POINTER_LIVE)
        if not want_pointer:
            continue
        if cursor.get(code) == wk:
            print(f"  pointer already sent for week {wk} — no-op.")
            continue
        if not live.get("ahead") or not live.get(""):
            print("  pointer NOT sent — portal pages didn't all verify live.")
            continue
        body = mb.pointer_sms(brief, ahead_url)
        ok, why = mb.validate(body, portal["name"],
                              subjects=brief.get("subjects", ()))
        if not ok:
            print(f"  ABORT {code}: pointer failed the Monday law ({why}).")
            continue
        seat = f"parents:{code}"
        if not notify._recipients(seat):
            print(f"  ABORT {code}: no number configured for {seat} "
                  f"(set MOBILE_MESSAGE_PARENTS_{code.upper()}) — nothing sent.")
            continue
        ok, detail = notify.send_sms(seat, body)
        if ok:
            cursor[code] = wk
            sent.append(code)
            print("  pointer SENT ✓")
        else:
            reason = (detail or "unknown").splitlines()[0].split(":", 1)[0][:48]
            print(f"  pointer SEND FAILED ({reason}) — cursor not advanced, "
                  "safe to re-run.")

    if not a.dry_run:
        cp = os.path.join(priv, CURSOR)
        os.makedirs(os.path.dirname(cp), exist_ok=True)
        json.dump(cursor, open(cp, "w"), indent=2)

    print(f"\n=== portals published {len(published)} · pointers sent {len(sent)} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
