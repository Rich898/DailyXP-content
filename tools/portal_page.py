#!/usr/bin/env python3
"""
portal_page.py — the always-available parent PORTAL (PARENT-COMMS-V2 §5).

The Friday report answers "how did THIS WEEK go"; the portal answers the other
two questions a paying parent has — "what is he working on right now" and "how
is he doing OVERALL, by subject" — on a page they can open any time. Messages
become pointers; the portal becomes the product. The accumulating history is the
switching cost: cancelling stops the map of THIS kid's misconceptions,
calibration and depth from growing.

STRUCTURE — the THREE parts of the parent report, time-phased, on one page:
  1. THE WEEK AHEAD      (Monday, forward)  what each subject is covering this
                         week + one assessment date. From monday_brief.week_ahead.
                         The Monday SMS is a thin POINTER to this panel.
  2. THIS WEEK           (Friday, backward) what happened: the subject spine
                         (report_stories.subject_blocks, rendered by report_page)
                         — so Monday's plan and Friday's resolution share one
                         shape. The founding "confidently shallow" cross renders
                         in the running picture below.
  3. THE RUNNING PICTURE (Friday, cumulative) where each subject stands
                         term-to-date, this week folded in: the landed tally, the
                         per-topic position + depth cards, and term trends
                         (switch on at 4+ weeks; say so before then).
  + ARCHIVE  past Friday reports (dated paths; the bare slug serves latest).
  + FOOTER   the verdict-ladder legend, an "updated {date}" stamp, build stamp.

PORTAL LAWS (PARENT-COMMS-V2 §5, to ratify):
  * FRESHNESS CONTRACT. Judgment-shaped facts (positions, depth, trends)
    recompute FRIDAY only; the This-Week panel refreshes Monday; the page shows
    a visible "updated {date}". NO same-night results, ever — an always-on
    surface must not become a Tuesday-8pm interrogation feed.
  * DEPTH CEILING. A rung renders only where evidenced ("—" otherwise); an
    MCQ-only topic never implies more than "can list it".
  * POSITIONS WEEKLY, TRENDS MONTHLY. Per-topic position shows any week;
    per-subject trend waits for the monthly (4+ week) window.
  * DIGNITY / AGING. Repaired topics and resolved confident-wrongs collapse into
    "fixed it" wins rather than accumulating as a rap sheet. (The teach-back
    quote ARCHIVE waits on the outstanding APP 8 privacy advice — not built here.)

PRIVACY: same model as report_page — fully self-contained, ZERO fetch, noindex,
unguessable slug. When family #2 arrives the same renderer moves behind the
Supabase magic-link door; the renderer doesn't change, only what guards it does.

CODE DECIDES, LANGUAGE DRESSES: build_portal() reads only already-computed facts
(the ledger topics, the targets block, the assessment radar, the week's targets
diff, the banked snapshots). No AI.
"""
import datetime as _dt

import report_page as rp   # reuse the dark design system + band/depth/ceiling

_e = rp._e

# Depth rungs that are SHALLOW (recall-level) vs DEEP (explanation-level). The
# founding "confidently shallow" insight is solid confidence over a shallow rung.
_SHALLOW_DEPTH = {"not_yet", "knows", "lists"}
_DEEP_DEPTH = {"connects", "applies"}

_CSS = rp._CSS + """
/* portal-specific */
.updated{font-size:11px;color:var(--haze);letter-spacing:.04em}
.section .when{font-weight:400;letter-spacing:.04em;color:var(--haze);text-transform:none}
/* component 1 — THE WEEK AHEAD */
.wa-grid{display:grid;gap:9px}
.wa-row{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 15px}
.wa-row .s{font-family:'Archivo Black','Arial Black',sans-serif;text-transform:uppercase;font-size:12px;letter-spacing:.03em;color:var(--reef)}
.wa-row .wa-unit{font-family:'Space Grotesk',sans-serif;text-transform:none;letter-spacing:0;color:var(--haze);font-size:12.5px;font-weight:400}
.wa-intent{font-size:15px;line-height:1.4;margin-top:4px}
.wa-chips{margin-top:6px}
.wa-chips .chip{display:inline-block;font-size:12px;background:#123528;color:var(--kelp);border-radius:99px;padding:2px 9px;margin:4px 6px 0 0}
.wa-hedge{font-size:12.5px;color:#E7B24A;margin-top:6px;line-height:1.4}
.wa-assess{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--flare);border-radius:12px;padding:12px 15px;margin-top:9px;font-size:14.5px;line-height:1.45}
.wa-assess .k{font-size:10px;letter-spacing:.12em;color:var(--haze);font-weight:700;margin-right:4px}
.tw-soon,.trend.soon{color:var(--haze);font-size:14px;line-height:1.5;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 17px}
.now-grid{display:grid;gap:9px}
.now-row{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 15px}
.now-row .s{font-family:'Archivo Black','Arial Black',sans-serif;text-transform:uppercase;font-size:12px;letter-spacing:.03em;color:var(--reef)}
.now-row .f{font-size:15px;margin-top:3px;line-height:1.4}
.now-row .a{font-size:12.5px;color:var(--haze);margin-top:4px}
.now-row .a b{color:var(--ink)}
.tw{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 17px}
.tw .nc{margin:0 0 8px}
.tw .nc .k{font-size:10px;letter-spacing:.12em;color:var(--haze);font-weight:700}
.tw .chip{display:inline-block;font-size:13px;background:#122C42;color:var(--reef);border-radius:99px;padding:3px 10px;margin:5px 6px 0 0}
.tw .intent{font-size:14.5px;line-height:1.5;margin:10px 0 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:11px}
.card .subj{font-family:'Archivo Black','Arial Black',sans-serif;text-transform:uppercase;font-size:13px;letter-spacing:.03em;color:var(--reef);margin-bottom:9px}
.trow{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;padding:8px 0;border-top:1px solid var(--line)}
.trow:first-of-type{border-top:none}
.trow .tn{font-size:14.5px;line-height:1.3}
.trow .pos,.trow .dep{font-size:12.5px;white-space:nowrap;text-align:right}
.trow .dot{font-size:12px;margin-right:5px}
.dot.d0{color:#F0703F}.dot.d1{color:#E8963C}.dot.d2{color:#8FBE45}.dot.d3{color:var(--kelp)}
.trow .dep{color:var(--ink)}.trow .dep.none{color:var(--haze)}
.cshallow{grid-column:1 / -1;background:#0D1A2C;border-left:3px solid var(--reef);border-radius:0 8px 8px 0;padding:8px 12px;margin-top:4px;font-size:13px;line-height:1.45;color:var(--ink)}
.cshallow b{color:var(--reef)}
.trend{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px}
.trend.soon{color:var(--haze);font-size:14px;line-height:1.5}
.trow.trend-row{grid-template-columns:1fr auto}
.arch{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:6px 6px}
.arch a{display:flex;justify-content:space-between;text-decoration:none;color:var(--ink);padding:11px 12px;border-top:1px solid var(--line);font-size:14.5px}
.arch a:first-child{border-top:none}
.arch a .wk{color:var(--haze);font-size:13px;font-family:'Space Mono',monospace}
.legend{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 17px;font-size:13px;line-height:1.6;color:var(--haze)}
.legend b{color:var(--ink)}
.legend .lr{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.legend .lr span{background:#1C2B42;border-radius:6px;padding:3px 8px;font-size:11.5px}
"""

# Position bands reuse report_page's ratified scale (state -> band -> label/colour).
_BANDS = rp.BANDS
_STATE_BAND = rp.STATE_BAND
_RUNG_LABEL = rp.RUNG_LABEL


# --------------------------------------------------------------------------- #
# Facts assembly — deterministic, from already-computed data only.

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
    """Per-subject landed-of-total, folding this week in — the running tally the
    RUNNING PICTURE leads with. `landed` = developing/solid."""
    _LANDED = {"developing", "solid"}
    out = []
    for c in cards:
        total = len(c["rows"])
        landed = sum(1 for r in c["rows"] if r.get("state") in _LANDED)
        out.append({"subject": c["subject"], "landed": landed, "total": total})
    return out


def build_portal(name, week_of, topics, subjects_block, radar,
                 week_ahead=None, this_week_blocks=None, this_week_fluency=None,
                 snapshots=None, archive=None, updated=None):
    """Assemble the portal — the THREE-part parent report on one always-current
    page (PARENT-COMMS-V2 §1/§5):

      week_ahead        component 1 (Monday, forward): monday_brief.week_ahead()
                        output {rows, assessment, subjects}.
      this_week_blocks  component 2 (Friday, backward): report_stories
                        .subject_blocks() — what happened, the subject spine.
      running           component 3 (Friday, cumulative): where each subject
                        stands term-to-date (subject cards + landed tally +
                        term trends), this week folded in.

    All three derive from already-computed facts. `archive` = [{"week","url"}]
    newest-first.
    """
    cards = subject_cards(topics)
    return {
        "name": name.split()[0] if name else "",
        "week_of": week_of,
        "updated": updated or _dt.date.today().isoformat(),
        "week_ahead": week_ahead or {},
        "this_week": {"blocks": this_week_blocks or [], "fluency": this_week_fluency},
        "running": {"cards": cards, "cumulative": _cumulative(cards),
                    "trends": term_trends(snapshots or [])},
        "archive": archive or [],
    }


# --------------------------------------------------------------------------- #
# Rendering

def _week_ahead_section(wa):
    """Component 1 — THE WEEK AHEAD (Monday, forward). Per subject: what class is
    on + what his sets are covering (NEW flagged), plus one assessment line.
    Refreshed Monday; a stale panel on a pull page is forgivable."""
    rows = (wa or {}).get("rows") or []
    assessment = (wa or {}).get("assessment")
    if not rows and not assessment:
        return ""
    out = []
    for r in rows:
        unit = f"<span class='wa-unit'>{_e(r['unit'])}</span>" if r.get("unit") else ""
        newchips = "".join(f"<span class='chip'>new: {_e(t)}</span>" for t in r.get("new", []))
        intent = f"<div class='wa-intent'>{_e(r.get('intent',''))}</div>" if r.get("intent") else ""
        hedge = ("<div class='wa-hedge'>Confirming this subject's page for your "
                 "teacher — treat as a guide this week.</div>" if r.get("hedged") else "")
        out.append(f"<div class='wa-row'><div class='s'>{_e(r['subject'])} {unit}</div>"
                   f"{intent}<div class='wa-chips'>{newchips}</div>{hedge}</div>")
    assess_html = ""
    if assessment and assessment.get("date"):
        when = _friendly_date(assessment.get("date"), assessment.get("days"))
        assess_html = ("<div class='wa-assess'><span class='k'>ONE DATE</span> "
                       f"<b>{_e(assessment.get('task'))}</b> — {_e(when)}. His sets are "
                       "already steering practice toward it.</div>")
    return ("<div class='section'>THE WEEK AHEAD <span class='when'>· updated Monday</span></div>"
            f"<div class='wa-grid'>{''.join(out)}</div>{assess_html}")


def _friendly_date(iso, days=None):
    try:
        d = _dt.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return iso or ""
    txt = d.strftime("%A %-d %B") if hasattr(d, "strftime") else iso
    if isinstance(days, int) and 0 <= days <= 7:
        return f"{txt} (this week)"
    return txt


def _this_week_section(this_week, name):
    """Component 2 — THIS WEEK, WHAT HAPPENED (Friday, backward). The subject
    spine, rendered by report_page's per-block renderer so Monday's plan and
    Friday's resolution share one shape. Placeholder until Friday's run."""
    blocks = (this_week or {}).get("blocks") or []
    fluency = (this_week or {}).get("fluency")
    if not blocks:
        return ("<div class='section'>THIS WEEK <span class='when'>· updated Friday</span></div>"
                "<div class='tw-soon'>This week's report lands Friday evening — what "
                "each subject actually worked, where it landed, and the one thing worth "
                "knowing.</div>")
    flu = ""
    if fluency:
        flu = ("<div class='fluency'>On <b>" + _e(fluency) + "</b>, " + _e(name)
               + " could pick the right answer but not yet put the why in his own "
               "words — so the deeper level was held until the explanation catches "
               "up. That safeguard is the rigour behind every position here.</div>")
    body = "".join(rp._subject_block(b, name) for b in blocks)
    return ("<div class='section'>THIS WEEK <span class='when'>· updated Friday</span></div>"
            f"{flu}{body}")


def _topic_row(r):
    band = _STATE_BAND.get(r.get("state"), 1)
    label, colour = _BANDS[band][0], _BANDS[band][1]
    dep = r.get("depth")
    dep_html = (f"<span class='dep'>{_e(_RUNG_LABEL[dep].capitalize())}</span>"
                if dep in _RUNG_LABEL else "<span class='dep none'>&mdash;</span>")
    row = (f"<div class='trow'><span class='tn'>{_e(r.get('topic'))}</span>"
           f"<span class='pos'><span class='dot d{colour}'>&#9679;</span>{_e(label)}</span>"
           f"<span class='dep-wrap'>{dep_html}</span>")
    if r.get("confidently_shallow"):
        row += ("<div class='cshallow'><b>Strong recall</b> — he can pick this "
                "confidently, but hasn't yet shown he can explain it. His next "
                "written question targets exactly that.</div>")
    return row + "</div>"


def _running_section(running):
    """Component 3 — THE RUNNING PICTURE (Friday, cumulative). Leads with the
    per-subject landed tally (this week folded in), then the full where-he-stands
    cards (position + depth, the confidently-shallow cross), then term trends."""
    cards = (running or {}).get("cards") or []
    if not cards and not (running or {}).get("trends"):
        return ""
    cum = (running or {}).get("cumulative") or []
    tally = "<span class='sep'> · </span>".join(
        f"{_e(c['subject'])} {c['landed']} of {c['total']} landed"
        for c in cum if c.get("total"))
    tally_html = f"<div class='cumf'>{tally}</div>" if tally else ""
    body = []
    for c in cards:
        rows = "".join(_topic_row(r) for r in c["rows"])
        body.append(f"<div class='card'><div class='subj'>{_e(c['subject'])}</div>{rows}</div>")
    return ("<div class='section'>THE RUNNING PICTURE <span class='when'>· updated Friday</span></div>"
            f"{tally_html}{''.join(body)}{_trends_section((running or {}).get('trends'))}")


def _trends_section(trends):
    if not trends:
        return ("<div class='section'>TERM TRENDS</div>"
                "<div class='trend soon'>The term trend fills in here once there are "
                "four weeks of history to compare — before then a &ldquo;trend&rdquo; "
                "would be noise, so we don't fake one. Weekly snapshots are banking "
                "now.</div>")
    rows = []
    for r in trends["rows"]:
        gained = r["gained"]
        tail = (f" <span style='color:var(--kelp)'>&uarr; +{gained} this term</span>"
                if gained > 0 else "")
        rows.append(f"<div class='trow trend-row'><span class='tn'>{_e(r['subject'])}</span>"
                    f"<span class='pos'>{r['landed']} of {r['total']} landed{tail}</span></div>")
    return ("<div class='section'>TERM TRENDS</div>"
            f"<div class='trend'>{''.join(rows)}</div>"
            f"<p class='notes' style='color:var(--haze);font-size:12.5px'>"
            f"Across {trends['weeks']} weeks of history.</p>")


def _archive_section(archive):
    if not archive:
        return ""
    links = "".join(
        f"<a href='{_e(a['url'])}'><span>Week report</span>"
        f"<span class='wk'>{_e(a['week'])}</span></a>" for a in archive)
    return ("<div class='section'>ARCHIVE</div>"
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
            "<p style='margin:10px 0 0'>Positions update every Friday; this week's "
            "class focus updates Monday. Questions? Text Rich.</p></div>")


def render(portal, kid_wrap_url=None):
    """Full self-contained HTML for one kid's portal page."""
    name = portal.get("name", "")
    stamp = rp.build_stamp()
    wrap_link = (f" &nbsp;·&nbsp; <a href='{_e(kid_wrap_url)}'>{_e(name)}'s player card</a>"
                 if kid_wrap_url else "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="xpdaily-build" content="{_e(stamp)}" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="robots" content="noindex, nofollow" />
<meta name="theme-color" content="#0B1220" />
<title>XPDaily — {_e(name)}'s picture</title>
<style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="top"><span class="brand">XPDAILY · THE FULL PICTURE</span><span class="updated">updated {_e(portal.get('updated',''))}</span></div>
  <div class="hero">{_e(name)}'s full picture — the week ahead, the week just gone, and how it's adding up</div>
  {_week_ahead_section(portal.get('week_ahead'))}
  {_this_week_section(portal.get('this_week'), name)}
  {_running_section(portal.get('running'))}
  {_archive_section(portal.get('archive'))}
  {_legend()}
  <p class="foot">This is {_e(name)}'s picture, kept current — open it any time.{wrap_link}</p>
  <p class="foot">build {_e(stamp)}</p>
</div>
</body>
</html>"""
