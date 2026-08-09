#!/usr/bin/env python3
"""
wed_checkin.py — the Wednesday midweek check-in (REPORTING.md touchpoint 2: ACTIVATE).

Runs Wednesday 7:30am Sydney (wed-checkin.yml, cron 30 21 * * 2 UTC). One SMS
per kid to that kid's own parent seat ("parents:<code>"): a momentum read
sampled from the SAME week-word engine Friday's report will use (coherence by
construction — Wednesday can never contradict Friday, because they are the
same computation at two moments), plus at most ONE ask (a strength the parent
can draw out at dinner) and at most ONE help action (a flagged gap, dressed
as five minutes, planted for Friday's wrap to harvest). Wednesday is the
EXPECTATION-SETTER for Friday: every text ends pointing at the wrap, so the
report lands as a resolution, never a surprise verdict.

Design laws:
  * CODE DECIDES, LANGUAGE DRESSES. The deterministic layer picks every fact
    (week-word, direction, attendance phrase, ask topic, gap topic). The
    model turns the fact card into sentences — nothing else. If the API is
    down or the composed text fails validation, a deterministic fallback
    (the redlined approved voices, parameterised) sends instead: the
    Wednesday rhythm never goes silent and never goes off-law over an API
    blip.
  * HONEST MOMENTUM, UNDRAMATIC. Up is said, flat is said, down is said —
    "a bit behind last week", never bare "behind", never accusatory, never
    dramatic. QUIET (engagement dip) OUTRANKS SLOWER (comprehension dip):
    thin evidence never gets a comprehension judgement stacked on it.
  * ONE WEEK-WORD ENGINE. momentum() is the thresholds Friday samples on
    the full week; Wednesday samples Mon–Tue vs LAST week's Mon–Tue —
    like for like.
  * NO NUMBERS. The validator rejects any outgoing text containing a digit,
    a %, or a slash. Attendance is words ("kept both days", "one run in").
    Comprehension ratios are computed and printed NOWHERE (soundbyte law).
  * GAPS ARRIVE DRESSED AS HELP, with the Friday plant ("it's the one
    Friday's wrap will centre on"). Difficulty belongs to the set.
  * PUBLIC-LOG HYGIENE. Actions logs print codes + safe statuses only —
    never names, never message text. Failure detail lands PRIVATE
    (work/wed_checkin_last_error.txt).
  * IDEMPOTENT. Cursor (private work/wed_checkin_cursor.json) records
    (student, wednesday) pairs; send is attempted BEFORE the cursor
    advances, so a failed send retries on redispatch.
  * THE LEDGER IS NOT TOUCHED. Reads state.json + runs.json; writes only
    its own cursor.

TODO (blocked on sweep support): assessment radar — one clause when a dated
assessment is inside a fortnight. Needs structured assessment dates in
targets/<monday>.json; free-text ledger notes are deliberately not parsed.

Usage:
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private            # live
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private --dry-run
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private --date 2026-08-05
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private --no-ai   # fallback voices only
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:                                    # pragma: no cover
    ZoneInfo = None

CURSOR_FILE = os.path.join("work", "wed_checkin_cursor.json")
ERROR_FILE = os.path.join("work", "wed_checkin_last_error.txt")

# Week-word engine thresholds (Friday samples the same engine on the full week).
COMP_DELTA = 0.12          # comprehension ratio shift that counts as a real move
MAX_LEN = 440              # SMS budget for the whole check-in
MIN_LEN = 40

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"   # house model for language tasks (see compose.py)
MAX_TOKENS = 300

# The four redlined voices (ratified 9 Aug 2026). They are BOTH the tone
# anchors handed to the model AND the shape of the deterministic fallback.
APPROVED_VOICES = {
    ("strong", "up"):
        "Midweek read: Harrison's kept both days and it's building on last "
        "week. Tonight's ask: get him to explain how the Church held power "
        "over kings — saying it out loud cements it. Friday's wrap should "
        "be a good one.",
    ("solid", "flat"):
        "Steady week for Harrison so far, tracking level with last week. One "
        "thing worth five minutes: he's still circling 'variables in "
        "experiments' — ask him to set dinner up as the experiment: what "
        "changes, what gets measured, what stays the same. It's the one "
        "Friday's wrap will centre on.",
    ("quiet", "down"):
        "Harrison's a bit behind last week — happens. If tonight allows, sit "
        "with him for the first two questions when the quiz lands; the door "
        "back in is smaller than it looks. Full picture in Friday's wrap.",
    ("slower", "down"):
        "Harrison's showing up but working harder for it than last week. "
        "Worth five minutes tonight: 'linear equations' — get him to talk "
        "you through one. Friday's wrap will show where it landed.",
}


# --------------------------------------------------------------------------- #
# Pure logic (everything above main() is testable without network or files)

def sydney_today():
    if ZoneInfo is None:
        return date.today()
    return datetime.now(ZoneInfo("Australia/Sydney")).date()


def week_windows(asof):
    """(this_week_days, prev_week_days) — the Mon+Tue ISO pairs either side.
    Like-for-like: Wednesday compares Mon–Tue against LAST week's Mon–Tue."""
    mon = asof - timedelta(days=asof.weekday())
    this = [(mon + timedelta(days=i)).isoformat() for i in range(2)]
    prev = [(mon - timedelta(days=7) + timedelta(days=i)).isoformat() for i in range(2)]
    return this, prev


def window_stats(runs, student, day_isos):
    """days_done + mean comprehension ratio (best run per day) for a window.
    The ratio lives and dies here — it is printed nowhere."""
    best = {}
    for r in runs:
        if r.get("student") != student or r.get("run_date") not in day_isos:
            continue
        d = r["run_date"]
        sc = int(r.get("score") or 0)
        if d not in best or sc > best[d][0]:
            best[d] = (sc, r.get("max_score") or r.get("maxScore"))
    ratios = [s / int(m) for s, m in best.values() if m and int(m) > 0]
    return {"days_done": len(best), "possible": len(day_isos),
            "comp": (sum(ratios) / len(ratios)) if ratios else None}


def momentum(now, prev):
    """The week-word, sampled midweek. Quiet outranks slower by rule order.
    direction: up | flat | down | none (none = no prior week on file)."""
    no_prior = prev["days_done"] == 0 and prev["comp"] is None
    if no_prior:
        word = "quiet" if now["days_done"] == 0 else "solid"
        return {"word": word, "direction": "none"}
    if now["days_done"] == 0:
        return {"word": "quiet", "direction": "down"}
    if now["days_done"] < prev["days_done"]:
        return {"word": "quiet", "direction": "down"}
    comps = now["comp"] is not None and prev["comp"] is not None
    if comps and now["comp"] <= prev["comp"] - COMP_DELTA:
        return {"word": "slower", "direction": "down"}
    if now["days_done"] > prev["days_done"] or (comps and now["comp"] >= prev["comp"] + COMP_DELTA):
        return {"word": "strong", "direction": "up"}
    return {"word": "solid", "direction": "flat"}


def attendance_phrase(now):
    if now["days_done"] == 0:
        return "no runs in yet"
    if now["days_done"] >= now["possible"]:
        return "kept both days so far"
    return "one run in so far"


def _lt_key(t):
    return (t.get("last_tested") or "", t.get("times_seen") or 0)


def pick_ask(topics):
    """ONE strength for the dinner-table ask: solid beats developing, then
    most recently tested."""
    cands = [t for t in topics if t.get("state") in ("solid", "developing")]
    cands.sort(key=lambda t: (t.get("state") == "solid", _lt_key(t)), reverse=True)
    return cands[0] if cands else None


def pick_gap(topics):
    """ONE gap for the five-minute help: repair-flag first, else shaky —
    most recently tested first. Never more than one."""
    for pool in ([t for t in topics if t.get("repair")],
                 [t for t in topics if t.get("state") == "shaky"]):
        pool.sort(key=_lt_key, reverse=True)
        if pool:
            return pool[0]
    return None


def name_for(runs, student):
    dated = sorted((r for r in runs if r.get("student") == student and r.get("name")),
                   key=lambda r: r.get("run_date") or "")
    return dated[-1]["name"] if dated else student.upper()


def display_topic(raw, subject=""):
    """Ledger topic names are for the ledger ("Triangle area (½bh) / area
    recall"); outgoing text needs a speakable, LAW-LEGAL name. Deterministic:
    drop parentheticals, slashes become hyphens, digits/% removed, long
    hyphen chains cut at the first segment. Falls back to the subject."""
    t = re.sub(r"\([^)]*\)", "", raw or "")
    t = t.replace("/", "-")
    t = re.sub(r"[\d%\u00bc\u00bd\u00be]", "", t)
    t = re.sub(r"\s*-\s*", "-", t)
    t = re.sub(r"\s+", " ", t).strip(" -\u2013\u2014\u00b7")
    if "-" in t and len(t) > 20:
        t = t.split("-")[0].strip()
    if len(t) < 3:
        t = (subject or "that topic").strip()
    return t


def _slim(t):
    if not t:
        return None
    return {"topic": display_topic(t.get("topic"), t.get("subject", "")),
            "subject": t.get("subject"),
            "colour": f"(full ledger name: {t.get('topic')}) {t.get('note', '')}"}


def fact_card(code, name, now, prev, topics):
    m = momentum(now, prev)
    return {
        "code": code, "name": name,
        "momentum": {"word": m["word"], "direction": m["direction"],
                     "attendance": attendance_phrase(now)},
        "ask": _slim(pick_ask(topics)),
        "gap": _slim(pick_gap(topics)),
    }


# ---- outgoing-text law (deterministic; applies to AI and fallback alike) --- #

def validate(text, name):
    """(ok, reason). Every outgoing Wednesday text must pass this."""
    if not text or len(text) < MIN_LEN:
        return False, "too-short"
    if len(text) > MAX_LEN:
        return False, "too-long"
    if name.split()[0] not in text:
        return False, "no-name"
    if re.search(r"\d", text):
        return False, "digits"
    if "%" in text or "/" in text:
        return False, "ratio-chars"
    for m in re.finditer(r"behind", text, re.IGNORECASE):
        if not text[:m.start()].lower().rstrip().endswith("a bit"):
            return False, "bare-behind"
    if "friday" not in text.lower():
        return False, "no-friday"
    for w in ("miss", "streak", "score", "wrong", "fail"):
        if re.search(rf"\b{w}\w*", text, re.IGNORECASE):
            return False, f"banned-word:{w}"
    return True, "ok"


# ---- deterministic fallback (the approved voices, parameterised) ----------- #

def _ask_bit(card):
    a = card.get("ask")
    if not a:
        return ""
    return (f" Tonight's ask: get him to explain {a['topic']} — saying it "
            f"out loud cements it. Five minutes, he does the talking.")


def _gap_bit(card, plant=True):
    g = card.get("gap")
    if not g:
        return ""
    tail = " It's the one Friday's wrap will centre on." if plant else ""
    return (f" One thing worth five minutes: he's still circling "
            f"'{g['topic']}' — get him to talk you through it.{tail}")


def fallback_render(card):
    name = card["name"].split()[0]
    word, direction = card["momentum"]["word"], card["momentum"]["direction"]
    att = card["momentum"]["attendance"]
    if word == "quiet":
        opener = (f"{name}'s a bit behind last week — happens."
                  if direction == "down" else
                  f"Quiet start to the week for {name} — happens.")
        return (opener + " If tonight allows, sit with him for the first two "
                "questions when the quiz lands; the door back in is smaller "
                "than it looks. Full picture in Friday's wrap.")
    if word == "slower":
        body = _gap_bit(card, plant=False) or (" Worth five minutes tonight: "
                                               "sit in on the first couple of "
                                               "questions with him.")
        return (f"{name}'s showing up but working harder for it than last "
                f"week.{body} Friday's wrap will show where it landed.")
    if word == "strong":
        line = f"Midweek read: {name}'s {att} and it's building on last week."
        extra = _ask_bit(card) or _gap_bit(card)
        return line + extra + " Friday's wrap should be a good one."
    # solid — flat or no-prior
    opener = (f"Steady week for {name} so far, tracking level with last week."
              if direction == "flat" else
              f"Steady start to the week for {name} — {att}.")
    extra = _gap_bit(card) or _ask_bit(card)
    closer = "" if "Friday" in extra else " More in Friday's wrap."
    return opener + extra + closer


# ---- the AI dresser -------------------------------------------------------- #

SYSTEM = """You turn ONE fact card into ONE SMS from XP Daily to a parent, in the product's redlined voice.

The card is the complete truth: momentum word + direction + attendance phrase, at most one ask (a strength), at most one gap (with colour notes). Use ONLY these facts. Invent nothing — no topics, no events, no claims beyond the card.

HARD RULES (the text is rejected if any is broken):
- No digits anywhere. No percentages. No slashes. Attendance is said in words.
- Never a bare "behind" — only "a bit behind". Never accusatory, never dramatic, never guilt.
- The kid owns effort and wins; difficulty belongs to the set/quiz, never the kid.
- At most ONE ask and ONE five-minute action, drawn only from the card. Colour notes may inspire the action's wording (e.g. a dinner-table framing) but never add facts.
- Never these words in any form: miss, streak, score, wrong, fail.
- Topic names in the card are display-safe — use them as given (natural lowercase is fine). Never quote ledger names from colour.
- Colour informs HOW to frame the one action (e.g. a dinner-table setup) — it is never content to report. Never say a topic is locked, maintenance, repair, chronic, or assessed.
- If a gap exists, the five-minute action IS the gap, and the Friday line points at it ("it's the one Friday's wrap will centre on"). If no gap but an ask exists and momentum isn't down, use the ask. Never both an ask and a gap action.
- ALWAYS end by pointing at Friday's wrap — Wednesday sets the expectation Friday resolves.
- One paragraph, under four hundred characters, plain text, no emojis, no sign-off.

Tone anchors (match this register exactly):
1. "Midweek read: Harrison's kept both days and it's building on last week. Tonight's ask: get him to explain how the Church held power over kings — saying it out loud cements it. Friday's wrap should be a good one."
2. "Steady week for Harrison so far, tracking level with last week. One thing worth five minutes: he's still circling 'variables in experiments' — ask him to set dinner up as the experiment: what changes, what gets measured, what stays the same. It's the one Friday's wrap will centre on."
3. "Harrison's a bit behind last week — happens. If tonight allows, sit with him for the first two questions when the quiz lands; the door back in is smaller than it looks. Full picture in Friday's wrap."
4. "Harrison's showing up but working harder for it than last week. Worth five minutes tonight: 'linear equations' — get him to talk you through one. Friday's wrap will show where it landed."

Output ONLY the SMS text. No quotes, no preamble, no markdown."""


def compose_ai(card, api_key, model=DEFAULT_MODEL):
    """One attempt; caller validates and falls back. Returns text or None."""
    user = ("Write the Wednesday check-in for this fact card:\n\n"
            + json.dumps(card, ensure_ascii=False, indent=1))
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


def render(card, api_key=None, use_ai=True, model=DEFAULT_MODEL):
    """(text, source) — AI if it validates, else the approved fallback.
    The fallback MUST validate; that is asserted, not hoped."""
    name = card["name"]
    if use_ai and api_key:
        text = compose_ai(card, api_key, model)
        if text:
            ok, why = validate(text, name)
            if ok:
                return text, "ai"
            fail = why
        else:
            fail = "api-error"
    else:
        fail = "ai-off"
    text = fallback_render(card)
    ok, why = validate(text, name)
    if not ok:                                          # pragma: no cover
        raise AssertionError(f"fallback failed its own law: {why}")
    return text, f"fallback({fail})"


# --------------------------------------------------------------------------- #

def plan_cards(state, runs, cursor, asof, students):
    """Pure: which kids get a card this Wednesday. Codes-only log lines."""
    this_d, prev_d = week_windows(asof)
    sent = cursor.get("sent", {})
    cards, log = [], []
    for s in students:
        if asof.isoformat() in sent.get(s, []):
            log.append(f"[{s}] already sent for {asof.isoformat()} — no-op.")
            continue
        topics = (state.get("students", {}).get(s, {}) or {}).get("topics", []) or []
        now = window_stats(runs, s, this_d)
        prev = window_stats(runs, s, prev_d)
        card = fact_card(s, name_for(runs, s), now, prev, topics)
        m = card["momentum"]
        log.append(f"[{s}] card built (word={m['word']}, dir={m['direction']}, "
                   f"ask={'y' if card['ask'] else 'n'}, gap={'y' if card['gap'] else 'n'}).")
        cards.append(card)
    return cards, log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--date", default=None, help="Override Sydney date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="plan only — no send, no cursor write")
    ap.add_argument("--no-ai", action="store_true", help="fallback voices only")
    a = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import notify
    import roster

    asof = date.fromisoformat(a.date) if a.date else sydney_today()
    priv = a.private_dir

    # Refresh runs.json (same gating as the soundbyte: skip offline).
    if os.environ.get("RESULTS_URL") and os.environ.get("RESULTS_KEY"):
        try:
            import ingest_results
            summary, errs = ingest_results.ingest(
                priv, os.environ["RESULTS_URL"], os.environ["RESULTS_KEY"])
            print(f"ingest: {summary}")
            for e in errs:
                print(f"  ⚠ {e}")
        except BaseException as e:
            print(f"⚠ ingest failed ({type(e).__name__}) — using committed runs.json.")
    else:
        print("ingest skipped (no RESULTS_URL/KEY) — using committed runs.json.")

    state = json.load(open(os.path.join(priv, "work", "state.json")))
    runs = json.load(open(os.path.join(priv, "work", "runs.json"))).get("runs", [])
    cpath = os.path.join(priv, CURSOR_FILE)
    cursor = json.load(open(cpath)) if os.path.exists(cpath) else {"sent": {}}

    cards, log = plan_cards(state, runs, cursor, asof, roster.active())
    for line in log:
        print(line)
    if not cards:
        print("nothing to send.")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if a.dry_run:
        for c in cards:
            _, src = render(c, api_key, use_ai=not a.no_ai)
            print(f"[{c['code']}] DRY-RUN — rendered via {src}; send + cursor suppressed.")
        return

    advanced, failed = 0, []
    for c in cards:
        text, src = render(c, api_key, use_ai=not a.no_ai)
        ok, detail = notify.send_sms(f"parents:{c['code']}", text,
                                     ref=f"xpd-wed-{c['code']}-{asof.isoformat()}",
                                     dry_run=False)
        if ok:
            cursor.setdefault("sent", {}).setdefault(c["code"], []).append(asof.isoformat())
            advanced += 1
            print(f"[{c['code']}] check-in sent ✓ (via {src.split('(')[0]})")
        else:
            failed.append((c["code"], detail))
            print(f"[{c['code']}] ⚠ send FAILED — will retry on redispatch.")
    if advanced:
        with open(cpath, "w") as fh:
            json.dump(cursor, fh, indent=1)
            fh.write("\n")
        print(f"cursor advanced for {advanced} kid(s).")
    if failed:
        with open(os.path.join(priv, ERROR_FILE), "w") as fh:
            for code, detail in failed:
                fh.write(f"{asof.isoformat()} {code}: {detail}\n")
        print("failure detail in private work/wed_checkin_last_error.txt")


if __name__ == "__main__":
    main()
