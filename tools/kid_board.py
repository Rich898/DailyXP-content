#!/usr/bin/env python3
"""
kid_board.py — THE BOARD: the kid's Monday week-ahead (KID-WEEKLY-FRAMEWORK.md
§4, as revised by Rich's round-1 feedback, 31 Aug). Deterministic facts, no AI.

A USEFUL TOOL FOR THE BOYS, in Rich's ratified order (rounds 1–2, 31 Aug):
  1. THIS WEEK'S GROUND      — what school is covering (the parents' Week
     Ahead facts, same engine, kid-dressed; he sees them FIRST — the
     reveal-order law).
  2. UP FOR GRABS THIS WEEK  — the week's achievements as cards, each
     carrying its BADGE. A "run" is simply the day's quiz (tonight's run,
     tomorrow's run) — never a thing drawn on the board (round 2: the tile
     strip was confusing, removed). ONE weekly showing-up achievement leads:
     ON THE BOARD, 4 of the 5 nightly runs (a real badge, awarded by
     achievements.py from this week). EVERY card is a badge the nightly
     achievements engine actually awards — the board is a forward READ of
     that engine, never a new reward system. That is what makes the loop
     work end-to-end today: available (board, Monday) → earned (nightly
     pass → the quiz end screen) → settled (Friday wrap's UNLOCKS) →
     banked (the Season page, next build).
  3. BOSS RADAR              — tests and dates, as countdowns.

ROUND-1/2 LAWS (Rich, 31 Aug — locked by tests):
  * Headlines are ALWAYS white (accent lives in eyebrows/chips/nav).
  * The sub keeps the sentence "The week of Monday {date} is live".
  * "Contract" never renders; "up for grabs" appears ONCE (the section head).
  * No rank names and no XP promises on the board — XP is earned, never
    dangled ("50 XP from X" reads as a gift).
  * Rolls-on framing only: "failed"/"missed" can never render here.
  * kid_wrap.violations() runs over the FULL page; render() refuses a breach.
  * NOTHING ships unseen: every design change is previewed to Rich BEFORE
    merge or deploy — no exceptions, deadline or not (the 31 Aug lesson).

Published to /w/<slug>/board/ (the existing wrap slug — no new slug kind) by
Monday's run, BEFORE the 4pm nudge; kid_nudge appends the link only after
verifying the live page carries THIS week's <meta name="xpdaily-week">.
Self-contained HTML, zero fetch, noindex, build-stamped (report_page model).
"""
import argparse
import datetime as dt
import glob
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import friday_report as fr           # noqa: E402
import friday_report_run as frun     # noqa: E402
import kid_wrap as kw                # noqa: E402
import monday_brief as mb            # noqa: E402
import report_page                   # noqa: E402
import soundbyte as sb               # noqa: E402
from planner import load_targets_for  # noqa: E402

BOARD_URLS = os.path.join("work", "board_urls.json")


def _e(s):
    return html.escape(str(s if s is not None else ""))


# --------------------------------------------------------------------------- #
# Facts — every badge below exists in achievements.py's award set (the
# kid_wrap CABINET); the board only ever names what that engine can pay.

def pick_lock_it(topics):
    """The topic nearest solid: developing, most-seen first (the same read as
    kid_wrap.badge_hints), name-tiebroken for determinism."""
    dev = [t for t in (topics or []) if t.get("state") == "developing"]
    dev.sort(key=lambda t: (-(t.get("times_seen") or 0), t.get("topic") or ""))
    return dev[0] if dev else None


def pick_comeback(topics):
    """A repair topic's exit — most-seen REPAIR/repair-flagged topic."""
    rep = [t for t in (topics or [])
           if t.get("state") == "REPAIR" or t.get("repair")]
    rep.sort(key=lambda t: (-(t.get("times_seen") or 0), t.get("topic") or ""))
    return rep[0] if rep else None


def full_clear_watch(topics):
    """The subject closest to Full Clear (1–2 non-solid zones left, 3+ topics).
    A proximity read — the award itself stays achievements.py's call."""
    by_subj = {}
    for t in topics or []:
        s = t.get("subject")
        if s:
            by_subj.setdefault(s, []).append(t)
    best = None
    for subj, ts in sorted(by_subj.items()):
        if len(ts) < 3:
            continue
        left = sum(1 for t in ts if t.get("state") != "solid")
        if 1 <= left <= 2 and (best is None or left < best["left"]):
            best = {"subject": subj, "left": left, "n": len(ts)}
    return best


def streak_night(streak, earned_raw):
    """(tier_name, day_index 0–4) if the next streak tier lands on one of this
    week's runs, played straight through from Monday. None otherwise."""
    raw = " ".join(str(b.get("badge") or "") for b in (earned_raw or [])).lower()
    nxt = next(((n, t) for n, t in kw.STREAK_TIERS
                if n > streak and t.lower() not in raw), None)
    if not nxt:
        return None
    gap = nxt[0] - streak
    if 1 <= gap <= 5:
        return {"tier": nxt[1], "night": nxt[0], "day_idx": gap - 1}
    return None


def week_up_for_grabs(topics, streak, earned_raw):
    """The week's achievements, as cards (Rich round 2: the prior card format
    with the badge on each). EVERY card is a real achievements.py badge — the
    board reads the reward engine, never invents one. Showing up first, then
    craft, then mastery on named ground. Capped at six."""
    B = kw.BADGE_ICON
    cards = [{
        "icon": B["On the Board"], "fam": "SHOWING UP", "name": "ON THE BOARD",
        "terms": "Run 4 of the 5 nights this week — one off-night can't kill "
                 "it. The full five still takes Perfect Week on top."}]
    sn = streak_night(streak, earned_raw)
    if sn:
        phrase = "tonight" if sn["day_idx"] == 0 else \
            ("Tuesday", "Wednesday", "Thursday", "Friday")[sn["day_idx"] - 1] + " night"
        cards.append({
            "icon": B["Streak"], "fam": "SHOWING UP",
            "name": f"STREAK — {sn['tier'].upper()}",
            "terms": f"Your streak walks in at {streak}. Night {sn['night']} "
                     f"of the chain lands {phrase} if the chain holds."})
    cards.append({
        "icon": B["Clean Run"], "fam": "CRAFT", "name": "CLEAN RUN",
        "terms": "Any run: zero lucky guesses, zero sure-but-wrongs. Calm "
                 "calls, honest calls — the set can be hard and this still "
                 "lands."})
    lock = pick_lock_it(topics)
    if lock:
        cards.append({
            "icon": B["Locked It"],
            "fam": f"MASTERY · {(lock.get('subject') or 'THE LEDGER').upper()}",
            "name": f"LOCK IT: {str(lock.get('topic', '')).upper()}",
            "terms": "Take it the last step to solid and it goes in the "
                     "cabinet.",
            "sits": {"band": kw.STATE_BAND.get(lock.get("state"), 3)}})
    back = pick_comeback(topics)
    if back and back.get("topic") != (lock or {}).get("topic"):
        cards.append({
            "icon": B["Comeback"],
            "fam": f"MASTERY · {(back.get('subject') or 'THE LEDGER').upper()}",
            "name": f"BOUNCE BACK: {str(back.get('topic', '')).upper()}",
            "terms": "The comeback. Pull it out of repair and the badge pays "
                     "out.",
            "way_in": True})
    fc = full_clear_watch(topics)
    if fc:
        z = "zone" if fc["left"] == 1 else "zones"
        cards.append({
            "icon": B["Full Clear"],
            "fam": f"MASTERY · {fc['subject'].upper()}",
            "name": f"FULL CLEAR: {fc['subject'].upper()}",
            "terms": f"{fc['left']} {z} left — every {fc['subject']} topic "
                     "solid takes the whole subject."})
    return cards[:6]


def board_facts(code, asof, priv, runs, state, targets, prev_targets):
    """Everything the board renders, from the shared engines. Forward-only:
    nothing here reads last week's results."""
    topics = state.get("students", {}).get(code, {}).get("topics", [])

    def _blocks(tdata):
        # load_targets_for KeyErrors on a file with no students block (or the
        # {} an absent prev-file loads as) — empty week, not a crash.
        if (tdata or {}).get("students"):
            return load_targets_for(code, tdata)
        return {}, {}

    tmap, subjects_block = _blocks(targets)
    _, prev_subjects_block = _blocks(prev_targets)

    from portal_run import UNVERIFIED, upcoming_dates
    name = fr.name_for(runs, code)
    radar = fr.assessment_radar(topics, tmap, asof)
    brief = mb.week_ahead(name, subjects_block, prev_subjects_block, radar,
                          unverified=UNVERIFIED.get(code, ()))
    upcoming = upcoming_dates(topics, tmap, asof)
    if radar:
        upcoming = [u for u in upcoming
                    if (u.get("task"), u.get("date")) != (radar.get("task"),
                                                          radar.get("date"))]

    mine = [r for r in runs if r.get("student") == code]
    present = {r.get("run_date") for r in mine if r.get("run_date")}
    played = sorted(d for d in present if d <= asof.isoformat())
    streak = 0
    if played:
        streak = sb.current_school_streak(present, dt.date.fromisoformat(played[-1]))

    earned = frun.load_json(os.path.join(priv, "work",
                                         "achievements_earned.json"), {}) or {}
    earned_raw = (earned.get(code) or {}).get("earned", [])

    return {"code": code, "name": name.split()[0], "week_of": frun.week_of(asof),
            "brief": brief, "radar": radar, "upcoming": upcoming,
            "streak": streak,
            "grabs": week_up_for_grabs(topics, streak, earned_raw)}


# --------------------------------------------------------------------------- #
# Rendering — headlines white (round-1 law); reef stays in eyebrows/chips.

_CSS = """
/* THE BOARD — Monday, forward. Kid design system (kid_wrap.py dark tokens).
   Headlines ALWAYS white (Rich, round 1); reef = forward accents only,
   bolt = badges and the Friday event. */
:root{--paper:#EAF0F7;--ink:#EAF0F7;--flare:#FF6A47;--reef:#5AA9E6;--kelp:#4FD6A0;
--haze:#8B97AC;--line:#243247;--bolt:#FFB800;--boltdeep:#FFCF66;--plate:#0E1B2D;--card:#101F35}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:#0B1220;background-image:radial-gradient(120% 90% at 50% 2%,#16273f 0%,#0B1220 55%,#070c15 100%);background-attachment:fixed;color:var(--ink);font-family:'Space Grotesk',system-ui,sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:640px;margin:0 auto;padding:20px 16px 96px}
.display{font-family:'Archivo Black','Arial Black',sans-serif;letter-spacing:-.01em}
.top{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.top .brand{font-size:11px;letter-spacing:.16em;color:var(--haze)}
.top .week{font-size:11px;color:var(--haze)}
.kick{margin:22px 0 2px;font-family:'Space Mono',ui-monospace,monospace;font-weight:700;font-size:11px;letter-spacing:.14em;color:var(--haze)}
.kick b{color:var(--reef);background:rgba(90,169,230,.12);border:1.5px solid var(--reef);border-radius:6px;padding:1px 7px;margin-right:6px}
h1.word{font-size:54px;line-height:1;margin:2px 0 8px;color:var(--ink);animation:heroPop .55s cubic-bezier(.2,1.3,.4,1) both}
.sub{font-size:17px;line-height:1.45;margin:4px 0 22px;max-width:52ch}
.sub b{color:var(--boltdeep)}
.section{margin:30px 0 10px;font-size:11px;letter-spacing:.15em;color:var(--haze);font-weight:700}
@keyframes heroPop{0%{opacity:0;transform:scale(.86)}60%{opacity:1;transform:scale(1.03)}100%{transform:scale(1)}}
.ground{background:var(--card);border:2px solid var(--line);border-radius:14px;padding:12px 15px;margin-bottom:9px}
.ground .nm{font-family:'Archivo Black','Arial Black',sans-serif;font-size:14px;letter-spacing:.03em;margin-bottom:6px}
.ground .row{font-size:14px;line-height:1.5;color:#C7D0DE}
.ground .row b{color:var(--ink);font-weight:600}
.chip{display:inline-block;font-family:'Space Mono',monospace;font-weight:700;font-size:9px;letter-spacing:.1em;color:var(--reef);background:rgba(90,169,230,.13);border:1px solid rgba(90,169,230,.5);border-radius:5px;padding:1.5px 6px;margin-right:6px;vertical-align:1px}
.intro{font-size:13.5px;color:var(--haze);margin:-2px 0 10px;line-height:1.5}
.ach{display:flex;align-items:flex-start;gap:13px;background:var(--card);border:2px solid var(--line);border-radius:14px;padding:13px 15px;margin-bottom:10px;position:relative}
.ach .i{font-size:26px;line-height:1;margin-top:2px}
.ach .body{flex:1;padding-right:52px}
.ach .fam{font-family:'Space Mono',monospace;font-weight:700;font-size:9.5px;letter-spacing:.13em;color:var(--reef)}
.ach .fam.gold{color:var(--boltdeep)}
.ach h3{margin:3px 0 4px;font-family:'Archivo Black','Arial Black',sans-serif;font-size:15px;letter-spacing:.01em}
.ach p{margin:4px 0 0;font-size:13.5px;line-height:1.5;color:#C7D0DE}
.ach .open{position:absolute;top:12px;right:12px;font-family:'Space Mono',monospace;font-weight:700;font-size:9.5px;letter-spacing:.12em;color:var(--boltdeep);background:rgba(255,184,0,.14);border:1.5px dashed var(--bolt);border-radius:6px;padding:3px 8px}
.ach .sits{margin-top:7px;font-size:11.5px;color:var(--haze)}
.ach .sits b{color:var(--ink)}
.ach .sits .stars{display:inline-block;margin-left:6px;font-size:13px;letter-spacing:.12em;color:var(--bolt)}
.ach .sits .stars i{font-style:normal;color:#33415C}
.boss{background:var(--plate);color:var(--paper);border-radius:14px;padding:14px 16px;margin-bottom:10px;position:relative;overflow:hidden}
.boss:after{content:"";position:absolute;left:0;right:0;bottom:0;height:4px;background:linear-gradient(90deg,var(--bolt),#FFE08A,var(--bolt));background-size:200% 100%}
.boss .eyebrow{font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.12em;color:var(--bolt)}
.boss h3{font-family:'Archivo Black','Arial Black',sans-serif;font-size:19px;margin:3px 0 2px}
.boss .when{font-family:'Space Mono',monospace;font-size:12px;color:#B8C0CF}
.boss .when b{color:var(--boltdeep)}
.boss p{margin:8px 0 0;font-size:14px;line-height:1.5;color:#D9DEE9}
.boss.far{background:var(--card);color:var(--ink);border:2px solid var(--line)}
.boss.far:after{display:none}
.boss.far .eyebrow{color:var(--haze)}
.boss.far h3{font-size:16px;font-family:'Space Grotesk',sans-serif;font-weight:700}
.boss.far p{color:#C7D0DE}
.move{background:var(--plate);color:var(--paper);border-radius:16px;padding:17px 18px;position:relative;overflow:hidden}
.move:after{content:"";position:absolute;left:0;right:0;bottom:0;height:4px;background:linear-gradient(90deg,var(--bolt),#FFE08A,var(--bolt));background-size:200% 100%}
.move .eyebrow{font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.14em;color:var(--bolt)}
.move p{margin:8px 0 0;font-size:17px;line-height:1.5}
.move b{color:var(--bolt)}
.play{display:inline-block;margin-top:12px;font-family:'Archivo Black','Arial Black',sans-serif;font-size:15px;letter-spacing:.03em;color:#1A1205;background:linear-gradient(135deg,var(--bolt),#FFCF66);border-radius:12px;padding:12px 22px;text-decoration:none}
.play:focus-visible{outline:2px solid var(--paper);outline-offset:2px}
.foot{margin-top:26px;font-size:12.5px;color:var(--haze);line-height:1.6;border-top:2px solid var(--line);padding-top:14px}
.knav{position:fixed;left:0;right:0;bottom:0;background:rgba(10,17,30,.92);backdrop-filter:blur(10px);border-top:1px solid var(--line)}
.knav .in{max-width:640px;margin:0 auto;display:flex}
.knav a,.knav span.off{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;padding:10px 4px 12px;text-decoration:none;color:var(--haze);font-size:10px;letter-spacing:.08em;font-family:'Space Mono',monospace;font-weight:700}
.knav svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.knav a.on{color:var(--boltdeep)}
.knav span.off{opacity:.45}
.knav a:focus-visible{outline:2px solid var(--reef);outline-offset:-2px;border-radius:8px}
.rv{opacity:0;transform:translateY(14px);transition:opacity .5s ease,transform .5s ease}
.rv.in{opacity:1;transform:none}
@media (prefers-reduced-motion: no-preference){
 .boss:after,.move:after{animation:charge 2s linear infinite}
 @keyframes charge{0%{background-position:0 0}100%{background-position:200% 0}}
}
@media (prefers-reduced-motion: reduce){
 h1.word{animation:none !important}
 .rv{opacity:1;transform:none;transition:none}
}
"""

_JS = """
(function(){
 var rm = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
 if(rm) return;
 var io = ('IntersectionObserver' in window) ? new IntersectionObserver(function(es){
   es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
 },{threshold:.12}) : null;
 document.querySelectorAll('.rv').forEach(function(el){ io ? io.observe(el) : el.classList.add('in'); });
})();
"""


def _ground_block(brief):
    rows = brief.get("rows") or []
    if not rows:
        return ("<div class='section'>THIS WEEK'S GROUND</div>"
                "<div class='ground'><div class='row'>This week the sets keep "
                "working the current topics while we sync with what school "
                "posts — the ground refreshes here the moment it lands.</div>"
                "</div>")
    cards = []
    for r in rows:
        news = r.get("new") or []
        holds = [c for c in (r.get("covering") or []) if c not in news]
        parts = []
        if news:
            parts.append("<span class='chip'>NEW</span>"
                         + " &middot; ".join(f"<b>{_e(n)}</b>" for n in news))
        if holds:
            parts.append(("holds " if not news else "&middot; holds ")
                         + " and ".join(f"<b>{_e(h)}</b>" for h in holds[:3]))
        cards.append(f"<div class='ground rv'><div class='nm'>"
                     f"{_e(r['subject'].upper())}</div>"
                     f"<div class='row'>{' '.join(parts)}</div></div>")
    return ("<div class='section'>THIS WEEK'S GROUND &mdash; WHAT SCHOOL "
            f"COVERS</div>{''.join(cards)}")


def _grabs_block(grabs):
    if not grabs:
        return ""
    cards = []
    for c in grabs:
        gold = " gold" if c["fam"].startswith("MASTERY") else ""
        extra = ""
        if c.get("sits"):
            band = c["sits"]["band"]
            stars = ("<span class='stars'>" + "★" * band
                     + f"<i>{'★' * (4 - band)}</i></span>")
            extra = (f"<div class='sits'>Where it sits: "
                     f"<b>{_e(kw.BANDS[band])}</b>{stars} — the door's "
                     "open.</div>")
        elif c.get("way_in"):
            extra = ("<div class='sits'>The way in: <b>it's queued in this "
                     "week's rotation from tonight.</b></div>")
        cards.append(
            f"<div class='ach rv'><span class='i'>{c['icon']}</span>"
            f"<span class='body'><span class='fam{gold}'>{_e(c['fam'])}</span>"
            f"<h3>{_e(c['name'])}</h3><p>{_e(c['terms'])}</p>{extra}</span>"
            "<span class='open'>OPEN</span></div>")
    intro = ("<p class='intro rv'>Each one is a badge — it lands in the quiz "
             "the moment it's earned, and Friday's wrap tallies the week. "
             "Anything not taken rolls on. No strikes, no debt.</p>")
    return ("<div class='section rv'>UP FOR GRABS THIS WEEK</div>"
            f"{intro}{''.join(cards)}")


def _radar_block(radar, upcoming):
    cards = []
    if radar:
        days = radar["days"]
        when = "day out" if days == 1 else "days out"
        foc = radar.get("focus")
        line = "Your sets are already steering at it."
        if foc:
            line = (f"Your sets are already steering at it — "
                    f"<b>{_e(foc)}</b> is first in the rotation from tonight.")
        cards.append(
            f"<div class='boss rv'><span class='eyebrow'>BOSS APPROACHING"
            f"</span><h3>{_e(radar['task'])}</h3>"
            f"<div class='when'>{_e(radar.get('subject') or '')} &middot; "
            f"<b>{days} {when}</b></div><p>{line}</p></div>")
    for u in upcoming[:2]:
        days = u["days"]
        when = "day out" if days == 1 else "days out"
        cards.append(
            f"<div class='boss far rv'><span class='eyebrow'>ON THE HORIZON"
            f"</span><h3>{_e(u['task'])}"
            f"{' &middot; ' + _e(u['subject']) if u.get('subject') else ''}</h3>"
            f"<div class='when'>{days} {when}</div>"
            "<p>The rotation keeps its ground warm.</p></div>")
    if not cards:
        return ""
    return f"<div class='section rv'>BOSS RADAR &mdash; TESTS AND DATES</div>{''.join(cards)}"


def _move_block(play_url):
    btn = (f"<a class='play' href='{_e(play_url)}'>PLAY TONIGHT'S RUN "
           "&rarr;</a>" if play_url else "")
    return ("<div class='section rv'>THE WHOLE MOVE</div>"
            "<div class='move rv'><span class='eyebrow'>EVERYTHING ABOVE "
            "ADVANCES ONE WAY</span><p><b>Play tonight's run.</b> Five "
            f"minutes — everything above moves when you do.</p>{btn}</div>")


def _nav():
    board_icon = ("<svg viewBox='0 0 24 24' aria-hidden='true'>"
                  "<path d='M5 21V4'/><path d='M5 4h13l-2.5 4L18 12H5'/></svg>")
    wrap_icon = ("<svg viewBox='0 0 24 24' aria-hidden='true'>"
                 "<circle cx='12' cy='12' r='8.5'/>"
                 "<path d='M8.4 12.4l2.4 2.4 4.8-5.2'/></svg>")
    season_icon = ("<svg viewBox='0 0 24 24' aria-hidden='true'>"
                   "<path d='M5 20v-6M12 20V9.5M19 20V4.5'/>"
                   "<path d='M3 20h18'/></svg>")
    return ("<nav class='knav'><div class='in'>"
            f"<a class='on' aria-current='page' href='./'>{board_icon}"
            "<span>BOARD</span></a>"
            f"<a href='../'>{wrap_icon}<span>WRAP</span></a>"
            f"<span class='off'>{season_icon}<span>SEASON &middot; SOON</span>"
            "</span></div></nav>")


def render(facts, play_url=""):
    """The full self-contained board page. Refuses (ValueError) on any
    language-law breach — the wrap's own mechanism, same LAWS list — and on
    the board's own banned settle words."""
    name = facts["name"]
    week = facts["week_of"]
    week_label = dt.date.fromisoformat(week).strftime("%A %-d %B")
    stamp = report_page.build_stamp()

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="xpdaily-build" content="{_e(stamp)}" />
<meta name="xpdaily-week" content="{_e(week)}" />
<meta name="robots" content="noindex, nofollow" />
<meta name="theme-color" content="#0B1220" />
<title>XPDaily &mdash; {_e(name)}'s board</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;600;700&family=Space+Mono:wght@700&display=swap" />
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="top"><span class="brand">XPDAILY &middot; THE BOARD &middot; {_e(name.upper())}</span><span class="week">Week of {_e(week_label.split(' ', 1)[1])}</span></div>
  <div class="kick"><b>MONDAY</b>THE BOARD GOES UP &middot; SETTLES FRIDAY</div>
  <h1 class="word display">GAME ON.</h1>
  <p class="sub">The week of <b>{_e(week_label)}</b> is live &mdash; the ground
  school covers, this week's achievements, and what's on the radar.</p>
  {_ground_block(facts["brief"])}
  {_grabs_block(facts["grabs"])}
  {_radar_block(facts["radar"], facts["upcoming"])}
  {_move_block(play_url)}
  <p class="foot">The ground up top is the same week your parents' page shows
  from Monday evening &mdash; you see it first. The board itself is yours; the
  wrap tallies it Friday.<br>
  XP Daily &middot; week of {_e(week_label)}</p>
</div>
{_nav()}
<script>{_JS}</script>
</body>
</html>"""

    broken = kw.violations(page)
    if broken:
        raise ValueError(f"kid board breached language law: {broken}")
    low = page.lower()
    for banned in ("failed", "missed", "contract"):   # runs, never contracts;
        if banned in low:                             # rolls on, never failed
            raise ValueError(f"kid board carries a banned word: {banned}")
    if low.count("up for grabs") > 1:                 # said once (round 1)
        raise ValueError("kid board repeats 'up for grabs'")
    return page


# --------------------------------------------------------------------------- #
# Runner

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--date", default=None,
                    help="ISO date (default: today in Australia/Sydney)")
    ap.add_argument("--student", help="one player (default: all active)")
    ap.add_argument("--dry-run", action="store_true",
                    help="render previews only; no deploy, no URL registry")
    a = ap.parse_args()

    import netlify_deploy as deploy
    import roster

    if a.date:
        asof = dt.date.fromisoformat(a.date)
    else:
        from zoneinfo import ZoneInfo
        asof = dt.datetime.now(ZoneInfo("Australia/Sydney")).date()
    if asof.weekday() >= 5:
        print("weekend — no board day; nothing to do.")
        return 0

    priv = a.private_dir
    codes = [a.student] if a.student else roster.active()
    monday = (asof - dt.timedelta(days=asof.weekday())).isoformat()

    runs = (frun.load_json(os.path.join(priv, "work", "runs.json"), {}) or {}).get("runs", [])
    state = frun.load_json(os.path.join(priv, "work", "state.json"), {}) or {}
    tfiles = sorted(glob.glob(os.path.join(priv, "targets", "*.json")))
    targets = frun.load_json(tfiles[-1], {}) if tfiles else {}
    prev_targets = frun.load_json(tfiles[-2], {}) if len(tfiles) > 1 else {}
    # aliased seats (t1 → y8) borrow their curriculum at read time — the
    # sweep never writes them a block of their own (roster.alias_targets)
    roster.alias_targets(targets, codes)
    roster.alias_targets(prev_targets, codes)

    live_codes = [c for c in codes if c in state.get("students", {})]
    for c in codes:
        if c not in live_codes:
            print(f"[{c}] no ledger — skipped.")

    slugs = frun.slugs_for(priv, live_codes) if live_codes else {}
    urls_path = os.path.join(priv, BOARD_URLS)
    board_urls = frun.load_json(urls_path, {}) or {}
    ok_all = True
    for code in live_codes:
        facts = board_facts(code, asof, priv, runs, state, targets,
                            prev_targets)
        try:
            page = render(facts, play_url=roster.play_url(code))
        except ValueError as e:
            print(f"[{code}] REFUSED: {e} — nothing deployed for this seat.")
            ok_all = False
            continue
        print(f"[{code}] ground-subjects={len(facts['brief'].get('rows', []))} "
              f"up-for-grabs={len(facts['grabs'])} "
              f"radar={'y' if facts['radar'] else 'n'} streak={facts['streak']}")
        if a.dry_run:
            out = os.path.join(priv, "work", f"preview_board_{code}.html")
            open(out, "w").write(page)
            print(f"  DRY-RUN -> work/preview_board_{code}.html")
            continue
        path = f"{slugs[code]['wrap']}/board"
        if deploy.publish(path, page, kind="w"):
            board_urls[code] = {"url": deploy.url_for(path, kind="w"),
                                "week_of": monday}
            print("  board LIVE ✓ (per-kid URL withheld from public log)")
        else:
            print("  board deploy FAILED — the nudge sends without the link.")
            ok_all = False

    if not a.dry_run and live_codes:
        os.makedirs(os.path.dirname(urls_path), exist_ok=True)
        json.dump(board_urls, open(urls_path, "w"), indent=2)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
