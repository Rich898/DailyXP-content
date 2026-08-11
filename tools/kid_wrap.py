#!/usr/bin/env python3
"""
kid_wrap.py — the KID weekly wrap (KID-REPORT.md; REPORTING.md surface C).

A PLAYER CARD, NOT A REPORT CARD. If a line would sit comfortably in a school
report it is wrong here; if it would sit in a game's end-of-week summary it is
right. The voice is a fellow player — never a teacher, never a parent.

THE TRANSPARENCY LAW (KID-REPORT.md §2 — load-bearing):
  This page consumes the SAME objects the parent page consumes — the fact card
  from friday_report.build_card, the stories from report_stories.build_stories,
  the quote from report_stories.pick_quote. It never computes its own week facts,
  so the two surfaces physically cannot describe different weeks. The kid page
  ADDS game metrics (XP by day, streak, season total, level, badges, events);
  it never SUBTRACTS a fact. Every gap the parent report names arrives here as
  a TARGET (see targets_from()), framed as pursuit, not deficit.

THE SINGLE EXCEPTION — integrity. A quarantined teach-back is never surfaced
here in any form: no "didn't count", no inferable gap. The quote arrives
pre-gated by report_stories.pick_quote (the identical gate the parent page
uses) and nothing in this module reads teach-back text from anywhere else.
The LAWS list below bans the vocabulary outright, and render() refuses to
emit a page that violates it.

LANGUAGE LAWS (KID-REPORT.md §5, enforced by violations()):
  * praise the MOVE, never the player  * difficulty belongs to the set
  * hard is the point, said believably * rungs attach to TOPICS, never to him
  * no guilt, no nagging, no comparison (brother / class / his past self)
  * never speak for his parents

VISUAL LANGUAGE: the quiz shell (shell/template_v3.html) — paper/ink palette,
Archivo Black display, Space Mono numbers, skewed speed segments, ink event
plates, bolt-gold badges. It should feel like the game, because it is.

Self-contained HTML, zero fetch, noindex — the same privacy model as
report_page.py. Deployed by friday_report_run.py to /w/<slug>/.
"""
import html
import re
from datetime import date, timedelta

# --------------------------------------------------------------------------- #
# The level curve — the long arc behind the season total.
#
# Deterministic and deliberately front-loaded: early levels land fast (a level
# roughly every 1-2 good weeks at the start of a season), later ones stretch.
# This is a GAME economy element (KID-REPORT.md §3), not a target — the planner
# picks question difficulty, so XP is a measure of showing up, and a level is a
# milestone on that, never an ask. No surface ever says "get N XP".
LEVEL_BASE = 2000     # cost of level 1 -> 2
LEVEL_STEP = 400      # each subsequent level costs this much more


def level_for(total):
    """(level, xp_into_level, xp_needed_for_next) from a season total."""
    total = max(0, int(total or 0))
    lvl, spent, cost = 1, 0, LEVEL_BASE
    while total - spent >= cost:
        spent += cost
        lvl += 1
        cost += LEVEL_STEP
    return lvl, total - spent, cost


# --------------------------------------------------------------------------- #
# Language laws — banned constructions, checked against the FULL rendered page.
# Case-insensitive substring/regex checks. Kept blunt on purpose: a false
# positive costs a rewrite; a false negative costs a kid's trust.

LAWS = [
    # person-level praise (Hattie & Timperley — the weakest feedback there is)
    r"you'?re (so )?(smart|clever|brilliant|gifted|talented|a natural)",
    r"such a (smart|clever|bright)",
    # rung-as-label-for-the-child — the banned construction
    r"you'?re an? [\w' -]*(not yet|knows it|can list it|can connect it|can apply)[\w' -]*(kid|player|student)",
    r"(kid|player|student) who (can only|just) (knows|lists)",
    # guilt / nagging
    r"you should have", r"why didn'?t you", r"you need to try", r"try harder",
    r"if only you", r"you failed", r"\bdisappointing\b", r"\blazy\b",
    # comparison — brother, class, cohort, his own past self as a rebuke
    r"your brother", r"\bharrison did\b", r"\broshan did\b",
    r"(rest|top|most) of (the|your) class", r"other (kids|students|players)",
    r"better than you", r"used to be better", r"last week you were",
    # speaking for his parents
    r"your (mum|mom|dad|parents) (will|would|is|are)",
    # integrity vocabulary — never on a kid surface, in any form
    r"didn'?t count", r"\bcheat", r"\bquarantin", r"\bintegrity\b",
    r"\bflagged\b", r"not your own (words|writing)", r"\bplagiar",
    # school-report register that has no business on a player card
    r"\bmust improve\b", r"\bunsatisfactory\b", r"\bunderperform",
]


def violations(text):
    """Law breaches in a rendered page (checked on tag-stripped, entity-unescaped
    text — an escaped apostrophe must not smuggle a banned construction past)."""
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text or "")).lower()
    return [p for p in LAWS if re.search(p, plain)]


# --------------------------------------------------------------------------- #
# Game facts — the ADDITIVE layer (allowed here, deliberately not on the
# parent page: motivating to a player, misleading to a parent).

_EVENT_KINDS = (("BLITZ", "Blitz", "\u26a1"),
                ("BATTLEGROUND", "Battleground", "\U0001f6e1"),
                ("BOSS", "Battleground", "\U0001f6e1"))  # boss slot = battleground era


def _event_kind(tag):
    t = (tag or "").upper()
    for key, label, icon in _EVENT_KINDS:
        if key in t or (key == "BOSS" and t.endswith(".5")):
            return {"label": label, "icon": icon}
    return None


def game_facts(runs, student, week_days, earned_this_week, asof,
               season_total=0, accuracy=None):
    """Everything game-side the wrap shows beyond the shared card/stories.

    Reads run scores/dates/tags and the badge ledger only — never teach-back
    text (integrity law: nothing here can leak a quarantined row).
    """
    from soundbyte import current_school_streak

    mine = [r for r in runs if r.get("student") == student]
    in_week = [r for r in mine if r.get("run_date") in week_days]

    # XP by day — best run per day (the same best-of-day rule every layer uses)
    best = {}
    for r in in_week:
        d = r["run_date"]
        sc = int(r.get("score") or 0)
        if d not in best or sc > best[d]["pts"]:
            best[d] = {"pts": sc, "tag": r.get("tag") or ""}
    days = []
    for iso in week_days:
        wd = date.fromisoformat(iso).strftime("%a")
        row = best.get(iso)
        days.append({"day": wd, "date": iso,
                     "pts": row["pts"] if row else None,
                     "event": _event_kind(row["tag"]) if row else None})

    # streak — school-day semantics, one definition everywhere (soundbyte /
    # achievements). Anchored on the LAST PLAYED day so a wrap built before
    # tonight's run is ingested never zeroes an honest streak.
    present = {r.get("run_date") for r in mine if r.get("run_date")}
    played = sorted(d for d in present if d <= asof.isoformat())
    streak = 0
    if played:
        streak = current_school_streak(present, date.fromisoformat(played[-1]))

    # events this week, in order
    events = []
    for r in sorted(in_week, key=lambda r: r.get("run_date") or ""):
        kind = _event_kind(r.get("tag"))
        if not kind:
            continue
        qs = [q for q in (r.get("questions") or [])
              if q.get("ok") is not None and not q.get("skipped")
              and q.get("phase") != "teach"]
        events.append({"label": kind["label"], "icon": kind["icon"],
                       "day": date.fromisoformat(r["run_date"]).strftime("%a"),
                       "pts": int(r.get("score") or 0),
                       "zones_ok": sum(1 for q in qs if q.get("ok")),
                       "zones": len(qs)})

    # overall accuracy — ONE number, framed as the line to beat (the ratified
    # lean on KID-REPORT.md §9). Same >=10 floor the parent trend uses; the
    # per-subject split stays parent-side (report-card territory over here).
    acc = None
    if accuracy:
        right = sum(v.get("right", 0) for v in accuracy.values())
        asked = sum(v.get("asked", 0) for v in accuracy.values())
        if asked >= 10:
            acc = {"pct": round(100 * right / asked), "right": right, "asked": asked}

    lvl, into, need = level_for(season_total)
    return {"days": days, "streak": streak, "events": events,
            "season_total": int(season_total or 0),
            "level": {"n": lvl, "into": into, "need": need},
            "accuracy": acc,
            "badges": list(earned_this_week or [])}


# --------------------------------------------------------------------------- #
# Targets — every gap the parent report names, re-dressed as pursuit.
# This function IS the transparency law made executable: its input is the same
# card + stories the parent page renders, and test_kid_wrap locks the union.

def targets_from(card, stories):
    """Ordered stalk-list: [{topic, subject?, state, trace?, misconception?,
    flavour}] — the union of every gap surface on the parent page."""
    seen, out = set(), []

    def add(topic, flavour, subject=None, state=None, trace=None, misc=None):
        if not topic or topic in seen:
            return
        seen.add(topic)
        out.append({"topic": topic, "subject": subject, "state": state,
                    "trace": trace, "misconception": misc, "flavour": flavour})

    for s in stories or []:
        if s.get("status") == "TO CLOSE" and s.get("topic"):
            add(s["topic"], "close", s.get("subject"), s.get("state"),
                s.get("trace"), s.get("misconception"))
    r = card.get("radar") or {}
    if r.get("focus"):
        add(r["focus"], "assess", r.get("subject"))
    a = card.get("action") or {}
    if a.get("kind") in ("repair", "behind") and a.get("topic"):
        add(a["topic"], a["kind"], a.get("subject"))
    for subj, topic in (card.get("standing") or {}).get("exceptions") or []:
        add(topic, "behind", subj)
    for topic in (card.get("movement") or {}).get("down") or []:
        add(topic, "slid")
    return out


# --------------------------------------------------------------------------- #
# Rendering

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;600;700&family=Space+Mono:wght@700&display=swap');
:root{--paper:#F7F8F4;--ink:#101B2D;--flare:#FF4D29;--reef:#0E6BA8;--kelp:#0E8A5F;
--haze:#7A8496;--line:#D9DDD3;--bolt:#FFB800;--boltdeep:#8A5A00;--plate:#0E1B2D}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:'Space Grotesk',system-ui,sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:640px;margin:0 auto;padding:20px 16px 56px}
.display{font-family:'Archivo Black','Arial Black',sans-serif;letter-spacing:-.01em}
.num{font-family:'Space Mono',ui-monospace,monospace;font-weight:700}
.top{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.top .brand{font-size:11px;letter-spacing:.16em;color:var(--haze)}
.top .week{font-size:11px;color:var(--haze)}
.kick{margin:24px 0 2px;font-family:'Space Mono',ui-monospace,monospace;font-weight:700;font-size:11px;letter-spacing:.14em;color:var(--haze)}
.kick b{color:var(--boltdeep);background:#FFF3D6;border:1.5px solid var(--bolt);border-radius:6px;padding:1px 7px;margin-right:6px}
h1.word{font-size:52px;line-height:1;margin:2px 0 8px}
.strong{color:var(--kelp)}.solid{color:var(--reef)}.quiet{color:var(--haze)}.slower{color:var(--flare)}
.sub{font-size:17px;line-height:1.45;margin:4px 0 24px;max-width:52ch}
.section{margin:30px 0 10px;font-size:11px;letter-spacing:.15em;color:var(--haze);font-weight:700}
/* THE RUN — the inverted ink plate, the game's own event-banner voice */
.run{background:var(--plate);color:var(--paper);border-radius:16px;padding:18px 18px 20px;position:relative;overflow:hidden}
.run:after{content:"";position:absolute;left:0;right:0;bottom:0;height:5px;background:linear-gradient(90deg,var(--flare),var(--bolt),var(--flare));background-size:200% 100%}
.bars{display:flex;gap:8px;align-items:flex-end;height:96px;margin:6px 0 4px}
.bar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:5px;height:100%}
.bar .col{width:100%;border-radius:6px 6px 3px 3px;background:linear-gradient(180deg,var(--bolt),var(--flare));min-height:6px}
.bar .col.off{background:none;border:1.5px dashed #33415C;min-height:26px;border-radius:6px}
.bar .v{font-family:'Space Mono',monospace;font-size:10px;color:#B8C0CF;line-height:1}
.bar .v.ev{color:var(--bolt)}
.dayrow{display:flex;gap:8px;margin-top:2px}
.dayrow span{flex:1;text-align:center;font-size:10px;letter-spacing:.1em;color:#8B94A8}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.stat{flex:1 1 44%;background:#16233B;border:1px solid #26344F;border-radius:12px;padding:10px 12px;min-width:130px}
.stat .k{font-size:10px;letter-spacing:.12em;color:#8B94A8}
.stat .v{font-size:22px;margin-top:3px;color:var(--paper)}
.stat .v i{font-style:normal;font-size:13px;color:#8B94A8;margin-left:4px}
.stat .lv{height:7px;border-radius:99px;background:#26344F;overflow:hidden;margin-top:8px}
.stat .lv span{display:block;height:100%;background:linear-gradient(90deg,var(--bolt),var(--flare));border-radius:99px}
.stat .n{font-size:10.5px;color:#8B94A8;margin-top:5px}
.runline{font-size:13.5px;color:#B8C0CF;margin:14px 0 0;line-height:1.5}
/* WHAT YOU BEAT */
.beat{background:#fff;border:2px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px}
.tagchip{display:inline-block;font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.1em;padding:3px 8px;border-radius:6px;margin-bottom:8px;background:#E8F4EE;color:var(--kelp)}
.tagchip.rank{background:#FFF3D6;color:var(--boltdeep);border:1.5px solid var(--bolt)}
.beat h3{margin:0 0 4px;font-size:17px;line-height:1.3}
.beat p{margin:6px 0 0;font-size:14.5px;line-height:1.5;color:#3A4356}
.dots{display:flex;gap:4px;margin-top:8px;align-items:center}
.dots u{text-decoration:none;font-size:10px;color:var(--haze);margin-right:3px;letter-spacing:.08em}
.dots i{font-style:normal;width:8px;height:8px;border-radius:99px;background:#D6D9D1;display:inline-block}
.dots i.y{background:var(--kelp)} .dots i.n{background:#E8963C}
.ladder{display:flex;gap:4px;margin-top:10px;font-size:10px;color:var(--haze);flex-wrap:wrap}
.ladder span{padding:3px 7px;border-radius:6px;background:#EEF1EA}
.ladder span.on{background:var(--kelp);color:#fff;font-weight:700}
.badges{display:flex;flex-direction:column;gap:8px;margin-bottom:10px}
.badge{display:flex;align-items:center;gap:12px;border:2px solid var(--bolt);background:linear-gradient(135deg,#FFF9EB,#FFF3D6);border-radius:12px;padding:10px 13px}
.badge .bic{font-size:24px;line-height:1}
.badge .bnm{font-family:'Archivo Black','Arial Black',sans-serif;font-size:14px;color:var(--boltdeep)}
.badge .bds{font-size:12.5px;color:var(--haze);margin-top:1px}
/* YOUR OWN WORDS */
.quote{background:#fff;border:2px solid var(--line);border-left:5px solid var(--kelp);border-radius:12px;padding:15px 17px;font-size:16px;line-height:1.55}
.quote .attr{display:block;margin-top:9px;font-size:12px;color:var(--haze)}
.quote .why{display:block;margin-top:8px;font-size:13.5px;color:#3A4356;line-height:1.5}
/* STALKING */
.stalkintro{font-size:13.5px;color:var(--haze);margin:-2px 0 10px;line-height:1.5}
.stalk{background:#fff;border:2px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px}
.stalk h3{margin:0 0 4px;font-size:17px;line-height:1.3}
.stalk .eyebrow{font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.12em;color:var(--flare)}
.stalk p{margin:7px 0 0;font-size:14.5px;line-height:1.5;color:#3A4356}
.scale{margin:10px 0 2px}
.scale .track{display:flex;gap:3px;height:9px}
.scale .track b{flex:1;border-radius:99px;background:#E8EAE4}
.scale .track b.on0{background:#E8663C}.scale .track b.on1{background:#E8963C}
.scale .track b.on2{background:#7FA83C}.scale .track b.on3{background:var(--kelp)}
.scale .lab{margin-top:5px;font-size:11.5px;color:var(--haze)}
.scale .lab b{color:var(--ink)}
.trap{background:#FAFBF8;border-left:3px solid #E8963C;padding:8px 12px;margin-top:9px;font-size:13.5px;line-height:1.5}
.trap b{color:var(--flare)}
.boss{background:var(--plate);color:var(--paper);border:none;position:relative;overflow:hidden}
.boss:after{content:"";position:absolute;left:0;right:0;bottom:0;height:4px;background:linear-gradient(90deg,var(--bolt),#FFE08A,var(--bolt));background-size:200% 100%}
.boss .eyebrow{color:var(--bolt)}
.boss h3{font-family:'Archivo Black','Arial Black',sans-serif;font-size:20px}
.boss .when{font-family:'Space Mono',monospace;font-size:12px;color:#B8C0CF;margin-top:2px}
.boss p{color:#D9DEE9}
.sure .eyebrow{color:var(--reef)}
/* THE ONE MOVE */
.move{background:var(--ink);color:var(--paper);border-radius:16px;padding:17px 18px}
.move .eyebrow{font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.14em;color:var(--bolt)}
.move p{margin:8px 0 0;font-size:17px;line-height:1.5}
.move b{color:var(--bolt)}
/* LADDER EXPLAINER */
.how{background:#fff;border:2px dashed var(--line);border-radius:14px;padding:14px 16px}
.how p{margin:8px 0 0;font-size:13.5px;line-height:1.55;color:#3A4356}
.foot{margin-top:26px;font-size:12.5px;color:var(--haze);line-height:1.6;border-top:2px solid var(--line);padding-top:14px}
@media (prefers-reduced-motion: no-preference){
 .run:after,.boss:after{animation:charge 2s linear infinite}
 @keyframes charge{0%{background-position:0 0}100%{background-position:200% 0}}
}
"""

RUNGS = [("not_yet", "not yet"), ("knows", "knows it"), ("lists", "can list it"),
         ("connects", "can connect it"), ("applies", "can apply it elsewhere")]
RUNG_LABEL = dict(RUNGS)

# Where a topic sits — the SAME bands and colours as the parent page, because
# they are the same facts. Only the surrounding words change register.
BANDS = [("Not started yet", 0), ("Getting started", 0), ("Building", 1),
         ("Nearly there", 2), ("Solid", 3)]
STATE_BAND = {"untested": 1, "REPAIR": 1, "shaky": 2, "developing": 3, "solid": 4}

# The week-word — SAME word as the parent page (same engine), game-flavoured.
WORD_CAP = {"strong": "Strong", "solid": "Solid", "quiet": "Quiet", "slower": "Harder"}
WORD_SUB = {
    "strong": "Ground taken. The kind of week that moves a season.",
    "solid": "Showed up, held the line. Most good weeks look exactly like this.",
    "quiet": "A light week on the board. The run's still here — it picks back up when you do.",
    "slower": "The sets came in harder this week. That's the game finding your edge, "
              "and the edge is where topics rank up.",
}
DIR_TAIL = {"up": "climbing on last week", "flat": "level with last week",
            "down": "off last week's pace"}

BADGE_ACT = {
    "First Blood": "first run ever on the board",
    "Clean Run": "a whole run — zero lucky guesses, zero confident-wrongs",
    "Locked It": "took a topic all the way to solid",
    "Full Clear": "every live topic in a subject, solid",
    "Comeback": "pulled a topic out of REPAIR",
    "Untouchable": "a solid topic held through three spaced checks",
    "Perfect Week": "all five school nights, played",
    "Calm Hands": "slowed down and landed one that used to get rushed",
    "Sure Shot": "called Sure on a repair topic — and it was",
    "Boss Slayer": "cleared Friday's event, every slot",
    "Blitz Master": "beat your own Blitz record",
}
BADGE_ICON = {"First Blood": "\U0001fa78", "Clean Run": "\U0001f9ca",
              "Locked It": "\U0001f512", "Full Clear": "\U0001f4a0",
              "Comeback": "\U0001f501", "Untouchable": "\U0001f6e1",
              "Streak": "\U0001f525", "Perfect Week": "\U0001f4c5",
              "Calm Hands": "\U0001f9d8", "Sure Shot": "\U0001f3af",
              "Boss Slayer": "\U0001f409", "Blitz Master": "\u26a1"}


def _e(s):
    return html.escape(str(s if s is not None else ""))


# ---- hero -------------------------------------------------------------------

def _hero(card):
    word = card["week_word"]["word"]
    if card.get("baseline"):
        kick = "<div class='kick'><b>WEEK 1</b>THE START LINE</div>"
    else:
        tail = DIR_TAIL.get(card["week_word"]["direction"], "")
        kick = f"<div class='kick'>THE WEEK'S READ{' · ' + _e(tail) if tail else ''}</div>"
    sub = WORD_SUB.get(word, "")
    if card.get("baseline") and word == "solid":
        sub = ("First week on the board — the map's drawn, the ledger's live, "
               "and everything below is the opening state of the season.")
    return (f"{kick}<h1 class='word display {word}'>{WORD_CAP.get(word, word)}</h1>"
            f"<p class='sub'>{_e(sub)}</p>")


# ---- the run ----------------------------------------------------------------

def _run_block(game, card):
    days = game["days"]
    played = [d for d in days if d["pts"] is not None]
    peak = max((d["pts"] for d in played), default=0) or 1
    bars, labels = [], []
    for d in days:
        if d["pts"] is None:
            bars.append("<div class='bar'><div class='col off'></div>"
                        "<span class='v'>&mdash;</span></div>")
        else:
            h = max(10, round(84 * d["pts"] / peak))
            ev = d.get("event")
            v = (f"{ev['icon']}{d['pts']:,}" if ev else f"{d['pts']:,}")
            bars.append(f"<div class='bar'><div class='col' style='height:{h}px'></div>"
                        f"<span class='v{' ev' if ev else ''}'>{v}</span></div>")
        labels.append(f"<span>{_e(d['day'].upper())}</span>")

    lvl = game["level"]
    pct = round(100 * lvl["into"] / lvl["need"]) if lvl["need"] else 0
    left = lvl["need"] - lvl["into"]
    chips = [
        f"<div class='stat'><div class='k'>STREAK</div><div class='v num'>"
        f"\U0001f525 {game['streak']}<i>school nights</i></div></div>",
        f"<div class='stat'><div class='k'>SEASON</div>"
        f"<div class='v num'>{game['season_total']:,}<i>XP</i></div></div>",
        f"<div class='stat'><div class='k'>LEVEL</div><div class='v num'>{lvl['n']}</div>"
        f"<div class='lv'><span style='width:{pct}%'></span></div>"
        f"<div class='n num'>{left:,} XP to Lv {lvl['n'] + 1}</div></div>",
    ]
    if game.get("accuracy"):
        a = game["accuracy"]
        tail = "the start-line number" if card.get("baseline") else "the line to beat"
        chips.append(f"<div class='stat'><div class='k'>SHOTS LANDED</div>"
                     f"<div class='v num'>{a['pct']}%</div>"
                     f"<div class='n'>{a['right']} of {a['asked']} — {tail}</div></div>")

    line = ""
    if not played:
        line = ("<p class='runline'>Nothing on the board this week — no debt, no "
                "backlog. The rotation just carries everything forward.</p>")
    elif any(d["pts"] is None for d in days):
        line = ("<p class='runline'>Blank days carry no debt — those topics simply "
                "stay in the rotation. Points ride on difficulty, so day-to-day "
                "swings mean the sets changed, not you.</p>")
    else:
        line = ("<p class='runline'>Points ride on difficulty — day-to-day swings "
                "mean the sets changed, not you.</p>")

    return ("<div class='section'>THE RUN</div><div class='run'>"
            f"<div class='bars'>{''.join(bars)}</div>"
            f"<div class='dayrow'>{''.join(labels)}</div>"
            f"<div class='chips'>{''.join(chips)}</div>{line}</div>")


# ---- what you beat ----------------------------------------------------------

def _dots(trace):
    if not trace:
        return ""
    seen = {}
    for t in trace:
        d = t.get("day", "")
        if d not in seen or t.get("ok"):
            seen[d] = t.get("ok")
    dots = "".join(f"<i class='{'y' if v else 'n' if v is False else ''}'></i>"
                   for v in seen.values())
    return f"<div class='dots'><u>THIS WEEK</u>{dots}</div>"


def _beat_block(card, stories, game):
    cards = []
    for s in stories or []:
        if s.get("status") == "RESOLVED":
            cards.append(
                f"<div class='beat'><span class='tagchip'>TAKEN DOWN</span>"
                f"<h3>{_e(s['topic'])}</h3>"
                "<p>Wrong early in the week, right by the end — turned inside five "
                "days. It comes back once more to prove the hold.</p>"
                f"{_dots(s.get('trace'))}</div>")
        elif s.get("status") == "TRENDING WELL":
            cards.append(
                f"<div class='beat'><span class='tagchip'>RAN CLEAN</span>"
                f"<h3>{_e(s['topic'])}</h3>"
                "<p>Used to bite; ran clean all week. It drops to light patrols and "
                "the freed slots go to new ground.</p>"
                f"{_dots(s.get('trace'))}</div>")
        elif s.get("status") == "DEEPENED":
            frm = RUNG_LABEL.get(s.get("from"), s.get("from"))
            to = RUNG_LABEL.get(s.get("to"), s.get("to"))
            rungs = "".join(
                f"<span class='{'on' if k == s.get('to') else ''}'>{_e(v)}</span>"
                for k, v in RUNGS)
            cards.append(
                f"<div class='beat'><span class='tagchip rank'>RANK UP</span>"
                f"<h3>{_e(s['topic'])} &mdash; {_e(frm)} \u2192 {_e(to)}</h3>"
                "<p>That jump can't be grinded — only an explanation gets a topic "
                "there. Yours did.</p>"
                f"<div class='ladder'>{rungs}</div></div>")

    for topic in (card.get("movement") or {}).get("up") or []:
        if any(s.get("topic") == topic for s in stories or []):
            continue
        cards.append(f"<div class='beat'><span class='tagchip'>MOVED UP</span>"
                     f"<h3>{_e(topic)}</h3>"
                     "<p>Stepped up a band on the ledger this week — the rotation "
                     "eases off it and spends the time elsewhere.</p></div>")

    for ev in game.get("events") or []:
        if ev["label"] == "Blitz":
            cards.append(f"<div class='beat'><span class='tagchip rank'>"
                         f"{ev['icon']} BLITZ</span><h3>{ev['pts']:,} XP on the "
                         f"doubled clock</h3><p>{_e(ev['day'])}'s tempo event — "
                         "speed under pressure, banked.</p></div>")
        else:
            pct = round(100 * ev["zones_ok"] / ev["zones"]) if ev["zones"] else 0
            tail = (" The field's yours this week." if pct == 100 else
                    " Contested ground carries no penalty — it just comes back around.")
            cards.append(f"<div class='beat'><span class='tagchip rank'>"
                         f"{ev['icon']} BATTLEGROUND</span>"
                         f"<h3>Claimed {ev['zones_ok']} of {ev['zones']} zones</h3>"
                         f"<p>{_e(ev['day'])}'s claim on the week's hardest ground."
                         f"{tail}</p></div>")

    badges = ""
    if game.get("badges"):
        rows = []
        for b in game["badges"]:
            nm = b.get("badge", "")
            base = nm.split(" ")[0] if nm.startswith("Streak") else nm
            icon = BADGE_ICON.get(base, "\U0001f3c5")
            act = b.get("label") or BADGE_ACT.get(base) or "earned this week"
            if base == "Streak":
                act = b.get("label") or "school nights in a row"
            rows.append(f"<div class='badge'><span class='bic'>{icon}</span>"
                        f"<span><span class='bnm'>{_e(nm)}</span>"
                        f"<div class='bds'>{_e(act)}</div></span></div>")
        badges = f"<div class='badges'>{''.join(rows)}</div>"

    if not cards and not badges:
        body = ("<div class='beat'><p style='margin:0'>Nothing closed out this week "
                "— the board below is still standing. That's a list, not a verdict: "
                "everything on it is already scheduled to come back around.</p></div>")
    else:
        body = badges + "".join(cards)
    return f"<div class='section'>WHAT YOU BEAT</div>{body}"


# ---- your own words ---------------------------------------------------------

def _words_block(quote):
    if not quote:
        return ""
    attr = "written by you this week, quoted word for word"
    if quote.get("subject"):
        attr = f"{_e(quote['subject'])} teach-back &middot; {attr}"
    depth = quote.get("depth")
    why = ""
    if depth in ("connects", "applies"):
        why = ("<span class='why'>Picking answers can't take a topic past "
               "<b>can list it</b> — explaining can. This is what that looks like.</span>")
    return ("<div class='section'>FINISHING MOVE &mdash; YOUR OWN WORDS</div>"
            f"<div class='quote'>&ldquo;{_e(quote['text'])}&rdquo;"
            f"<span class='attr'>{attr}</span>{why}</div>")


# ---- stalking ---------------------------------------------------------------

def _scale(state):
    band = STATE_BAND.get(state, 1)
    label, colour = BANDS[band][0], BANDS[band][1]
    segs = "".join(f"<b class='{'on' + str(colour) if i < band else ''}'></b>"
                   for i in range(4))
    return (f"<div class='scale'><div class='track'>{segs}</div>"
            f"<div class='lab'>Where it sits: <b>{_e(label)}</b></div></div>")


def _assess_card(radar):
    if not radar:
        return ""
    days = radar["days"]
    when = "days out" if days != 1 else "day out"
    read = radar["readiness"]
    foc = radar.get("focus")
    if read == "ready":
        line = "You're armed for it — the ground it covers is holding."
    elif read == "building":
        line = "Nearly armed." + (f" <b>{_e(foc)}</b> is the missing piece — "
                                  "it's first in the rotation." if foc else "")
    else:
        line = "Long runway on this one." + (f" <b>{_e(foc)}</b> is the opening move."
                                             if foc else "")
    return (f"<div class='stalk boss'><span class='eyebrow'>BOSS APPROACHING</span>"
            f"<h3>{_e(radar['task'])}</h3>"
            f"<div class='when'>{_e(radar.get('subject') or '')} &middot; "
            f"{days} {when}</div><p>{line}</p></div>")


def _stalk_block(card, stories):
    targets = targets_from(card, stories)
    cards = [_assess_card(card.get("radar"))]

    FLAV = {
        "close": "Fresh gap, small and specific — it's back next week.",
        "assess": "It guards the ground the test covers — first in the rotation.",
        "repair": "Due a revisit — the rotation has it queued.",
        "behind": "The syllabus has moved onto this one — a few focused minutes "
                  "brings it into range.",
        "slid": "Slipped a step this week. Happens — it's re-queued and comes "
                "back around.",
    }
    for t in targets:
        misc = t.get("misconception")
        trap = ""
        if misc and misc.get("why"):
            trap = (f"<div class='trap'>How it got you: picked <b>{_e(misc['picked'])}</b> "
                    f"&mdash; the answer was <b>{_e(misc['correct'])}</b>. "
                    f"{_e(misc['why'])} It goes down the moment you can say why.</div>")
        scale = _scale(t["state"]) if t.get("state") else ""
        cards.append(f"<div class='stalk'><span class='eyebrow'>TARGET</span>"
                     f"<h3>{_e(t['topic'])}</h3>{scale}"
                     f"<p>{_e(FLAV.get(t['flavour'], FLAV['close']))}</p>"
                     f"{trap}{_dots(t.get('trace'))}</div>")

    w = next((s for s in stories or [] if s.get("status") == "WATCHING"), None)
    if w:
        cards.append(
            f"<div class='stalk sure'><span class='eyebrow'>SURE-CHECK</span>"
            f"<h3>{w['count']} of {w['of']} Sure calls didn't land</h3>"
            "<p>Sureness is its own stat — the quiz keeps pairing it with results, "
            "so it trains like everything else. No move needed; watch it settle.</p></div>")

    body = "".join(c for c in cards if c)
    if not body:
        body = ("<div class='stalk'><p style='margin:0'>Nothing stalking you this "
                "week — the board is clear. The rotation keeps testing the "
                "perimeter anyway; that's how it stays clear.</p></div>")
    intro = ("<p class='stalkintro'>Targets, not verdicts — everything here is "
             "already scheduled to come back around. Gaps live on this list "
             "exactly as long as they take to close.</p>")
    return f"<div class='section'>STALKING YOU NEXT WEEK</div>{intro}{body}"


# ---- the one move -----------------------------------------------------------

def _move_block(card):
    a = card.get("action") or {}
    k = a.get("kind")
    if k == "assess":
        p = (f"Before the {_e(a.get('task', 'test'))}: say <b>{_e(a['topic'])}</b> "
             "out loud in four sentences, no notes. Explaining is the finishing "
             "move — it's the only thing that ranks a topic past listing.")
    elif k == "repair":
        p = (f"Say <b>{_e(a['topic'])}</b> out loud in four sentences, no notes. "
             "It's due, and explaining is what ranks it up.")
    elif k == "behind":
        p = (f"Five minutes on <b>{_e(a['topic'])}</b> — the syllabus has moved "
             "onto it, and five minutes now puts it in range of the rotation.")
    elif k == "ask":
        p = (f"<b>{_e(a['topic'])}</b> is solid — so teach it to someone out loud "
             "tonight. Teaching a thing is the strongest lock there is.")
    else:
        p = "No repairs on the board. The nightly run is the whole move."
    return ("<div class='section'>THE ONE MOVE</div><div class='move'>"
            f"<span class='eyebrow'>HIGHEST-LEVERAGE PLAY</span><p>{p}</p></div>")


# ---- the ladder explainer ---------------------------------------------------

def _ladder_block():
    rungs = "".join(f"<span>{_e(v)}</span>" for _, v in RUNGS)
    return ("<div class='section'>THE LADDER &mdash; HOW TOPICS RANK UP</div>"
            "<div class='how'>"
            f"<div class='ladder'>{rungs}</div>"
            "<p>Speed questions top out at <b>knows it</b>. Steady questions top "
            "out at <b>can list it</b> — four options can prove recognition, never "
            "explanation. The only way a topic reaches <b>can connect it</b> is the "
            "teach-back: explaining the thing in your own words. Use it somewhere "
            "it wasn't taught and it hits <b>can apply it elsewhere</b>.</p>"
            "<p>It's the one track in the game that can't be grinded — which is "
            "exactly why it's the one that counts in an exam room.</p></div>")


# ---- assembly ---------------------------------------------------------------

def render(card, stories=None, quote=None, game=None):
    """Full self-contained HTML for one kid-week wrap. Raises ValueError if the
    rendered page breaches a language law — a broken page is better than a
    law-breaking one, and the caller's deploy simply skips."""
    stories = stories or []
    game = game or {"days": [], "streak": 0, "events": [], "season_total": 0,
                    "level": {"n": 1, "into": 0, "need": LEVEL_BASE},
                    "accuracy": None, "badges": []}
    name = card["name"].split()[0]
    week = card.get("week_of", "")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="noindex, nofollow" />
<meta name="theme-color" content="#F7F8F4" />
<title>XPDaily — {_e(name)}'s wrap</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="top"><span class="brand">XPDAILY &middot; WEEK WRAP &middot; {_e(name.upper())}</span><span class="week">Week of {_e(week)}</span></div>
  {_hero(card)}
  {_run_block(game, card)}
  {_beat_block(card, stories, game)}
  {_words_block(quote)}
  {_stalk_block(card, stories)}
  {_move_block(card)}
  {_ladder_block()}
  <p class="foot">Your parents' Friday page shows this exact week — same facts,
  different dressing. Nothing here they don't see; nothing there you don't.<br>
  XP Daily &middot; week of {_e(week)} &middot; this page is yours.</p>
</div>
</body>
</html>"""

    broken = violations(page)
    if broken:
        raise ValueError(f"kid wrap breached language law: {broken}")
    return page
