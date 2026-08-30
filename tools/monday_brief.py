#!/usr/bin/env python3
"""
monday_brief.py — the WEEK AHEAD, component 1 of the three-part parent report
(PARENT-COMMS-V2 §4; the loop's forward half). Deterministic. No LLM.

The parent report is three time-phased components, all rendered in the PORTAL:
  1. THE WEEK AHEAD  (Monday)  — per subject, what school is covering this week
                                  and what his sets will do about it. THIS FILE.
  2. THIS WEEK       (Friday)  — what happened: the subject spine (report_stories
                                  .subject_blocks + report_page).
  3. THE RUNNING PICTURE (Friday) — the cumulative wrap: term-to-date by subject.

Monday is a PULL panel on the portal; the Monday SMS is a thin POINTER
("here's what's being covered this week — <link>"), NOT the content. That is the
whole design: a pointer carries no sweep-derived claim, so it can never tell a
paying parent something false about their kid's school week — which is why it
works today, before the sweep-trust gate that governs a CONTENT push.

THE MONDAY LAW (V2 §4, enforced by validate()):
  * Forward-looking only. No verdicts, no standing words (solid / building /
    behind / developing / "close to locking in" / "keeping pace" ...), no result
    words, no digits EXCEPT a single assessment date. Topic names, dates and
    plan intent are the only legal fact classes.
  * Assessment claims are hedged as practice-coverage ("his sets are steering
    toward it"), never an outcome prediction.
  * Per-teacher subjects are hedged/omitted for any seat whose teacher page the
    sweep didn't verify (another family's teacher may differ at beta).
  * Fail-soft: if the newest targets aren't THIS Monday's, the honest
    continuation form — never silent, never invented.

Panel content (the portal Week-Ahead) can carry the per-topic detail because it
is PULL; the pointer SMS stays a pointer. Both derive from ONE deterministic
fact set — the wed_checkin pattern: code decides, nothing is invented.
"""
import re
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wed_checkin import display_topic          # law-legal topic names  # noqa: E402


# --------------------------------------------------------------------------- #
# Forward facts — what each subject is covering this week (from the targets).

def _live(block):
    return [t for t in (block.get("topics") or []) if t.get("status") == "live"]


def new_or_changed(subjects_block, prev_subjects_block):
    """Per subject, the live topics that are NEW vs last week's targets — the
    'NEW OR CHANGED' the panel leads with (never the whole carry-forward file)."""
    prev = {s: {t.get("topic") for t in _live(b or {})}
            for s, b in (prev_subjects_block or {}).items()}
    out = {}
    for subj, block in (subjects_block or {}).items():
        prior = prev.get(subj, set())
        out[subj] = [t.get("topic") for t in _live(block) if t.get("topic") not in prior]
    return out


def week_ahead(name, subjects_block, prev_subjects_block=None, radar=None,
               unverified=()):
    """The Week-Ahead fact set. Per subject: what class is on (unit), what it's
    covering this week (live topics, NEW ones flagged), and whether the read is
    hedged (per-teacher subject the sweep couldn't verify). Plus one assessment
    line if a dated test is near. Forward-only — no ledger state ever enters."""
    unverified = set(unverified or ())
    nc = new_or_changed(subjects_block, prev_subjects_block)
    rows = []
    for subj in sorted(subjects_block or {}):
        block = subjects_block[subj] or {}
        live = _live(block)
        if not live:
            continue
        covering = [display_topic(t.get("topic"), subj) for t in live]
        new_names = {display_topic(t, subj) for t in nc.get(subj, [])}
        rows.append({
            "subject": subj,
            "unit": block.get("unit") or block.get("module") or block.get("current_unit"),
            "covering": covering,
            "new": [c for c in covering if c in new_names],
            "hedged": subj in unverified,
            "intent": _intent(covering, [c for c in covering if c in new_names]),
        })
    assess = None
    if radar and radar.get("date"):
        assess = {"task": radar.get("task"), "date": radar.get("date"),
                  "days": radar.get("days"), "subject": radar.get("subject")}
    return {"name": (name or "").split()[0], "rows": rows, "assessment": assess,
            "subjects": [r["subject"] for r in rows]}


def _intent(covering, new):
    """A forward clause for a subject. The vocabulary is exactly two verbs
    (Rich, 30 Aug): 'continues', 'moves into', or both — new topics always
    arrive under 'moves into', carried-forward ones under 'continues'.
    Deterministic; no verdicts, no state."""
    if new and len(new) == len(covering):
        return "moves into " + _join(new)
    if new:
        return "moves into " + _join(new) + " and continues " + _join(
            [c for c in covering if c not in new])
    return "continues " + _join(covering)


def _join(items, cap=3):
    items = items[:cap]
    if not items:
        return "this week's topics"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


# --------------------------------------------------------------------------- #
# Fail-soft continuation form (targets not fresh this Monday).

def is_fresh(targets_week_of, asof):
    """Is the newest targets file THIS Monday's? asof is a date; targets_week_of
    an ISO Monday string. Fail-soft when we can't tell."""
    if not targets_week_of:
        return False
    mon = (asof - _timedelta(asof.weekday())).isoformat()
    return targets_week_of == mon


def _timedelta(days):
    from datetime import timedelta
    return timedelta(days=days)


# --------------------------------------------------------------------------- #
# The Monday POINTER SMS — thin, carries no sweep-derived claim (works pre-gate).

def _date_phrase(iso):
    try:
        d = date.fromisoformat(iso)
    except (TypeError, ValueError):
        return ""
    return d.strftime("%A %-d %B") if hasattr(d, "strftime") else iso


def pointer_sms(brief, portal_url, subjects_named=True):
    """The Monday SMS: a POINTER to the portal's Week-Ahead panel, not the
    content. Names the subjects at most (stable, not sweep-fragile) and points
    at the link. No per-topic claims, no dates asserted, no verdicts — safe to
    send before the sweep-trust gate. Deterministic; always passes validate()."""
    name = brief["name"]
    subs = brief.get("subjects") or []
    if subjects_named and subs:
        lead = (f"{name}'s plan for the week is up — what {_join(subs, cap=4)} "
                f"are covering, and what to look out for.")
    else:
        lead = f"{name}'s learning plan for the week is up."
    return (f"XP Daily — {lead} Have a look here: {portal_url}")


# --------------------------------------------------------------------------- #
# The Monday law — validates ANY Monday text (pointer or a future content push).

# Standing / verdict / result vocabulary that must never appear in a forward
# Monday message. Checked against the text with the topic names + subjects +
# assessment date masked out, so a topic legitimately containing one of these
# words ("Building structures") can't trip it.
_MONDAY_DENY = [
    r"\bsolid\b", r"\bbuilding\b", r"\bbehind\b", r"\bdeveloping\b",
    r"\bshaky\b", r"\bmastered?\b", r"\bstrong(?:er)?\b", r"\bquiet\b",
    r"\bslower\b", r"\bstruggl", r"\bahead\b", r"\bimprov", r"\bslipp",
    r"\bkeeping pace\b", r"\bon track\b", r"\bon pace\b", r"\bat the door\b",
    r"\blocking in\b", r"\blanded\b", r"\bconsolidat", r"\bfell\b",
    r"\bdropped\b", r"\bweak(?:er)?\b", r"\bdid well\b", r"\bwent well\b",
    # result words
    r"\bmiss\w*", r"\bscore\w*", r"\bwrong\b", r"\bfail\w*", r"\bcorrect\b",
    r"\baccuracy\b", r"\bgrade[ds]?\b",
]


def validate(text, name, allow_date_phrase="", topics=(), subjects=(),
             min_len=30, max_len=460):
    """(ok, reason) for a Monday message. Forward-only, no verdicts, no digits
    except the single assessment date phrase. Topic/subject names and the date
    phrase are masked before the checks so real content can't false-trip."""
    if not text or len(text) < min_len:
        return False, "too-short"
    if len(text) > max_len:
        return False, "too-long"
    if name and name.split()[0] not in text:
        return False, "no-name"
    masked = re.sub(r"https?://\S+", " ", text)          # the link is legal
    for token in list(topics) + list(subjects) + ([allow_date_phrase] if allow_date_phrase else []):
        if token:
            masked = masked.replace(token, " ")
    if "%" in masked or "/" in masked:
        return False, "ratio-chars"
    if re.search(r"\d", masked):
        return False, "digits-outside-date"
    for pat in _MONDAY_DENY:
        m = re.search(pat, masked, re.IGNORECASE)
        if m:
            return False, f"standing-word:{m.group(0).strip().lower()}"
    return True, "ok"
