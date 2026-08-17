#!/usr/bin/env python3
"""
review.py — the SECOND-PASS review gate (roadmap #1).

The validator (validate.py) is a mechanical checker: schema present, the keyed
answer is one of the options, no duplicate ids/prompts vs history. It CANNOT tell
that a *distractor is also true*, that a stated fact is wrong, that a question is
off-syllabus, or that it's trivially easy. That is precisely the class of fault
that reaches a child unless a human reads every set — the gap that keeps this
system from running hands-off.

This closes that gap. It is a CRITIC, not an editor: it reads each composed
question with a stronger model and returns a per-slot verdict (clean / flag +
severity + category + one-line note). It never rewrites — recomposing a flagged
slot is the orchestrator's job (run_daily), which rebuilds only the flagged
slots and re-reviews, then publishes or HOLDS.

Why a different (stronger) model than compose: catching "two defensible answers"
is a judgement task, exactly where the bigger model earns its cost — and verify
is a smaller job than generate, so a strong critic over a cheap writer beats a
strong writer with no critic, for less money. Model is overridable
(DAILYXP_REVIEW_MODEL / --model) — treat the default as a tunable, and let the
nightly flag-rate tell you whether the cheap writer is good enough.

Needs ANTHROPIC_API_KEY. Zero third-party deps (urllib), same as compose.

Usage:
  ANTHROPIC_API_KEY=... python3 tools/review.py work/set.json \
      [--targets ../DailyXP-private/targets/2026-08-03.json] [--model claude-opus-4-8]
  from review import review_set  ->  (verdict_dict, error | None)
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error

API_URL = "https://api.anthropic.com/v1/messages"
# A STRONGER model than compose on purpose — the review is a judgement task.
DEFAULT_MODEL = os.environ.get("DAILYXP_REVIEW_MODEL", "claude-opus-4-8")
MAX_TOKENS = 8000
REVIEW_EFFORT = os.environ.get("DAILYXP_REVIEW_EFFORT", "high")  # judgement task — reason hard

CATEGORIES = ["multiple_answers", "factual_error", "off_syllabus", "trivial", "ambiguous", "length_tell"]

SYSTEM = """You are the QUALITY GATE for a nightly spaced-repetition quiz used by two secondary-school boys.
The questions were written by another model and have ALREADY passed a mechanical validator (schema is correct,
the keyed answer is one of the options, nothing duplicates a past question). Your job is the thing that validator
CANNOT do: read each question as a sharp teacher and catch faults of MEANING.

You are a critic, NOT an editor. You do not rewrite. You do not voice style or wording preferences. You flag only
genuine faults, in exactly these categories:

- "multiple_answers": more than one option is defensibly correct, so a knowledgeable student could pick a
  non-keyed option and be right. This is the most important and most common fault. Check EVERY option against the
  question — not just the keyed one. (Real miss this gate exists to catch: a question asked for "the controlled
  variable" and keyed one option, when a second option was ALSO a controlled variable.)
- "factual_error": something stated in the prompt, the keyed answer, or the `why` is factually wrong — including a
  `why` that teaches a false rule even when the keyed answer happens to be right.
- "off_syllabus": the question tests material the student is NOT studying at all — genuinely beyond their level or
  outside their curriculum. Use the curriculum context provided. IMPORTANT: this is a spaced-repetition tool, so it
  deliberately resurfaces earlier topics for revision — a question on a topic listed under `revision_topics` (or any
  reasonable prior-term revision) is ON-syllabus and must NOT be flagged. Off_syllabus means material that is on
  NEITHER the live list NOR a plausible revision of past study. If no context is provided, do NOT assess this category.
- "trivial": the question gives its own answer away, or is so easy it tests nothing.
- "ambiguous": the wording is genuinely unclear, or the correct answer depends on an unstated assumption.

Severity:
- "block" — MUST NOT go live as written. Use for: any multiple_answers, any factual_error, and clear off_syllabus.
  (A student would be marked wrong for a right answer, or taught something false.)
- "warn" — publishable, but worth a human glance. Mild issues: slightly too easy, a small ambiguity a careful
  student would resolve, a `why` that is thin but not wrong.

Be conservative. When a question is sound, mark it clean — do not invent faults to look thorough. When genuinely
unsure whether something rises to a fault, use "warn", not "block": a false block costs a child their quiz, so
reserve "block" for faults you can name concretely.

Teach-back slots have a prompt but no options or answer (understanding is graded, not recall). For these,
"multiple_answers" and "trivial" do NOT apply — judge only factual soundness and clarity.

Some sets are REVERSED format (the set tag contains "REVERSED"): the prompt states an answer and the options are
candidate QUESTIONS — the keyed option is the question that answer belongs to. Judge with the same categories,
mapped: "multiple_answers" = the stated answer ALSO genuinely answers a non-keyed candidate question (check every
candidate); "factual_error" = the stated fact is wrong, OR the keyed question is not actually answered by it, OR
the `why` mis-states a distractor's true answer; "trivial" = the three distractor questions are so unrelated the
match gives itself away. The reversed format itself is deliberate — never flag it as "ambiguous".

Some sets are BATTLEGROUND format (the Friday Battleground): each steady slot is one claimable zone on a weak topic, and
the format VARIES per zone — spot-the-lie (which statement is FALSE), true/false, plain multiple choice, or a sum shown
with four answer options. Judge each on its own format with the same categories. For spot-the-lie, verify ALL FOUR
statements yourself: "multiple_answers" = a second statement is also false OR the keyed one is actually true; "factual_error"
= the keyed statement is true / the `why` mis-explains. For true/false and sums, "factual_error" = the keyed answer is
wrong or the `why` is wrong; "multiple_answers" = a distractor is also defensibly correct. "trivial" = the answer is an
obvious giveaway rather than a real misconception. The varied formats are deliberate — never flag a format itself as
"ambiguous"; only flag genuine wording ambiguity.

Output ONLY a JSON object, no prose, no markdown fences. Exactly one entry per slotId given, and no others:
{ "<slotId>": {"verdict":"clean"|"flag","severity":"block"|"warn","categories":[...],"note":"one concrete sentence, empty if clean"} }
For a clean question use: {"verdict":"clean","severity":"","categories":[],"note":""}."""


def curriculum_context(targets, student):
    """Compact 'what's live for this boy' context so the reviewer can judge off-syllabus.
    Returns None if targets is missing — the reviewer then skips the off_syllabus check."""
    if not targets:
        return None
    st = targets.get("students", {}).get(student, {})
    live, revision, formats = [], [], {}
    for subj, block in st.get("subjects", {}).items():
        fmt = block.get("assessment_format")
        if fmt:
            formats[subj] = fmt
        for t in block.get("topics", []):
            status = t.get("status")
            row = {"subject": subj, "topic": t["topic"], "status": status}
            if status in ("live", "upcoming", "not_yet_posted"):
                live.append(row)
            elif status == "prior_term":
                revision.append(row)   # legitimately resurfaced by the scheduler — NOT off-syllabus
    return {"student": student, "live_topics": live, "revision_topics": revision,
            "assessment_formats": formats}


def build_user(cset, curriculum):
    qs = []
    for q in cset.get("questions", []):
        row = {"slotId": q["id"], "phase": q["phase"], "subject": q["subject"], "prompt": q["prompt"]}
        if q.get("options"):
            row["options"] = q["options"]
            row["answer"] = q.get("answer")
            row["why"] = q.get("why", "")
        qs.append(row)
    payload = {
        "for": f"{cset.get('student')} {cset.get('tag')} ({cset.get('day')} {cset.get('date')})",
        "curriculum_context": curriculum if curriculum else "none provided — do not assess off_syllabus",
        "questions": qs,
    }
    return ("Review every question below. Output only the JSON verdict object described — one entry per slotId.\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2))


def call_api(system, user, model, api_key, thinking=True):
    msg = {
        "model": model, "max_tokens": MAX_TOKENS, "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if thinking:
        # adaptive thinking + high effort — the correct control for the current Opus tier;
        # this is what makes the reviewer actually WORK THE REASONING (e.g. recompute a `why`)
        msg["thinking"] = {"type": "adaptive"}
        msg["output_config"] = {"effort": REVIEW_EFFORT}
    body = json.dumps(msg).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode())
    # text blocks only — thinking blocks (type 'thinking') are intentionally dropped
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def parse_json(text):
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    a, b = t.find("{"), t.rfind("}")
    if a != -1 and b != -1:
        t = t[a:b + 1]
    return json.loads(t)


def normalise(raw_verdicts, cset):
    """Normalise the model's per-slot verdicts and compute the set-level outcome.
    Fail-safe: a slot the model forgot to rule on is treated as a WARN, never silently clean."""
    slots = [q["id"] for q in cset.get("questions", [])]
    flags, warns, clean = {}, {}, []
    for sid in slots:
        v = raw_verdicts.get(sid) or {}
        verdict = v.get("verdict", "flag")
        cats = [c for c in (v.get("categories") or []) if c in CATEGORIES]
        note = (v.get("note") or "").strip()
        sev = v.get("severity", "")
        if sid not in raw_verdicts:
            warns[sid] = {"severity": "warn", "categories": ["ambiguous"],
                          "note": "reviewer returned no verdict for this slot — held as warn"}
        elif verdict == "clean":
            clean.append(sid)
        elif sev == "block":
            flags[sid] = {"severity": "block", "categories": cats or ["ambiguous"], "note": note}
        else:  # any non-clean, non-block verdict → warn
            warns[sid] = {"severity": "warn", "categories": cats, "note": note}

    # --- deterministic answer-length gate (SEASONS.md LAW 1) ------------------
    # The LLM cannot self-police the length tell, so it is enforced here in code,
    # AFTER the model verdict and independent of it. A per-slot sole-longest
    # violation is promoted to BLOCK (forces recompose); a whole-run distribution
    # skew (correct answer piling on length-rank 1) blocks the set as well.
    try:
        import answer_length as _al
        _a = _al.audit(cset.get("questions", []))
        for sid in _a["slot_violations"]:
            existing = flags.get(sid, {})
            cats = sorted(set(existing.get("categories", []) + ["length_tell"]))
            flags[sid] = {"severity": "block", "categories": cats,
                          "note": _al.guidance_note(
                              next(q for q in cset["questions"] if q.get("id") == sid))}
            clean = [c for c in clean if c != sid]
            warns.pop(sid, None)
        _run_len_flag = None
        if _a["run_distribution_violation"]:
            _run_len_flag = (f"answer-length distribution: correct answer is the longest "
                             f"in {_a['longest_count']}/{_a['mc_total']} slots "
                             f"({int(_a['longest_share']*100)}%); target ~25%. "
                             f"Recompose the flagged slots so the length-rank spreads.")
    except Exception as _e:
        _run_len_flag = f"answer-length gate error (non-blocking): {_e}"
        _a = None

    return {
        "ok": len(flags) == 0,          # publishable when nothing is BLOCK (warns don't block)
        "blocking": sorted(flags),
        "flags": flags,                 # block-level, per slot
        "warns": warns,                 # advisory, per slot
        "clean": clean,
        "model": None,                  # filled by review_set
        "length_audit": _a,             # full LAW-1 audit for logging/metric
        "length_run_flag": _run_len_flag,
    }


def review_set(cset, curriculum=None, model=DEFAULT_MODEL, api_key=None, max_retries=2):
    """Returns (verdict_dict, error | None). verdict_dict.ok is False iff any slot is BLOCK.
    Placeholder / empty sets are trivially clean (nothing to review)."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, "ANTHROPIC_API_KEY not set"
    if cset.get("status") == "placeholder" or not cset.get("questions"):
        return {"ok": True, "blocking": [], "flags": {}, "warns": {}, "clean": [], "model": None,
                "length_audit": None, "length_run_flag": None,
                "skipped": "placeholder/empty — nothing to review"}, None

    user = build_user(cset, curriculum)
    thinking = True
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            raw = call_api(SYSTEM, user, model, api_key, thinking=thinking)
            verdicts = parse_json(raw)
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:200]
            # some deployments reject the thinking param — degrade once, then keep retrying
            if thinking and ("thinking" in detail.lower() or e.code == 400):
                thinking = False
                last_err = f"HTTP {e.code} (retrying without thinking): {detail}"
                continue
            return None, f"review API HTTP {e.code}: {detail}"
        except Exception as e:
            last_err = f"review parse error: {e}"
            user += f"\n\nYour previous reply could not be parsed as the required JSON object ({e}). Reply with ONLY the JSON verdict object."
            continue
        out = normalise(verdicts, cset)
        out["model"] = model
        return out, None
    return None, last_err or "review failed"


def print_verdict(v):
    if v.get("skipped"):
        print(f"REVIEW — skipped ({v['skipped']})")
        return
    n_clean, n_warn, n_block = len(v["clean"]), len(v["warns"]), len(v["flags"])
    verdict = "PASS" if v["ok"] else "HOLD"
    print(f"REVIEW [{v.get('model')}] — {verdict}: {n_clean} clean, {n_warn} warn, {n_block} block")
    for sid, f in v["flags"].items():
        print(f"  ⛔ {sid}  [{','.join(f['categories'])}]  {f['note']}")
    for sid, w in v["warns"].items():
        print(f"  ⚠  {sid}  [{','.join(w['categories'])}]  {w['note']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("set_path")
    ap.add_argument("--targets", default=None, help="a targets/<week>.json for the off-syllabus check")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args()
    cset = json.load(open(a.set_path))
    curric = None
    if a.targets:
        curric = curriculum_context(json.load(open(a.targets)), cset.get("student"))
    v, err = review_set(cset, curriculum=curric, model=a.model)
    if err:
        print(f"REVIEW ERROR: {err}")
        sys.exit(2)
    print_verdict(v)
    sys.exit(0 if v["ok"] else 1)


if __name__ == "__main__":
    main()
