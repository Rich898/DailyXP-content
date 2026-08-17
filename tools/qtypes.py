"""
qtypes.py — Shell v3.1 INPUT-type assignment (the outer axis above the MC format bank).

Each speed/steady slot gets an input type: mc | numeric | text | cloze. Typed slots take a
keypad/word answer instead of four options, so a child can't reverse-engineer the answer from
the choices (both boys' flagged weakness). Deterministic — seeded by student+date+tag, so a run
is stable on re-plan but the mix shifts day to day.

Rules (Rich's calls):
- numeric: ONLY calculation topics (a numeric answer must exist); allowed in speed AND steady.
- text / cloze: any non-calc STEADY topic (words stay out of the timed speed section).
- throwback slots stay plain recall (SEASONS LAW 3, like-for-like) — never typed.
- mc is the default and always the fallback; formats.py then labels the mc slots.

Only runs on STANDARD days — Wednesday (reversed) and Friday (Battleground) stay MC, handled by
the planner. Named qtypes (not `types`) to avoid shadowing Python's stdlib `types` module.

── BASELINE DIAL (tune these) ─────────────────────────────────────────────────
"""
import hashlib
import formats  # is_calc_topic + the seeding spirit

# Baseline mix (Rich: "a bit more than the conservative default"). Raise/lower to taste.
P_NUMERIC = 0.85        # a calc slot becomes a numeric keypad question this often
P_TYPED_STEADY = 0.65   # a non-calc STEADY slot becomes text/cloze/order this often
P_CLOZE_SHARE = 0.5     # of the text/cloze ones, this share are cloze (rest short-text)
P_ORDER_SHARE = 0.45    # of ORDER-eligible typed steady slots, this share become tap-to-order
MIN_MC = 1              # keep at least this many mc slots/run for format-bank variety (0 = allow all-typed)

MC, NUMERIC, TEXT, CLOZE, ORDER = "mc", "numeric", "text", "cloze", "order"

# A slot is order-eligible only when its topic signals a genuine single sequence (chronology,
# process, life cycle...). Keyword-gated so we never force an ordering onto a non-sequential topic.
_ORDER_HINTS = ("chronolog", "timeline", "sequence", "order of", "steps", "process", "stages",
                "life cycle", " cycle", "causes", "consequence", "rise", "fall of", "reign",
                "revolution", "evolution", "method", "procedure", "events", "timeline", "era",
                "war ", "world war", "development", "phases")


def is_orderable(subject, topic):
    t = (topic or "").lower()
    return any(h in t for h in _ORDER_HINTS)


def _roll(parts):
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def candidate_type(slot):
    """The typed type this slot COULD take, or MC if it can't be typed."""
    if slot.get("throwback"):
        return MC                                   # LAW 3: like-for-like recall, never typed
    phase = slot.get("phase")
    if phase not in ("speed", "steady"):
        return MC
    if formats.is_calc_topic(slot.get("subject", ""), slot.get("topic", "")):
        return NUMERIC                              # calc → keypad (speed or steady)
    if phase == "steady":
        if is_orderable(slot.get("subject", ""), slot.get("topic", "")):
            return "wordorder"                      # a word answer OR a tap-to-order sequence
        return "textcloze"                          # non-calc steady → a word answer
    return MC                                       # non-calc speed stays MC (words are steady-only)


def assign_types(slots, student, date_str, tag):
    """Assign slot['type'] to every speed/steady slot. Mutates and returns slots."""
    typed = []
    for i, s in enumerate(slots):
        if s.get("phase") not in ("speed", "steady"):
            continue
        cand = candidate_type(s)
        chosen = MC
        sid = s.get("slot", i)
        if cand == NUMERIC and _roll([student, date_str, tag, sid, "num"]) < P_NUMERIC:
            chosen = NUMERIC
        elif cand in ("textcloze", "wordorder") and _roll([student, date_str, tag, sid, "txt"]) < P_TYPED_STEADY:
            if cand == "wordorder" and _roll([student, date_str, tag, sid, "ord"]) < P_ORDER_SHARE:
                chosen = ORDER
            else:
                chosen = CLOZE if _roll([student, date_str, tag, sid, "cz"]) < P_CLOZE_SHARE else TEXT
        s["type"] = chosen
        if chosen != MC:
            typed.append(i)

    # Floor: keep at least MIN_MC mc slots so the format bank still has something to vary.
    ss = [i for i, s in enumerate(slots) if s.get("phase") in ("speed", "steady")]
    n_mc = len(ss) - len(typed)
    if n_mc < MIN_MC and typed:
        need = MIN_MC - n_mc
        # revert the weakest-claim typed slots (highest revert-roll) back to mc
        ranked = sorted(typed, key=lambda i: _roll([student, date_str, tag, slots[i].get("slot", i), "rv"]), reverse=True)
        for i in ranked[:need]:
            slots[i]["type"] = MC
    return slots


def type_summary(slots):
    """Short 'numeric×2 text×1 cloze×1 mc×3' string for the plan render."""
    from collections import Counter
    c = Counter(s.get("type", MC) for s in slots if s.get("phase") in ("speed", "steady"))
    order = [NUMERIC, TEXT, CLOZE, ORDER, MC]
    parts = [f"{t}×{c[t]}" for t in order if c.get(t)]
    return " ".join(parts) if parts else "mc-only"


def assign_x2(slots, student, date_str, tag):
    """Flag exactly ONE eligible slot as hidden double-XP (x2), deterministically seeded. A throwback
    is excluded (it's a like-for-like retention check, not a reward moment). Mutates + returns slots."""
    elig = [i for i, s in enumerate(slots) if s.get("phase") in ("speed", "steady") and not s.get("throwback")]
    if not elig:
        return slots
    pick = min(elig, key=lambda i: _roll([student, date_str, tag, slots[i].get("slot", i), "x2"]))
    slots[pick]["x2"] = True
    return slots
