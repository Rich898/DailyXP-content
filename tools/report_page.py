#!/usr/bin/env python3
"""
report_page.py — the hosted weekly PARENT report (REPORTING.md surface A).

A NARRATIVE, not a dashboard. The SMS is the tier-1 report; this is the deep
dive it links to — "this week, bounded", one kid, one week.

STRUCTURE (subject-first, PARENT-COMMS-V2 §3 — supersedes the insight-type order):
  1. verdict          the week-word + hero line — readable in ten seconds
  2. the week strip    nights · topics practised · events, in one line
  3. BY SUBJECT        the spine: one block per subject that closes Monday's loop
                      — what class is on → what his sets worked → where each
                      topic stands (band + depth where evidenced) → one
                      misconception detail → next week. The fluency-illusion
                      catch (a right MCQ held back by a not-yet explanation) is
                      narrated here. Falls back to legacy story cards when no
                      subject blocks are supplied.
  4. cross-cutting     demoted below the subjects: what's coming (assessment),
                      in his own words (integrity-gated quote), say/do, depth
                      movement, worth-a-watch, week-on-week (aggregate), speed.
  5. where it adds up  the cumulative-by-subject strip → the portal.
  6. reading notes     the honest caveats that make everything above trustworthy

PRIVACY: fully self-contained. Every fact is baked in at build time — ZERO fetch
calls, no endpoint, no report.json on any server. The ledger never leaves the
private repo. (When family #2 arrives these same pages move behind the login
wall; the renderer doesn't change, only what guards it does.)

DOCTRINE:
  * CODE DECIDES, LANGUAGE DRESSES. Everything here is already chosen by
    friday_report.build_card + report_stories.build_stories.
  * NUMBERS ARE ALLOWED ON FRIDAY — but only ones that mean something. Accuracy
    and the XP total, yes. Points-per-day as a headline, no: difficulty varies,
    so it is the least trustworthy figure and it must not lead.
  * NO-ANXIETY: every flagged thing arrives WITH its fix, in the same card.
  * PROCESS-LEVEL PRAISE (Hattie & Timperley): praise the MOVE, not the child.
    "You explained why it works" beats "you're so clever" — person-level praise
    is the weakest form of feedback.
  * UNDER-CLAIM. Week 1 has no prior; thin evidence says so out loud.
"""
import datetime as _dt
import html
import os as _os


def build_stamp():
    """Commit + render-time stamp baked into every page (<meta xpdaily-build>).

    Two jobs: (a) a human can View Source and know exactly which build they are
    looking at — the 28 Aug incident (stale pages serving under a green
    pipeline) was only diagnosable by eyeballing colours; (b) netlify_deploy's
    verify() asserts THIS stamp in the fetched page, so "deploy ready" can
    never again pass on last week's content. The timestamp makes every render
    unique; GITHUB_SHA is present in every Actions run ("local" elsewhere).
    """
    sha = (_os.environ.get("GITHUB_SHA") or "local")[:9]
    return f"{sha} {_dt.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}"

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;600;700&family=Space+Mono:wght@700&display=swap');
:root{--ink:#EAF0F7;--flare:#FF6A47;--reef:#5AA9E6;--kelp:#4FD6A0;--haze:#8B97AC;--line:#243247;--card:#101F35}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:#0B1220;background-image:radial-gradient(120% 90% at 50% 2%,#16273f 0%,#0B1220 55%,#070c15 100%);background-attachment:fixed;color:var(--ink);font-family:'Space Grotesk',system-ui,sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:640px;margin:0 auto;padding:22px 16px 60px}
.display{font-family:'Archivo Black','Arial Black',sans-serif;letter-spacing:-.01em}
.num{font-family:'Space Mono',ui-monospace,monospace;font-weight:700}
.top{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.top .brand{font-size:11px;letter-spacing:.16em;color:var(--haze)}
.top .week{font-size:11px;color:var(--haze)}
.hero{font-size:14px;color:var(--haze);margin:22px 0 2px}
h1.word{font-size:50px;line-height:1;margin:0 0 6px}
.strong{color:var(--kelp)}.solid{color:var(--reef)}.quiet{color:var(--haze)}.slower{color:var(--flare)}
.sub{font-size:17px;line-height:1.45;margin:6px 0 24px;max-width:52ch}
.section{margin:32px 0 10px;font-size:11px;letter-spacing:.15em;color:var(--haze)}
.depth{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.depth .move{font-size:17px;line-height:1.45;margin:0 0 4px}
.depth .arrow{color:var(--kelp);font-weight:700}
.rung{display:inline-block;font-size:12px;font-weight:700;padding:3px 9px;border-radius:99px;background:#1C2B42;color:var(--ink)}
.rung.hi{background:#123528;color:var(--kelp)}
.ladder{display:flex;gap:4px;margin-top:12px;font-size:10px;color:var(--haze);flex-wrap:wrap}
.ladder span{padding:3px 7px;border-radius:6px;background:#1C2B42}
.ladder span.on{background:var(--kelp);color:#06231A;font-weight:700}
.assess{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.assess .task{font-size:19px;font-weight:700;margin:0 0 3px}
.assess .when{font-size:13px;color:var(--haze)}
.assess .read{margin-top:9px;font-size:15px;line-height:1.45}
.pill{display:inline-block;font-size:11px;font-weight:700;padding:3px 9px;border-radius:99px;margin-left:7px;vertical-align:middle}
.pill.ready{background:#123528;color:var(--kelp)}.pill.building{background:#122C42;color:var(--reef)}.pill.early{background:#2E1813;color:var(--flare)}
.story{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:15px 17px;margin-bottom:10px}
.story h3{font-size:16px;margin:0 0 3px;line-height:1.3}
.tag{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.08em;padding:3px 8px;border-radius:5px;margin-bottom:8px}
.tag.RESOLVED,.tag.DEEPENED{background:#123528;color:var(--kelp)}
.tag.TRENDINGWELL{background:#122C42;color:var(--reef)}
.tag.WATCHING{background:#2C2512;color:#E7B24A}
.tag.TOCLOSE{background:#2E1813;color:var(--flare)}
.scale{margin:11px 0 4px}
.scale .track{display:flex;gap:3px;height:9px}
.scale .track b{flex:1;border-radius:99px;background:#1C2B42}
.scale .track b.on0{background:#F0703F}
.scale .track b.on1{background:#E8963C}
.scale .track b.on2{background:#8FBE45}
.scale .track b.on3{background:var(--kelp)}
.scale .lab{display:flex;justify-content:space-between;margin-top:6px;font-size:11.5px;color:var(--haze)}
.scale .lab b{font-weight:700;color:var(--ink)}
.days{display:flex;gap:4px;margin-top:7px;align-items:center}
.days u{text-decoration:none;font-size:10px;color:var(--haze);margin-right:3px;letter-spacing:.08em}
.days i{font-style:normal;width:7px;height:7px;border-radius:99px;background:#33415C;display:inline-block}
.days i.y{background:var(--kelp)}
.days i.n{background:#E8963C}
.diag{background:#0D1A2C;border-left:3px solid var(--line);padding:9px 12px;margin:9px 0;font-size:14px;line-height:1.45}
.diag b{color:var(--flare)}
.next{font-size:14px;color:var(--haze);line-height:1.45;margin-top:8px}
.next b{color:var(--ink);font-weight:600}
.quote{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--kelp);border-radius:12px;padding:16px 18px;font-size:16px;line-height:1.55}
.quote .attr{display:block;margin-top:9px;font-size:12px;color:var(--haze)}
.sd{display:grid;gap:10px}
.sd .box{border-radius:14px;padding:16px 18px}
.sd .say{background:#123528;border:1px solid #1E5C46}
.sd .do{background:#0C1728;border:1px solid #24324B;color:var(--ink)}
.sd .lbl{font-size:11px;letter-spacing:.15em;margin-bottom:6px;opacity:.75}
.sd .body{font-size:16px;line-height:1.5}
.acc{width:100%;border-collapse:collapse;font-size:14px}
.acc td{padding:7px 4px;border-bottom:1px solid var(--line)}
.acc td.b{width:50%}
.acc .bar{height:8px;border-radius:99px;background:#1C2B42;overflow:hidden}
.acc .bar span{display:block;height:100%;background:var(--kelp);border-radius:99px}
.acc td.n{text-align:right;color:var(--haze);font-size:13px}
.wow{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:9px}
.wow .cell{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--haze);border-radius:12px;padding:12px 14px}
.wow .cell.up{border-left-color:var(--kelp)}
.wow .cell.down{border-left-color:#E8963C}
.wow .cell .k{font-size:11px;letter-spacing:.08em;color:var(--haze);text-transform:uppercase}
.wow .cell .v{font-size:26px;font-weight:700;margin-top:3px;font-family:'Space Mono',monospace}
.wow .cell.up .v i{color:var(--kelp);font-style:normal}
.wow .cell.down .v i{color:#E8963C;font-style:normal}
.wow .cell.flat .v i{color:var(--haze);font-style:normal}
.wow .cell .was{font-size:12px;color:var(--haze)}
.wow .cell .n{font-size:12px;color:var(--haze);margin-top:5px;line-height:1.4}
.wow.empty{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;display:block}
.plan{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px}
.plan ul{margin:0;padding-left:18px}
.plan li{font-size:15px;line-height:1.5;margin-bottom:6px}
.xp{display:flex;align-items:baseline;justify-content:space-between;margin-top:30px;padding-top:16px;border-top:2px solid var(--line)}
.xp .lbl{font-size:11px;letter-spacing:.14em;color:var(--haze)}
.xp .v{font-size:28px;color:var(--flare)}
details{margin-top:14px}
summary{cursor:pointer;font-size:12px;color:var(--reef);letter-spacing:.04em}
.notes{font-size:12.5px;color:var(--haze);line-height:1.6;margin-top:10px}
.foot{margin-top:22px;font-size:12.5px;color:var(--haze);line-height:1.55}
.foot a{color:var(--reef)}
/* activity strip (V2 §3.2) — the week in one line */
.strip{display:flex;flex-wrap:wrap;gap:8px 18px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:6px 0 4px}
.strip .cell{font-size:14px;color:var(--haze)}
.strip .cell b{color:var(--ink);font-weight:700;font-family:'Space Mono',monospace}
/* SUBJECT SPINE (V2 §3.3) — one block per subject, Monday's loop closed */
.subj{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:15px 17px;margin-bottom:12px}
.subj-head{font-size:17px;line-height:1.25;margin:0 0 7px}
.subj-head .sh-subj{font-family:'Archivo Black','Arial Black',sans-serif;letter-spacing:.03em;text-transform:uppercase;font-size:13px;color:var(--reef)}
.subj-head .sh-unit{font-weight:700}
.subj-worked{font-size:13.5px;color:var(--haze);line-height:1.45;margin:0 0 10px}
.subj-worked b{color:var(--ink);font-weight:600}
.subj-table{width:100%;border-collapse:collapse;font-size:14px}
.subj-table th{text-align:left;font-size:10px;letter-spacing:.1em;color:var(--haze);font-weight:700;padding:0 6px 5px 0;text-transform:uppercase}
.subj-table td{padding:7px 6px 7px 0;border-top:1px solid var(--line);vertical-align:top;line-height:1.35}
.subj-table td.pos{white-space:nowrap}
.subj-table .dot{font-size:12px;margin-right:5px;vertical-align:baseline}
.dot.d0{color:#F0703F}.dot.d1{color:#E8963C}.dot.d2{color:#8FBE45}.dot.d3{color:var(--kelp)}
.subj-table .dep{color:var(--ink)}
.subj-table .dep.none{color:var(--haze)}
.subj-table .tq{font-size:11.5px;color:var(--haze);margin-top:3px;white-space:nowrap}
.subj-table .tq b{font-family:'Space Mono',ui-monospace,monospace;color:var(--haze);font-weight:700}
.subj-table .moved{font-style:normal;color:var(--kelp);font-size:12px}
.subj-table .moved.new{color:var(--reef)}
.subj-detail{background:#0D1A2C;border-left:3px solid var(--line);padding:9px 12px;margin:11px 0 0;font-size:13.5px;line-height:1.45}
.subj-detail b{color:var(--ink)}
.subj-detail .pick{color:var(--flare)}
.subj-next{font-size:13.5px;color:var(--haze);line-height:1.45;margin:9px 0 0}
.subj-next b{color:var(--ink);font-weight:600}
.fluency{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--reef);border-radius:12px;padding:13px 16px;margin-bottom:12px;font-size:14.5px;line-height:1.5}
.fluency b{color:var(--reef)}
/* cumulative footer strip (V2 §3.5) */
.cumf{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 16px;font-size:14px;line-height:1.6;color:var(--ink)}
.cumf a{color:var(--reef);white-space:nowrap}
.cumf .sep{color:var(--haze)}
"""

RUNGS = [("not_yet", "not yet"), ("knows", "knows it"), ("lists", "can list it"),
         ("connects", "can connect it"), ("applies", "can apply it elsewhere")]
RUNG_LABEL = dict(RUNGS)
WORD_SUB = {
    "strong": "High activity and things moving forward — a week to celebrate.",
    "solid": "Steady and on pace — the undramatic kind of good week.",
    "quiet": "A lighter week on the nightly runs — nothing lost, just worth easing back in.",
    "slower": "He showed up, but the set bit back this week — the learning needs a little support.",
}
WORD_CAP = {"strong": "Strong", "solid": "Solid", "quiet": "Quiet", "slower": "Harder"}
# Headlines are phrased from the BAND (where the topic sits), not from the
# week's events, so the title and the scale beneath it can never contradict.
HEADLINE = {
    "RESOLVED": "{topic} — came good this week",
    "TRENDING WELL": "{topic} — a clean run",
    "TO CLOSE": "{topic} — {band_phrase}",
    "DEEPENED": "{topic} — understood more deeply",
    "WATCHING": "Worth a light watch",
}
BAND_PHRASE = {0: "not started yet", 1: "early on this one", 2: "still building",
               3: "close, one thing to fix", 4: "solid, just a slip"}


def _e(s):
    return html.escape(str(s if s is not None else ""))


def _hero(card):
    name = card["name"].split()[0]
    if card.get("baseline"):
        return f"{name} · first week on the board"
    tail = {"up": "building on last week", "down": "off last week's pace",
            "flat": "tracking level with last week"}.get(card["week_word"]["direction"], "")
    return f"{name}" + (f" · {tail}" if tail else "")


def _depth_block(card, stories):
    """The ledger made visible — depth movement, or an honest explanation of why not."""
    name = card["name"].split()[0]
    moves = [s for s in stories if s.get("status") == "DEEPENED"]
    if moves:
        m = moves[0]
        frm = RUNG_LABEL.get(m["from"], m["from"])
        to = RUNG_LABEL.get(m["to"], m["to"])
        line = (f"{_e(name)} moved from <span class='rung'>{_e(frm)}</span> "
                f"<span class='arrow'>&rarr;</span> <span class='rung hi'>{_e(to)}</span> "
                f"on <strong>{_e(m['topic'])}</strong>.")
        extra = ("That's the jump exams reward — explaining how ideas connect, "
                 "not just recalling them." if m["to"] == "connects" else "")
        rungs = "".join(f"<span class='{'on' if k == m['to'] else ''}'>{_e(v)}</span>"
                        for k, v in RUNGS)
        return ("<div class='section'>WHAT CHANGED</div><div class='depth'>"
                f"<p class='move'>{line}</p><p class='next'>{extra}</p>"
                f"<div class='ladder'>{rungs}</div></div>")
    rungs = "".join(f"<span>{_e(v)}</span>" for _, v in RUNGS)
    return ("<div class='section'>WHAT CHANGED</div><div class='depth'>"
            "<p class='move'>No movement in depth of understanding to report yet.</p>"
            f"<p class='next'>Multiple-choice questions can only show that {_e(name)} "
            "<em>knows</em> or <em>can list</em> something. Moving up to "
            "<em>can connect it</em> needs a written explanation, and those run once "
            "or twice a night — so this fills in over weeks, not days.</p>"
            f"<div class='ladder'>{rungs}</div></div>")


def _assess_block(card):
    r = card.get("radar")
    if not r:
        return ""
    when = "this week" if r["days"] <= 7 else "next week"
    read = r["readiness"]
    if read == "ready":
        line = "He's in good shape for it — the topics it covers are holding."
    elif read == "building":
        foc = f" <strong>{_e(r['focus'])}</strong> is the one to firm up." if r.get("focus") else ""
        line = "Coming together — most of it has landed." + foc
    else:
        foc = f" <strong>{_e(r['focus'])}</strong> is the place to start." if r.get("focus") else ""
        line = ("Early days on this topic yet, so a good week to get ahead of it — "
                "plenty of runway." + foc)
    days_txt = "in a few days" if r["days"] <= 7 else f"in {r['days']} days"
    return ("<div class='section'>WHAT'S COMING</div>"
            f"<div class='assess'><div class='task'>{_e(r['task'])}"
            f"<span class='pill {read}'>{_e(read)}</span></div>"
            f"<div class='when'>{_e(r['subject'])} · {when} ({days_txt})</div>"
            f"<div class='read'>{line}</div></div>")


# Where a topic sits, as a SCALE rather than a verdict. A wrong answer is a
# position on a journey, not a cross — the bands run red -> amber -> green so a
# gap reads as "early on this", which is both kinder AND more informative than
# a tick/cross. This is the confidence axis (state) made visible on every card.
BANDS = [("Not started yet", 0), ("Getting started", 0), ("Building", 1),
         ("Nearly there", 2), ("Solid", 3)]
STATE_BAND = {"untested": 1, "REPAIR": 1, "shaky": 2, "developing": 3, "solid": 4}


def _scale(state, trace=None):
    """A 4-segment red->green scale showing where this topic currently sits."""
    band = STATE_BAND.get(state, 1)
    label, colour = BANDS[band][0], BANDS[band][1]
    segs = "".join(f"<b class='{'on'+str(colour) if i < band else ''}'></b>"
                   for i in range(4))
    days = ""
    if trace:
        seen = {}
        for t in trace:                      # one dot per DAY, best result that day
            d = t.get("day", "")
            if d not in seen or t.get("ok"):
                seen[d] = t.get("ok")
        dots = "".join(
            f"<i class='{'y' if v else 'n' if v is False else ''}' title='{_e(k)}'></i>"
            for k, v in seen.items())
        days = f"<div class='days'><u>THIS WEEK</u>{dots}</div>"
    return (f"<div class='scale'><div class='track'>{segs}</div>"
            f"<div class='lab'><span>Where it sits: <b>{_e(label)}</b></span></div>"
            f"{days}</div>")


def _story_card(s, name):
    status = s["status"]
    cls = status.replace(" ", "")
    band = STATE_BAND.get(s.get("state"), 1)
    head = HEADLINE.get(status, "{topic}").format(
        topic=_e(s.get("topic") or ""), band_phrase=BAND_PHRASE.get(band, "still building"))
    body = ""
    if status == "WATCHING":
        body = (f"<p class='next'>On {s['count']} of the {s['of']} questions {_e(name)} "
                "marked “Sure” this week, the answer didn't land. Confidence running a "
                "step ahead of knowledge is normal at this age — a tendency, not a trait.</p>")
    m = s.get("misconception")
    diag = ""
    if m and m.get("why"):
        diag = (f"<div class='diag'>He chose <b>{_e(m['picked'])}</b>; the answer was "
                f"<strong>{_e(m['correct'])}</strong>.<br>{_e(m['why'])}</div>")
    scale = _scale(s.get("state"), s.get("trace")) if s.get("topic") else ""
    return (f"<div class='story'><span class='tag {cls}'>{_e(status)}</span>"
            f"<h3>{head}</h3>{scale}{body}{diag}"
            f"<p class='next'><b>Next:</b> {_e(s.get('next',''))}</p></div>")


def _quote_block(q, name):
    if not q:
        return ""
    attr = f"{_e(name)}'s own explanation"
    if q.get("secs") and q["secs"] >= 60:
        attr += f", {int(q['secs']//60)} min of writing"
    if q.get("subject"):
        attr = f"{_e(q['subject'])} teach-back — {attr}"
    return ("<div class='section'>IN HIS OWN WORDS</div>"
            f"<div class='quote'>“{_e(q['text'])}”<span class='attr'>{attr}</span></div>")


def _say_do(card, stories, quote):
    """Two scripts. PROCESS-level praise (name the move), never person-level."""
    name = card["name"].split()[0]
    deep = next((s for s in stories if s["status"] == "DEEPENED"), None)
    if quote and deep:
        say = ("Point at what he actually did: “You explained <em>why</em> it works, "
               "not just what the answer was — that's the part that earns marks.”")
    elif quote:
        say = ("Quote his own line back and name the move: “You put that in your own "
               "words — that's the bit that makes it stick.”")
    else:
        say = ("Keep it about the habit, not the ability: “You showed up to it this "
               "week — that's the part that compounds.”")
    a = card["action"]
    k = a.get("kind")
    if k == "assess":
        do = (f"Five minutes on <strong>{_e(a['topic'])}</strong> before the "
              f"{_e(a['task'])} — ask him to talk you through it. He does the talking.")
    elif k == "repair":
        do = (f"Five minutes on <strong>{_e(a['topic'])}</strong> — it's due a revisit. "
              "Ask him to explain it back to you.")
    elif k == "behind":
        do = (f"Five minutes on <strong>{_e(a['topic'])}</strong> — the class has moved "
              "to it, so a quick catch-up helps.")
    elif k == "ask":
        do = (f"Ask him to explain <strong>{_e(a['topic'])}</strong> to you. He's got it "
              "solid, and teaching it out loud locks it in.")
    else:
        do = "Nothing to fix this week — just keep the nightly run going."
    return ("<div class='section'>SAY ONE THING · DO ONE THING</div><div class='sd'>"
            f"<div class='box say'><div class='lbl'>SAY</div><div class='body'>{say}</div></div>"
            f"<div class='box do'><div class='lbl'>DO · FIVE MINUTES</div>"
            f"<div class='body'>{do}</div></div></div>")


def _accuracy(acc):
    if not acc:
        return ""
    rows = []
    for subj in sorted(acc, key=lambda s: -acc[s]["asked"]):
        r = acc[subj]
        pct = round(100 * r["right"] / r["asked"]) if r["asked"] else 0
        rows.append(f"<tr><td>{_e(subj)}</td><td class='b'><div class='bar'>"
                    f"<span style='width:{pct}%'></span></div></td>"
                    f"<td class='n'>{r['right']} of {r['asked']}</td></tr>")
    return ("<div class='section'>HOW THE WEEK WENT, BY SUBJECT</div>"
            f"<table class='acc'>{''.join(rows)}</table>"
            "<p class='notes'>Small numbers of questions — read these as a rough shape, "
            "not a measurement.</p>")


def _next_week(card, stories):
    """The plan for next week — the FEED-FORWARD half of the feedback model
    ("where to next?"), which most reports omit. Consolidates what the story
    cards each promise individually, plus what the ledger will schedule, so a
    parent can see the system has a plan rather than just a verdict.

    Deliberately NOT a points target: a target on points rewards choosing easier
    questions. Targets belong on mastery and cadence.
    """
    name = card["name"].split()[0]
    items = []
    r = card.get("radar")
    if r:
        focus = f" — {_e(r['focus'])} first" if r.get("focus") else ""
        items.append(f"<li><b>{_e(r['task'])}</b> practice steps up{focus}.</li>")
    closing = [s for s in stories if s.get("status") == "TO CLOSE" and s.get("topic")]
    if closing:
        names = ", ".join(_e(s["topic"]) for s in closing[:3])
        items.append(f"<li>Back for another look: {names}.</li>")
    easing = [s for s in stories if s.get("status") in ("TRENDING WELL", "RESOLVED")
              and s.get("topic")]
    if easing:
        names = ", ".join(_e(s["topic"]) for s in easing[:2])
        items.append(f"<li>Easing off to light maintenance: {names} — "
                     f"those slots go to newer content.</li>")
    deep = [s for s in stories if s.get("status") == "DEEPENED"]
    if deep:
        items.append("<li>A written explanation question, aimed one rung higher.</li>")
    elif not card.get("baseline"):
        items.append("<li>More written-explanation questions — they're the only way "
                     "to show understanding beyond recall.</li>")
    if not items:
        items.append("<li>Steady as it is — the nightly run is the whole plan.</li>")
    return ("<div class='section'>NEXT WEEK</div>"
            f"<div class='plan'><ul>{''.join(items)}</ul>"
            f"<p class='next'>{_e(name)} doesn't need to be told any of this — "
            "the quiz just does it.</p></div>")


def _wow(rows, card):
    """Week-over-week strip — the 'is this working?' answer, OVERALL.

    Week 1 has no prior, so instead of a blank we show what will appear next
    Friday. That's honest (it under-claims rather than faking a trend) and it
    sets the expectation that this section is where the payoff accumulates.
    """
    if not rows:
        if not card.get("baseline"):
            return ""
        return ("<div class='section'>WEEK ON WEEK</div><div class='wow empty'>"
                "<p class='move'>Nothing to compare against yet — this is week one.</p>"
                "<p class='next'>From next Friday this is where you'll see the trend: "
                "nights run, how much landed across all subjects together, and how many "
                "topics moved up a rung in understanding. Comparisons are kept overall "
                "rather than subject-by-subject — a single week is only a few questions "
                "per subject, which is too few to mean anything.</p></div>")
    cells = []
    for r in rows:
        d = r.get("dir", "flat")
        arrow = {"up": "&uarr;", "down": "&darr;", "flat": "&rarr;"}[d]
        prev = ("" if r.get("prev") is None
                else f"<span class='was'>was {_e(r['prev'])}</span>")
        cells.append(
            f"<div class='cell {d}'><div class='k'>{_e(r['label'])}</div>"
            f"<div class='v'>{_e(r['now'])} <i>{arrow}</i></div>"
            f"{prev}<div class='n'>{_e(r.get('note',''))}</div></div>")
    return ("<div class='section'>WEEK ON WEEK</div>"
            f"<div class='wow'>{''.join(cells)}</div>"
            "<p class='notes'>Compared overall, not subject by subject — one week is "
            "only a handful of questions per subject, too few to read a trend from.</p>")


def _notes(card, extra_notes):
    base = []
    if card.get("baseline"):
        base.append("This is the first week, so there's no previous week to compare "
                    "against — nothing here is a trend yet. Trajectory starts next Friday.")
    base.append("Depth (\u201cknows it / can list it / can connect it / can apply it "
                "elsewhere\u201d) is based on the SOLO taxonomy, a standard framework "
                "for assessing depth of understanding, written here in plain language.")
    base.append("Daily points aren't compared across days — question difficulty varies, "
                "so points are a rough guide only.")
    base += list(extra_notes or [])
    items = "".join(f"<p class='notes'>{_e(n)}</p>" for n in base)
    return f"<details><summary>Reading notes — how to read this</summary>{items}</details>"


def _speed(sp, name):
    """Fluency — shown only when it MOVED (see report_stories.speed_shift)."""
    if not sp:
        return ""
    if sp["faster"]:
        line = (f"{_e(name)} is answering about {sp['pct']}% faster than last week "
                f"({sp['prev']}s &rarr; {sp['now']}s a question). Recall getting "
                f"automatic is what frees up thinking room in a test.")
    else:
        line = (f"{_e(name)} is taking about {sp['pct']}% longer per question than "
                f"last week ({sp['prev']}s &rarr; {sp['now']}s) — usually a sign the "
                f"material got harder, which is where it should be.")
    return f"<div class='section'>SPEED</div><div class='depth'><p class='move'>{line}</p></div>"


def _activity_strip(card):
    """The week in one line (V2 §3.2): nights · topics practised · events.
    Uses the excused-aware denominator already in the card (activity.possible)."""
    a = card.get("activity") or {}
    dd, poss = a.get("days_done", 0), a.get("possible", 0)
    cells = [f"<span class='cell'><b>{dd} of {poss}</b> nights run</span>",
             f"<span class='cell'><b>{a.get('topics_practised', 0)}</b> topics practised</span>"]
    ev = a.get("events", 0)
    if ev:
        cells.append(f"<span class='cell'><b>{ev}</b> event{'s' if ev != 1 else ''} cleared</span>")
    return f"<div class='strip'>{''.join(cells)}</div>"


def _subject_block(b, name):
    """One subject block: what class is on -> what his sets worked -> where each
    topic stands (band + depth WHERE EVIDENCED, plus the week's practice
    volume) -> one detail -> next week.

    The detail slot holds ONE thing per subject, best first: the fluency-catch
    narration when it fired on this subject's topic (`fluency_detail`, set by
    the portal's Weekly-update page — Rich, 30 Aug: that safeguard IS the
    detail worth knowing), else the misconception from the ranked stories.
    """
    unit = f" <span class='sh-unit'>&mdash; {_e(b['unit'])}</span>" if b.get("unit") else ""
    worked = " &middot; ".join(f"<b>{_e(w)}</b>" for w in b.get("worked", []))
    worked_html = (f"<div class='subj-worked'>This week his sets worked: {worked}</div>"
                   if worked else "")
    rows = []
    for t in b.get("topics", []):
        band = STATE_BAND.get(t.get("state"), 1)
        label, colour = BANDS[band][0], BANDS[band][1]
        dep = t.get("depth")
        if dep in RUNG_LABEL:
            dep_html = f"<span class='dep'>{_e(RUNG_LABEL[dep].capitalize())}</span>"
        else:
            dep_html = "<span class='dep none'>&mdash;</span>"
        moved = t.get("moved")
        if moved == "up":
            dep_html += " <em class='moved'>&middot; moved up this week</em>"
        elif moved == "new":
            dep_html += " <em class='moved new'>&middot; new this week</em>"
        # practice volume: always the asked count; the right count only once
        # there are 2+ answers — a single question's accuracy is pure noise.
        asked = t.get("asked")
        if asked:
            tq = f"<b>{asked}</b> asked"
            if asked >= 2 and t.get("right") is not None:
                tq += f" &middot; <b>{t['right']}</b> right"
            tq_html = f"<div class='tq'>{tq}</div>"
        else:
            tq_html = ""
        rows.append(
            f"<tr><td>{_e(t.get('topic'))}{tq_html}</td>"
            f"<td class='pos'><span class='dot d{colour}'>&#9679;</span>{_e(label)}</td>"
            f"<td>{dep_html}</td></tr>")
    table = ("<table class='subj-table'><tr><th>Topic</th><th>Where he is</th>"
             f"<th>Depth</th></tr>{''.join(rows)}</table>")
    detail = ""
    if b.get("fluency_detail"):
        detail = (f"<div class='subj-detail'><b>The detail worth knowing:</b> "
                  f"on <b>{_e(b['fluency_detail'])}</b> {_e(name)} could pick the "
                  "right answer but couldn't yet put the why in his own words "
                  "&mdash; so the deeper level was held until the explanation "
                  "catches up. That safeguard sits behind every position here."
                  "</div>")
    else:
        m = b.get("detail")
        if m and m.get("why"):
            detail = (f"<div class='subj-detail'><b>The detail worth knowing:</b> "
                      f"he chose <span class='pick'>{_e(m['picked'])}</span>; the answer was "
                      f"<b>{_e(m['correct'])}</b>. {_e(m['why'])}</div>")
    nxt = (f"<div class='subj-next'><b>Next week:</b> {_e(b['next'])}.</div>"
           if b.get("next") else "")
    return (f"<div class='subj'><div class='subj-head'>"
            f"<span class='sh-subj'>{_e(b['subject'])}</span>{unit}</div>"
            f"{worked_html}{table}{detail}{nxt}</div>")


def _subject_blocks(blocks, fluency, name):
    """The subject spine — the redesign's core (V2 §3). Empty string when there
    are no blocks (the page falls back to the legacy story cards)."""
    if not blocks:
        return ""
    flu = ""
    if fluency:
        flu = ("<div class='fluency'>On <b>" + _e(fluency) + "</b>, " + _e(name)
               + " could pick the right answer but not yet put the why in his own "
               "words &mdash; so the system held the deeper level until the "
               "explanation catches up. That safeguard is the rigour behind every "
               "&ldquo;solid&rdquo; here.</div>")
    body = "".join(_subject_block(b, name) for b in blocks)
    return f"<div class='section'>BY SUBJECT &mdash; THIS WEEK</div>{flu}{body}"


def _cumulative_footer(card, portal_url):
    """The cumulative-by-subject strip (V2 §3.5) — landed of total per subject,
    linking the portal. Already computed (card.snapshot), never rendered before."""
    rows = (card.get("snapshot") or {}).get("rows") or []
    parts = []
    for r in rows:
        total = (r.get("landed", 0) or 0) + (r.get("building", 0) or 0)
        if total:
            parts.append(f"{_e(r['subject'])} {r['landed']} of {total} topics landed")
    if not parts:
        return ""
    strip = "<span class='sep'> &middot; </span>".join(parts)
    link = (f"<span class='sep'> &middot; </span><a href='{_e(portal_url)}'>full picture &rarr;</a>"
            if portal_url else "")
    return (f"<div class='section'>WHERE IT ADDS UP</div>"
            f"<div class='cumf'>{strip}{link}</div>")


def render(card, stories=None, quote=None, accuracy=None, kid_wrap_url=None,
           extra_notes=None, speed=None, wow=None, subjects=None, fluency=None,
           portal_url=None):
    """Full self-contained HTML for one kid-week parent report."""
    stories = stories or []
    subjects = subjects or []
    name = card["name"].split()[0]
    word = card["week_word"]["word"]
    subj_spine = _subject_blocks(subjects, fluency, name)
    # With the subject spine live, per-topic RESOLVED/TRENDING/TO CLOSE stories
    # are told inside their subject block — only the topic-less WATCHING tendency
    # remains as a cross-cutting card. Without a spine (minimal/legacy render) the
    # full WHAT HAPPENED section is the fallback. DEEPENED is always the depth
    # block's job, never a duplicate card.
    if subj_spine:
        residual = [s for s in stories if s.get("status") == "WATCHING"]
        residual_label = "WORTH A WATCH"
    else:
        residual = [s for s in stories if s.get("status") != "DEEPENED"]
        residual_label = "WHAT HAPPENED"
    story_html = "".join(_story_card(s, name) for s in residual)
    stories_section = (f"<div class='section'>{residual_label}</div>{story_html}"
                       if story_html else "")
    wrap_link = (f" &nbsp;·&nbsp; <a href='{_e(kid_wrap_url)}'>{_e(name)}'s player card</a>"
                 if kid_wrap_url else "")
    stamp = build_stamp()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="xpdaily-build" content="{_e(stamp)}" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="noindex, nofollow" />
<meta name="theme-color" content="#0B1220" />
<title>XPDaily — {_e(name)}'s week</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="top"><span class="brand">XPDAILY · WEEKLY REPORT</span><span class="week">Week of {_e(card.get('week_of',''))}</span></div>
  <div class="hero">{_e(_hero(card))}</div>
  <h1 class="word display {word}">{WORD_CAP.get(word, word)}</h1>
  <p class="sub">{_e(WORD_SUB.get(word,''))}</p>
  {_activity_strip(card)}
  {subj_spine}
  {_assess_block(card)}
  {_quote_block(quote, name)}
  {_say_do(card, stories, quote)}
  {_depth_block(card, stories)}
  {stories_section}
  {_wow(wow, card)}
  {_speed(speed, name)}
  {_accuracy(accuracy)}
  {_next_week(card, stories)}
  {_cumulative_footer(card, portal_url)}
  <div class="xp"><span class="lbl">SEASON TOTAL</span><span class="v num">{card['xp_total']:,} XP</span></div>
  {_notes(card, extra_notes)}
  <p class="foot">This is {_e(name)}'s week, bounded — nothing here needs a reply.{wrap_link}</p>
  <p class="foot">build {_e(stamp)}</p>
</div>
</body>
</html>"""
