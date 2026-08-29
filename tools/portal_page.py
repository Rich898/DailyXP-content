#!/usr/bin/env python3
"""
portal_page.py — the always-available parent PORTAL (PARENT-COMMS-V2 §5).

The Friday report answers "how did THIS WEEK go"; the portal answers the other
two questions a paying parent has — "what is he working on right now" and "how
is he doing OVERALL, by subject" — on a page they can open any time. Messages
become pointers; the portal becomes the product. The accumulating history is the
switching cost: cancelling stops the map of THIS kid's misconceptions,
calibration and depth from growing.

STRUCTURE (top to bottom = the three questions):
  1. NOW           per subject: current class focus + the assessment radar.
  2. THIS WEEK     the sweep diff (NEW OR CHANGED, never the whole file) + what
                   his sets are doing about it — Monday's content as a PULL.
  3. SUBJECT CARDS per-topic position AND depth, side by side. This is where the
                   founding insight finally renders: solid recall x shallow depth
                   -> "strong recall; hasn't yet shown he can explain it" —
                   confidently shallow, on a page, per topic.
  4. TERM TRENDS   from the weekly snapshots — switches on at 4+ weeks, and says
                   so rather than faking a trend before then.
  5. ARCHIVE       past Friday reports (dated paths; the bare slug serves latest).
  6. FOOTER        the verdict-ladder legend, an "updated {date}" stamp, build
                   stamp.

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


def now_rows(subjects_block, radar):
    """Per-subject current class focus (live targets) + the assessment radar (V2
    §5.1). Focus lists the topics the school currently has live; the radar line
    attaches to its subject."""
    rows = []
    radar_subj = (radar or {}).get("subject")
    for subj in sorted(subjects_block or {}):
        block = subjects_block[subj] or {}
        live = [t.get("topic") for t in block.get("topics", [])
                if t.get("status") == "live"]
        unit = block.get("unit") or block.get("module") or block.get("current_unit")
        assess = None
        if radar and radar_subj == subj and radar.get("date"):
            assess = {"task": radar.get("task"), "date": radar.get("date"),
                      "days": radar.get("days")}
        if live or unit or assess:
            rows.append({"subject": subj, "unit": unit, "focus": live[:4],
                         "assess": assess})
    return rows


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


def build_portal(name, week_of, topics, subjects_block, radar,
                 this_week=None, snapshots=None, archive=None, updated=None):
    """Assemble the full portal data structure from already-computed facts.
    `this_week` = {"new_or_changed": [topic...], "intent": str} (Monday's diff,
    or the honest continuation form). `archive` = [{"week","url"}] newest-first.
    """
    return {
        "name": name.split()[0] if name else "",
        "week_of": week_of,
        "updated": updated or _dt.date.today().isoformat(),
        "now": now_rows(subjects_block, radar),
        "this_week": this_week or {},
        "subjects": subject_cards(topics),
        "trends": term_trends(snapshots or []),
        "archive": archive or [],
    }


# --------------------------------------------------------------------------- #
# Rendering

def _now_section(rows):
    if not rows:
        return ""
    out = []
    for r in rows:
        unit = f"<div class='f'>{_e(r['unit'])}</div>" if r.get("unit") else ""
        focus = ""
        if r.get("focus"):
            focus = "<div class='a'>Working on: <b>" + _e(" · ".join(r["focus"])) + "</b></div>"
        assess = ""
        a = r.get("assess")
        if a:
            when = ("this week" if (a.get("days") or 99) <= 7 else
                    f"in {a['days']} days" if a.get("days") is not None else a.get("date"))
            assess = (f"<div class='a'>Coming up: <b>{_e(a.get('task'))}</b> — {_e(when)}</div>")
        out.append(f"<div class='now-row'><div class='s'>{_e(r['subject'])}</div>"
                   f"{unit}{focus}{assess}</div>")
    return ("<div class='section'>NOW</div>"
            f"<div class='now-grid'>{''.join(out)}</div>")


def _this_week_section(tw):
    if not tw:
        return ""
    nc = tw.get("new_or_changed") or []
    intent = tw.get("intent")
    if not nc and not intent:
        return ""
    chips = "".join(f"<span class='chip'>{_e(t)}</span>" for t in nc)
    nc_html = (f"<div class='nc'><span class='k'>NEW OR CHANGED THIS WEEK</span><br>{chips}</div>"
               if chips else "")
    intent_html = f"<div class='intent'>{_e(intent)}</div>" if intent else ""
    return ("<div class='section'>THIS WEEK</div>"
            f"<div class='tw'>{nc_html}{intent_html}</div>")


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


def _subjects_section(cards):
    if not cards:
        return ""
    out = []
    for c in cards:
        rows = "".join(_topic_row(r) for r in c["rows"])
        out.append(f"<div class='card'><div class='subj'>{_e(c['subject'])}</div>{rows}</div>")
    return ("<div class='section'>BY SUBJECT — WHERE HE STANDS</div>"
            f"{''.join(out)}")


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
  <div class="hero">{_e(name)} — always here, always current</div>
  {_now_section(portal.get('now'))}
  {_this_week_section(portal.get('this_week'))}
  {_subjects_section(portal.get('subjects'))}
  {_trends_section(portal.get('trends'))}
  {_archive_section(portal.get('archive'))}
  {_legend()}
  <p class="foot">This is {_e(name)}'s picture, kept current — open it any time.{wrap_link}</p>
  <p class="foot">build {_e(stamp)}</p>
</div>
</body>
</html>"""
