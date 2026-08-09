#!/usr/bin/env python3
"""
wed_checkin.py — the Wednesday midweek check-in (REPORTING.md touchpoint 2:
ACTIVATE + expectation-setter), MERGED with Wednesday's soundbyte.

Runs Wednesday EVENING (wed-checkin.yml: polls 6:25pm + 8:25pm Sydney, five
minutes ahead of the soundbyte polls). One SMS per kid to that kid's parent
seat. Two shapes:

  MERGED (tonight's run is in): the soundbyte's three beats on top (did it +
  XP + verdict — rendered by soundbyte.py's own proven machinery), then the
  check-in body: honest momentum (Mon–Wed vs LAST week's Mon–Wed), at most
  ONE ask or five-minute action, always ending pointed at Friday's wrap.
  Marks BOTH cursors so the evening-soundbyte job no-ops for this kid.

  CUTOFF (8:25pm, tonight's run not in): the check-in cannot go silent — a
  scheduled weekly touchpoint that silently vanishes is louder and more
  alarming than a neutral line. Body carries the Mon–Tue read (like for
  like: Mon–Tue vs last Mon–Tue) plus the tonight-status law: STATUS PLUS
  OPEN DOOR, NEVER JUDGMENT — "tonight's run isn't in yet — if it lands
  later this evening, the usual text will follow" (the 9:30 soundbyte poll
  keeps that promise). Only when the set was actually PUBLISHED today: our
  gaps are never reported as the kid's (fail-soft: can't verify -> no note).

Design laws:
  * CODE DECIDES, LANGUAGE DRESSES. The deterministic layer picks every
    fact (week-word, direction, attendance, tonight-status, ask topic, gap
    topic). The model dresses the check-in BODY only; the soundbyte line is
    deterministic and law-proven by its own module. If the API fails or the
    body fails validation, the redlined fallback voices send — the
    Wednesday never goes silent or off-law over an API blip.
  * HONEST MOMENTUM, UNDRAMATIC. Up is said, flat is said, down is said —
    "a bit behind last week", never bare "behind", never accusatory. QUIET
    OUTRANKS SLOWER: thin evidence never gets a comprehension judgement.
  * ONE WEEK-WORD ENGINE, LIKE FOR LIKE. momentum() is the thresholds
    Friday samples on the full week; the window is Mon..today-with-run
    (3 days merged, 2 days at cutoff) against the SAME days last week.
  * NO NUMBERS IN THE BODY. The validator rejects digits, %, and slashes
    in the check-in body. The soundbyte line above it carries XP under its
    own law. Ledger topic names pass display_topic() so raw names
    ("Triangle area (½bh) / area recall") never leak.
  * GAPS ARRIVE DRESSED AS HELP, planted for Friday ("it's the one
    Friday's wrap will centre on"). Difficulty belongs to the set.
  * PUBLIC-LOG HYGIENE. Actions logs print codes + safe statuses only.
    Failure detail lands PRIVATE (work/wed_checkin_last_error.txt).
  * IDEMPOTENT + COORDINATED. Own cursor work/wed_checkin_cursor.json; a
    merged send also advances the SOUNDBYTE cursor (both jobs share the
    daily-quiz concurrency group, so there is no race). Send before
    advance; failures retry next poll.
  * THE LEDGER IS NOT TOUCHED. Reads state.json + runs.json; writes only
    cursors.

TODO (blocked on sweep support): assessment radar — one clause when a dated
assessment is inside a fortnight. Needs structured dates in targets/.

Usage:
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private --dry-run
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private --date 2026-08-05 --force-cutoff
  python3 tools/wed_checkin.py --private-dir ../DailyXP-private --no-ai
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, time as dtime, timedelta

try:
    from zoneinfo import ZoneInfo
except ImportError:                                    # pragma: no cover
    ZoneInfo = None

CURSOR_FILE = os.path.join("work", "wed_checkin_cursor.json")
ERROR_FILE = os.path.join("work", "wed_checkin_last_error.txt")

COMP_DELTA = 0.12          # week-word engine threshold (Friday uses the same)
MAX_LEN = 460              # body budget (the soundbyte line rides above it)
MIN_LEN = 40
CUTOFF = dtime(20, 15)     # Sydney: at/after this, a missing run gets the status line

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"   # house model for language tasks (see compose.py)
MAX_TOKENS = 300

LIVE_SET_URL = "https://raw.githubusercontent.com/Rich898/DailyXP-content/main/{code}.json"


# --------------------------------------------------------------------------- #
# Pure logic (everything above main() is testable without network or files)

def sydney_now():
    if ZoneInfo is None:
        return datetime.now()
    return datetime.now(ZoneInfo("Australia/Sydney"))


def is_cutoff(now_dt):
    """Past the evening cutoff? (The 8:25pm poll lands here; 6:25 doesn't.)"""
    return now_dt.time() >= CUTOFF


def week_windows(asof, include_today):
    """Like-for-like windows: Mon..Tue (+Wed when tonight's run is in),
    against the SAME days last week."""
    n = 3 if include_today else 2
    mon = asof - timedelta(days=asof.weekday())
    this = [(mon + timedelta(days=i)).isoformat() for i in range(n)]
    prev = [(mon - timedelta(days=7) + timedelta(days=i)).isoformat() for i in range(n)]
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
        return "no runs in yet this week"
    if now["days_done"] >= now["possible"]:
        return "kept every day so far" if now["possible"] > 2 else "kept both days so far"
    if now["days_done"] == 1:
        return "one run in so far"
    return "two runs in so far"


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


def fact_card(code, name, now, prev, topics, tonight):
    """tonight: 'in' | 'not-in-yet' | 'unverified' (set not confirmed
    published — our gap, never noted to the parent)."""
    m = momentum(now, prev)
    return {
        "code": code, "name": name,
        "momentum": {"word": m["word"], "direction": m["direction"],
                     "attendance": attendance_phrase(now)},
        "tonight": tonight,
        "ask": _slim(pick_ask(topics)),
        "gap": _slim(pick_gap(topics)),
    }


# ---- outgoing-text law (deterministic; the check-in BODY, AI and fallback) - #

def validate(text, name):
    """(ok, reason). Every outgoing check-in body must pass this."""
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

TONIGHT_NOTE = ("tonight's run isn't in yet — if it lands later this "
                "evening, the usual text will follow.")


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
    note = f" And {TONIGHT_NOTE}" if card.get("tonight") == "not-in-yet" else ""
    if word == "quiet":
        opener = (f"{name}'s a bit behind last week — happens."
                  if direction == "down" else
                  f"Quiet week for {name} so far — happens.")
        return (opener + note + " If tonight allows, sit with him for the "
                "first two questions when the quiz lands; the door back in "
                "is smaller than it looks. Full picture in Friday's wrap.")
    if word == "slower":
        body = _gap_bit(card, plant=False) or (" Worth five minutes tonight: "
                                               "sit in on the first couple of "
                                               "questions with him.")
        return (f"{name}'s showing up but working harder for it than last "
                f"week.{note}{body} Friday's wrap will show where it landed.")
    if word == "strong":
        line = f"Midweek read: {name}'s {att} and it's building on last week.{note}"
        extra = _ask_bit(card) or _gap_bit(card)
        return line + extra + " Friday's wrap should be a good one."
    # solid — flat or no-prior
    opener = (f"Midweek read: steady week for {name}, {att}, tracking level "
              f"with last week.{note}"
              if direction == "flat" else
              f"Midweek read: steady week for {name} so far — {att}.{note}")
    extra = _gap_bit(card) or _ask_bit(card)
    closer = "" if "Friday" in extra else " More in Friday's wrap."
    return opener + extra + closer


# ---- the AI dresser (BODY only; the soundbyte line is deterministic) ------- #

SYSTEM = """You turn ONE fact card into the BODY of an SMS from XP Daily to a parent, in the product's redlined voice. (When tonight's run is in, a separate deterministic result line is prepended by code — never write the result yourself.)

The card is the complete truth: momentum word + direction + attendance phrase, tonight-status, at most one ask (a strength), at most one gap (with colour notes). Use ONLY these facts. Invent nothing — no topics, no events, no results, no claims beyond the card.

HARD RULES (the text is rejected if any is broken):
- No digits anywhere. No percentages. No slashes. Attendance is said in words.
- Never a bare "behind" — only "a bit behind". Never accusatory, never dramatic, never guilt.
- The kid owns effort and wins; difficulty belongs to the set/quiz, never the kid.
- If tonight is "not-in-yet": state it once, neutrally, with the open door — "tonight's run isn't in yet — if it lands later this evening, the usual text will follow." Status plus open door, never judgment. If tonight is "in" or "unverified", do not mention tonight's run at all.
- At most ONE ask and ONE five-minute action, drawn only from the card. Colour notes may inspire the action's wording (e.g. a dinner-table framing) but never add facts.
- Never these words in any form: miss, streak, score, wrong, fail.
- Topic names in the card are display-safe — use them as given (natural lowercase is fine). Never quote ledger names from colour.
- Colour informs HOW to frame the one action — it is never content to report. Never say a topic is locked, maintenance, repair, chronic, or assessed.
- If a gap exists, the five-minute action IS the gap, and the Friday line points at it ("it's the one Friday's wrap will centre on"). If no gap but an ask exists and momentum isn't down, use the ask. Never both an ask and a gap action.
- ALWAYS end by pointing at Friday's wrap — Wednesday sets the expectation Friday resolves.
- One paragraph, under four hundred characters, plain text, no emojis, no sign-off.

Tone anchors (match this register exactly):
1. "Midweek read: Alex's kept every day so far and it's building on last week. Tonight's ask: get him to explain how the Church held power over kings — saying it out loud cements it. Friday's wrap should be a good one."
2. "Midweek read: steady week for Alex, tracking level with last week. One thing worth five minutes: he's still circling 'variables in experiments' — ask him to set dinner up as the experiment: what changes, what gets measured, what stays the same. It's the one Friday's wrap will centre on."
3. "Alex's a bit behind last week — happens. If tonight allows, sit with him for the first two questions when the quiz lands; the door back in is smaller than it looks. Full picture in Friday's wrap."
4. "Midweek read: Alex kept both days so far, and tonight's run isn't in yet — if it lands later this evening, the usual text will follow. One thing worth five minutes when he's back: 'linear equations' — get him to talk you through one. It's the one Friday's wrap will centre on."

Output ONLY the SMS body. No quotes, no preamble, no markdown."""


def compose_ai(card, api_key, model=DEFAULT_MODEL):
    """One attempt; caller validates and falls back. Returns text or None."""
    user = ("Write the Wednesday check-in body for this fact card:\n\n"
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


def render_body(card, api_key=None, use_ai=True, model=DEFAULT_MODEL):
    """(body, source) — AI if it validates, else the approved fallback.
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

def plan(state, runs, ck_cursor, sb_cursor, asof, students, cutoff):
    """Pure: what each kid gets at this poll. Codes-only log lines.
    Returns (jobs, log); each job: {code, card, sb_facts|None, mark_sb}.
      - run in tonight  -> MERGED (sb line + body) unless soundbyte already
        sent (then body-only, momentum still includes tonight).
      - no run, cutoff  -> body with the tonight-status (card['tonight']
        already resolved by the caller: not-in-yet vs unverified).
      - no run, early   -> silent no-op (a later poll decides).
    """
    from soundbyte import facts_for as sb_facts_for
    sent_ck = ck_cursor.get("sent", {})
    sent_sb = sb_cursor.get("sent", {})
    a_iso = asof.isoformat()
    jobs, log = [], []
    for s in students:
        if a_iso in sent_ck.get(s, []):
            log.append(f"[{s}] check-in already sent for {a_iso} — no-op.")
            continue
        topics = (state.get("students", {}).get(s, {}) or {}).get("topics", []) or []
        run_in = any(r.get("student") == s and r.get("run_date") == a_iso for r in runs)
        if not run_in and not cutoff:
            log.append(f"[{s}] no run yet, before cutoff — waiting.")
            continue
        tonight = "in" if run_in else None      # caller resolved not-in vs unverified
        this_d, prev_d = week_windows(asof, include_today=run_in)
        card = fact_card(s, name_for(runs, s),
                         window_stats(runs, s, this_d),
                         window_stats(runs, s, prev_d), topics, tonight)
        sbf, mark_sb = None, False
        if run_in and a_iso not in sent_sb.get(s, []):
            sbf = sb_facts_for(runs, s, a_iso)
            mark_sb = True
        m = card["momentum"]
        shape = "merged" if sbf else ("body-only" if run_in else "cutoff")
        log.append(f"[{s}] {shape} (word={m['word']}, dir={m['direction']}, "
                   f"ask={'y' if card['ask'] else 'n'}, gap={'y' if card['gap'] else 'n'}).")
        jobs.append({"code": s, "card": card, "sb_facts": sbf, "mark_sb": mark_sb})
    return jobs, log


def set_published_today(code, a_iso, timeout=10):
    """Was today's set actually live? Fail-soft: any doubt -> False, and the
    parent never hears about OUR gap."""
    try:
        with urllib.request.urlopen(LIVE_SET_URL.format(code=code), timeout=timeout) as r:
            d = json.load(r)
        return d.get("date") == a_iso
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--date", default=None, help="Override Sydney date (YYYY-MM-DD)")
    ap.add_argument("--dry-run", action="store_true", help="plan + render only — no send, no cursor writes")
    ap.add_argument("--no-ai", action="store_true", help="fallback voices only")
    ap.add_argument("--force-cutoff", action="store_true", help="treat this poll as the cutoff")
    a = ap.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import notify
    import roster
    import soundbyte as sb

    now = sydney_now()
    asof = date.fromisoformat(a.date) if a.date else now.date()
    a_iso = asof.isoformat()
    cutoff = a.force_cutoff or is_cutoff(now)
    priv = a.private_dir

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
    ck_path = os.path.join(priv, CURSOR_FILE)
    sb_path = os.path.join(priv, sb.CURSOR_FILE)
    ck_cursor = json.load(open(ck_path)) if os.path.exists(ck_path) else {"sent": {}}
    sb_cursor = json.load(open(sb_path)) if os.path.exists(sb_path) else {"sent": {}}

    print(f"poll: {a_iso} cutoff={'yes' if cutoff else 'no'}")
    jobs, log = plan(state, runs, ck_cursor, sb_cursor, asof, roster.active(), cutoff)
    for line in log:
        print(line)
    if not jobs:
        print("nothing to send.")
        return

    # Resolve tonight-status for cutoff jobs: not-in-yet only if the set was
    # verifiably published today; otherwise 'unverified' (never mentioned).
    for j in jobs:
        if j["card"]["tonight"] is None:
            pub = set_published_today(j["code"], a_iso)
            j["card"]["tonight"] = "not-in-yet" if pub else "unverified"
            print(f"[{j['code']}] tonight-status resolved: "
                  f"{'published, not in yet' if pub else 'set unverified — status line withheld'}.")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if a.dry_run:
        for j in jobs:
            _, src = render_body(j["card"], api_key, use_ai=not a.no_ai)
            shape = "merged" if j["sb_facts"] else "body"
            print(f"[{j['code']}] DRY-RUN — {shape} rendered via {src}; send + cursors suppressed.")
        return

    advanced, sb_advanced, failed = 0, 0, []
    for j in jobs:
        body, src = render_body(j["card"], api_key, use_ai=not a.no_ai)
        if j["sb_facts"]:
            text = sb.render_line(j["sb_facts"], a_iso) + "\n" + body
        else:
            text = body
        ok, detail = notify.send_sms(f"parents:{j['code']}", text,
                                     ref=f"xpd-wed-{j['code']}-{a_iso}", dry_run=False)
        if ok:
            ck_cursor.setdefault("sent", {}).setdefault(j["code"], []).append(a_iso)
            advanced += 1
            if j["mark_sb"]:
                sb_cursor.setdefault("sent", {}).setdefault(j["code"], []).append(a_iso)
                sb_advanced += 1
            print(f"[{j['code']}] check-in sent ✓ ({'merged' if j['sb_facts'] else 'body'}, via {src.split('(')[0]})")
        else:
            failed.append((j["code"], detail))
            print(f"[{j['code']}] ⚠ send FAILED — will retry next poll.")
    if advanced:
        with open(ck_path, "w") as fh:
            json.dump(ck_cursor, fh, indent=1)
            fh.write("\n")
    if sb_advanced:
        with open(sb_path, "w") as fh:
            json.dump(sb_cursor, fh, indent=1)
            fh.write("\n")
    if advanced:
        print(f"cursors advanced (check-in {advanced}, soundbyte {sb_advanced}).")
    if failed:
        with open(os.path.join(priv, ERROR_FILE), "w") as fh:
            for code, detail in failed:
                fh.write(f"{a_iso} {code}: {detail}\n")
        print("failure detail in private work/wed_checkin_last_error.txt")


if __name__ == "__main__":
    main()
