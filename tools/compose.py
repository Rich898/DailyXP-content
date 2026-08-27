#!/usr/bin/env python3
"""
compose.py — limb #3: turn a planner plan into a validated question set via the API.

The planner (limb #2a) decides WHICH slots exist (subject/topic/intent/phase).
This asks the language model to fill only the LANGUAGE of each slot — prompt,
options, answer, why — then assembles the set with ids/phases/subjects taken
straight from the plan (so structure is deterministic, the model can't drift the
schema), validates it, and retries feeding the validation errors back in.

The LLM never holds state and never decides scheduling — it writes questions to a
fixed spec. That's the whole architecture: state in the ledger, language in the model.

Needs ANTHROPIC_API_KEY in the environment. Zero third-party deps (urllib).

Usage:
  ANTHROPIC_API_KEY=... python3 tools/compose.py --plan work/plan.json \
      --seen-from history --out work/set.json [--model claude-sonnet-5]
  from tools.compose import compose_set  ->  (set_dict | None, errors)
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "tools"))
from validate import validate_set, seen_prompts  # noqa: E402
from answer_length import guidance_note  # noqa: E402  — reuse the ratified length-tell fix note

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"   # strong + economical for language tasks; override with --model
MAX_TOKENS = 8000                   # a 12-Q set is ~2.4k out; headroom so JSON never truncates

SYSTEM = """You write quiz questions for a spaced-repetition study tool used by two secondary-school boys.
You are given a fixed plan of slots. You fill ONLY the language of each slot. You do not choose topics,
you do not add or drop slots, you do not decide difficulty beyond what the guidance says.

Hard rules (a set is rejected if any is broken):
- Keep EVERY question SHORT, DIRECT, and about ONE thing — this is the most important rule. Ask a plain
  question ("Where was Shakespeare born?"), never a "which best reflects..." or "which statement is..."
  framing. Each option is a SHORT answer — a single word, name, date, or brief phrase (target 1-4 words,
  never more than ~6), and NEVER a compound sentence that packs in two facts. A child should take in the
  question and all four options at a glance. This applies to BOTH speed and steady. If an option is a full
  sentence or contains "and"/"but" joining two facts, it is TOO LONG — rewrite it as a short phrase.
- Each speed/steady question: exactly ONE uncontestable correct answer, present verbatim in its four options.
- Distractors must encode the REAL misconception named in the slot's guidance — not random wrong values.
- Every speed/steady question has a `why` (1-2 sentences) that re-teaches the point, not just "correct".
- Never reuse any prompt in the "already seen" list, and never repeat a prompt within this set.
- Teach-back slots: a single reasoning prompt (no options/answer) — understanding is graded, not recall.
- BATTLEGROUND slots (only when the plan's instructions declare them — the Friday Battleground): each slot is one
  CLAIMABLE zone on a weak topic — a direct multiple-choice question with one uncontestable correct option,
  plausible-misconception distractors, readable for a struggling student. `why` states the answer, explains why,
  and names the misconception. All other rules still apply.
- Match the school framing in the guidance; keep difficulty calm unless told otherwise.

Output ONLY a JSON object, no prose, no markdown fences:
- speed/steady slot = multiple choice: { "prompt": "...", "options": ["...","...","...","..."], "answer": "<one of options>", "why": "..." }
- scrub slot (ONLY when the slot's "mode" is "scrub"): SAME multiple-choice JSON as speed/steady — but the child physically RUBS OUT the three wrong answers with a finger, so distractor quality is load-bearing. Extra hard rules for these slots:
  * EXACTLY four options. Distractors are the SAME CATEGORY as the answer (prefer the misconception named in the guidance over random wrong facts), mutually exclusive with it, one unambiguous correct answer.
  * Similar length and format across ALL FOUR options — the correct answer must never stand out as the longest or the shortest.
  * NEVER "all of the above" / "none of the above" / compound options.
  * NEVER a negative stem ("Which is NOT...", "All EXCEPT...", "Which is false...") — the child ERASES wrong answers; a negative stem inverts the gesture.
- swipe slot (ONLY when the slot's "type" is "swipe"): a fast two-way SORT, not multiple choice.
  { "type":"swipe", "prompt":"<one short thing to judge>", "left":"<bucket A>", "right":"<bucket B>", "answer":"<exactly the correct bucket, copied from left or right>", "why":"..." }
  * prompt is ONE item/statement, readable at a glance (e.g. "Copper", "7 x 8 = 56", "Whales are fish").
  * left/right = a clean mutually-exclusive pair of SHORT labels (1-2 words): True/False, Metal/Non-metal, Prime/Composite, Fact/Opinion, Solid/Liquid. Fit the pair to the topic; default True/False.
  * answer copied verbatim from left or right. Across a swipe block VARY which side is correct — never all one bucket.
- numeric slot (ONLY when the slot's "type" is "numeric"): a typed-answer maths question, NO options.
  { "type":"numeric", "prompt":"<a clear maths question>", "answer":<the numeric answer as a NUMBER, not a string>, "calc":<true|false>, "pre":"<prefix e.g. $ or empty>", "post":"<unit e.g. ' cm' or empty>", "why":"..." }
  * answer is a plain number (56, 105, 52.5) — the exact value only; units go in pre/post, never in answer.
  * calc:true = a METHOD question (word problem / multi-step / needs a calculator for the arithmetic — knowing the method is the skill). calc:false = MENTAL (a times-table fact or simple operation — doing it in the head IS the skill; keep numbers small enough to do mentally).
  * pre = prefix before the answer (e.g. "$"); post = unit after (e.g. " cm\u00b2", " km/h"). Empty string if none.
  * why re-teaches the method or fact in one line.
- order slot (ONLY when the slot's "type" is "order"): a drag-to-SEQUENCE question, NO options.
  { "type":"order", "prompt":"<what to order, e.g. 'Order these events by date'>", "sequence":["<item>","<item>","<item>","<item>"], "top":"<label for the top/first end>", "bot":"<label for the bottom/last end>", "why":"..." }
  * sequence = 3-5 short items in their CORRECT order (top to bottom). The shell shuffles them; the student drags them back.
  * MUST be an UNAMBIGUOUS single correct order (chronological, numeric size, magnitude, process steps) — never a subjective or tie-able order.
  * top/bot label the axis ends (Earliest/Latest, Smallest/Largest, First/Last, Closest/Farthest).
  * items are SHORT labels (a few words), readable at a glance; why states the correct order and the reason in one line.
- text slot (ONLY when the slot's "type" is "text"): a typed SHORT-answer question, NO options.
  { "type":"text", "prompt":"<a question with a short specific answer>", "accept":["<canonical answer>","<variant/synonym>"], "why":"..." }
  * accept[0] is the CANONICAL answer (shown if wrong). Add genuine alternate forms/synonyms (e.g. ["oxygen","o2"], ["neil armstrong","armstrong"]).
  * The answer must be SHORT (a word or two) with ONE clear correct answer. The matcher already forgives case/spelling/plurals/articles — do NOT add spelling variants, only real synonyms.
  * why states the answer and a one-line reason.
- teach slot: { "prompt": "..." }
Include every slotId given, and no others."""


def build_user(plan, seen):
    slots = []
    for s in plan["slots"]:
        row = {
            "slotId": s["slot"], "phase": s["phase"], "subject": s["subject"],
            "topic": s["topic"], "intent": s["intent"], "guidance": s.get("guidance", ""),
            "type": s.get("type", "mc"), "mech": s.get("mech", ""),
            "mode": s.get("mode", ""),
        }
        slots.append(row)
    payload = {
        "for": f"{plan['student']} {plan['tag']} ({plan['day']} {plan['date']})",
        "instructions": plan.get("composer_instructions", ""),
        "slots": slots,
        "already_seen_prompts": sorted(seen),
    }
    return ("Compose the questions for this plan. Fill every slot; output only the JSON object described.\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2))


def call_api(system, user, model, api_key):
    body = json.dumps({
        "model": model, "max_tokens": MAX_TOKENS, "system": system,
        "thinking": {"type": "disabled"},   # structured JSON task — thinking wastes budget and truncated the set
        "messages": [{"role": "user", "content": user}],
    }).encode()
    req = urllib.request.Request(API_URL, data=body, method="POST", headers={
        "x-api-key": api_key, "anthropic-version": "2023-06-01", "content-type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode())
    # concatenate any text blocks
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")


def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    # grab the outermost object if the model added stray text
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end != -1:
        t = t[start:end + 1]
    return json.loads(t)


def _build_q(s, filled):
    """Build one question dict from a plan slot + model output. MC by default; swipe when slot type=swipe."""
    f = filled.get(s["slot"], {})
    typ = s.get("type", "mc")
    q = {"id": s["slot"], "phase": s["phase"], "subject": s["subject"],
         "prompt": f.get("prompt", "")}
    if s.get("block"):
        q["block"] = s["block"]            # block metadata drives the shell's doorway card
    if typ == "swipe" and s["phase"] in ("speed", "steady"):
        q["type"] = "swipe"
        q["left"] = f.get("left", "")
        q["right"] = f.get("right", "")
        q["answer"] = f.get("answer", "")
        q["why"] = f.get("why", "")
        q["fresh"] = bool(s.get("fresh", True))
        if s.get("throwback"):
            q["throwback"] = True
            q["fresh"] = False
    elif typ == "numeric" and s["phase"] in ("speed", "steady"):
        q["type"] = "numeric"
        q["answer"] = f.get("answer")
        q["calc"] = bool(f.get("calc"))
        q["pre"] = f.get("pre", "")
        q["post"] = f.get("post", "")
        q["why"] = f.get("why", "")
        q["fresh"] = bool(s.get("fresh", True))
        if s.get("throwback"):
            q["throwback"] = True
            q["fresh"] = False
    elif typ == "order" and s["phase"] in ("speed", "steady"):
        q["type"] = "order"
        q["sequence"] = f.get("sequence", [])
        q["top"] = f.get("top", "")
        q["bot"] = f.get("bot", "")
        q["why"] = f.get("why", "")
        q["fresh"] = bool(s.get("fresh", True))
        if s.get("throwback"):
            q["throwback"] = True
            q["fresh"] = False
    elif typ == "text" and s["phase"] in ("speed", "steady"):
        q["type"] = "text"
        q["accept"] = f.get("accept", [])
        q["why"] = f.get("why", "")
        q["fresh"] = bool(s.get("fresh", True))
        if s.get("throwback"):
            q["throwback"] = True
            q["fresh"] = False
    elif s["phase"] in ("speed", "steady"):
        q["answer"] = f.get("answer")
        q["why"] = f.get("why", "")
        q["options"] = f.get("options", [])
        if s.get("mode") == "scrub":
            q["mode"] = "scrub"        # delivery mode from the PLAN, never from the model
        q["fresh"] = bool(s.get("fresh", True))
        if s.get("throwback"):
            q["throwback"] = True
            q["fresh"] = False
        if s["intent"] == "repair":
            q["repair"] = True
    return q


def assemble(plan, filled):
    """Build the set schema from the plan (structure) + model output (language)."""
    questions = [_build_q(s, filled) for s in plan["slots"]]
    return {
        "student": plan["student"], "date": plan["date"], "day": plan["day"],
        "tag": plan["tag"], "title": f"DailyXP · {plan['day']} {plan['date']}",  # name-free title
        "questions": questions,
    }


_SLOT_ERR_RE = re.compile(r"^\s*\[([^\]]+)\]")


def _err_slot(err):
    """The slot id an error is scoped to (validate prefixes slot errors with [id]),
    or None for a set-level error (missing date, wrong teach count, …)."""
    m = _SLOT_ERR_RE.match(err or "")
    return m.group(1) if m else None


def _fix_hint(errs):
    """Pointed, model-actionable fix text for one slot's validation errors."""
    fixes = []
    for e in errs:
        if "length tell" in e:
            fixes.append(guidance_note(None))
        elif "REPEATS" in e:
            fixes.append("This prompt was already served to this student (it is in "
                         "already_seen_prompts). Ask a GENUINELY DIFFERENT question on the same "
                         "topic — a different fact, angle, or value — never a reworded version of a "
                         "seen prompt.")
        else:
            fixes.append(e.split("] ", 1)[-1] if "] " in e else e)
    return "  ".join(fixes)


def _partition_errors(errors):
    """Split validation errors into ({slotId: [errs]} slot-scoped, [set-level errs])."""
    slot_errs, set_errs = {}, []
    for e in errors:
        sid = _err_slot(e)
        (slot_errs.setdefault(sid, []).append(e) if sid else set_errs.append(e))
    return slot_errs, set_errs


def _retry_message(errors):
    """Whole-set retry instruction (the fallback path): name each failing slot with its
    SPECIFIC fix and tell the model to change ONLY those slots, keeping the rest verbatim.
    Used for a set-level error that can't be sliced, or when slicing is switched off."""
    slot_errs, set_errs = _partition_errors(errors)
    lines = ["Your previous set was REJECTED. Do NOT regenerate the whole set from scratch."]
    if slot_errs:
        lines.append("Change ONLY these slots — keep every OTHER slot's prompt, options, answer "
                     "and why EXACTLY as you last sent them:")
        for sid, es in slot_errs.items():
            lines.append(f"  - slot {sid}: " + _fix_hint(es))
    if set_errs:
        lines.append("Set-level problems to fix as well:")
        lines += [f"  - {e}" for e in set_errs]
    lines.append("Resend the COMPLETE JSON object for the whole set, with only the required changes applied.")
    return "\n".join(lines)


def build_user_slots(plan, slot_ids, prev_filled, objections, seen):
    """A FOCUSED message that recomposes ONLY the named slots (slot-splicing, HARDENING
    item 5 follow-up). The rest of the set is fixed and must not be resent — this is what
    stops the whole-set churn that made fixing one slot re-roll the good ones."""
    rows = []
    for s in plan["slots"]:
        if s["slot"] in slot_ids:
            rows.append({
                "slotId": s["slot"], "phase": s["phase"], "subject": s["subject"],
                "topic": s["topic"], "intent": s["intent"], "guidance": s.get("guidance", ""),
                "type": s.get("type", "mc"), "mech": s.get("mech", ""), "mode": s.get("mode", ""),
                "your_rejected_version": prev_filled.get(s["slot"]),
                "why_rejected__fix_exactly_this": objections.get(s["slot"], ""),
            })
    payload = {
        "for": f"{plan['student']} {plan['tag']} ({plan['day']} {plan['date']})",
        "instructions": plan.get("composer_instructions", ""),
        "rewrite_only_these_slots": rows,
        "already_seen_prompts": sorted(seen),
    }
    return ("The set was rejected only on the slots below. Rewrite ONLY these slots — fix exactly the "
            "stated problem, stay on the same topic and intent, and do NOT resend or change any other "
            "slot. Output ONLY a JSON object keyed by slotId, each value carrying the same fields you "
            "would normally emit for that slot type (prompt/options/answer/why, etc.).\n\n"
            + json.dumps(payload, ensure_ascii=False, indent=2))


def compose_set(plan, seen=None, model=DEFAULT_MODEL, api_key=None, max_retries=None, history_dir=None):
    """Returns (set_dict | None, errors).

    First pass composes the whole set. On a validation failure the retry recomposes ONLY
    the slots that failed (slot-splicing) and stitches them back, so fixing one bad slot
    never churns the good ones — the reliable fix for the deep-history t1 compose-fails
    (HARDENING item 5 follow-up). Falls back to a whole-set regenerate for the rare
    set-level error, or when DAILYXP_WHOLE_SET_RECOMPOSE=1 forces the old behaviour."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, ["ANTHROPIC_API_KEY not set"]
    if plan.get("status_gate") == "FROZEN":
        # never compose for a frozen student — publish the placeholder instead
        return ({"student": plan["student"], "status": "placeholder", "date": plan["date"],
                 "day": "", "title": "DailyXP", "questions": []}, [])
    if seen is None:
        seen = seen_prompts(plan["student"], history_dir)
    if max_retries is None:
        # Scrub blocks carry extra hard constraints (exactly 4 tiles, no negative stem,
        # no answer-length tell) and the deepest-history seats meet repeat pressure first,
        # so a scrub-bearing plan gets a larger budget before it gives up.
        max_retries = 4 if any(sl.get("mode") == "scrub" for sl in plan.get("slots", [])) else 2
    splice = os.environ.get("DAILYXP_WHOLE_SET_RECOMPOSE") != "1"

    filled, last_errors = None, []
    for attempt in range(max_retries + 1):
        try:
            if filled is None:
                # first pass (or recovery from a parse error) — compose the whole set
                filled = parse_json(call_api(SYSTEM, build_user(plan, seen), model, api_key))
            else:
                slot_errs, set_errs = _partition_errors(last_errors)
                if splice and slot_errs and not set_errs:
                    # SLOT-SPLICE: recompose only the failing slots; keep the rest verbatim
                    objs = {sid: _fix_hint(es) for sid, es in slot_errs.items()}
                    sub = parse_json(call_api(
                        SYSTEM, build_user_slots(plan, set(slot_errs), filled, objs, seen), model, api_key))
                    if isinstance(sub, dict):
                        for sid in slot_errs:
                            if sid in sub:
                                filled[sid] = sub[sid]
                else:
                    # whole-set regenerate (set-level error, or slicing disabled)
                    filled = parse_json(call_api(
                        SYSTEM, build_user(plan, seen) + "\n\n" + _retry_message(last_errors), model, api_key))
        except urllib.error.HTTPError as e:
            return None, [f"API HTTP {e.code}: {e.read().decode()[:200]}"]
        except Exception as e:
            last_errors = [f"compose/parse error: {e}"]
            filled = None                 # bad reply → fresh whole-set compose next round
            continue
        candidate = assemble(plan, filled)
        errors, warns = validate_set(candidate, history_dir)
        if not errors:
            return candidate, warns
        last_errors = errors
    return None, last_errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--seen-from", dest="history_dir", default=os.path.join(REPO, "history"))
    a = ap.parse_args()
    plan = json.load(open(a.plan))
    s, errs = compose_set(plan, model=a.model, history_dir=a.history_dir)
    if s is None:
        print("COMPOSE FAILED:")
        for e in errs:
            print("  " + e)
        sys.exit(1)
    json.dump(s, open(a.out, "w"), indent=2, ensure_ascii=False)
    kind = "placeholder" if s.get("status") == "placeholder" else f"{len(s['questions'])} Qs"
    print(f"COMPOSED ✓ {s.get('tag', s.get('status'))} ({kind}) -> {a.out}" + (f"  [warnings: {len(errs)}]" if errs else ""))


if __name__ == "__main__":
    main()
