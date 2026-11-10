#!/usr/bin/env python3
"""revision_topup.py — author each boy's Part-2 "top-up" for the exam-week
revision tool, autonomously, from GitHub Actions.

WHY THIS EXISTS
---------------
The revision tool (separate from the main DailyXP pipeline) runs two phases on
one Netlify bookmark per boy each day:

  Part 1  balanced ~30-min exam practice   (served from Supabase `revision_quiz`)
     |    boy finishes -> the page POSTs a run into `revision_runs` (part=1)
  Part 2  a custom "top-up" authored from EXACTLY what he got wrong
          (re-teach the THEME, then re-test with NEW, similar-but-different
           questions), served from Supabase `revision_reteach`.

Part 2 is the only piece that needs an AI write to the database between the two
phases. It used to depend on an unattended Claude *session* firing a trigger and
completing a privileged DB write — which failed whenever that session was down
or its DB write needed a human approval that wasn't there. This script removes
that dependency: a plain GitHub Actions cron reads the run with the Supabase
service key, authors the top-up with the Claude API, and writes it back. No
session, no human in the loop.

WHAT IT DOES (idempotent; safe to run every few minutes)
  For each ACTIVE row in `revision_quiz`:
    1. find the most recent Part-1 run for that student+day in `revision_runs`
    2. if none yet -> skip (he hasn't finished Part 1 today)
    3. if a `revision_reteach` row for (student, day) is already status='ready'
       and built from this exact run (source_ts match) -> skip (already done)
    4. otherwise: collect what he got wrong, ask Claude for a theme-based
       re-teach + NEW practice (never the exact wrong questions), and UPSERT it
       into `revision_reteach` with status='ready'.

ENV (all already present as GitHub Actions secrets for this repo):
  SUPABASE_URL           https://<ref>.supabase.co
  SUPABASE_SERVICE_KEY   sb_secret_* service role key (apikey header; no Bearer)
  ANTHROPIC_API_KEY      for the authoring call
  REVISION_TOPUP_MODEL   (optional) override model id (default below)

Zero third-party deps — stdlib urllib only, same as tools/compose.py.

Public-repo hygiene: logs print the student KEY and counts only, never a
question, answer, or re-teach body. (The keys already appear across the repo's
docs; the content never leaves Supabase.)
"""

import json
import os
import sys
import time
import urllib.request
import urllib.parse
import urllib.error

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = os.environ.get("REVISION_TOPUP_MODEL", "claude-sonnet-5")
ANTHROPIC_VERSION = "2023-06-01"
MAX_TOKENS = 8000
RUN_LOOKBACK = 25          # recent runs to scan per student+day for the Part-1 run
HTTP_TIMEOUT = 60


# ----------------------------------------------------------------------------
# Supabase REST (service key -> role from the apikey header; never Bearer)
# ----------------------------------------------------------------------------
def _sb_request(method, path, key, body=None, extra_headers=None):
    url = f"{SB_URL.rstrip('/')}/rest/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"apikey": key, "User-Agent": "dailyxp-revision-topup/1"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else None


def sb_get(path, key):
    return _sb_request("GET", path, key)


def sb_upsert(table, row, key):
    """UPSERT on the table's unique constraint (student, day)."""
    return _sb_request(
        "POST", table, key, body=[row],
        extra_headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
    )


# ----------------------------------------------------------------------------
# Anthropic (x-api-key, same shape as tools/compose.py)
# ----------------------------------------------------------------------------
def claude(system, user, api_key, model=DEFAULT_MODEL, retries=1):
    payload = {
        "model": model,
        "max_tokens": MAX_TOKENS,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(
                ANTHROPIC_URL, data=json.dumps(payload).encode(),
                headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT * 2) as resp:
                out = json.loads(resp.read().decode())
            parts = [b.get("text", "") for b in out.get("content", [])
                     if b.get("type") == "text"]
            return "".join(parts)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        if attempt < retries:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Anthropic call failed: {last}")


# ----------------------------------------------------------------------------
# Core
# ----------------------------------------------------------------------------
def latest_part1_run(student, day, key):
    """Most recent Part-1 run for this student+day, or None."""
    q = urllib.parse.urlencode({
        "select": "received_at,payload",
        "student": f"eq.{student}",
        "day": f"eq.{day}",
        "order": "received_at.desc",
        "limit": str(RUN_LOOKBACK),
    })
    rows = sb_get(f"revision_runs?{q}", key) or []
    for r in rows:
        p = r.get("payload") or {}
        # part may be int 1 or string "1"
        if str(p.get("part")) == "1":
            return p
    return None


def wrong_items(payload):
    """Distinct (subject, question) the boy got wrong in this run.

    Retries can log the same question twice (false then true); we keep a theme
    as 'missed' if it was EVER wrong this run — that is the thing to re-teach.
    """
    seen, out = set(), []
    for a in payload.get("answers", []):
        if a.get("correct") is True:
            continue
        subj = (a.get("s") or "General").strip()
        q = (a.get("q") or "").strip()
        k = (subj, q)
        if not q or k in seen:
            continue
        seen.add(k)
        out.append({"s": subj, "q": q, "t": a.get("t") or "short"})
    return out


def weak_subjects(payload):
    """Subjects where he dropped at least one mark, strongest-miss last."""
    bs = payload.get("bySubject") or {}
    rows = []
    for subj, v in bs.items():
        c, n = v.get("c", 0), v.get("n", 0)
        if n and c < n:
            rows.append((subj, c, n))
    rows.sort(key=lambda r: (r[1] - r[2]))   # biggest gap first
    return rows


SYSTEM = (
    "You are an expert NSW high-school exam tutor writing a short, warm, "
    "confidence-building 'top-up' revision set for one student, in the week "
    "before end-of-year exams. The student has just finished a practice test; "
    "you are given the exact questions they got WRONG, grouped by subject.\n\n"
    "TEACH BY WORKED EXAMPLE. Per weak theme:\n"
    "  1) a 'teach' card that WORKS THROUGH a clear example of this kind of "
    "problem or idea, step by step — show HOW it is done, do not just define "
    "it. For maths/numeric themes, fully solve one example with FRESH numbers "
    "(different from the question they missed), showing each line of working "
    "on its own line. For written/concept themes, give the key idea plus a "
    "short annotated model of a good answer. 2-5 short lines; light HTML only "
    "(<b>, and <br> to break each working line).\n"
    "  2) then 2 NEW 'now you try' practice cards on that SAME theme, "
    "SCAFFOLDED: the first closely mirrors the worked example, the second a "
    "little harder toward exam level. Use DIFFERENT numbers / examples / "
    "wording — NEVER replay or lightly reword the exact question they missed. "
    "The point is for them to copy the method from the worked example, then "
    "stretch it.\n\n"
    "Pitch it at their year level, encouraging and plain. Cover the weak themes "
    "(aim 4-7 themes); keep the whole set doable in ~25-30 minutes.\n\n"
    "OUTPUT: STRICT JSON ONLY (no prose, no markdown fences). An object:\n"
    '{ "intro": "<=200 chars, warm 1-2 sentence framing of what this top-up '
    'covers and why", "questions": [ ...cards... ] }\n\n'
    "Card schemas (use EXACTLY these keys):\n"
    '  teach:  {"s":"<subject>","t":"teach","title":"<short>","body":"<worked '
    'example, step by step; <b>/<br> ok>"}\n'
    '  mc:     {"s":"<subject>","t":"mc","q":"<new question>","opts":["A","B",'
    '"C","D"],"a":<0-based index of the correct option>,"e":"<1-sentence why>"}\n'
    '  short:  {"s":"<subject>","t":"short","q":"<new question>","keys":'
    '["accepted","keyword","synonyms"],"model":"<one model answer sentence>"}\n\n'
    "Order the cards so each 'teach' worked example is immediately followed by "
    "its own 2 'now you try' cards. Every question must be solvable by copying "
    "the method shown in its teach card. Return ONLY the JSON object."
)


def build_user_prompt(student_label, day, wrongs, weaks):
    lines = [f"Student year-level context: {student_label}.",
             f"Practice set: {day}.", ""]
    if weaks:
        lines.append("Subjects with dropped marks (subject: got/total):")
        for subj, c, n in weaks:
            lines.append(f"  - {subj}: {c}/{n}")
        lines.append("")
    lines.append("Exact questions they got WRONG (for each theme: a step-by-step "
                 "WORKED EXAMPLE, then NEW scaffolded 'now you try' questions):")
    by = {}
    for w in wrongs:
        by.setdefault(w["s"], []).append(w["q"])
    for subj, qs in by.items():
        lines.append(f"[{subj}]")
        for q in qs:
            lines.append(f"  - {q}")
    lines.append("")
    lines.append("Write the top-up JSON now.")
    return "\n".join(lines)


def parse_json_object(text):
    """Pull the first well-formed JSON object out of the model text."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1]
        if t.lstrip().lower().startswith("json"):
            t = t.lstrip()[4:]
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(t[start:end + 1])


VALID_T = {"teach", "mc", "short", "tb"}


def validate_cards(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("questions"), list):
        raise ValueError("missing questions array")
    cards = obj["questions"]
    if not cards:
        raise ValueError("empty questions array")
    for i, c in enumerate(cards):
        if not isinstance(c, dict) or c.get("t") not in VALID_T:
            raise ValueError(f"card {i}: bad type")
        if c["t"] == "teach" and not c.get("body"):
            raise ValueError(f"card {i}: teach has no body")
        if c["t"] == "mc":
            opts = c.get("opts")
            if not isinstance(opts, list) or len(opts) < 2:
                raise ValueError(f"card {i}: mc needs opts")
            if not isinstance(c.get("a"), int) or not (0 <= c["a"] < len(opts)):
                raise ValueError(f"card {i}: mc answer index out of range")
        if c["t"] == "short" and not c.get("q"):
            raise ValueError(f"card {i}: short has no q")
    return cards


def label_for(student):
    # Light year-level hint for pitch; falls back gracefully for new keys.
    return {"roshan": "Year 9 (NSW)", "harrison": "Year 8 (NSW)"}.get(
        student, "NSW high school")


def process(student, day, service_key, api_key, dry_run=False, force=False):
    tag = f"[{student}/{day}]"
    run = latest_part1_run(student, day, service_key)
    if not run:
        print(f"{tag} no Part-1 run yet — skip")
        return "skip-no-run"
    src_ts = run.get("ts")

    existing = sb_get(
        f"revision_reteach?select=status,source_ts&student=eq.{student}"
        f"&day=eq.{day}", service_key) or []
    if existing and not force:
        e = existing[0]
        if e.get("status") == "ready" and src_ts and e.get("source_ts") == src_ts:
            print(f"{tag} already built from this run (source_ts match) — skip")
            return "skip-done"

    wrongs = wrong_items(run)
    weaks = weak_subjects(run)
    print(f"{tag} Part-1 run found: {len(wrongs)} wrong across "
          f"{len(weaks)} weak subject(s)")

    if not wrongs:
        # Nothing wrong — give a light consolidation set so Part 2 still exists.
        print(f"{tag} clean sweep — authoring a light consolidation top-up")

    if dry_run:
        print(f"{tag} DRY-RUN: would author + upsert (no API, no write)")
        return "dry"

    user = build_user_prompt(label_for(student), day, wrongs, weaks)
    text = claude(SYSTEM, user, api_key)
    obj = parse_json_object(text)
    cards = validate_cards(obj)
    intro = (obj.get("intro") or
             "A quick top-up on the few things worth a second look — "
             "learn the idea, then try a couple of fresh ones.")[:280]

    row = {
        "student": student,
        "day": day,
        "status": "ready",
        "intro": intro,
        "questions": cards,
        "source_ts": src_ts,
    }
    sb_upsert("revision_reteach", row, service_key)
    n_teach = sum(1 for c in cards if c["t"] == "teach")
    n_q = len(cards) - n_teach
    print(f"{tag} UPSERT ready: {n_teach} teach + {n_q} practice cards "
          f"(source_ts={src_ts})")
    return "built"


def main(argv):
    global SB_URL
    dry_run = "--dry-run" in argv
    force = "--force" in argv

    SB_URL = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_KEY")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not SB_URL or not service_key:
        print("FATAL: SUPABASE_URL / SUPABASE_SERVICE_KEY not set", file=sys.stderr)
        return 2
    if not api_key and not dry_run:
        print("FATAL: ANTHROPIC_API_KEY not set", file=sys.stderr)
        return 2

    active = sb_get(
        "revision_quiz?select=student,day&active=eq.true&order=student.asc",
        service_key) or []
    if not active:
        print("no active revision_quiz rows — nothing to do")
        return 0
    print(f"active roster: {len(active)} student(s)")

    results, failures = {}, 0
    for row in active:
        student, day = row.get("student"), row.get("day")
        if not student or not day:
            continue
        try:
            results[student] = process(student, day, service_key, api_key,
                                       dry_run=dry_run, force=force)
        except Exception as e:  # noqa: BLE001 — one boy's failure must not block the other
            failures += 1
            results[student] = f"ERROR: {e}"
            print(f"[{student}/{day}] ERROR: {e}", file=sys.stderr)

    print("summary:", json.dumps(results))
    # Non-zero only if every active student failed, so a transient single-boy
    # API blip still lets the other boy's top-up land and the run reads green
    # for partial success.
    return 1 if active and failures == len(active) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
