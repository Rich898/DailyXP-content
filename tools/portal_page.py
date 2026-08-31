#!/usr/bin/env python3
"""
portal_page.py — the PARENT PORTAL: the parent's product home (PARENT-PORTAL-BRIEF).

Not a report page — a small product. The parent report is THREE distinct,
designed pages, reached from a home screen by an app-style nav, each laid out
on its own terms:

  /p/<slug>/            HOME — the front door. Who this is, what's on the radar,
                        three doorways (each with a live one-line teaser), the
                        account surface (v1: honest stub), the kid's player card.
  /p/<slug>/ahead/      THE WEEK AHEAD (Monday, forward) — the light glance:
                        per subject, what school is covering this week and what
                        his sets will do about it; ONE assessment date. From
                        monday_brief.week_ahead(). The Monday SMS points here.
  /p/<slug>/week/       THIS WEEK (Friday, backward) — the deep read: the
                        verdict word, then the subject spine (what school set →
                        what his sets worked → where each topic stands → the one
                        misconception detail → next week), with the
                        fluency-illusion catch narrated. Blocks come from
                        report_stories.subject_blocks, drawn by report_page's
                        own block renderer so Friday's two surfaces share one
                        shape. The Friday SMS points here.
  /p/<slug>/picture/    THE RUNNING PICTURE (Friday, cumulative) — the map:
                        the per-subject landed tally, position + depth on every
                        active topic (the confidently-shallow cross rendered
                        where it fires), term trends (4-week gate), the archive
                        of past Friday reports, and the legend.

WHY REAL PAGES, not client-side tabs: each page gets its own layout and its own
hero (the anti-long-scroll mandate); the Monday/Friday SMS pointers deep-link
cleanly; every page is small, self-contained and individually stamp-verified by
the existing one-page-per-path deploy machinery (publish slug "abc/ahead" lands
at /p/abc/ahead/). Navigation is a fixed bottom app bar — thumb reach on the
phone where parents open this — plus doorway cards on home.

PAGE ACCENTS (one system, three time-frames): the WEEK AHEAD is reef (the blue
horizon, forward), THIS WEEK is flare (the live heat of the week), the RUNNING
PICTURE is kelp (what has grown). Home is ink. Everything else reuses
report_page's ratified dark system — tokens, bands, depth ceiling, fonts.

PORTAL LAWS (PARENT-COMMS-V2 §5, to ratify):
  * FRESHNESS CONTRACT. Judgment-shaped facts (positions, depth, trends)
    recompute FRIDAY only; the Week-Ahead page refreshes Monday; every page
    carries a visible "updated {date}" and names its own cadence. NO same-night
    results, ever — an always-on surface must not become an interrogation feed.
  * FORWARD-ONLY AHEAD. The Week-Ahead page renders only monday_brief facts —
    no ledger state can reach it by construction.
  * DEPTH CEILING. A rung renders only where evidenced ("—" otherwise); an
    MCQ-only topic never implies more than "can list it".
  * POSITIONS WEEKLY, TRENDS MONTHLY. Per-topic position shows any week;
    per-subject trend waits for the 4+ week window, and the page says so.
  * DIGNITY / AGING. Repaired topics collapse into wins, not a rap sheet. (The
    teach-back quote archive waits on the APP 8 privacy advice — not built.)

ACCOUNT SURFACE (v1 stub, designed-in): home carries YOUR ACCOUNT — the four
touchpoints with their cadence and an honest "text Rich to change anything"
line (the documented opt-out path). When per-touchpoint config (C6) and the
magic-link door (family #2) arrive, they land in this space; the shell doesn't
change, what fills it does.

PRIVACY: same model as report_page — fully self-contained, ZERO fetch, noindex,
unguessable lowercase slug, build-stamped for netlify_deploy.verify().

CODE DECIDES, LANGUAGE DRESSES: build_portal() reads only already-computed
facts. Every sentence here is fixed copy around code-picked facts. No AI.
"""
import datetime as _dt

import report_page as rp   # reuse the dark design system + band/depth/ceiling

_e = rp._e

# Depth rungs that are SHALLOW (recall-level) vs DEEP (explanation-level). The
# founding "confidently shallow" insight is solid confidence over a shallow rung.
_SHALLOW_DEPTH = {"not_yet", "knows", "lists"}
_DEEP_DEPTH = {"connects", "applies"}

# Position bands reuse report_page's ratified scale (state -> band -> label/colour).
_BANDS = rp.BANDS
_STATE_BAND = rp.STATE_BAND
_RUNG_LABEL = rp.RUNG_LABEL


# --------------------------------------------------------------------------- #
# Facts assembly — deterministic, from already-computed data only.
# (Kept intact from the first build; the presentation below is what was redone.)

def _confidently_shallow(state, depth):
    """The founding cross: strong recall (solid) over a shallow/unevidenced rung.
    solid x {knows,lists,not_yet, or no teach-back yet} — he can pick it but
    hasn't yet shown he can explain it. Never fires for a topic that reached
    connects/applies."""
    if state != "solid":
        return False
    return depth is None or depth in _SHALLOW_DEPTH


def subject_cards(topics):
    """Per-subject, per-topic position + depth (V2 §5.3). Every ACTIVE ledger
    topic (not archived/frozen) renders both axes; the confidently-shallow cross
    is flagged. Ordered by subject, then weakest-first inside a subject so the
    work to do reads top-down."""
    order = {"REPAIR": 0, "shaky": 1, "untested": 2, "developing": 3, "solid": 4}
    by_subj = {}
    for tp in topics:
        st = tp.get("state")
        if st in (None, "FROZEN", "archived", "retired"):
            continue
        by_subj.setdefault(tp.get("subject") or "Other", []).append(tp)
    cards = []
    for subj in sorted(by_subj):
        rows = []
        for tp in sorted(by_subj[subj], key=lambda t: order.get(t.get("state"), 5)):
            rows.append({"topic": tp.get("topic"), "state": tp.get("state"),
                         "depth": tp.get("depth"),
                         "confidently_shallow": _confidently_shallow(
                             tp.get("state"), tp.get("depth"))})
        if rows:
            cards.append({"subject": subj, "rows": rows})
    return cards


def term_trends(snapshots, min_weeks=4):
    """Per-subject term trend from the banked weekly snapshots (V2 §5.4). Returns
    None (with the honest "fills in at N weeks" copy left to the renderer) until
    there are min_weeks of snapshots — a trend before then is noise. Each
    snapshot is {week_of, <code>:{topic:state}, ...}; the trend counts landed
    topics per subject over time.

    `snapshots` here is pre-filtered to ONE kid: a list of
    {week_of, topics:{topic:state}, subjects:{topic:subject}} oldest-first.
    """
    if not snapshots or len(snapshots) < min_weeks:
        return None
    _LANDED = {"developing", "solid"}
    series = []
    for snap in snapshots:
        by_subj = {}
        subjmap = snap.get("subjects", {})
        for topic, st in (snap.get("topics") or {}).items():
            subj = subjmap.get(topic, "Other")
            b = by_subj.setdefault(subj, {"landed": 0, "total": 0})
            b["total"] += 1
            if st in _LANDED:
                b["landed"] += 1
        series.append({"week_of": snap.get("week_of"), "by_subject": by_subj})
    subjects = sorted({s for pt in series for s in pt["by_subject"]})
    rows = []
    for subj in subjects:
        first = next((pt["by_subject"][subj]["landed"] for pt in series
                      if subj in pt["by_subject"]), 0)
        last_pt = next((pt["by_subject"][subj] for pt in reversed(series)
                        if subj in pt["by_subject"]), None)
        if not last_pt:
            continue
        rows.append({"subject": subj, "landed": last_pt["landed"],
                     "total": last_pt["total"], "gained": last_pt["landed"] - first})
    return {"weeks": len(series), "rows": rows}


def _cumulative(cards):
    """Per-subject rollup for the RUNNING PICTURE's bars, both axes with
    explicit criteria (Rich, 31 Aug — "what's the criteria for it"):
      landed     topics at developing/solid — "Nearly there" or better under
                 questioning (the position axis).
      explained  landed topics whose depth has ALSO reached connects/applies —
                 he can explain them, not just pick them (the depth axis).
    The gap between the two is the exam-risk band: strong recall, shallow
    roots, at subject level."""
    _LANDED = {"developing", "solid"}
    out = []
    for c in cards:
        total = len(c["rows"])
        landed = sum(1 for r in c["rows"] if r.get("state") in _LANDED)
        explained = sum(1 for r in c["rows"]
                        if r.get("state") in _LANDED
                        and r.get("depth") in _DEEP_DEPTH)
        out.append({"subject": c["subject"], "landed": landed,
                    "explained": explained, "total": total})
    return out


def topic_history(snapshots, topics):
    """{topic: [state, ...]} oldest→newest from the banked weekly snapshots,
    with the LIVE state appended so every strip ends at now. Topics appear
    only from the week they were first tracked — a short strip honestly means
    recently started, never missing data."""
    hist = {}
    for snap in snapshots or []:
        for topic, st in (snap.get("topics") or {}).items():
            hist.setdefault(topic, []).append(st)
    out = {}
    for tp in topics or []:
        name = tp.get("topic")
        if name is None:
            continue
        seq = list(hist.get(name, []))
        if tp.get("state") is not None:
            seq.append(tp.get("state"))
        out[name] = seq
    return out


# The four scheduled parent touchpoints — the account surface's v1 truth.
# Static because it IS the current truth: everything sends, and the only
# off-switch is a text to Rich. Wiring (C6) replaces this with real config.
DEFAULT_TOUCHPOINTS = [
    {"when": "Monday evening", "what": "The week-ahead pointer",
     "why": "A short text when the Week Ahead page refreshes"},
    {"when": "Wednesday evening", "what": "The check-in",
     "why": "One praise line and one five-minute help action"},
    {"when": "Friday evening", "what": "The report",
     "why": "The week's read, and this page brought up to date"},
    {"when": "School nights", "what": "The soundbyte",
     "why": "Done-it reassurance once the run is in"},
]


def build_portal(name, week_of, topics, subjects_block, radar,
                 week_ahead=None, this_week_blocks=None, this_week_fluency=None,
                 snapshots=None, archive=None, updated=None,
                 week_verdict=None, activity=None, touchpoints=None,
                 upcoming=None, this_week_of=None, accuracy=None):
    """Assemble the portal fact set — everything the four pages draw from
    (PARENT-COMMS-V2 §1/§5):

      week_ahead        THE WEEK AHEAD (Monday, forward): monday_brief
                        .week_ahead() output {rows, assessment, subjects}.
      this_week_blocks  THIS WEEK (Friday, backward): report_stories
                        .subject_blocks() — what happened, the subject spine.
      week_verdict      optional {"word": strong|solid|quiet|slower} from the
                        Friday card — the This-Week page's hero when present.
      activity          optional {"days_done","possible","topics_practised",
                        "events"} from the Friday card (excused-aware).
      running           THE RUNNING PICTURE (Friday, cumulative): subject cards
                        + landed tally + term trends, this week folded in.
      touchpoints       account-surface rows; DEFAULT_TOUCHPOINTS until real
                        per-family config exists (C6).
      upcoming          every dated thing on the radar, [{task, date, subject?,
                        days?}] — tests, study-guide releases, due dates
                        (Rich, 30 Aug: plural, not one). Falls back to the
                        single `radar` when not supplied. Sorted by date.
      this_week_of      the Monday (ISO) of the week the blocks REPORT — on a
                        Monday-seed build that is last week, not `week_of`.
                        The Weekly update page prints its Mon–Fri span so the
                        reported week is never ambiguous (Rich, 30 Aug).
      accuracy          {subject: {"asked", "right"}} for the whole week
                        (report_stories.subject_accuracy shape) — feeds the
                        accuracy-by-subject bars and the question totals. It
                        may legitimately cover subjects the spine doesn't
                        (warm-ups, event questions); without it the page sums
                        the per-topic counts instead.

    All facts arrive already computed. `archive` = [{"week","url"}] newest-first.
    """
    cards = subject_cards(topics)
    if not upcoming:
        upcoming = [dict(radar)] if radar and radar.get("date") else []
    upcoming = sorted((u for u in upcoming if u.get("date") and u.get("task")),
                      key=lambda u: u["date"])
    return {
        "name": name.split()[0] if name else "",
        "week_of": week_of,
        "updated": updated or _dt.date.today().isoformat(),
        "week_ahead": week_ahead or {},
        "radar": radar or {},
        "upcoming": upcoming,
        "this_week": {"blocks": this_week_blocks or [], "fluency": this_week_fluency,
                      "week_of": this_week_of},
        "accuracy": accuracy or {},
        "week_verdict": week_verdict or {},
        "activity": activity or {},
        "running": {"cards": cards, "cumulative": _cumulative(cards),
                    "trends": term_trends(snapshots or []),
                    "history": topic_history(snapshots or [], topics)},
        "archive": archive or [],
        "touchpoints": touchpoints if touchpoints is not None else DEFAULT_TOUCHPOINTS,
    }


# --------------------------------------------------------------------------- #
# The portal shell — shared chrome: top bar, bottom app nav, footer.

_CSS = rp._CSS + """
/* ------------------------------------------------ portal shell */
:root{--acc:var(--ink)}
body.pg-ahead{--acc:var(--reef)}
body.pg-week{--acc:var(--flare)}
body.pg-picture{--acc:var(--kelp)}
body{padding-bottom:84px}
.ptop{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.ptop .brand{font-size:11px;letter-spacing:.16em;color:var(--haze)}
.ptop .upd{font-size:11px;color:var(--haze)}
.peyebrow{margin:26px 0 0;font-size:11px;letter-spacing:.16em;font-weight:700;color:var(--acc);text-transform:uppercase}
/* headlines are ALWAYS white (Rich, 30 Aug) — the accent lives in the eyebrow,
   chips and nav, never the page title. Includes the verdict word on This Week. */
.phero{margin:6px 0 0;font-family:'Archivo Black','Arial Black',sans-serif;letter-spacing:-.01em;line-height:1.04;font-size:31px;color:var(--ink)}
.phero.name{font-size:38px}
body.pg-week h1.word{color:var(--ink)}
.psub{font-size:15px;line-height:1.5;color:var(--haze);margin:10px 0 22px;max-width:52ch}
.psub b{color:var(--ink);font-weight:600}
.pwhen{display:inline-block;font-size:10.5px;letter-spacing:.1em;font-weight:700;color:var(--haze);border:1px solid var(--line);border-radius:99px;padding:4px 11px;margin:2px 0 20px}
.pwhen b{color:var(--acc)}
.pnav{position:fixed;left:0;right:0;bottom:0;z-index:40;background:rgba(9,14,24,.93);-webkit-backdrop-filter:blur(12px);backdrop-filter:blur(12px);border-top:1px solid var(--line)}
.pnav .in{max-width:640px;margin:0 auto;display:flex}
.pnav a{flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;padding:10px 0 calc(9px + env(safe-area-inset-bottom,0px));text-decoration:none;color:var(--haze);font-size:9.5px;font-weight:700;letter-spacing:.07em;text-transform:uppercase;position:relative}
.pnav a svg{width:21px;height:21px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.pnav a.on{color:var(--ink)}
.pnav a.on svg{stroke:var(--acc)}
.pnav a.on::before{content:'';position:absolute;top:-1px;left:50%;transform:translateX(-50%);width:26px;height:3px;border-radius:0 0 3px 3px;background:var(--acc)}
.pfoot{margin-top:30px;border-top:1px solid var(--line);padding-top:16px}
.pfoot p{margin:0 0 8px;font-size:12.5px;color:var(--haze);line-height:1.55}
.pfoot a{color:var(--reef)}
/* ------------------------------------------------ home */
.radar{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--flare);border-radius:12px;padding:12px 15px;margin:0 0 20px;font-size:14.5px;line-height:1.45}
.radar .k{font-size:10px;letter-spacing:.12em;color:var(--haze);font-weight:700;margin-right:5px}
.doors{display:grid;gap:11px;margin-bottom:8px}
.door{display:grid;grid-template-columns:auto 1fr auto;gap:14px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:16px;padding:15px 14px 15px 15px;text-decoration:none;color:var(--ink)}
.door:active{transform:scale(.99)}
.door .ic{width:42px;height:42px;border-radius:12px;display:flex;align-items:center;justify-content:center;flex:none}
.door .ic svg{width:22px;height:22px;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.door.d-ahead .ic{background:#122C42}.door.d-ahead .ic svg{stroke:var(--reef)}.door.d-ahead .h{color:var(--reef)}
.door.d-week .ic{background:#2E1813}.door.d-week .ic svg{stroke:var(--flare)}.door.d-week .h{color:var(--flare)}
.door.d-picture .ic{background:#123528}.door.d-picture .ic svg{stroke:var(--kelp)}.door.d-picture .h{color:var(--kelp)}
.door .h{font-family:'Archivo Black','Arial Black',sans-serif;text-transform:uppercase;font-size:12.5px;letter-spacing:.04em}
.door .d{font-size:13.5px;color:var(--ink);line-height:1.45;margin-top:3px}
.door .m{font-size:10.5px;letter-spacing:.08em;color:var(--haze);text-transform:uppercase;margin-top:6px}
.door .go{color:var(--haze);font-size:22px;line-height:1}
.rowlink{display:flex;justify-content:space-between;align-items:center;gap:12px;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px 16px;text-decoration:none;color:var(--ink);font-size:14px;line-height:1.4;margin-top:10px}
.rowlink .go{color:var(--haze);font-size:20px;line-height:1}
.rowlink .sub{display:block;font-size:12px;line-height:1.45;color:var(--haze);margin:2px 0 0;max-width:none}
.acct{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden}
.acct .row{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 16px;border-top:1px solid var(--line)}
.acct .row:first-child{border-top:none}
.acct .when{font-size:10.5px;letter-spacing:.09em;color:var(--haze);font-weight:700;text-transform:uppercase}
.acct .what{font-size:14.5px;margin-top:2px}
.acct .why{font-size:12.5px;color:var(--haze);margin-top:2px;line-height:1.4}
.acct .on-pill{flex:none;font-size:10px;font-weight:700;letter-spacing:.06em;background:#123528;color:var(--kelp);border-radius:99px;padding:3px 10px}
.acct-note{font-size:12.5px;color:var(--haze);line-height:1.55;margin-top:10px}
.acct-note b{color:var(--ink);font-weight:600}
.howto{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:15px 17px}
.howto .lead{font-size:14px;line-height:1.55;margin:0}
.howto .lead b{color:var(--ink)}
.howto .ax{margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}
.howto .axk{font-size:10.5px;letter-spacing:.11em;color:var(--ink);font-weight:700;text-transform:uppercase}
.howto .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}
.howto .chips span{background:#1C2B42;border-radius:6px;padding:3px 8px;font-size:11.5px;white-space:nowrap;color:var(--ink)}
.howto .chips .dot{font-size:9px;margin-right:4px;vertical-align:1px}
.howto .axsub{font-size:12.5px;color:var(--haze);line-height:1.5;margin-top:7px}
.howto .why{font-size:13px;line-height:1.55;margin:12px 0 0;padding-top:12px;border-top:1px solid var(--line);color:var(--haze)}
.howto .why b{color:var(--ink)}
.howto .why .cs{color:var(--reef)}
/* ------------------------------------------------ the week ahead */
.wa-grid{display:grid;gap:10px}
.wa-row{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.wa-row .nm{font-family:'Archivo Black','Arial Black',sans-serif;text-transform:uppercase;font-size:12.5px;letter-spacing:.03em;color:var(--reef);margin-bottom:8px}
.wa-line{display:grid;grid-template-columns:52px 1fr;gap:10px;align-items:baseline;padding:3px 0}
.wa-line .wa-k{font-size:10px;letter-spacing:.12em;color:var(--haze);font-weight:700;text-transform:uppercase}
.wa-line .wa-v{font-size:15px;line-height:1.45}
.wa-line.topic .wa-v{font-weight:600;font-size:15.5px}
.wa-hedge{font-size:12.5px;color:#E7B24A;margin-top:7px;line-height:1.4}
.wa-dates{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--flare);border-radius:14px;padding:13px 16px;margin:0 0 14px}
.wa-dates .k{display:block;font-size:10px;letter-spacing:.14em;color:var(--flare);font-weight:700;margin-bottom:3px}
.wa-dates .dr{display:flex;justify-content:space-between;align-items:baseline;gap:12px;padding:8px 0;border-top:1px solid var(--line);font-size:14.5px;line-height:1.4}
.wa-dates .dr.first{border-top:none}
.wa-dates .dr .dw{color:var(--haze);font-size:13px;white-space:nowrap}
.wa-dates .steer{font-size:12.5px;color:var(--haze);margin-top:6px;line-height:1.45}
.wa-empty,.tw-empty,.map-empty{color:var(--haze);font-size:14.5px;line-height:1.55;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:15px 17px}
/* ------------------------------------------------ the weekly update */
.byn{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:9px}
.byn .cell{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.byn .k{font-size:10.5px;letter-spacing:.08em;color:var(--haze);text-transform:uppercase;font-weight:700}
.byn .v{font-size:24px;font-weight:700;font-family:'Space Mono',ui-monospace,monospace;margin-top:4px;line-height:1.1}
.byn .v .u{font-size:13px;color:var(--haze);font-weight:400;font-family:'Space Grotesk',system-ui,sans-serif}
.byn .sub{font-size:11.5px;color:var(--haze);margin-top:3px;line-height:1.35}
.accs{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 16px;margin-top:9px}
.accs .h{font-size:13.5px;font-weight:700}
.accs .hsub{font-size:11.5px;color:var(--haze);margin:2px 0 7px}
.accs .ar{display:grid;grid-template-columns:minmax(72px,auto) 1fr auto;gap:12px;align-items:center;padding:6px 0}
.accs .s{font-size:13px}
.accs .bar{height:9px;border-radius:99px;background:#1C2B42;overflow:hidden}
.accs .bar i{display:block;height:100%;background:var(--kelp);border-radius:99px}
.accs .v{font-size:12.5px;font-family:'Space Mono',ui-monospace,monospace;font-weight:700;white-space:nowrap;text-align:right}
.accs .v .n{color:var(--haze);font-weight:400;font-family:'Space Grotesk',system-ui,sans-serif}
.accs .note{font-size:11.5px;color:var(--haze);margin-top:7px;line-height:1.4}
.loop{display:flex;justify-content:space-between;align-items:center;gap:12px;background:#0D1A2C;border:1px solid var(--line);border-radius:14px;padding:13px 16px;margin-top:18px;text-decoration:none;color:var(--ink);font-size:14px;line-height:1.45}
.loop .go{color:var(--haze);font-size:20px;line-height:1}
.loop b{color:var(--acc)}
/* ------------------------------------------------ the running picture */
.tally{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:15px 17px;margin-bottom:8px}
.tally .tr{display:grid;grid-template-columns:minmax(72px,auto) 1fr auto;gap:12px;align-items:center;padding:6px 0}
.tally .s{font-size:12px;font-weight:700;letter-spacing:.02em;text-transform:uppercase}
.tally .bar{display:flex;gap:2px;height:10px;border-radius:99px;overflow:hidden}
.tally .bar i{display:block;height:100%;flex:1;background:#1C2B42}
.tally .bar i.h0{background:#F0703F}.tally .bar i.h1{background:#E8963C}
.tally .bar i.h2{background:#8FBE45}.tally .bar i.h3{background:var(--kelp)}
.tally .n{font-size:12px;color:var(--haze);font-family:'Space Mono',ui-monospace,monospace;white-space:nowrap;text-align:right}
.tally .term{margin:9px 0 0;padding-top:9px;border-top:1px solid var(--line);font-size:12.5px;line-height:1.5;color:var(--haze)}
.tally .term b{color:var(--kelp);font-weight:700}
.tally-note{font-size:12px;color:var(--haze);line-height:1.5;margin:0 0 22px}
.tally-note b{color:var(--ink);font-weight:600}
.risk-note{font-size:12.5px;color:var(--haze);line-height:1.5;margin:-2px 0 10px}
.hist{display:flex;gap:2px;margin-top:4px}
.hist i{width:8px;height:8px;border-radius:2px;background:#33415C;flex:none}
.hist i.h0{background:#F0703F}.hist i.h1{background:#E8963C}
.hist i.h2{background:#8FBE45}.hist i.h3{background:var(--kelp)}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:14px 16px;margin-bottom:12px}
.map-subj{font-family:'Archivo Black','Arial Black',sans-serif;text-transform:uppercase;font-size:13px;letter-spacing:.03em;color:var(--kelp);margin-bottom:9px}
.cshallow{background:#0D1A2C;border-left:3px solid var(--reef);border-radius:0 8px 8px 0;padding:8px 12px;margin:2px 0 6px;font-size:13px;line-height:1.45;color:var(--ink)}
.cshallow b{color:var(--reef)}
.arch{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:5px 6px}
.arch a{display:flex;justify-content:space-between;text-decoration:none;color:var(--ink);padding:11px 12px;border-top:1px solid var(--line);font-size:14.5px}
.arch a:first-child{border-top:none}
.arch a .wk{color:var(--haze);font-size:13px;font-family:'Space Mono',ui-monospace,monospace}
.legend{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 17px;font-size:13px;line-height:1.6;color:var(--haze)}
.legend b{color:var(--ink)}
.legend .lr{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.legend .lr span{background:#1C2B42;border-radius:6px;padding:3px 8px;font-size:11.5px}
"""

# Bottom-nav glyphs — inline, stroke-only, inherit colour from the nav state.
_ICONS = {
    "": ("Home",
         "<svg viewBox='0 0 24 24' aria-hidden='true'>"
         "<path d='M3.5 11 12 4l8.5 7'/><path d='M6 10.2V20h12v-9.8'/></svg>"),
    "ahead": ("Week ahead",
              "<svg viewBox='0 0 24 24' aria-hidden='true'>"
              "<rect x='3.5' y='5' width='17' height='15.5' rx='2.5'/>"
              "<path d='M3.5 9.5h17M8 3v4M16 3v4'/></svg>"),
    "week": ("Weekly update",
             "<svg viewBox='0 0 24 24' aria-hidden='true'>"
             "<circle cx='12' cy='12' r='8.5'/>"
             "<path d='M8.4 12.4l2.4 2.4 4.8-5.2'/></svg>"),
    "picture": ("Picture",
                "<svg viewBox='0 0 24 24' aria-hidden='true'>"
                "<path d='M5 20v-6M12 20V9.5M19 20V4.5'/><path d='M3 20h18'/></svg>"),
}
PAGE_KEYS = ("", "ahead", "week", "picture")
_BODY_CLASS = {"": "pg-home", "ahead": "pg-ahead", "week": "pg-week",
               "picture": "pg-picture"}


def _hrefs(current, nav=None):
    """Nav targets for one page. Relative by default so the four published pages
    link each other with zero configuration (and the committed preview works
    straight off the filesystem); `nav` overrides with explicit URLs."""
    if nav:
        return nav
    if current == "":
        return {"": "./", "ahead": "ahead/", "week": "week/", "picture": "picture/"}
    return {"": "../", "ahead": "../ahead/", "week": "../week/",
            "picture": "../picture/"}


def _nav_bar(current, hrefs):
    tabs = []
    for key in PAGE_KEYS:
        label, icon = _ICONS[key]
        on = " class='on' aria-current='page'" if key == current else ""
        tabs.append(f"<a{on} href='{_e(hrefs[key])}'>{icon}<span>{_e(label)}</span></a>")
    return f"<nav class='pnav'><div class='in'>{''.join(tabs)}</div></nav>"


def _friendly_date(iso, days=None):
    try:
        d = _dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    txt = d.strftime("%A %-d %B")
    if isinstance(days, int) and 0 <= days <= 7:
        return f"{txt} (this week)"
    return txt


def _short_date(iso):
    """'Mon 31 Aug' — the human form for the freshness stamp and archive rows."""
    try:
        d = _dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    return d.strftime("%a %-d %b")


def _week_label(week_of):
    try:
        d = _dt.date.fromisoformat(week_of)
    except (TypeError, ValueError):
        return week_of or ""
    return "week of " + d.strftime("%-d %B")


def _span_label(monday_iso):
    """'Mon 24 – Fri 28 Aug' (or 'Mon 31 Aug – Fri 4 Sep' across a month
    boundary) — the unambiguous name of a reported school week."""
    try:
        mon = _dt.date.fromisoformat(monday_iso)
    except (TypeError, ValueError):
        return ""
    fri = mon + _dt.timedelta(days=4)
    if mon.month == fri.month:
        return f"{mon.strftime('%a %-d')} – {fri.strftime('%a %-d %b')}"
    return f"{mon.strftime('%a %-d %b')} – {fri.strftime('%a %-d %b')}"


def _subject_key(subject):
    """ONE canonical subject order for the whole portal (Rich, 30 Aug): the
    Week Ahead, the Weekly update and the Running Picture all list subjects in
    the same order, so a parent's eye lands in the same place on every page.
    monday_brief.week_ahead and subject_cards already sort this way; pages
    that receive pre-built blocks re-sort with this key."""
    return (subject or "").lower()


def _shell(key, portal, hero_html, body_html, hrefs, title):
    """One finished page: head (stamp early, inside verify()'s 4KB window),
    top bar, page hero, body, footer, bottom nav.

    NAMING (Rich, 30 Aug — "let's not get confused about what we call the
    pages"): the <title> is the PAGE's own name; the masthead is the product
    (XP DAILY), never a page label; "the full picture" survives only as
    home's descriptive phrase until the D6 name decision."""
    name = portal.get("name", "")
    stamp = rp.build_stamp()
    foot = ("<div class='pfoot'>"
            f"<p>This is {_e(name)}'s picture, kept current — open it any time. "
            "Nothing here needs a reply; questions go to Rich by text.</p>"
            "<p>Positions and depth refresh Friday evening; the week ahead "
            "refreshes Monday. Nothing updates mid-week — the read stays "
            "weekly on purpose.</p>"
            f"<p>build {_e(stamp)}</p></div>")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="xpdaily-build" content="{_e(stamp)}" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="noindex, nofollow" />
<meta name="theme-color" content="#0B1220" />
<title>{_e(title)}</title>
<style>{_CSS}</style>
</head>
<body class="{_BODY_CLASS[key]}">
<div class="wrap">
  <div class="ptop"><span class="brand">XP DAILY</span><span class="upd">updated {_e(_short_date(portal.get('updated','')))}</span></div>
  {hero_html}
  {body_html}
  {foot}
</div>
{_nav_bar(key, hrefs)}
</body>
</html>"""


# --------------------------------------------------------------------------- #
# HOME — the front door: radar, three doorways with live teasers, the account
# surface (v1 stub), the kid's player card.

def _join_names(items, cap=3):
    items = list(items)[:cap]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _ahead_teaser(portal):
    rows = (portal.get("week_ahead") or {}).get("rows") or []
    n = len(portal.get("upcoming") or [])
    if not rows:
        return "What school is covering this week, and what his sets will do about it."
    subs = _join_names([r["subject"] for r in rows])
    if n == 1:
        return f"{subs} — plus one date on the radar."
    if n > 1:
        count = {2: "two", 3: "three", 4: "four"}.get(n, "the")
        return f"{subs} — plus {count} dates on the radar."
    return f"{subs} — what school posted, and what his sets will do about it."


def _week_teaser(portal):
    word = (portal.get("week_verdict") or {}).get("word")
    blocks = (portal.get("this_week") or {}).get("blocks") or []
    if word in rp.WORD_CAP:
        return f"{rp.WORD_CAP[word]} — {rp.WORD_SUB[word][:1].lower()}{rp.WORD_SUB[word][1:]}"
    if blocks:
        subs = _join_names([b["subject"] for b in blocks])
        return f"What {subs} worked, where each topic stands, and the one detail worth knowing."
    return "How the week actually went, subject by subject — lands Friday evening."


def _picture_teaser(portal):
    cum = [c for c in (portal.get("running") or {}).get("cumulative") or []
           if c.get("total")]
    if not cum:
        return "Position and depth on every topic, adding up week by week."
    strip = " · ".join(f"{c['subject']} {c['landed']} of {c['total']} landed"
                       for c in cum[:2])
    return strip + (" · the whole map." if len(cum) > 2 else ".")


def _radar_strip(portal):
    """The most actionable fact a parent can be handed, on the front door: the
    NEAREST upcoming date. Practice-coverage hedge, never an outcome
    prediction. The full list lives on the Week Ahead page."""
    up = portal.get("upcoming") or []
    if not up:
        return ""
    a = up[0]
    when = _friendly_date(a.get("date"), a.get("days"))
    return ("<div class='radar'><span class='k'>ON THE RADAR</span>"
            f"<b>{_e(a['task'])}</b> — {_e(when)}. His sets are already steering "
            "practice toward it.</div>")


def _doors(portal, hrefs):
    doors = [
        ("ahead", "d-ahead", "The week ahead", _ahead_teaser(portal),
         "Refreshes Monday evening"),
        ("week", "d-week", "The weekly update", _week_teaser(portal),
         "Refreshes Friday evening"),
        ("picture", "d-picture", "The running picture", _picture_teaser(portal),
         "Adds up every Friday"),
    ]
    out = []
    for key, cls, title, teaser, meta in doors:
        icon = _ICONS[key][1]
        out.append(
            f"<a class='door {cls}' href='{_e(hrefs[key])}'>"
            f"<span class='ic'>{icon}</span>"
            f"<span><span class='h'>{_e(title)}</span>"
            f"<span class='d' style='display:block'>{_e(teaser)}</span>"
            f"<span class='m' style='display:block'>{_e(meta)}</span></span>"
            f"<span class='go'>&#8250;</span></a>")
    return f"<div class='doors'>{''.join(out)}</div>"


def _account_section(portal):
    """YOUR ACCOUNT — v1 is an honest stub: the four touchpoints and their
    cadence, all currently on, and the documented way to change anything (a
    text to Rich — the opt-out path, D5). Per-touchpoint switches and sign-in
    land in this exact space when they exist; the shell is already theirs."""
    rows = []
    for tp in portal.get("touchpoints") or []:
        rows.append(
            "<div class='row'><div>"
            f"<div class='when'>{_e(tp['when'])}</div>"
            f"<div class='what'>{_e(tp['what'])}</div>"
            f"<div class='why'>{_e(tp['why'])}</div></div>"
            "<span class='on-pill'>ON</span></div>")
    if not rows:
        return ""
    return ("<div class='section'>YOUR ACCOUNT</div>"
            f"<div class='acct'>{''.join(rows)}</div>"
            "<p class='acct-note'><b>Want anything changed?</b> Any of these can "
            "be switched off, or contact details updated, with a text to Rich — "
            "done the same day, no forms. Self-serve controls will live right "
            "here once sign-in arrives.</p>")


def _how_to_read(name):
    """HOW TO READ THE REPORT — the front door teaches the reading model once
    (Rich, 30 Aug): the mission (comprehension mapped on the SOLO taxonomy,
    in plain words), the two axes with their real visual vocabulary (the
    coloured position dots, the depth rungs, the evidence gate), and what it
    means for a parent. The Running Picture keeps its short at-point-of-use
    legend; both draw chips from the same constants so they cannot drift."""
    bands = "".join(
        f"<span><span class='dot d{colour}'>&#9679;</span>{_e(label)}</span>"
        for label, colour in rp.BANDS[1:])
    rungs = "".join(f"<span>{_e(v)}</span>" for _, v in rp.RUNGS)
    return (
        "<div class='section'>HOW TO READ THE REPORT</div>"
        "<div class='howto'>"
        f"<p class='lead'>These pages map <b>how well {_e(name)} actually "
        "understands</b> what school is teaching — not just whether answers "
        "come out right. The depth side follows the <b>SOLO taxonomy</b>, a "
        "standard framework for measuring depth of understanding, written "
        "here in plain words. Every topic is read on two axes:</p>"
        "<div class='ax'><div class='axk'>1 · Where he is</div>"
        f"<div class='chips'>{bands}</div>"
        "<div class='axsub'>How reliably the topic comes out right under "
        "questioning — a position on a journey, red to green. Early is not "
        "failing; it's early.</div></div>"
        "<div class='ax'><div class='axk'>2 · Depth</div>"
        f"<div class='chips'>{rungs}</div>"
        "<div class='axsub'>How deeply he can explain it. Quick questions can "
        "only prove the first rungs — climbing further takes a written "
        "explanation in his own words, so depth moves over weeks, not days. "
        "A rung shows only once he's evidenced it; a dash means not shown "
        "yet, never a fail.</div></div>"
        "<p class='why'><b>Why both matter:</b> a topic can be "
        "<span class='cs'>Solid on recall while the explanation hasn't caught "
        "up</span> — strong memory, shallow roots. Marks alone would call that "
        "finished; these pages flag it, and his next written questions target "
        "it automatically.</p>"
        f"<p class='why'><b>What it means for you:</b> nothing here needs "
        f"fixing at home — the sets adjust themselves every night. The one "
        f"thing that genuinely helps is conversation: ask {_e(name)} to "
        "explain a topic out loud. Explaining is exactly the move that climbs "
        "the depth ladder.</p>"
        "</div>")


def _home_page(portal, hrefs, kid_wrap_url=None):
    name = portal.get("name", "")
    hero = (f"<h1 class='phero name'>{_e(name)}</h1>"
            "<p class='psub'>The full picture — what's coming, how the week "
            "went, and how it's all adding up. Three pages, kept current, "
            "always here.</p>")
    wrap_link = ""
    if kid_wrap_url:
        wrap_link = (f"<a class='rowlink' href='{_e(kid_wrap_url)}'>"
                     f"<span><b>{_e(name)}'s player card</b>"
                     "<span class='sub'>The same week, the way he sees it — "
                     "XP, streaks and badges.</span></span>"
                     "<span class='go'>&#8250;</span></a>")
    body = (_radar_strip(portal)
            + _doors(portal, hrefs)
            + wrap_link
            + _how_to_read(name)
            + _account_section(portal))
    return _shell("", portal, hero, body, hrefs, f"{name} — XP Daily")


# --------------------------------------------------------------------------- #
# THE WEEK AHEAD — Monday, forward. The light glance. Forward facts only, by
# construction: everything on this page comes from monday_brief.week_ahead().

def _upcoming_dates(upcoming):
    """UPCOMING DATES — every dated thing on the radar (tests, study-guide
    releases, due dates), nearest first. The steering line renders once,
    hedged as practice-coverage, never an outcome prediction."""
    if not upcoming:
        return ""
    rows = []
    for i, u in enumerate(upcoming):
        first = " first" if i == 0 else ""
        subj = ""
        if u.get("subject") and u["subject"].lower() not in (u.get("task") or "").lower():
            subj = f" <span class='dw'>· {_e(u['subject'])}</span>"
        rows.append(f"<div class='dr{first}'><span><b>{_e(u['task'])}</b>{subj}</span>"
                    f"<span class='dw'>{_e(_short_date(u['date']))}</span></div>")
    return ("<div class='wa-dates'><span class='k'>UPCOMING DATES</span>"
            f"{''.join(rows)}"
            "<div class='steer'>His nightly sets steer practice toward these as "
            "they approach.</div></div>")


def _ahead_row(r):
    """One subject, three classifications (Rich, 30 Aug): SUBJECT — the header;
    TOPIC — what class is on (the unit; never fabricated, so the line is
    omitted when the targets carry none); FOCUS — the forward clause, always
    'continues' / 'moves into' / or both (monday_brief._intent)."""
    topic = (f"<div class='wa-line topic'><span class='wa-k'>Topic</span>"
             f"<span class='wa-v'>{_e(r['unit'])}</span></div>"
             if r.get("unit") else "")
    focus = (f"<div class='wa-line'><span class='wa-k'>Focus</span>"
             f"<span class='wa-v'>{_e(_cap(r.get('intent', '')))}</span></div>"
             if r.get("intent") else "")
    hedge = ("<div class='wa-hedge'>Confirming this subject's page for "
             "your teacher — treat as a guide this week.</div>"
             if r.get("hedged") else "")
    return (f"<div class='wa-row'><div class='nm'>{_e(r['subject'])}</div>"
            f"{topic}{focus}{hedge}</div>")


def _ahead_page(portal, hrefs):
    name = portal.get("name", "")
    wa = portal.get("week_ahead") or {}
    rows = wa.get("rows") or []
    hero = ("<div class='peyebrow'>MONDAY · FORWARD</div>"
            "<h1 class='phero'>The week ahead</h1>"
            f"<p class='psub'>The {_e(_week_label(portal.get('week_of')))} — what "
            f"school is covering, and what {_e(name)}'s sets will do about it.</p>")
    parts = [_upcoming_dates(portal.get("upcoming"))]
    if rows:
        parts.append(f"<div class='wa-grid'>{''.join(_ahead_row(r) for r in rows)}</div>")
    else:
        parts.append("<div class='wa-empty'>This week's plan syncs in on Monday. "
                     f"Until then {_e(name)}'s sets keep working the current "
                     "topics — the nightly run doesn't wait for the paperwork."
                     "</div>")
    parts.append(f"<a class='loop' href='{_e(hrefs['week'])}'>"
                 "<span>How it lands is Friday's story — the plan above gets "
                 "its answer in the <b>Weekly update</b>.</span>"
                 "<span class='go'>&#8250;</span></a>")
    return _shell("ahead", portal, hero, "".join(parts), hrefs,
                  f"The week ahead — {name} · XP Daily")


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


# --------------------------------------------------------------------------- #
# THE WEEKLY UPDATE — Friday, backward. The deep read: verdict word, activity
# strip, then the subject spine (report_page's renderer, so Friday's two
# surfaces share one shape). The fluency-illusion catch renders INSIDE its
# subject's block as the detail worth knowing (Rich, 30 Aug), never as a
# page-level interruption.

def _fold_fluency(blocks, fluency):
    """Place the fluency-catch narration into the block that owns its topic —
    it becomes that subject's detail slot (shallow copies; callers' dicts are
    never mutated). If no block carries the topic, the note is dropped rather
    than floated page-level."""
    if not fluency:
        return blocks
    out, placed = [], False
    for b in blocks:
        names = set(b.get("worked") or []) | {t.get("topic") for t in b.get("topics") or []}
        if not placed and fluency in names:
            b = dict(b, fluency_detail=fluency)
            placed = True
        out.append(b)
    return out


def _week_totals(activity, accuracy, blocks):
    """(asked, right) for the week, best source first: explicit runner totals,
    else the accuracy-by-subject sums, else the per-topic counts — so the
    tiles, the bars and the tables always agree with each other."""
    activity = activity or {}
    if activity.get("questions") is not None:
        return activity["questions"], activity.get("right")
    if accuracy:
        return (sum(v.get("asked") or 0 for v in accuracy.values()),
                sum(v.get("right") or 0 for v in accuracy.values()))
    return (sum(t.get("asked") or 0 for b in blocks for t in b.get("topics") or []),
            sum(t.get("right") or 0 for b in blocks for t in b.get("topics") or []))


def _by_the_numbers(activity, blocks, accuracy=None):
    """BY THE NUMBERS — the week's totals as a deliberate tile section (Rich,
    30 Aug): nights run (excused-aware denominator), questions answered,
    overall accuracy, topics practised.

    Overall accuracy renders only at 10+ answered (the small-sample law —
    below that a percentage is noise, and the per-topic counts already tell
    the story). No game-layer tallies here: events and achievement counts
    belong to the kid's surfaces (V2 §7 — parents hear stories, never
    tallies), so there is no "events cleared" or "achievements unlocked"
    tile (Rich, 30 Aug)."""
    activity = activity or {}
    asked, right = _week_totals(activity, accuracy, blocks)
    cells = []
    if activity.get("possible"):
        cells.append(("Nights run",
                      f"{activity.get('days_done', 0)}<span class='u'> of "
                      f"{activity['possible']}</span>", ""))
    if asked:
        cells.append(("Questions answered", f"{asked}", ""))
        if right is not None and asked >= 10:
            pct = round(100 * right / asked)
            cells.append(("Overall accuracy", f"{pct}<span class='u'>%</span>",
                          f"{right} of {asked} right"))
    if activity.get("topics_practised"):
        cells.append(("Topics practised", f"{activity['topics_practised']}", ""))
    if not cells:
        return ""
    tiles = "".join(
        f"<div class='cell'><div class='k'>{_e(k)}</div><div class='v'>{v}</div>"
        + (f"<div class='sub'>{_e(sub)}</div>" if sub else "") + "</div>"
        for k, v, sub in cells)
    return ("<div class='section'>BY THE NUMBERS</div>"
            f"<div class='byn'>{tiles}</div>")


def _accuracy_chart(accuracy, blocks):
    """Accuracy by subject, whole week — single-hue bars sorted best-first,
    every row direct-labelled "pct% · n" so the sample size is never hidden
    (Rich, 30 Aug — the prior-prototype section, restored). A subject enters
    at 2+ answered; the chart renders only when there are two subjects to
    compare. Length is the only encoding — accuracy is one measure, so the
    bars share one hue and never take the verdict colours."""
    data = accuracy
    if not data:
        data = {}
        for b in blocks:
            for t in b.get("topics") or []:
                if t.get("asked"):
                    d = data.setdefault(b.get("subject") or "Other",
                                        {"asked": 0, "right": 0})
                    d["asked"] += t["asked"]
                    d["right"] += t.get("right") or 0
    rows = [(s, v["asked"], v.get("right") or 0)
            for s, v in (data or {}).items() if (v.get("asked") or 0) >= 2]
    if len(rows) < 2:
        return ""
    rows.sort(key=lambda r: (-(r[2] / r[1]), -r[1], _subject_key(r[0])))
    bars = []
    for subj, asked, right in rows:
        pct = round(100 * right / asked)
        bars.append(f"<div class='ar'><span class='s'>{_e(subj)}</span>"
                    f"<span class='bar'><i style='width:{pct}%'></i></span>"
                    f"<span class='v'>{pct}% <span class='n'>&middot; n{asked}"
                    "</span></span></div>")
    return ("<div class='accs'><div class='h'>Accuracy by subject</div>"
            "<div class='hsub'>Whole week &middot; n = questions asked</div>"
            f"{''.join(bars)}"
            "<div class='note'>Small counts per subject — read these as a "
            "rough shape, not a measurement.</div></div>")


def _week_page(portal, hrefs):
    name = portal.get("name", "")
    tw = portal.get("this_week") or {}
    blocks = sorted(tw.get("blocks") or [], key=lambda b: _subject_key(b.get("subject")))
    blocks = _fold_fluency(blocks, tw.get("fluency"))
    # The topic / where-he-is / depth table carries the whole story; the
    # "this week his sets worked" intro repeated its first column (Rich,
    # 30 Aug) — stripped here, on the portal only.
    blocks = [{k: v for k, v in b.items() if k != "worked"} for b in blocks]
    word = (portal.get("week_verdict") or {}).get("word")
    span = _span_label(tw.get("week_of") or "")
    eyebrow_txt = f"Weekly update · {span}" if span else "Weekly update · Friday evening"
    eyebrow = f"<div class='peyebrow'>{_e(eyebrow_txt)}</div>"
    if word in rp.WORD_CAP:
        # The verdict IS this page's hero — the ten-second read, then the why.
        hero = (eyebrow
                + f"<h1 class='word display {_e(word)}' style='margin-top:6px'>"
                + f"{_e(rp.WORD_CAP[word])}</h1>"
                + f"<p class='psub'>{_e(rp.WORD_SUB[word])} The subject-by-"
                  "subject read is below — each one closes the loop Monday "
                  "opened.</p>")
    else:
        hero = (eyebrow + "<h1 class='phero'>The weekly update</h1>"
                + f"<p class='psub'>What {_e(name)}'s sets worked, where each "
                  "topic stands, and the one detail worth knowing — subject by "
                  "subject.</p>")
    parts = []
    if blocks:
        parts.append(_by_the_numbers(portal.get("activity"), blocks,
                                     accuracy=portal.get("accuracy")))
        parts.append(_accuracy_chart(portal.get("accuracy"), blocks))
        parts.append("<div class='section'>BY SUBJECT</div>")
        parts.append("".join(rp._subject_block(b, name) for b in blocks))
        if any(t.get("asked") for b in blocks for t in b.get("topics") or []):
            parts.append("<p class='notes'>Per-topic question counts are small "
                         "by design — a handful each week — so read them as "
                         "practice volume, not a score. The coloured position "
                         "is the considered read; it weighs more evidence than "
                         "one week.</p>")
    else:
        parts.append("<div class='tw-empty'>The weekly update lands Friday "
                     "evening — what each subject actually worked, where it "
                     "landed, and the one thing worth knowing. The plan it will "
                     "be answering is on the Week Ahead page.</div>")
    parts.append(f"<a class='loop' href='{_e(hrefs['picture'])}'>"
                 "<span>Where it all adds up — every topic's position and "
                 "depth, on <b>The running picture</b>.</span>"
                 "<span class='go'>&#8250;</span></a>")
    return _shell("week", portal, hero, "".join(parts), hrefs,
                  f"The weekly update — {name} · XP Daily")


# --------------------------------------------------------------------------- #
# THE RUNNING PICTURE — Friday, cumulative. The map: tally, position + depth on
# every active topic (the confidently-shallow cross), trends, archive, legend.

def _history_strip(states):
    """A topic's week-by-week micro-timeline: one cell per banked week (oldest
    → newest, the last cell is now), coloured on the same band scale as the
    position dots — identity never rides on colour alone, the labelled dot
    sits on the same row. Renders only with 2+ points (a one-cell strip says
    nothing)."""
    if not states or len(states) < 2:
        return ""
    cells = []
    for st in states:
        band = _STATE_BAND.get(st)
        cls = f" class='h{_BANDS[band][1]}'" if band is not None else ""
        cells.append(f"<i{cls}></i>")
    return f"<div class='hist'>{''.join(cells)}</div>"


def _topic_tr(r, history=None):
    """One topic on the map: position + depth side by side, on the SAME table
    vocabulary the This-Week spine uses — plus the longitudinal strip under
    the topic name (this page is the picture OVER TIME, Rich, 31 Aug). The
    confidently-shallow cross renders as a full-width callout under its
    topic."""
    band = _STATE_BAND.get(r.get("state"), 1)
    label, colour = _BANDS[band][0], _BANDS[band][1]
    dep = r.get("depth")
    dep_html = (f"<span class='dep'>{_e(_RUNG_LABEL[dep].capitalize())}</span>"
                if dep in _RUNG_LABEL else "<span class='dep none'>&mdash;</span>")
    strip = _history_strip((history or {}).get(r.get("topic")))
    rows = (f"<tr><td>{_e(r.get('topic'))}{strip}</td>"
            f"<td class='pos'><span class='dot d{colour}'>&#9679;</span>{_e(label)}</td>"
            f"<td>{dep_html}</td></tr>")
    if r.get("confidently_shallow"):
        rows += ("<tr><td colspan='3'><div class='cshallow'><b>Strong recall</b> "
                 "— he can pick this confidently, but hasn't yet shown he can "
                 "explain it. His next written question targets exactly that."
                 "</div></td></tr>")
    return rows


def _tally(running):
    """THE SUBJECT PICTURE — each subject's bar IS its topics: one tile per
    topic, coloured by that topic's band, weakest first — the table's dot
    column compressed into a bar, zero new vocabulary (Rich, 31 Aug: the
    landed/explained stacking read as a score and connected to nothing
    below; this replaces it). The reading rule is one sentence, on the page.
    The term-trend line folds in here once four weeks of snapshots bank."""
    cards = [c for c in (running or {}).get("cards") or [] if c.get("rows")]
    if not cards:
        return ""
    rows = []
    for c in cards:
        segs = "".join(
            f"<i class='h{_BANDS[_STATE_BAND.get(r.get('state'), 1)][1]}'></i>"
            for r in c["rows"])
        total = len(c["rows"])
        watch = sum(1 for r in c["rows"]
                    if r.get("state") not in ("developing", "solid"))
        label = (f"{total} topic{'s' if total != 1 else ''} &middot; "
                 + (f"{watch} to watch" if watch else "none to watch"))
        rows.append(f"<div class='tr'><span class='s'>{_e(c['subject'])}</span>"
                    f"<span class='bar'>{segs}</span>"
                    f"<span class='n'>{label}</span></div>")
    trends = (running or {}).get("trends")
    if trends:
        gains = [f"<b>{_e(r['subject'])} +{r['gained']}</b>"
                 for r in trends["rows"] if r["gained"] > 0]
        term = ("This term: " + " &middot; ".join(gains) + " landed, across "
                f"{trends['weeks']} weeks." if gains else
                f"Holding steady across {trends['weeks']} weeks — nothing lost.")
    else:
        term = ("The term trend joins this card once four weeks of history "
                "bank — before then a &ldquo;trend&rdquo; would be noise. "
                "Weekly snapshots are banking now.")
    return (f"<div class='tally'>{''.join(rows)}"
            f"<div class='term'>{term}</div></div>"
            "<p class='tally-note'>Each bar is that subject's topics, coloured "
            "<b>exactly like the rows below</b> — the more green, the more "
            "solid. Red and amber are where revision starts; &ldquo;to "
            "watch&rdquo; counts them.</p>")


def _archive_section(archive):
    if not archive:
        return ""
    links = "".join(
        f"<a href='{_e(a['url'])}'><span>Friday report</span>"
        f"<span class='wk'>{_e(_short_date(a['week']))}</span></a>" for a in archive)
    return ("<div class='section'>THE ARCHIVE</div>"
            f"<div class='arch'>{links}</div>")


def _legend():
    bands = "".join(f"<span>{_e(b[0])}</span>" for b in _BANDS[1:])
    rungs = "".join(f"<span>{_e(v)}</span>" for _, v in rp.RUNGS)
    return ("<div class='section'>HOW TO READ THIS</div><div class='legend'>"
            "<b>Where it sits</b> — the confidence scale, red &rarr; green:"
            f"<div class='lr'>{bands}</div>"
            "<b style='display:block;margin-top:10px'>Depth</b> — how deeply he "
            "understands it (the SOLO taxonomy, in plain words). A rung shows only "
            "once he's evidenced it:"
            f"<div class='lr'>{rungs}</div>"
            "<p style='margin:10px 0 0'>Positions update every Friday; the week "
            "ahead updates Monday. Questions? Text Rich.</p></div>")


def _picture_page(portal, hrefs):
    name = portal.get("name", "")
    running = portal.get("running") or {}
    cards = running.get("cards") or []
    hero = ("<div class='peyebrow'>TERM TO DATE · CUMULATIVE</div>"
            "<h1 class='phero'>The running picture</h1>"
            f"<p class='psub'>Where every topic stands and how deeply {_e(name)} "
            "understands it — the mastery map his weeks are drawing. Come "
            "assessment time this is the risk map: the weakest rows are where "
            "revision starts, and his sets are already steering there.</p>")
    parts = []
    if cards:
        parts.append(_tally(running))
        parts.append("<div class='section'>EVERY TOPIC &mdash; POSITION AND DEPTH</div>")
        parts.append("<p class='risk-note'>Weakest first — the top rows of "
                     "each subject are the revision priorities. The small "
                     "strip under a topic is its week-by-week history, oldest "
                     "to newest, ending at now.</p>")
        history = running.get("history") or {}
        for c in cards:
            rows = "".join(_topic_tr(r, history) for r in c["rows"])
            parts.append(
                f"<div class='card'><div class='map-subj'>{_e(c['subject'])}</div>"
                "<table class='subj-table'><tr><th>Topic</th><th>Where he is</th>"
                f"<th>Depth</th></tr>{rows}</table></div>")
    else:
        parts.append("<div class='map-empty'>The map draws itself in as Fridays "
                     "bank — each week adds every topic's position and depth "
                     "here.</div>")
    parts.append(_archive_section(portal.get("archive")))
    parts.append(_legend())
    return _shell("picture", portal, hero, "".join(parts), hrefs,
                  f"The running picture — {name} · XP Daily")


# --------------------------------------------------------------------------- #
# Entry point

def render_pages(portal, kid_wrap_url=None, nav=None):
    """The four portal pages, as {relative path: html}:

        ""         home (publish at  p/<slug>)
        "ahead"    the week ahead      (p/<slug>/ahead)
        "week"     the weekly update   (p/<slug>/week)
        "picture"  the running picture (p/<slug>/picture)

    Pages cross-link relatively by default (they live under one slug), so no
    base URL is needed at render time; `nav` = {key: href} overrides every
    page's nav targets (used by the artifact preview, where the four pages live
    at four absolute URLs). `kid_wrap_url` links home to the player card.

    The Weekly update IS the Friday report (Rich, 30 Aug) — there is no
    second "full report" page to link; the standalone `/r/` render's only
    remaining job is the frozen dated snapshot the archive lists.
    """
    return {
        "": _home_page(portal, _hrefs("", nav), kid_wrap_url=kid_wrap_url),
        "ahead": _ahead_page(portal, _hrefs("ahead", nav)),
        "week": _week_page(portal, _hrefs("week", nav)),
        "picture": _picture_page(portal, _hrefs("picture", nav)),
    }
