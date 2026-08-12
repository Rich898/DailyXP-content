#!/usr/bin/env python3
"""
kid_wrap.py — the KID weekly wrap (KID-REPORT.md; REPORTING.md surface C). v2.

A PLAYER CARD, NOT A REPORT CARD — and v2 is built like a game's end-of-week
screen: an identity (rank + insignia off the season level), a payoff (the
unlocks cabinet, with progress toward the NEXT badge), and coaching (the top
three targets each arrive with a how-to-beat-it, because a game that shows you
the counter is a game you come back to).

THE TRANSPARENCY LAW (KID-REPORT.md §2 — load-bearing):
  This page consumes the SAME objects the parent page consumes — the fact card
  from friday_report.build_card, the stories from report_stories.build_stories,
  the quote from report_stories.pick_quote — and never computes its own week
  facts. The kid page ADDS game metrics (rank, XP by day, streak, level,
  badges, events, coaching); it never SUBTRACTS a fact. The hit list leads
  with the top THREE targets, and every remaining parent-named gap still
  renders in the also-on-the-board line — concentration of effort, never
  omission of fact.

THE SINGLE EXCEPTION — integrity. A quarantined teach-back is never surfaced
here in any form. The quote arrives pre-gated by report_stories.pick_quote
(the identical gate the parent page uses); nothing in this module reads
teach-back text from anywhere else; and the LAWS list bans the vocabulary
outright. render() refuses to emit a page that breaches a law.

LANGUAGE LAWS (KID-REPORT.md §5, enforced by violations()):
  * praise the MOVE, never the player  * difficulty belongs to the set
  * hard is the point, said believably * rungs attach to TOPICS, never to him
  * no guilt, no nagging, no comparison * never speak for his parents
The ladder's plain words are FIXED (UNDERSTANDING.md) — ranks and stars are
dressing on the XP economy and the confidence bands, never new wording for
depth.

COACHING (the teaching layer): compose_coaching() is the one language task —
the model dresses deterministic facts (topic, what was picked, why the trap
works) into a beat-it line per target. Every line passes violations() or is
replaced by a deterministic fallback; code decides WHAT the targets are, the
model only phrases HOW to take them down. Same AI -> validator -> fallback
shape as friday_sms.

DYNAMICS: one inline <script> (self-contained means zero FETCH, not zero
motion — the shell itself is the precedent). Bars grow, counters tick, stars
pop, sections reveal. Everything is progressive enhancement over a complete
static page, and all of it stands down under prefers-reduced-motion.

Self-contained HTML, zero fetch, noindex — the report_page.py privacy model.
Deployed by friday_report_run.py to /w/<slug>/.
"""
import html
import json
import re
from datetime import date

# --------------------------------------------------------------------------- #
# The level curve + the rank ladder — the long arc behind the season total.
# Deterministic, front-loaded (early levels land fast), retunable here and
# nowhere else. A GAME economy element (KID-REPORT.md §3), never a target.

LEVEL_BASE = 2000     # cost of level 1 -> 2
LEVEL_STEP = 400      # each subsequent level costs this much more

# The identity ladder — "three-star general" is the season summit. Insignia
# are pure dressing on the level number; no rank ever claims understanding.
RANKS = [
    ("RECRUIT",        "\u25aa"),
    ("SCOUT",          "\u25aa\u25aa"),
    ("TROOPER",        "\u25aa\u25aa\u25aa"),
    ("CORPORAL",       "\u25b2"),
    ("SERGEANT",       "\u25b2\u25b2"),
    ("LIEUTENANT",     "\u25cf"),
    ("CAPTAIN",        "\u25cf\u25cf"),
    ("MAJOR",          "\u25cf\u25cf\u25cf"),
    ("COLONEL",        "\u25c6"),
    ("BRIGADIER",      "\u2605"),
    ("MAJOR GENERAL",  "\u2605\u2605"),
    ("GENERAL",        "\u2605\u2605\u2605"),
]


def level_for(total):
    """(level, xp_into_level, xp_needed_for_next) from a season total."""
    total = max(0, int(total or 0))
    lvl, spent, cost = 1, 0, LEVEL_BASE
    while total - spent >= cost:
        spent += cost
        lvl += 1
        cost += LEVEL_STEP
    return lvl, total - spent, cost


def rank_for(level):
    """(name, insignia) for a level. The summit holds past the top."""
    i = min(max(1, int(level or 1)), len(RANKS)) - 1
    return RANKS[i]


# --------------------------------------------------------------------------- #
# Language laws — banned constructions, checked against the FULL rendered page
# (and against every AI-composed coaching line before it is accepted).

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
    r"\bcareless\b", r"pay more attention",
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
    """Law breaches in rendered/composed text (tag-stripped, entity-unescaped —
    an escaped apostrophe must not smuggle a banned construction past)."""
    plain = html.unescape(re.sub(r"<[^>]+>", " ", text or "")).lower()
    return [p for p in LAWS if re.search(p, plain)]


# --------------------------------------------------------------------------- #
# Game facts — the ADDITIVE layer (allowed here, deliberately not on the
# parent page: motivating to a player, misleading to a parent).

CABINET = ["First Blood", "Clean Run", "Locked It", "Comeback", "Full Clear",
           "Untouchable", "Streak", "Perfect Week", "Calm Hands", "Sure Shot",
           "Boss Slayer", "Blitz Master"]
BADGE_ICON = {"First Blood": "\U0001fa78", "Clean Run": "\U0001f9ca",
              "Locked It": "\U0001f512", "Full Clear": "\U0001f4a0",
              "Comeback": "\U0001f501", "Untouchable": "\U0001f6e1",
              "Streak": "\U0001f525", "Perfect Week": "\U0001f4c5",
              "Calm Hands": "\U0001f9d8", "Sure Shot": "\U0001f3af",
              "Boss Slayer": "\U0001f409", "Blitz Master": "\u26a1"}
BADGE_ACT = {
    "First Blood": "first run ever on the board",
    "Clean Run": "a whole run — zero lucky guesses, zero confident-wrongs",
    "Locked It": "took a topic all the way to solid",
    "Full Clear": "every live topic in a subject, solid",
    "Comeback": "pulled a topic out of REPAIR",
    "Untouchable": "a solid topic held through three spaced checks",
    "Streak": "school nights in a row",
    "Perfect Week": "all five school nights, played",
    "Calm Hands": "slowed down and landed one that used to get rushed",
    "Sure Shot": "called Sure on a repair topic — and it was",
    "Boss Slayer": "cleared Friday's event, every slot",
    "Blitz Master": "beat your own Blitz record",
}
STREAK_TIERS = [(3, "Bronze"), (7, "Silver"), (14, "Gold")]

_EVENT_KINDS = (("BLITZ", "Blitz", "\u26a1"),
                ("BATTLEGROUND", "Battleground", "\U0001f6e1"),
                ("BOSS", "Battleground", "\U0001f6e1"))


def _event_kind(tag):
    t = (tag or "").upper()
    for key, label, icon in _EVENT_KINDS:
        if key in t or (key == "BOSS" and t.endswith(".5")):
            return {"label": label, "icon": icon}
    return None


def _base_badge(name):
    n = (name or "").strip()
    return "Streak" if n.lower().startswith("streak") else n


def badge_hints(streak, topics, earned_names, earned_raw=()):
    """Progress toward the NEXT badge — the payoff that makes badges a chase
    rather than a list. Deterministic reads of ledger + streak; capped at two.
    Rewards exactly the ledger's own goals: showing up, consolidating, repair.
    """
    hints = []
    raw = " ".join(str(b.get("badge") or "") for b in earned_raw).lower()
    if streak >= 1:
        nxt = next(((n, t) for n, t in STREAK_TIERS
                    if n > streak and t.lower() not in raw), None)
        if nxt:
            gap = nxt[0] - streak
            hints.append({"badge": f"Streak {nxt[1]}", "icon": BADGE_ICON["Streak"],
                          "line": f"{gap} school night{'s' if gap != 1 else ''} away",
                          "pct": round(100 * streak / nxt[0])})
    dev = [t for t in (topics or []) if t.get("state") == "developing"]
    dev.sort(key=lambda t: (t.get("times_seen") or 0), reverse=True)
    if dev and "Locked It" not in earned_names:
        hints.append({"badge": "Locked It", "icon": BADGE_ICON["Locked It"],
                      "line": f"{dev[0].get('topic')} is at the door of solid",
                      "pct": 66})
    rep = [t for t in (topics or [])
           if t.get("state") == "REPAIR" or t.get("repair")]
    if rep and len(hints) < 2:
        hints.append({"badge": "Comeback", "icon": BADGE_ICON["Comeback"],
                      "line": f"{rep[0].get('topic')} is the way in — it's queued",
                      "pct": 40})
    return hints[:2]


def game_facts(runs, student, week_days, earned_this_week, asof,
               season_total=0, accuracy=None, earned_all=None, topics=None):
    """Everything game-side the wrap shows beyond the shared card/stories.

    Reads run scores/dates/tags, the badge ledger and topic STATES only —
    never teach-back text (integrity law: nothing here can leak a
    quarantined row).
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

    # streak — school-day semantics, one definition everywhere. Anchored on the
    # LAST PLAYED day so a wrap built before tonight's ingest never zeroes an
    # honest streak.
    present = {r.get("run_date") for r in mine if r.get("run_date")}
    played = sorted(d for d in present if d <= asof.isoformat())
    streak = 0
    if played:
        streak = current_school_streak(present, date.fromisoformat(played[-1]))

    # events this week, in order, with a star read (Battleground tiers)
    events = []
    for r in sorted(in_week, key=lambda r: r.get("run_date") or ""):
        kind = _event_kind(r.get("tag"))
        if not kind:
            continue
        qs = [q for q in (r.get("questions") or [])
              if q.get("ok") is not None and not q.get("skipped")
              and q.get("phase") != "teach"]
        zk, zn = sum(1 for q in qs if q.get("ok")), len(qs)
        pct = round(100 * zk / zn) if zn else 0
        stars = 3 if pct == 100 else 2 if pct >= 75 else 1 if pct >= 50 else 0
        events.append({"label": kind["label"], "icon": kind["icon"],
                       "day": date.fromisoformat(r["run_date"]).strftime("%a"),
                       "pts": int(r.get("score") or 0),
                       "zones_ok": zk, "zones": zn, "stars": stars})

    # overall accuracy — ONE number, framed as the line to beat. Same >=10
    # floor the parent trend uses; per-subject stays parent-side.
    acc = None
    if accuracy:
        right = sum(v.get("right", 0) for v in accuracy.values())
        asked = sum(v.get("asked", 0) for v in accuracy.values())
        if asked >= 10:
            acc = {"pct": round(100 * right / asked), "right": right, "asked": asked}

    lvl, into, need = level_for(season_total)
    rk_name, rk_pips = rank_for(lvl)
    earned_names = { _base_badge(b.get("badge")) for b in (earned_all or []) }
    cabinet = [{"badge": b, "icon": BADGE_ICON[b], "earned": b in earned_names}
               for b in CABINET]
    return {"days": days, "streak": streak, "events": events,
            "season_total": int(season_total or 0),
            "level": {"n": lvl, "into": into, "need": need},
            "rank": {"name": rk_name, "pips": rk_pips},
            "accuracy": acc,
            "badges": list(earned_this_week or []),
            "cabinet": cabinet,
            "collected": sum(1 for c in cabinet if c["earned"]),
            "hints": badge_hints(streak, topics, earned_names, earned_all or [])}


# --------------------------------------------------------------------------- #
# Targets — every gap the parent report names, re-dressed as pursuit.
# targets_from() IS the transparency law made executable; test_kid_wrap locks
# the union. The renderer leads with the top three and lists the rest.

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
# Coaching — the teaching layer. AI dresses deterministic facts into a
# beat-it line per target; the validator gates every line; a deterministic
# fallback always exists. Code decides the targets, the model only phrases.

COACH_SYSTEM = """You write short BEAT-IT coaching lines for a secondary student's weekly game wrap.
Voice: a fellow player who knows the game — never a teacher, never a parent. Straight, specific, warm-blooded.

For each target you get the TOPIC, where it currently sits, and (when known) what was picked, the right answer, and why the trap works. Write ONE coaching line of two short sentences:
  1) Name the confusion plainly — the actual idea, not a vibe.
  2) Give a concrete next-time move the student can run in under a minute (a check, a rule to say out loud, an order of operations, a tell to watch for).

HARD LAWS — a line that breaks one is discarded:
- Praise the move, never the person. No "you're smart/clever". No guilt, no "you should have", no "careless", no "try harder".
- Difficulty belongs to the set; ability attaches to the TOPIC, never to the student.
- No comparisons to anyone. Never mention parents. Never mention counting, flags, or whether an answer was someone's own writing.
- Address the reader as "you" doing moves, not "you" being judged.
- Max 240 characters per line. Plain text, no emoji, no markdown.

Return ONLY JSON: an object mapping each target's "id" to its coaching line."""

# Deterministic fallbacks — rotated by position so three cards never repeat
# the same tactic. These are real tactics, not filler.
COACH_FALLBACK = [
    "Answer it in your head before you look at the options — the trap options "
    "are written for people who look first. If your answer isn't there, re-read "
    "the question, not the options.",
    "Say the rule out loud before you pick: if you can only say WHAT the answer "
    "is and not WHY it fits, that's the tell. The why is what the set keeps "
    "testing.",
    "Slow the first read down to half speed and underline what it's actually "
    "asking. Most of this one's misses are speed misses, and speed is the one "
    "thing you fully control.",
]


def compose_coaching(targets, api_key=None, model=None, student_year=""):
    """{topic: line} for the top three targets. AI -> validator -> fallback.
    Returns (coaching, source) where source is 'ai', 'mixed' or 'fallback'.
    """
    top = targets[:3]
    coaching = {t["topic"]: COACH_FALLBACK[i % len(COACH_FALLBACK)]
                for i, t in enumerate(top)}
    if not top or not api_key:
        return coaching, "fallback"

    payload = []
    for i, t in enumerate(top):
        row = {"id": str(i), "topic": t["topic"], "subject": t.get("subject") or "",
               "sits_at": t.get("state") or "unknown"}
        m = t.get("misconception") or {}
        if m.get("why"):
            row.update({"picked": m.get("picked"), "correct": m.get("correct"),
                        "why_the_trap_works": m.get("why")})
        payload.append(row)
    user = (f"The student is in year {student_year or 'secondary school'}. "
            f"TARGETS:\n{json.dumps(payload, ensure_ascii=False, indent=1)}\n\n"
            "Write the coaching lines. JSON only.")
    try:
        from grade_teachback import call_api, parse_json, DEFAULT_MODEL
        raw = call_api(COACH_SYSTEM, user, model or DEFAULT_MODEL, api_key)
        lines = parse_json(raw) or {}
    except Exception:
        return coaching, "fallback"

    used_ai = 0
    for i, t in enumerate(top):
        line = str(lines.get(str(i)) or "").strip()
        if line and len(line) <= 300 and not violations(line):
            coaching[t["topic"]] = line
            used_ai += 1
    src = "ai" if used_ai == len(top) else ("mixed" if used_ai else "fallback")
    return coaching, src


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
.kick{margin:22px 0 2px;font-family:'Space Mono',ui-monospace,monospace;font-weight:700;font-size:11px;letter-spacing:.14em;color:var(--haze)}
.kick b{color:var(--boltdeep);background:#FFF3D6;border:1.5px solid var(--bolt);border-radius:6px;padding:1px 7px;margin-right:6px}
h1.word{font-size:54px;line-height:1;margin:2px 0 8px;animation:heroPop .55s cubic-bezier(.2,1.3,.4,1) both}
.strong{color:var(--kelp)}.solid{color:var(--reef)}.quiet{color:var(--haze)}.slower{color:var(--flare)}
.sub{font-size:17px;line-height:1.45;margin:4px 0 22px;max-width:52ch}
.section{margin:30px 0 10px;font-size:11px;letter-spacing:.15em;color:var(--haze);font-weight:700}
@keyframes heroPop{0%{opacity:0;transform:scale(.86)}60%{opacity:1;transform:scale(1.03)}100%{transform:scale(1)}}
/* THE HUD — inverted ink plate, the game's own event-banner voice */
.run{background:var(--plate);color:var(--paper);border-radius:16px;padding:16px 18px 20px;position:relative;overflow:hidden}
.run:after{content:"";position:absolute;left:0;right:0;bottom:0;height:5px;background:linear-gradient(90deg,var(--flare),var(--bolt),var(--flare));background-size:200% 100%}
.rankrow{display:flex;align-items:center;justify-content:space-between;gap:10px;border-bottom:1px solid #26344F;padding-bottom:12px;margin-bottom:12px}
.rankrow .pips{font-family:'Space Mono',monospace;color:var(--bolt);font-size:20px;letter-spacing:.18em;line-height:1}
.rankrow .rk{font-family:'Archivo Black','Arial Black',sans-serif;font-size:24px;letter-spacing:.02em;background:linear-gradient(135deg,var(--bolt) 0%,var(--flare) 115%);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;color:var(--bolt)}
.rankrow .lv{text-align:right}
.rankrow .lv .n{font-family:'Space Mono',monospace;font-size:22px;color:var(--paper)}
.rankrow .lv .k{font-size:10px;letter-spacing:.14em;color:#8B94A8}
.bars{display:flex;gap:8px;align-items:flex-end;height:96px;margin:6px 0 4px}
.bar{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;gap:5px;height:100%}
.bar .col{width:100%;border-radius:6px 6px 3px 3px;background:linear-gradient(180deg,var(--bolt),var(--flare));min-height:6px;transform-origin:bottom;transition:transform .7s cubic-bezier(.2,.9,.3,1)}
.bar .col.off{background:none;border:1.5px dashed #33415C;min-height:26px;border-radius:6px}
.bar .v{font-family:'Space Mono',monospace;font-size:10px;color:#B8C0CF;line-height:1}
.bar .v.ev{color:var(--bolt)}
.bar .best{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:.1em;color:var(--bolt)}
.dayrow{display:flex;gap:8px;margin-top:2px}
.dayrow span{flex:1;text-align:center;font-size:10px;letter-spacing:.1em;color:#8B94A8}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.stat{flex:1 1 44%;background:#16233B;border:1px solid #26344F;border-radius:12px;padding:10px 12px;min-width:130px}
.stat .k{font-size:10px;letter-spacing:.12em;color:#8B94A8}
.stat .v{font-size:22px;margin-top:3px;color:var(--paper)}
.stat .v i{font-style:normal;font-size:13px;color:#8B94A8;margin-left:4px}
.stat .lv{height:7px;border-radius:99px;background:#26344F;overflow:hidden;margin-top:8px}
.stat .lv span{display:block;height:100%;background:linear-gradient(90deg,var(--bolt),var(--flare));border-radius:99px;transition:width .9s cubic-bezier(.2,.9,.3,1)}
.stat .n{font-size:10.5px;color:#8B94A8;margin-top:5px}
.runline{font-size:13.5px;color:#B8C0CF;margin:14px 0 0;line-height:1.5}
/* UNLOCKS */
.badges{display:flex;flex-direction:column;gap:8px;margin-bottom:10px}
.badge{display:flex;align-items:center;gap:12px;border:2px solid var(--bolt);background:linear-gradient(135deg,#FFF9EB,#FFF3D6);border-radius:12px;padding:10px 13px;animation:badgePop .5s cubic-bezier(.2,1.25,.4,1) both}
.badge .bic{font-size:24px;line-height:1}
.badge .bnm{font-family:'Archivo Black','Arial Black',sans-serif;font-size:14px;color:var(--boltdeep)}
.badge .bds{font-size:12.5px;color:var(--haze);margin-top:1px}
.badge .new{margin-left:auto;font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.12em;color:var(--boltdeep);background:#FFE9AE;border-radius:6px;padding:2px 7px;animation:chipPulse 2.2s ease-in-out infinite}
@keyframes badgePop{0%{opacity:0;transform:translateY(8px) scale(.94)}60%{opacity:1;transform:translateY(0) scale(1.02)}100%{transform:scale(1)}}
@keyframes chipPulse{0%,100%{box-shadow:0 0 0 0 rgba(255,184,0,.45)}50%{box-shadow:0 0 0 6px rgba(255,184,0,0)}}
.cab{background:#fff;border:2px solid var(--line);border-radius:14px;padding:12px 14px}
.cab .hd{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:9px}
.cab .hd .t{font-family:'Space Mono',monospace;font-weight:700;font-size:11px;letter-spacing:.12em;color:var(--haze)}
.cab .hd .c{font-family:'Space Mono',monospace;font-weight:700;font-size:12px;color:var(--boltdeep)}
.slots{display:grid;grid-template-columns:repeat(6,1fr);gap:8px}
.slot{text-align:center;border:1.5px solid var(--line);border-radius:10px;padding:7px 2px 5px;background:#FAFBF8}
.slot.got{border-color:var(--bolt);background:linear-gradient(135deg,#FFF9EB,#FFF3D6)}
.slot .i{font-size:18px;line-height:1;filter:grayscale(1);opacity:.35}
.slot.got .i{filter:none;opacity:1}
.slot .n{font-size:8px;letter-spacing:.02em;color:var(--haze);margin-top:3px;line-height:1.15}
.slot.got .n{color:var(--boltdeep);font-weight:700}
.hints{display:grid;gap:8px;margin-top:10px}
.hint{display:flex;align-items:center;gap:10px;border:1.5px dashed var(--line);border-radius:10px;padding:8px 11px;background:#FAFBF8}
.hint .i{font-size:18px}
.hint .b{font-family:'Space Mono',monospace;font-weight:700;font-size:11px;color:var(--ink)}
.hint .l{font-size:12px;color:var(--haze)}
.hint .bar{margin-left:auto;flex:0 0 64px;height:6px;border-radius:99px;background:#E4E7DF;overflow:hidden}
.hint .bar span{display:block;height:100%;background:linear-gradient(90deg,var(--bolt),var(--flare));border-radius:99px}
/* WHAT YOU BEAT */
.beat{background:#fff;border:2px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px}
.tagchip{display:inline-block;font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.1em;padding:3px 8px;border-radius:6px;margin-bottom:8px;background:#E8F4EE;color:var(--kelp)}
.tagchip.rank{background:#FFF3D6;color:var(--boltdeep);border:1.5px solid var(--bolt)}
.beat h3{margin:0 0 4px;font-size:17px;line-height:1.3}
.beat p{margin:6px 0 0;font-size:14.5px;line-height:1.5;color:#3A4356}
.stars{font-size:15px;letter-spacing:.14em;color:var(--bolt);margin-top:6px}
.stars i{font-style:normal;color:#D9DDD3}
.dots{display:flex;gap:4px;margin-top:8px;align-items:center}
.dots u{text-decoration:none;font-size:10px;color:var(--haze);margin-right:3px;letter-spacing:.08em}
.dots i{font-style:normal;width:8px;height:8px;border-radius:99px;background:#D6D9D1;display:inline-block}
.dots i.y{background:var(--kelp)} .dots i.n{background:#E8963C}
.ladder{display:flex;gap:4px;margin-top:10px;font-size:10px;color:var(--haze);flex-wrap:wrap}
.ladder span{padding:3px 7px;border-radius:6px;background:#EEF1EA}
.ladder span.on{background:var(--kelp);color:#fff;font-weight:700}
/* FINISHING MOVE */
.quote{background:#fff;border:2px solid var(--line);border-left:5px solid var(--kelp);border-radius:12px;padding:15px 17px;font-size:16px;line-height:1.55;position:relative}
.quote .attr{display:block;margin-top:9px;font-size:12px;color:var(--haze)}
.quote .why{display:block;margin-top:8px;font-size:13.5px;color:#3A4356;line-height:1.5}
.quote .stamp{position:absolute;top:-10px;right:12px;font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.1em;color:#fff;background:var(--kelp);border-radius:6px;padding:3px 8px;transform:rotate(2deg)}
/* THE HIT LIST */
.stalkintro{font-size:13.5px;color:var(--haze);margin:-2px 0 10px;line-height:1.5}
.stalk{background:#fff;border:2px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:10px}
.stalk h3{margin:0 0 4px;font-size:17px;line-height:1.3}
.stalk .eyebrow{font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.12em;color:var(--flare)}
.stalk p{margin:7px 0 0;font-size:14.5px;line-height:1.5;color:#3A4356}
.sits{margin:9px 0 0;display:flex;align-items:center;gap:9px}
.sits .lab{font-size:11.5px;color:var(--haze)}
.sits .lab b{color:var(--ink)}
.trap{background:#FAFBF8;border-left:3px solid #E8963C;padding:8px 12px;margin-top:9px;font-size:13.5px;line-height:1.5}
.trap b{color:var(--flare)}
.coach{background:var(--plate);color:#E9EBE4;border-radius:10px;padding:10px 13px;margin-top:9px;font-size:14px;line-height:1.5}
.coach .cl{font-family:'Space Mono',monospace;font-weight:700;font-size:9.5px;letter-spacing:.14em;color:var(--bolt);display:block;margin-bottom:4px}
.alsoline{font-size:13px;color:var(--haze);line-height:1.5;margin:2px 0 0}
.boss{background:var(--plate);color:var(--paper);border:none;position:relative;overflow:hidden}
.boss:after{content:"";position:absolute;left:0;right:0;bottom:0;height:4px;background:linear-gradient(90deg,var(--bolt),#FFE08A,var(--bolt));background-size:200% 100%}
.boss .eyebrow{color:var(--bolt)}
.boss h3{font-family:'Archivo Black','Arial Black',sans-serif;font-size:20px}
.boss .when{font-family:'Space Mono',monospace;font-size:12px;color:#B8C0CF;margin-top:2px}
.boss p{color:#D9DEE9}
.sure .eyebrow{color:var(--reef)}
/* THE ONE MOVE */
.move{background:var(--ink);color:var(--paper);border-radius:16px;padding:17px 18px;position:relative;overflow:hidden}
.move:after{content:"";position:absolute;left:0;right:0;bottom:0;height:4px;background:linear-gradient(90deg,var(--bolt),#FFE08A,var(--bolt));background-size:200% 100%}
.move .eyebrow{font-family:'Space Mono',monospace;font-weight:700;font-size:10px;letter-spacing:.14em;color:var(--bolt)}
.move p{margin:8px 0 0;font-size:17px;line-height:1.5}
.move b{color:var(--bolt)}
/* LADDER EXPLAINER */
.how{background:#fff;border:2px dashed var(--line);border-radius:14px;padding:12px 16px}
.how summary{cursor:pointer;font-family:'Space Mono',monospace;font-weight:700;font-size:11px;letter-spacing:.12em;color:var(--reef)}
.how p{margin:10px 0 0;font-size:13.5px;line-height:1.55;color:#3A4356}
.foot{margin-top:26px;font-size:12.5px;color:var(--haze);line-height:1.6;border-top:2px solid var(--line);padding-top:14px}
.rv{opacity:0;transform:translateY(14px);transition:opacity .5s ease,transform .5s ease}
.rv.in{opacity:1;transform:none}
@media (prefers-reduced-motion: no-preference){
 .run:after,.boss:after,.move:after{animation:charge 2s linear infinite}
 @keyframes charge{0%{background-position:0 0}100%{background-position:200% 0}}
}
@media (prefers-reduced-motion: reduce){
 h1.word,.badge{animation:none !important}
 .rv{opacity:1;transform:none;transition:none}
 .bar .col,.stat .lv span{transition:none}
}
"""

_JS = """
(function(){
 var rm = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
 if(rm) return;
 // section reveals
 var io = ('IntersectionObserver' in window) ? new IntersectionObserver(function(es){
   es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
 },{threshold:.12}) : null;
 document.querySelectorAll('.rv').forEach(function(el){ io ? io.observe(el) : el.classList.add('in'); });
 // bars grow from the floor
 document.querySelectorAll('.bar .col:not(.off)').forEach(function(c,i){
   c.style.transform='scaleY(0)';
   setTimeout(function(){ c.style.transform='scaleY(1)'; }, 150+i*90);
 });
 // counters tick up
 document.querySelectorAll('[data-count]').forEach(function(el){
   var end = parseInt(el.getAttribute('data-count'),10)||0, t0=null;
   function step(ts){ if(!t0)t0=ts; var p=Math.min(1,(ts-t0)/750);
     el.textContent = Math.round(end*(1-Math.pow(1-p,3))).toLocaleString();
     if(p<1) requestAnimationFrame(step); }
   requestAnimationFrame(step);
 });
 // level + hint bars fill
 document.querySelectorAll('[data-fill]').forEach(function(el){
   var w = el.getAttribute('data-fill'); el.style.width='0%';
   setTimeout(function(){ el.style.width=w+'%'; }, 350);
 });
 // stars pop in sequence
 document.querySelectorAll('.stars').forEach(function(s){
   var kids=s.childNodes; Array.prototype.forEach.call(s.querySelectorAll('b'),function(st,i){
     st.style.opacity='0'; st.style.display='inline-block'; st.style.transform='scale(.4)';
     st.style.transition='opacity .25s ease,transform .3s cubic-bezier(.2,1.4,.4,1)';
     setTimeout(function(){ st.style.opacity='1'; st.style.transform='scale(1)'; }, 250+i*140);
   });
 });
})();
"""

RUNGS = [("not_yet", "not yet"), ("knows", "knows it"), ("lists", "can list it"),
         ("connects", "can connect it"), ("applies", "can apply it elsewhere")]
RUNG_LABEL = dict(RUNGS)

# Where a topic sits — the SAME bands as the parent page (same facts), shown
# as a star meter (different dressing). The band WORD travels with it.
BANDS = ["Not started yet", "Getting started", "Building", "Nearly there", "Solid"]
STATE_BAND = {"untested": 1, "REPAIR": 1, "shaky": 2, "developing": 3, "solid": 4}

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


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _stars(filled, total=4):
    f = max(0, min(int(filled or 0), total))
    return ("<div class='stars'>" + "<b>\u2605</b>" * f
            + "<i>\u2605</i>" * (total - f) + "</div>")


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


# ---- the HUD ----------------------------------------------------------------

def _run_block(game, card):
    days = game.get("days") or []
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
            crown = ("<span class='best'>BEST</span>"
                     if d["pts"] == peak and len(played) > 1 else "")
            bars.append(f"<div class='bar'>{crown}"
                        f"<div class='col' style='height:{h}px'></div>"
                        f"<span class='v{' ev' if ev else ''}'>{v}</span></div>")
        labels.append(f"<span>{_e(d['day'].upper())}</span>")

    lvl = game.get("level") or {"n": 1, "into": 0, "need": LEVEL_BASE}
    rank = game.get("rank") or dict(zip(("name", "pips"), rank_for(lvl["n"])))
    pct = round(100 * lvl["into"] / lvl["need"]) if lvl["need"] else 0
    left = lvl["need"] - lvl["into"]

    rankrow = (f"<div class='rankrow'><div>"
               f"<div class='pips'>{_e(rank['pips'])}</div>"
               f"<div class='rk display'>{_e(rank['name'])}</div></div>"
               f"<div class='lv'><div class='n num'>LV {lvl['n']}</div>"
               f"<div class='k'>SEASON RANK</div></div></div>")

    chips = [
        f"<div class='stat'><div class='k'>STREAK</div><div class='v num'>"
        f"\U0001f525 <span data-count='{game.get('streak', 0)}'>{game.get('streak', 0)}</span>"
        f"<i>school nights</i></div></div>",
        f"<div class='stat'><div class='k'>SEASON</div>"
        f"<div class='v num'><span data-count='{game.get('season_total', 0)}'>"
        f"{game.get('season_total', 0):,}</span><i>XP</i></div></div>",
        f"<div class='stat'><div class='k'>NEXT RANK-UP</div>"
        f"<div class='v num'>{left:,}<i>XP to LV {lvl['n'] + 1}</i></div>"
        f"<div class='lv'><span data-fill='{pct}' style='width:{pct}%'></span></div></div>",
    ]
    if game.get("accuracy"):
        a = game["accuracy"]
        tail = "the start-line number" if card.get("baseline") else "the line to beat"
        chips.append(f"<div class='stat'><div class='k'>SHOTS LANDED</div>"
                     f"<div class='v num'><span data-count='{a['pct']}'>{a['pct']}</span>%</div>"
                     f"<div class='n'>{a['right']} of {a['asked']} — {tail}</div></div>")

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
            f"{rankrow}<div class='bars'>{''.join(bars)}</div>"
            f"<div class='dayrow'>{''.join(labels)}</div>"
            f"<div class='chips'>{''.join(chips)}</div>{line}</div>")


# ---- unlocks ----------------------------------------------------------------

def _unlocks_block(game):
    rows = []
    for b in game.get("badges") or []:
        nm = b.get("badge", "")
        base = _base_badge(nm)
        icon = BADGE_ICON.get(base, "\U0001f3c5")
        act = b.get("label") or BADGE_ACT.get(base) or "earned this week"
        rows.append(f"<div class='badge'><span class='bic'>{icon}</span>"
                    f"<span><span class='bnm'>{_e(nm)}</span>"
                    f"<div class='bds'>{_e(act)}</div></span>"
                    f"<span class='new'>NEW</span></div>")
    badges = f"<div class='badges'>{''.join(rows)}</div>" if rows else ""

    cab = game.get("cabinet") or []
    slots = "".join(
        f"<div class='slot{' got' if c['earned'] else ''}'>"
        f"<div class='i'>{c['icon']}</div><div class='n'>{_e(c['badge'])}</div></div>"
        for c in cab)
    cabinet = ""
    if cab:
        cabinet = (f"<div class='cab'><div class='hd'><span class='t'>THE CABINET"
                   f"</span><span class='c'>COLLECTED {game.get('collected', 0)} / "
                   f"{len(cab)}</span></div><div class='slots'>{slots}</div>")
        hints = game.get("hints") or []
        if hints:
            hr = "".join(
                f"<div class='hint'><span class='i'>{h['icon']}</span>"
                f"<span><div class='b'>{_e(h['badge'].upper())}</div>"
                f"<div class='l'>{_e(h['line'])}</div></span>"
                f"<span class='bar'><span data-fill='{h['pct']}' "
                f"style='width:{h['pct']}%'></span></span></div>"
                for h in hints)
            cabinet += f"<div class='hints'>{hr}</div>"
        cabinet += "</div>"
    if not badges and not cabinet:
        return ""
    return f"<div class='section rv'>UNLOCKS</div><div class='rv'>{badges}{cabinet}</div>"


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
                f"<div class='beat rv'><span class='tagchip'>TAKEN DOWN</span>"
                f"<h3>{_e(s['topic'])}</h3>{_stars(STATE_BAND.get(s.get('state'), 1))}"
                "<p>Wrong early in the week, right by the end — turned inside five "
                "days. It comes back once more to prove the hold.</p>"
                f"{_dots(s.get('trace'))}</div>")
        elif s.get("status") == "TRENDING WELL":
            cards.append(
                f"<div class='beat rv'><span class='tagchip'>RAN CLEAN</span>"
                f"<h3>{_e(s['topic'])}</h3>{_stars(STATE_BAND.get(s.get('state'), 1))}"
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
                f"<div class='beat rv'><span class='tagchip rank'>RANK UP</span>"
                f"<h3>{_e(s['topic'])} &mdash; {_e(frm)} \u2192 {_e(to)}</h3>"
                "<p>That jump can't be grinded — only an explanation gets a topic "
                "there. Yours did.</p>"
                f"<div class='ladder'>{rungs}</div></div>")

    for topic in (card.get("movement") or {}).get("up") or []:
        if any(s.get("topic") == topic for s in stories or []):
            continue
        cards.append(f"<div class='beat rv'><span class='tagchip'>MOVED UP</span>"
                     f"<h3>{_e(topic)}</h3>"
                     "<p>Stepped up a band on the ledger this week — the rotation "
                     "eases off it and spends the time elsewhere.</p></div>")

    for ev in game.get("events") or []:
        if ev["label"] == "Blitz":
            cards.append(f"<div class='beat rv'><span class='tagchip rank'>"
                         f"{ev['icon']} BLITZ</span><h3>{ev['pts']:,} XP on the "
                         f"doubled clock</h3><p>{_e(ev['day'])}'s tempo event — "
                         "speed under pressure, banked.</p></div>")
        else:
            pct = round(100 * ev["zones_ok"] / ev["zones"]) if ev["zones"] else 0
            tail = (" The field's yours this week." if pct == 100 else
                    " Contested ground carries no penalty — it just comes back around.")
            cards.append(f"<div class='beat rv'><span class='tagchip rank'>"
                         f"{ev['icon']} BATTLEGROUND</span>"
                         f"<h3>Claimed {ev['zones_ok']} of {ev['zones']} zones</h3>"
                         f"{_stars(ev.get('stars', 0), 3)}"
                         f"<p>{_e(ev['day'])}'s claim on the week's hardest ground."
                         f"{tail}</p></div>")

    if not cards:
        cards.append("<div class='beat rv'><p style='margin:0'>Nothing closed out "
                     "this week — the board below is still standing. That's a "
                     "list, not a verdict: everything on it is already scheduled "
                     "to come back around.</p></div>")
    return f"<div class='section rv'>WHAT YOU BEAT</div>{''.join(cards)}"


# ---- your own words ---------------------------------------------------------

def _words_block(quote):
    if not quote:
        return ""
    attr = "written by you this week, quoted word for word"
    if quote.get("subject"):
        attr = f"{_e(quote['subject'])} teach-back &middot; {attr}"
    depth = quote.get("depth")
    stamp, why = "", ""
    if depth in ("connects", "applies"):
        stamp = (f"<span class='stamp'>HIT: {_e(RUNG_LABEL.get(depth, depth)).upper()}"
                 "</span>")
        why = ("<span class='why'>Picking answers can't take a topic past "
               "<b>can list it</b> — explaining can. This is what that looks like.</span>")
    return ("<div class='section rv'>FINISHING MOVE &mdash; YOUR OWN WORDS</div>"
            f"<div class='quote rv'>{stamp}&ldquo;{_e(quote['text'])}&rdquo;"
            f"<span class='attr'>{attr}</span>{why}</div>")


# ---- the hit list -----------------------------------------------------------

def _sits(state):
    band = STATE_BAND.get(state, 1)
    return (f"<div class='sits'>{_stars(band)}"
            f"<span class='lab'>Where it sits: <b>{_e(BANDS[band])}</b></span></div>")


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
    return (f"<div class='stalk boss rv'><span class='eyebrow'>BOSS APPROACHING</span>"
            f"<h3>{_e(radar['task'])}</h3>"
            f"<div class='when'>{_e(radar.get('subject') or '')} &middot; "
            f"{days} {when}</div><p>{line}</p></div>")


FLAV = {
    "close": "Fresh gap, small and specific — it's back next week.",
    "assess": "It guards the ground the test covers — first in the rotation.",
    "repair": "Due a revisit — the rotation has it queued.",
    "behind": "The syllabus has moved onto this one — a few focused minutes "
              "brings it into range.",
    "slid": "Slipped a step this week. Happens — it's re-queued and comes "
            "back around.",
}


def _stalk_block(card, stories, coaching):
    targets = targets_from(card, stories)
    coaching = coaching or {}
    cards = [_assess_card(card.get("radar"))]

    for t in targets[:3]:
        misc = t.get("misconception")
        trap = ""
        if misc and misc.get("why"):
            trap = (f"<div class='trap'>How it got you: picked <b>{_e(misc['picked'])}</b> "
                    f"&mdash; the answer was <b>{_e(misc['correct'])}</b>. "
                    f"{_e(misc['why'])}</div>")
        coach = coaching.get(t["topic"])
        coach_html = (f"<div class='coach'><span class='cl'>BEAT IT NEXT TIME</span>"
                      f"{_e(coach)}</div>") if coach else ""
        sits = _sits(t["state"]) if t.get("state") else ""
        cards.append(f"<div class='stalk rv'><span class='eyebrow'>TARGET</span>"
                     f"<h3>{_e(t['topic'])}</h3>{sits}"
                     f"<p>{_e(FLAV.get(t['flavour'], FLAV['close']))}</p>"
                     f"{trap}{coach_html}{_dots(t.get('trace'))}</div>")

    rest = targets[3:]
    if rest:
        names = " &middot; ".join(_e(t["topic"]) for t in rest)
        cards.append(f"<p class='alsoline rv'>Also on the board, same deal, all "
                     f"queued: {names}.</p>")

    w = next((s for s in stories or [] if s.get("status") == "WATCHING"), None)
    if w:
        cards.append(
            f"<div class='stalk sure rv'><span class='eyebrow'>SURE-CHECK</span>"
            f"<h3>{w['count']} of {w['of']} Sure calls didn't land</h3>"
            "<p>Sureness is its own stat — the quiz keeps pairing it with results, "
            "so it trains like everything else. No move needed; watch it settle.</p></div>")

    body = "".join(c for c in cards if c)
    if not body:
        body = ("<div class='stalk rv'><p style='margin:0'>Nothing stalking you "
                "this week — the board is clear. The rotation keeps testing the "
                "perimeter anyway; that's how it stays clear.</p></div>")
    intro = ("<p class='stalkintro rv'>Targets, not verdicts — everything here is "
             "already scheduled to come back around. Gaps live on this list "
             "exactly as long as they take to close.</p>")
    return f"<div class='section rv'>STALKING YOU NEXT WEEK</div>{intro}{body}"


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
    return ("<div class='section rv'>THE ONE MOVE</div><div class='move rv'>"
            f"<span class='eyebrow'>HIGHEST-LEVERAGE PLAY</span><p>{p}</p></div>")


# ---- the ladder explainer ---------------------------------------------------

def _ladder_block():
    rungs = "".join(f"<span>{_e(v)}</span>" for _, v in RUNGS)
    return ("<details class='how rv'><summary>THE LADDER &mdash; HOW TOPICS RANK UP"
            "</summary>"
            f"<div class='ladder'>{rungs}</div>"
            "<p>Speed questions top out at <b>knows it</b>. Steady questions top "
            "out at <b>can list it</b> — four options can prove recognition, never "
            "explanation. The only way a topic reaches <b>can connect it</b> is the "
            "teach-back: explaining the thing in your own words. Use it somewhere "
            "it wasn't taught and it hits <b>can apply it elsewhere</b>.</p>"
            "<p>It's the one track in the game that can't be grinded — which is "
            "exactly why it's the one that counts in an exam room.</p></details>")


# ---- assembly ---------------------------------------------------------------

def render(card, stories=None, quote=None, game=None, coaching=None):
    """Full self-contained HTML for one kid-week wrap. Raises ValueError if the
    rendered page breaches a language law — a broken page is better than a
    law-breaking one, and the caller's deploy simply skips."""
    stories = stories or []
    game = game or {}
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
  {_unlocks_block(game)}
  {_beat_block(card, stories, game)}
  {_words_block(quote)}
  {_stalk_block(card, stories, coaching)}
  {_move_block(card)}
  {_ladder_block()}
  <p class="foot">Your parents' Friday page shows this exact week — same facts,
  different dressing. Nothing here they don't see; nothing there you don't.<br>
  XP Daily &middot; week of {_e(week)} &middot; this page is yours.</p>
</div>
<script>{_JS}</script>
</body>
</html>"""

    broken = violations(page)
    if broken:
        raise ValueError(f"kid wrap breached language law: {broken}")
    return page
