#!/usr/bin/env python3
"""
friday_sms.py — the Friday PARENT SMS (REPORTING.md surface B). The only thing
PUSHED on Friday's report clock; the hosted page (surface A) is the deep dive
it links to. Mirrors soundbyte.py / wed_checkin.py exactly:
  deterministic facts  ->  LLM dressing  ->  LAW VALIDATOR
  ->  deterministic fallback if the model fails the law  ->  SMS via notify.

THE SMS IS THE TIER-1 REPORT. A parent who never taps the link still received
the whole judgement: lead line + three headlines + XP + (if a test is near) the
readiness read. The link is the depth, NEVER a paywall — so the body must stand
alone and the link must read as "more if you want it".

FRIDAY LAW (how this validator differs from Wednesday's):
  * XP TOTAL IS ALLOWED and expected — it is the ONE number the daily soundbyte
    withheld precisely so the weekly report could carry it (soundbyte doctrine).
    So digits are permitted, but ONLY the season XP total; no ratios, no
    per-cent, no scores, no counts dressed as performance.
  * STILL NO RATIO CHARACTERS. '%' and score-slashes stay banned — comprehension
    never becomes a number, only a word (the week-word).
  * NO BARE GAP. 'behind' only as 'a step behind' (Friday's phrasing of
    Wednesday's 'a bit behind'), and any flagged area arrives WITH its fix in
    the same breath. quiet outranks a comprehension read on thin data.
  * BANNED WORDS unchanged: miss, wrong, fail, dumb, lazy — difficulty belongs
    to the set, effort and wins belong to the kid.
  * THE HEADLINES ARE CHOSEN BY CODE. friday_report.build_card() already picked
    the week-word, standing verdict, win and action. The model writes them into
    three short lines; it does not decide what they are.

The composer takes the fact card (friday_report.build_card) plus the kid's
report-page URL, and returns the SMS body. compose_ai / validate / fallback_render
have the same three-function shape as wed_checkin so the tests read the same.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"     # house language model (compose.py)
MAX_TOKENS = 512
MIN_LEN = 90
MAX_LEN = 600                          # a touch longer than Wed — carries 3 headlines + link

# Words that can never appear (difficulty is the set's, never the kid's).
BANNED = ("miss", "wrong", "fail", "dumb", "lazy", "stupid")


# --------------------------------------------------------------------------- #
# The law. Every outgoing Friday body passes this or it is not sent.

def validate(text, name, url=None):
    """(ok, reason). The Friday law — permits the XP total, nothing else numeric
    that reads as performance; no bare gap; link present and framed as optional.
    """
    if not text or len(text) < MIN_LEN:
        return False, "too-short"
    if len(text) > MAX_LEN:
        return False, "too-long"
    if name.split()[0] not in text:
        return False, "no-name"
    # ratio characters stay banned — comprehension is a word, never a number
    if "%" in text:
        return False, "percent"
    if re.search(r"\d\s*/\s*\d", text):
        return False, "score-slash"
    # 'behind' only as 'a step behind' (never bare / accusatory)
    for m in re.finditer(r"behind", text, re.IGNORECASE):
        prefix = text[:m.start()].lower().rstrip()
        if not (prefix.endswith("a step") or prefix.endswith("a bit")):
            return False, "bare-behind"
    for w in BANNED:
        if re.search(rf"\b{w}\w*", text, re.IGNORECASE):
            return False, f"banned-word:{w}"
    # the link is the deep dive; it must be present and must not read as a wall
    if url:
        if url not in text:
            return False, "no-link"
        low = text.lower()
        for wall in ("unlock", "log in to see", "sign in to see", "subscribe",
                     "upgrade to", "paywall", "members only"):
            if wall in low:
                return False, f"paywall-language:{wall}"
    return True, "ok"


# --------------------------------------------------------------------------- #
# Deterministic headline construction (CODE decides; these ARE the headlines).

WORD_LEAD = {
    "strong": "Strong week",
    "solid":  "Solid week",
    "quiet":  "Quiet week",
    "slower": "A harder week",
}


def _cap(s):
    return s[:1].upper() + s[1:] if s else s


def headlines(card):
    """The three deterministic headlines + the lead line, as plain strings.
    This is the tier-1 content; the model only smooths them into a message.
    Returns {"lead": str, "rows": [str, str, str], "readiness": str|None}.
    """
    name = card["name"].split()[0]
    word = card["week_word"]["word"]
    baseline = card.get("baseline")
    act = card["activity"]
    stand = card["standing"]
    win = card["win"]
    action = card["action"]
    radar = card.get("radar")

    # Lead: the standing+trajectory fusion, honest in week 1 (no trajectory).
    lead_word = WORD_LEAD.get(word, "This week")
    if baseline:
        lead = f"{lead_word} for {name} — first week on the board."
    else:
        d = card["week_word"]["direction"]
        tail = {"up": ", building on last week", "down": ", off last week's pace",
                "flat": ", tracking level with last week", "none": ""}.get(d, "")
        lead = f"{lead_word} for {name}{tail}."

    rows = []
    # Row 1 — the win (always something genuine). In a baseline week with no
    # run yet there is no win to open on; lead with 'getting going' so the
    # message never opens straight onto a gap (no-anxiety).
    if win["kind"] == "mastery":
        rows.append(f"Landed: {win['topic']}" if win.get("landed")
                    else f"Coming together: {win['topic']}")
    elif win["kind"] == "badge":
        rows.append(f"Earned the '{win['badge']}' badge")
    elif win["kind"] == "best_run":
        if win.get("starting"):
            rows.append(f"On the board — best run {win['day']}, {win['pts']:,} XP")
        else:
            rows.append(f"Best run {win['day']} — {win['pts']:,} XP")
    elif baseline and act["days_done"] == 0:
        rows.append("Just getting going — nightly runs are the whole game")
    # Row 2 — where he stands (verdict first, exception named with no bare 'behind').
    if stand["overall"] == "on":
        rows.append("Keeping pace across the board")
    else:
        exc = stand["exceptions"][0]
        rows.append(f"On pace, bar one: a step behind on {exc[1]}")
    # Row 3 — the one action (the no-anxiety fix; radar folds in if present).
    rows.append(_action_headline(action, radar))

    readiness = _readiness_line(radar) if radar else None
    return {"lead": lead, "rows": rows[:3], "readiness": readiness}


def _action_headline(action, radar):
    k = action.get("kind")
    if k == "assess":
        return (f"This week's 5 min: {action['topic']}, before the "
                f"{action['task']}")
    if k == "repair":
        return f"This week's 5 min: a quick pass over {action['topic']}"
    if k == "behind":
        return f"This week's 5 min: {action['topic']}"
    if k == "ask":
        return f"This week's 5 min: get him to explain {action['topic']}"
    return "Nothing needed this week — just keep the nightly run going"


def _readiness_line(radar):
    """The assessment-readiness read, phrased WITHOUT anxiety. 'early' never
    reads as alarm — it reads as 'here's the runway and what to aim at'."""
    days = radar["days"]
    when = "this week" if days <= 7 else "next week"
    task = radar["task"]
    if radar["readiness"] == "ready":
        return f"{task} {when} — he's in good shape for it."
    if radar["readiness"] == "building":
        foc = f", {radar['focus']} is the one to firm up" if radar.get("focus") else ""
        return f"{task} {when} — coming together{foc}."
    # early: plenty still to cover — framed as runway, with the aim point
    foc = f"; {radar['focus']} is the place to start" if radar.get("focus") else ""
    return f"{task} {when} — early days on it yet, so good week to get ahead{foc}."


# --------------------------------------------------------------------------- #
# Deterministic fallback (must pass the law; asserted, not hoped).

def fallback_render(card, url):
    """The approved Friday voice, parameterised. Always law-legal."""
    h = headlines(card)
    name = card["name"].split()[0]
    xp = card["xp_total"]
    parts = [h["lead"]]
    parts.append(" · ".join(h["rows"]) + ".")
    if h["readiness"]:
        parts.append(h["readiness"])
    parts.append(f"{name}'s season total is now {xp:,} XP.")
    parts.append(f"Full week in the report: {url}")
    return " ".join(parts)


# --------------------------------------------------------------------------- #
# The AI dresser — smooths the deterministic headlines into a warm message.

SYSTEM = """You turn ONE fact card + its three code-chosen headlines into a short Friday SMS from XPDaily to a parent, in the product's redlined voice. This is the WEEKLY REPORT — the resolution of the story Wednesday's check-in set up.

The card and the provided headlines are the COMPLETE truth. The three headlines are already decided by code (the win, where he stands, the one action) — your job is to write them into a warm, natural message, NOT to change what they say or add new claims. Invent nothing: no topics, no results, no events, no numbers beyond the season XP total and the link.

WHAT THIS SMS IS: the tier-1 report. A parent who never taps the link must still get the whole picture from the text alone. The link is the deep dive — frame it as "more if you want it", NEVER as a wall or a paywall.

HARD RULES (the text is rejected if any is broken):
- The ONLY number allowed is the season XP total (say it as given, with the comma) and the link. No percentages. No scores. No "x of y". No ratios. Comprehension is a WORD (strong/solid/quiet/harder), never a number.
- Never a bare "behind" — only "a step behind". Never accusatory, never dramatic, never guilt. Difficulty belongs to the set/quiz; effort and wins belong to the kid.
- Any flagged area must arrive WITH its fix in the same breath — never a bare worry. Under-claim when the week is thin; a quiet week is "quiet — happens", never a problem.
- If there's an assessment-readiness line, keep its calm framing: "early days on it" is RUNWAY (a good week to get ahead), never alarm. Name the one topic to start on if given.
- Never these words in any form: miss, wrong, fail, dumb, lazy.
- Include the link exactly as given, once, framed as the optional deep dive ("full week in the report", "the rest is here if you want it").
- Topic names in the card/headlines are display-safe — use them as given. Never quote raw ledger names.
- Warm, plain, specific. One short message, a few lines is fine, under six hundred characters, no emojis, no sign-off, no markdown.

WEEK 1: there is no prior week, so there is NO trajectory — do not imply improvement or decline versus last week. Frame it as a starting point ("first week on the board").

Tone anchors (match this register):
1. "Solid week for Harrison — first week on the board. He's on the board with a strong Monday run, keeping pace across the board, and there's a Geometry test coming up on the 20th — early days on that topic yet, so a good week to get ahead; angles on parallel lines is the place to start. Harrison's season total is now 5,502 XP. Full week in the report: <link>"
2. "Strong week for Alex, building on last week. Linear equations really landed, he's keeping pace everywhere, and this week's five minutes: get him to talk you through one equation out loud. Alex's season total is now 8,140 XP. The rest is here if you want it: <link>"
3. "Quiet week for Sam — happens. Nothing needed beyond getting the nightly run going again; the door back in is smaller than it looks. Sam's season total is now 3,020 XP. Full picture here: <link>"

Output ONLY the SMS body. No quotes, no preamble, no markdown."""


def compose_ai(card, url, api_key, model=DEFAULT_MODEL):
    """One attempt; caller validates and falls back. Returns text or None."""
    h = headlines(card)
    payload = {"card": card, "headlines": h, "link": url}
    user = ("Write the Friday report SMS for this fact card and its "
            "code-chosen headlines. Use the link exactly as given:\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=1))
    body = json.dumps({
        "model": model, "max_tokens": MAX_TOKENS, "system": SYSTEM,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.load(resp)
        text = "".join(b.get("text", "") for b in out.get("content", []))
        return text.strip().strip('"').strip()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def render_body(card, url, api_key=None, use_ai=True, model=DEFAULT_MODEL):
    """(body, source). AI if it validates against the Friday law, else the
    approved fallback — which MUST pass its own law (asserted)."""
    name = card["name"]
    if use_ai and api_key:
        text = compose_ai(card, url, api_key, model)
        if text:
            ok, why = validate(text, name, url)
            if ok:
                return text, "ai"
            fail = why
        else:
            fail = "api-error"
    else:
        fail = "ai-off"
    text = fallback_render(card, url)
    ok, why = validate(text, name, url)
    if not ok:                                          # pragma: no cover
        raise AssertionError(f"fallback failed its own law: {why}")
    return text, f"fallback({fail})"
