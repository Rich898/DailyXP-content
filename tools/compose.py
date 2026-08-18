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
- Keep EVERY question SHORT, DIRECT, and about ONE thing — this is the most important rule. Ask a plain
  question ("Where was Shakespeare born?"), never a "which best reflects..." or "which statement is..."
  framing. Each option is a SHORT answer — a single word, name, date, or brief phrase (target 1-4 words,
  never more than ~6), and NEVER a compound sentence that packs in two facts. A child should take in the
  question and all four options at a glance. This applies to BOTH speed and steady. If an option is a full
  sentence or contains "and"/"but" joining two facts, it is TOO LONG — rewrite it as a short phrase.
- Each MC speed/steady question: exactly ONE uncontestable correct answer, present verbatim in its options. (TYPED slots — numeric/text/cloze — have no options; see the typed legend.)
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

Output ONLY a JSON object, no prose, no markdown fences. Each slot's shape depends on its `type`:
- no `type` given = multiple choice: { "prompt": "...", "options": ["...","...","...","..."], "answer": "<one of options>", "why": "..." }
- `type` "numeric" / "text" / "cloze" = TYPED (no options): { "prompt": "...", "answer": "...", "accept": ["...","..."], "why": "..." }  — build these EXACTLY per the TYPED-INPUT legend in the instructions.
- `type` "order" = SEQUENCE (no options, no answer): { "prompt": "...", "sequence": ["<first>","<second>","<third>", ...], "why": "..." }  — items in the CORRECT order; the shell shuffles them for the student to tap back into order.
- teach slot: { "prompt": "..." }
Include every slotId given, and no others."""


def build_user(plan, seen):
    slots = []
    for s in list(plan["slots"]) + list(plan.get("encore", [])):
        row = {
            "slotId": s["slot"], "phase": s["phase"], "subject": s["subject"],
            "topic": s["topic"], "intent": s["intent"], "guidance": s.get("guidance", ""),
        }
        if s.get("format") and s.get("format") != "recall":
            row["format"] = s["format"]      # composer applies the matching legend entry
        if s.get("type") and s.get("type") != "mc":
            row["type"] = s["type"]           # typed slot — composer applies the TYPED-INPUT legend
        if s["slot"].startswith("E"):
            row["bonus"] = True               # optional encore question — same rules, extra for bonus XP
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
    """Build one question dict from a plan slot + model output. Shared by the main set and the encore."""
    f = filled.get(s["slot"], {})
    q = {"id": s["slot"], "phase": s["phase"], "subject": s["subject"],
         "prompt": f.get("prompt", "")}
    if s["phase"] in ("speed", "steady"):
        qtype = s.get("type", "mc")
        if qtype != "mc":
            q["type"] = qtype                         # mc stays implicit (back-compat)
        if qtype != "order":
            q["answer"] = f.get("answer")             # order carries a sequence, not an answer
        q["why"] = f.get("why", "")
        if qtype == "mc":
            q["options"] = f.get("options", [])
        elif qtype in ("numeric", "text", "cloze"):
            acc = f.get("accept")                     # LLM-authored accepted variants (synonyms/units)
            if acc is not None:
                q["accept"] = acc
        elif qtype == "order":
            q["sequence"] = f.get("sequence", [])     # LLM-authored CORRECT order (shell shuffles for display)
        # Carry fresh from the plan (a throwback slot is fresh:false — a revisit,
        # not new material; SEASONS.md LAW 3). Default true for everything else.
        q["fresh"] = bool(s.get("fresh", True))
        if s.get("throwback"):
            q["throwback"] = True
            q["fresh"] = False
        if s["intent"] == "repair":
            q["repair"] = True
        if s.get("x2"):
            q["x2"] = True                            # hidden double-XP (shell doesn't betray it pre-answer)
    return q


def assemble(plan, filled):
    """Build the set schema from the plan (structure) + model output (language)."""
    questions = [_build_q(s, filled) for s in plan["slots"]]
    out = {
        "student": plan["student"], "date": plan["date"], "day": plan["day"],
        "tag": plan["tag"], "title": f"DailyXP · {plan['day']} {plan['date']}",  # name-free title
        "questions": questions,
    }
    encore = [_build_q(s, filled) for s in plan.get("encore", [])]
    if encore:
        out["encore"] = encore                        # optional bonus round (shell offers it after teach-back)
    return out


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
