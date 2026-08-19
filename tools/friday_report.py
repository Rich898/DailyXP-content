#!/usr/bin/env python3
"""
friday_report.py — the FACTS layer for the Friday weekly report (REPORTING.md
touchpoint 3: JUDGE — the resolution of the story Wednesday set up).

This module computes; it does not send and it does not phrase. It turns the
ledger + this week's runs + the fresh targets into ONE fact card per kid. The
SMS composer (friday_sms.py) and the hosted-page renderer (report_page.py)
both consume that card; the model only ever dresses the card into sentences.

DOCTRINE ENCODED HERE (REPORTING.md):
  * CODE DECIDES, LANGUAGE DRESSES. Every fact below — the week-word, the
    standing verdict, the movement list, the win, the radar, the one action —
    is chosen by deterministic rules. Nothing here is an LLM call.
  * ONE WEEK-WORD ENGINE. The week-word comes from weekword.momentum() over
    Mon..Fri vs LAST week's Mon..Fri — the SAME function Wednesday sampled
    midweek. Wednesday planted; Friday harvests the same word off more days.
  * WEEK 1 HAS NO PRIOR. baseline=True drops trajectory, caps the word at
    solid/quiet (never strong/slower — both need a real prior), swaps the
    "since last week" row for "where he's starting", and renders a starting
    snapshot instead of movement. This week IS week 1.
  * THE NO-ANXIETY RULE. A flagged area always arrives WITH its fix. The card
    never surfaces a bare gap: pick_focus() returns the gap AND the five-minute
    action together, or nothing. Under-claim on thin data (quiet outranks a
    comprehension read).
  * KEEPING PACE, HONESTLY + COMPUTABLY. Targets know what's being TAUGHT
    (status=live); the ledger knows what's MASTERED. on_pace = live topics
    reaching developing/solid roughly as fast as they go live. "a step behind"
    = a topic taught a while but still shaky/untested. Never a bare "behind";
    never against other children (there is no cohort — behind can only mean
    behind his OWN syllabus).
  * THE RATIO NEVER LEAVES weekword.py. Comprehension is a word here, never a
    number. XP total IS allowed on the Friday surface (totals belong to the
    report + portal per the soundbyte doctrine) — it is the ONE number the
    daily layer withheld precisely so Friday could carry it.

The card is JSON-serialisable and law-checkable. friday_sms.validate() and the
page renderer are the two gates that turn it into outgoing text.
"""
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from weekword import window_stats, momentum          # THE shared engine  # noqa: E402
from wed_checkin import display_topic                 # law-legal topic names  # noqa: E402
from planner import load_targets_for, resolve_target  # the tolerant matcher  # noqa: E402
import soundbyte as sb                                 # season_total, facts   # noqa: E402

# States that count as "landed" for keeping-pace. developing = right once or
# twice; solid = consolidated. shaky/untested/REPAIR are "not landed yet".
LANDED = {"developing", "solid"}
BEHIND = {"shaky", "untested", "REPAIR"}


# --------------------------------------------------------------------------- #
# Week windows (Mon..Fri, this week vs last) — Friday's like-for-like sampling.

def week_days(asof):
    """This week's Mon..asof and last week's SAME span, as ISO lists. Friday
    proper is a full Mon..Fri; if the job runs before Friday (a test/early
    dispatch) it samples Mon..asof so a dry-run mid-week still works."""
    mon = asof - timedelta(days=asof.weekday())
    n = (asof - mon).days + 1              # 5 on Friday; fewer if run earlier
    this = [(mon + timedelta(days=i)).isoformat() for i in range(n)]
    prev = [(mon - timedelta(days=7) + timedelta(days=i)).isoformat() for i in range(n)]
    return this, prev


# --------------------------------------------------------------------------- #
# Standing vs the syllabus — the "keeping pace" computation.

def standing(topics, tmap):
    """Per-subject pace read from the ledger-vs-targets join.

    For each subject with at least one LIVE target topic: it's on pace unless a
    live topic has been seen at least once yet is still shaky/untested/REPAIR
    (taught, not landing) — that's the honest "a step behind", always the
    specific fixable topic, never a bare 'behind'. Untested-and-never-seen live
    topics are 'not yet reached', not 'behind' (you can't be behind on a topic
    class only just introduced) — they only count against pace once seen.

    Returns {subject: {"pace": "on"|"behind"|"quiet", "behind_topic": display|None}}.
    """
    # bucket ledger topics by subject with their resolved target status
    by_subj = {}
    for tp in topics:
        subj = tp.get("subject")
        tgt = resolve_target(tp.get("topic", ""), tmap)
        live = bool(tgt and tgt.get("status") == "live")
        by_subj.setdefault(subj, []).append((tp, live))

    out = {}
    for subj, rows in by_subj.items():
        live_rows = [(tp, tgt_live) for tp, tgt_live in rows if tgt_live]
        if not live_rows:
            continue                       # subject not currently taught -> no pace claim
        behind = None
        for tp, _ in live_rows:
            seen = (tp.get("times_seen") or 0) > 0
            if seen and tp.get("state") in BEHIND:
                # most-relevant behind topic = most seen (most taught, least landed)
                if behind is None or (tp.get("times_seen") or 0) > (behind.get("times_seen") or 0):
                    behind = tp
        if behind is not None:
            out[subj] = {"pace": "behind",
                         "behind_topic": display_topic(behind.get("topic"), subj)}
        else:
            out[subj] = {"pace": "on", "behind_topic": None}
    return out


def standing_summary(stand):
    """Lead-with-the-verdict, name-only-the-exceptions (REPORTING.md 'where he
    stands' row). Returns {"overall": "on"|"mostly", "exceptions": [(subj, topic)]}."""
    exceptions = [(s, v["behind_topic"]) for s, v in stand.items() if v["pace"] == "behind"]
    overall = "on" if not exceptions else "mostly"
    return {"overall": overall, "exceptions": exceptions}


# --------------------------------------------------------------------------- #
# Movement since last week (trajectory) — OFF in week 1 (baseline).

def movement(topics, prev_states):
    """Net + notable topic movement vs last Friday's snapshot.

    prev_states: {topic_name: state} from last week's state snapshot (see
    snapshot_states / the Friday job's weekly write). Advancement is measured
    on an ordinal ladder; only real transitions count.

    Returns {"net": int, "up": [display], "down": [display]} — 'up'/'down'
    hold the NOTABLE moves (biggest advance; any regression, which always
    needs action). Empty and net=0 when there is no prior (week 1).
    """
    rank = {"untested": 0, "REPAIR": 0, "shaky": 1, "developing": 2, "solid": 3}
    net, ups, downs = 0, [], []
    for tp in topics:
        name = tp.get("topic", "")
        if name not in prev_states:
            continue
        was, now = rank.get(prev_states[name], 0), rank.get(tp.get("state"), 0)
        if now > was:
            net += 1
            ups.append((now - was, display_topic(name, tp.get("subject", ""))))
        elif now < was:
            net -= 1
            downs.append(display_topic(name, tp.get("subject", "")))
    ups.sort(reverse=True)
    return {"net": net, "up": [d for _, d in ups[:2]], "down": downs[:2]}


# --------------------------------------------------------------------------- #
# The win — one genuine highlight to celebrate.

def pick_win(topics, prev_states, earned_this_week, best_day, days_done=0, baseline=False):
    """ONE win, chosen deterministically in priority order:
      1. a real ↑ transition this week (a topic that consolidated) — the
         strongest, because it's learning that stuck;
      2. else a badge earned this week (game-flavoured but real);
      3. else the best single run of the week (always exists if he played).
    Returns {"kind": ..., "text_key": ...} — display strings, no number
    except best_day's XP which is a legal Friday number.
    """
    rank = {"untested": 0, "REPAIR": 0, "shaky": 1, "developing": 2, "solid": 3}
    # 1) biggest genuine advance
    best_adv, best_topic = 0, None
    for tp in topics:
        name = tp.get("topic", "")
        if name in prev_states:
            adv = rank.get(tp.get("state"), 0) - rank.get(prev_states[name], 0)
            if adv > best_adv:
                best_adv, best_topic = adv, tp
    if best_topic is not None:
        landed = best_topic.get("state") == "solid"
        return {"kind": "mastery",
                "topic": display_topic(best_topic.get("topic"), best_topic.get("subject", "")),
                "landed": landed}
    # 2) a badge this week
    if earned_this_week:
        b = earned_this_week[0]
        return {"kind": "badge", "badge": b.get("badge"), "label": b.get("label", "")}
    # 3) best run of the week
    if best_day:
        # In a thin baseline week (played once, no movement, no new badge) a
        # single best run isn't a triumph — it's the first mark on the board.
        starting = baseline and days_done <= 1
        return {"kind": "best_run", "pts": best_day["pts"], "day": best_day["day"],
                "starting": starting}
    return {"kind": "none"}


# --------------------------------------------------------------------------- #
# Assessment radar — a dated test inside the fortnight (now unblocked: the
# 10 Aug sweep gave targets structured dates).

def assessment_radar(topics, tmap, asof, horizon_days=14):
    """The nearest live-topic assessment within the horizon, with the ledger
    readiness of the topics it covers. Returns None if nothing dated is near.

    Readiness is a WORD from the covered topics' states, never a number:
      ready    — all covered topics developing/solid
      building — a mix; some landed, some not
      early    — most covered topics still shaky/untested
    """
    near = []
    for tp in topics:
        tgt = resolve_target(tp.get("topic", ""), tmap)
        a = tgt.get("assessment") if tgt else None
        if not a or not a.get("date"):
            continue
        try:
            d = date.fromisoformat(a["date"])
        except ValueError:
            continue
        days = (d - asof).days
        if 0 <= days <= horizon_days:
            near.append((days, tp, a))
    if not near:
        return None
    near.sort(key=lambda x: x[0])
    days, _, a = near[0]
    task, task_date = a.get("task", "a test"), a["date"]
    # gather every covered topic that shares this task+date
    covered = [tp for dd, tp, aa in near
               if aa.get("task") == task and aa.get("date") == task_date]
    landed = sum(1 for tp in covered if tp.get("state") in LANDED)
    total = len(covered)
    if landed == total:
        readiness = "ready"
    elif landed == 0:
        readiness = "early"
    else:
        readiness = "building"
    # the weakest covered topic is the honest thing to point practice at
    weak = [tp for tp in covered if tp.get("state") in BEHIND]
    weak.sort(key=lambda tp: (tp.get("times_seen") or 0), reverse=True)
    focus = display_topic(weak[0].get("topic"), weak[0].get("subject", "")) if weak else None
    subj = covered[0].get("subject") if covered else ""
    return {"task": task, "date": task_date, "days": days, "subject": subj,
            "readiness": readiness, "focus": focus, "covered": total}


# --------------------------------------------------------------------------- #
# The one action — the no-anxiety fix, always paired with its gap.

def pick_focus(topics, radar, stand):
    """ONE five-minute action for the week, gap-dressed-as-help and never bare.
    Priority: (1) the assessment focus if a test is near — most actionable;
    (2) else a REPAIR-flagged topic; (3) else the standing 'behind' topic;
    (4) else a strength to draw out (an ask). Returns a dict the composer turns
    into a sentence, or a positive 'keep-going' when nothing needs repair.
    """
    if radar and radar.get("focus"):
        return {"kind": "assess", "topic": radar["focus"],
                "task": radar["task"], "days": radar["days"]}
    repair = [t for t in topics if t.get("repair") or t.get("state") == "REPAIR"]
    repair.sort(key=lambda t: (t.get("last_tested") or ""), reverse=True)
    if repair:
        return {"kind": "repair",
                "topic": display_topic(repair[0].get("topic"), repair[0].get("subject", ""))}
    exceptions = stand.get("exceptions") if isinstance(stand, dict) else None
    if exceptions:
        subj, topic = exceptions[0]
        return {"kind": "behind", "topic": topic, "subject": subj}
    # nothing to repair — draw out a strength instead (the pedagogy is him explaining)
    strong = [t for t in topics if t.get("state") == "solid"]
    strong.sort(key=lambda t: (t.get("last_tested") or ""), reverse=True)
    if strong:
        return {"kind": "ask",
                "topic": display_topic(strong[0].get("topic"), strong[0].get("subject", ""))}
    return {"kind": "none"}


# --------------------------------------------------------------------------- #
# Week activity facts (the safe "this week" row) + best day.

def week_activity(runs, student, this_days):
    """days done, events cleared (Battleground tags), and the best single run —
    all SAFE facts (no misses, no subjects). best_day carries a legal Friday XP.
    """
    mine = [r for r in runs if r.get("student") == student and r.get("run_date") in this_days]
    best_by_day = {}
    events = 0
    for r in mine:
        d = r["run_date"]
        sc = int(r.get("score") or 0)
        if d not in best_by_day or sc > best_by_day[d]["pts"]:
            wd = date.fromisoformat(d).strftime("%a")
            best_by_day[d] = {"pts": sc, "day": wd, "date": d}
        tag = (r.get("tag") or "").upper()
        if tag.endswith("BOSS") or tag.endswith("BATTLEGROUND") or tag.endswith(".5"):
            events += 1
    best_day = max(best_by_day.values(), key=lambda x: x["pts"]) if best_by_day else None
    topics_practised = len({q for r in mine for q in _topics_in_run(r)})
    return {"days_done": len(best_by_day), "possible": len(this_days),
            "events": events, "best_day": best_day, "topics_practised": topics_practised}


def _topics_in_run(r):
    """Best-effort set of topic labels touched in a run (for the 'topics
    practised' safe count). Falls back to the run's question count when the
    per-question topic isn't recorded."""
    qs = r.get("questions") or []
    names = set()
    for q in qs:
        if isinstance(q, dict):
            t = q.get("topic") or q.get("subject")
            if t:
                names.add(t)
    if not names and qs:
        return {f"__q{i}" for i in range(len(qs))}   # count questions if topics absent
    return names


# --------------------------------------------------------------------------- #
# Starting snapshot (week 1) / where-he-stands snapshot (compact, always).

def snapshot(topics):
    """Compact where-he-stands: per-subject counts of landed vs building, plus
    the strongest and shakiest named topic. Small enough for the report's
    footer snapshot; the full map is the (later) portal."""
    from collections import Counter
    subj_land = Counter()
    subj_build = Counter()
    for tp in topics:
        subj = tp.get("subject")
        if tp.get("state") in LANDED:
            subj_land[subj] += 1
        elif tp.get("state") in BEHIND:
            subj_build[subj] += 1
    rows = []
    for subj in sorted(set(list(subj_land) + list(subj_build))):
        rows.append({"subject": subj, "landed": subj_land[subj],
                     "building": subj_build[subj]})
    solids = [t for t in topics if t.get("state") == "solid"]
    solids.sort(key=lambda t: (t.get("times_seen") or 0), reverse=True)
    strongest = display_topic(solids[0].get("topic"), solids[0].get("subject", "")) if solids else None
    return {"rows": rows, "strongest": strongest}


def snapshot_states(topics):
    """{topic_name: state} — what the Friday job snapshots weekly so NEXT
    Friday's movement() has a prior. This is the mechanism that turns
    trajectory on from week 2."""
    return {tp.get("topic"): tp.get("state") for tp in topics}


# --------------------------------------------------------------------------- #
# THE FACT CARD — everything a report/SMS needs, all deterministic.

def name_for(runs, student):
    dated = sorted((r for r in runs if r.get("student") == student and r.get("name")),
                   key=lambda r: r.get("run_date") or "")
    return dated[-1]["name"] if dated else student.upper()


def build_card(student, runs, topics, tmap, asof, prev_states, earned_this_week,
               seed=0, baseline=False):
    """The complete deterministic fact card for one kid's Friday report."""
    this_d, prev_d = week_days(asof)
    now = window_stats(runs, student, this_d)
    prev = window_stats(runs, student, prev_d)

    # week-word from the shared engine; baseline caps it (no strong/slower w/o a real prior)
    m = momentum(now, prev)
    word, direction = m["word"], m["direction"]
    if baseline:
        direction = "none"
        if word in ("strong", "slower"):
            word = "solid" if now["days_done"] > 0 else "quiet"

    act = week_activity(runs, student, this_d)
    stand = standing(topics, tmap)
    stand_sum = standing_summary(stand)
    radar = assessment_radar(topics, tmap, asof)
    move = {"net": 0, "up": [], "down": []} if baseline else movement(topics, prev_states)
    win = pick_win(topics, {} if baseline else prev_states, earned_this_week,
                   act["best_day"], days_done=act["days_done"], baseline=baseline)
    focus = pick_focus(topics, radar, stand_sum)
    snap = snapshot(topics)
    total = sb.season_total([r for r in runs if r.get("student") == student],
                            asof.isoformat(), seed)

    return {
        "code": student,
        "name": name_for(runs, student),
        "baseline": baseline,
        "week_word": {"word": word, "direction": direction},
        "activity": {"days_done": act["days_done"], "possible": act["possible"],
                     "events": act["events"], "topics_practised": act["topics_practised"],
                     "best_day": act["best_day"]},
        "standing": stand_sum,              # overall + named exceptions
        "standing_detail": stand,           # per-subject (for the page's lower detail)
        "movement": move,                   # empty in baseline
        "win": win,
        "radar": radar,                     # None if no test near
        "action": focus,                    # the one no-anxiety fix, gap+help fused
        "snapshot": snap,                   # compact where-he-stands
        "xp_total": total,                  # the legal Friday number
        "week_of": (asof - timedelta(days=asof.weekday())).isoformat(),
    }
