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

API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-sonnet-5"   # strong + economical for language tasks; override with --model
MAX_TOKENS = 8000                   # a 12-Q set is ~2.4k out; headroom so JSON never truncates

SYSTEM = """You write quiz questions for a spaced-repetition study tool used by two secondary-school boys.
You are given a fixed plan of slots. You fill ONLY the language of each slot. You do not choose topics,
you do not add or drop slots, you do not decide difficulty beyond what the guidance says.

Hard rules (a set is rejected if any is broken):
- Each speed/steady question: exactly ONE uncontestable correct answer, present verbatim in its options.
- Distractors must encode the REAL misconception named in the slot's guidance — not random wrong values.
- Every speed/steady question has a `why` (1-2 sentences) that re-teaches the point, not just "correct".
- Never reuse any prompt in the "already seen" list, and never repeat a prompt within this set.
- Teach-back slots: a single reasoning prompt (no options/answer) — understanding is graded, not recall.
- REVERSED slots (only when the plan's instructions declare them): the prompt states an answer and the four
  options are candidate QUESTIONS — exactly one of which the stated answer genuinely answers; the other three
  must be questions whose true answers clearly differ. All other rules still apply (one uncontestable pick,
  `why` re-teaches, fresh prompts).
- BATTLEGROUND slots (only when the plan's instructions declare them — the Friday Battleground): each slot is one
  CLAIMABLE zone on a weak topic, and you pick the sharpest format for that topic from the MC family (all four-option,
  since the shell has no typed input): spot-the-lie (four statements, one false), true/false (options ['True','False']),
  plain multiple choice, or a sum shown WITH four answer options. Vary the formats across the four zones. Whatever the
  format: one uncontestable correct option, plausible-misconception distractors, readable for a struggling student.
  `why` states the answer, explains why, names the misconception. All other rules still apply.
- Match the school framing in the guidance; keep difficulty calm unless told otherwise.

Output ONLY a JSON object, no prose, no markdown fences. Shape:
{ "<slotId>": { "prompt": "...", "options": ["...","...","...","..."], "answer": "<one of options>", "why": "..." }, ... }
For teach slots the value is just { "prompt": "..." }. Include every slotId given, and no others."""


def build_user(plan, seen):
    slots = []
    for s in plan["slots"]:
        row = {
            "slotId": s["slot"], "phase": s["phase"], "subject": s["subject"],
            "topic": s["topic"], "intent": s["intent"], "guidance": s.get("guidance", ""),
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


def assemble(plan, filled):
    """Build the set schema from the plan (structure) + model output (language)."""
    questions = []
    for s in plan["slots"]:
        f = filled.get(s["slot"], {})
        q = {"id": s["slot"], "phase": s["phase"], "subject": s["subject"],
             "prompt": f.get("prompt", "")}
        if s["phase"] in ("speed", "steady"):
            q["options"] = f.get("options", [])
            q["answer"] = f.get("answer")
            q["why"] = f.get("why", "")
            q["fresh"] = True
            if s["intent"] == "repair":
                q["repair"] = True
        questions.append(q)
    return {
        "student": plan["student"], "date": plan["date"], "day": plan["day"],
        "tag": plan["tag"], "title": f"DailyXP · {plan['day']} {plan['date']}",  # name-free title
        "questions": questions,
    }


def compose_set(plan, seen=None, model=DEFAULT_MODEL, api_key=None, max_retries=2, history_dir=None):
    """Returns (set_dict | None, errors). Retries feeding validation errors back to the model."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None, ["ANTHROPIC_API_KEY not set"]
    if plan.get("status_gate") == "FROZEN":
        # never compose for a frozen student — publish the placeholder instead
        return ({"student": plan["student"], "status": "placeholder", "date": plan["date"],
                 "day": "", "title": "DailyXP", "questions": []}, [])
    if seen is None:
        seen = seen_prompts(plan["student"], history_dir)

    user = build_user(plan, seen)
    last_errors = []
    for attempt in range(max_retries + 1):
        try:
            raw = call_api(SYSTEM, user, model, api_key)
            filled = parse_json(raw)
        except urllib.error.HTTPError as e:
            return None, [f"API HTTP {e.code}: {e.read().decode()[:200]}"]
        except Exception as e:
            last_errors = [f"compose/parse error: {e}"]
            user += f"\n\nYour previous reply could not be parsed as the required JSON object ({e}). Reply with ONLY the JSON object."
            continue
        candidate = assemble(plan, filled)
        errors, warns = validate_set(candidate, history_dir)
        if not errors:
            return candidate, warns
        last_errors = errors
        user += ("\n\nYour previous set FAILED validation with these errors — fix them and resend the full JSON object:\n"
                 + "\n".join("- " + e for e in errors))
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
