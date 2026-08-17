#!/usr/bin/env python3
"""
planner.py — limb #2a: the slot planner (the scheduler BRAIN).

Deterministic. No LLM, no network. Reads:
  targets/<week>.json   what's LIVE in class + assessment dates  (targeting layer)
  work/state.json       per-topic state + per-boy status         (state layer)
Outputs a SET PLAN: N slots each tagged subject/topic/intent/fresh, plus a
composer-instruction block. The plan is the scaffold; the LLM language layer
(in-chat now, API at limb #3 — SAME contract) writes the actual questions.

Doctrine enforced in code:
  - FROZEN student  -> empty placeholder plan (the ABSENCE gate; can't compose for a sick kid)
  - REPAIR topics   -> guaranteed slot(s), placed in steady so confidence is captured
  - eligibility     -> only topics whose subject is LIVE in targets (+ REPAIR/prior-term threads)
  - priority        -> REPAIR > shaky > developing(spacing-weighted) > untested-if-fresh > solid(maintenance)
  - spacing         -> solid = occasional maintenance only; longer-since-last_tested ranks higher
  - assessment      -> subjects with an assessment within the horizon get boosted; format shapes the teach-back
  - trivially-fast  -> respected via state (reader keeps such topics 'untested'; planner never treats them as solid)
  - day directive   -> standard / blitz / boss / light-<subject> reshape the plan
  - no-repeat       -> topic selection only; the VALIDATOR is the hard question-level gate

Usage:
  python3 tools/planner.py --student y8 --date 2026-08-06 --day THU \
      --tag H2.4 --targets targets/2026-08-03.json --state work/state.json \
      --directive "light maths"   [--json plan.json]
"""
import argparse
import datetime as dt
import json
import re

STATE_PRIORITY = {"REPAIR": 100, "shaky": 70, "developing": 45, "untested": 30, "solid": 12}
ASSESS_HORIZON_DAYS = 16          # boost a subject if an assessment falls within this

# v3.1 question types (numeric/text/cloze/order + hidden x2 + encore) require the v3.1 SHELL to render.
# GATE: keep this False until the new shells are deployed to Netlify — the old shell can't display the
# new types and a run would break. Flip to True (one-line commit) once the shells are confirmed live.
V31_TYPES_LIVE = False

SHAPES = {
    "standard": {"speed": 7, "steady": 4, "teach": 1},
    "blitz":    {"speed": 10, "steady": 2, "teach": 1},
    "boss":     {"speed": 2, "steady": 4, "teach": 1},   # chain-heavy; misses-as-attacks
}
# recall-flavoured subjects lean speed; reasoning-flavoured lean steady (soft hints only)
SPEEDY = {"Maths", "History", "Science", "English", "Geography", "Commerce"}


def days_until(date_str, ref):
    try:
        return (dt.date.fromisoformat(date_str) - ref).days
    except Exception:
        return 9999


def _stem(s):
    """Normalise a topic string to a comparable stem (lowercase alnum words)."""
    return set(re.findall(r"[a-z0-9]+", (s or "").lower()))


def load_targets_for(student, targets):
    """Flatten targets for one student into {topic: {subject,status,fresh,assessment,format}}."""
    st = targets["students"].get(student, {})
    out = {}
    for subj, block in st.get("subjects", {}).items():
        fmt = block.get("assessment_format")
        for t in block.get("topics", []):
            out[t["topic"]] = {
                "subject": subj, "status": t.get("status"), "fresh": bool(t.get("fresh")),
                "assessment": t.get("assessment"), "format": fmt,
            }
    return out, st.get("subjects", {})


def resolve_target(topic, tmap):
    """Match a state-topic to a target row tolerantly (exact -> substring -> stem overlap).
    Compensates for wording drift between the two hand-built files. The proper fix is
    canonical topic IDs shared by both files (the 'curriculum taxonomy' moat)."""
    if topic in tmap:
        return tmap[topic]
    tl = topic.lower()
    for k, v in tmap.items():
        kl = k.lower()
        if tl in kl or kl in tl:
            return v
    ts = _stem(topic)
    best, best_ov = None, 0
    for k, v in tmap.items():
        ov = len(ts & _stem(k))
        if ov > best_ov and ov >= 2:          # need real overlap, not one shared word
            best, best_ov = v, ov
    return best


def score_topic(tp, tgt, ref):
    """Priority score for a state-topic, blended with targets + spacing + assessment."""
    base = STATE_PRIORITY.get(tp["state"], 20)

    # spacing: the longer since last tested, the more it's due (solid decays slowly)
    lt = tp.get("last_tested")
    if lt:
        age = max(0, (ref - dt.date.fromisoformat(lt)).days)
        base += min(age * 2, 24)

    # live-in-class boost; prior-term threads allowed but quieter
    status = (tgt or {}).get("status")
    if status == "live":
        base += 15
    elif status in ("upcoming", "not_yet_posted"):
        base += 6
    elif status == "prior_term" or tgt is None:
        base -= 8

    # assessment proximity boost (subject-level)
    a = (tgt or {}).get("assessment")
    if a and a.get("date"):
        d = days_until(a["date"], ref)
        if 0 <= d <= ASSESS_HORIZON_DAYS:
            base += 30 - d           # sooner = bigger
    # untested only really earns a slot if it's fresh/live
    if tp["state"] == "untested" and status not in ("live", "upcoming", "not_yet_posted"):
        base -= 25
    return base


def eligible_pool(state_student, tmap, ref):
    """Topics eligible for slots: in state AND (subject live in targets OR REPAIR OR has a live target row)."""
    pool = []
    for tp in state_student["topics"]:
        tgt = resolve_target(tp["topic"], tmap)
        subject_live = tgt is not None
        if not (subject_live or tp["repair"]):
            continue                                   # not live and not a repair thread -> skip
        pool.append({
            "subject": tp["subject"], "topic": tp["topic"], "state": tp["state"],
            "repair": tp["repair"], "last_tested": tp.get("last_tested"),
            "note": tp.get("note", ""), "fresh": (tgt or {}).get("fresh", False),
            "status": (tgt or {}).get("status"), "assessment": (tgt or {}).get("assessment"),
            "format": (tgt or {}).get("format"),
            "score": score_topic(tp, tgt, ref),
        })
    pool.sort(key=lambda x: x["score"], reverse=True)
    return pool


def intent_for(t):
    if t.get("_throwback"):
        return "throwback"
    if t["repair"]:
        return "repair"
    return {"shaky": "consolidate", "developing": "confirm", "solid": "maintenance",
            "untested": "fresh"}.get(t["state"], "confirm")


def fresh_flag_for(t):
    # v3.1 (item 8): HONEST fresh. Emit the sweep's per-topic flag — true = newly introduced this
    # week (incl. live-but-new; Rich's call), false = established. Skipping a fresh topic is the
    # benign "haven't covered this yet"; skipping an established one is a soft miss (ledger).
    # A throwback is by definition a revisit of previously-seen material → always fresh:false (LAW 3).
    if t.get("_throwback"):
        return False
    return bool(t.get("fresh", False))


def plan_set(student, date_str, day, tag, targets, state, directive):
    ref = dt.date.fromisoformat(date_str)
    s = state["students"][student]

    # ---- ABSENCE gate ----
    if s.get("status") == "FROZEN":
        return {
            "student": student, "date": date_str, "day": day, "tag": tag,
            "status_gate": "FROZEN", "reason": s.get("status_reason"),
            "shape": {"speed": 0, "steady": 0, "teach": 0}, "slots": [],
            "composer_instructions": "DO NOT COMPOSE. Student is FROZEN (absence). Publish the placeholder set; "
                                     "untested topics stay due and resurface on return. Never nag.",
        }

    tmap, subj_blocks = load_targets_for(student, targets)
    pool = eligible_pool(s, tmap, ref)

    # ---- day directive -> shape + subject weighting ----
    directive = (directive or "standard").lower()
    if "blitz" in directive:
        shape_key = "blitz"
    elif "boss" in directive:
        shape_key = "boss"
    else:
        shape_key = "standard"
    shape = dict(SHAPES[shape_key])

    light_subject = None
    m = re.search(r"(light|post-?test)\s+(\w+)", directive)
    if m:
        light_subject = m.group(2).capitalize()
    # a bare "light maths" also matches
    m2 = re.search(r"light\s+(\w+)", directive)
    if m2 and not light_subject:
        light_subject = m2.group(1).capitalize()

    # ---- allocation ----
    # A topic may take at most ONE slot per phase and TWO across the whole set,
    # so a REPAIR topic can hit speed (recall) AND steady (reasoning) — two angles —
    # but never pad the same phase twice. Genuinely-irrelevant topics (score < 0) are
    # never slotted; if that leaves the set short, we WARN instead of padding.
    n_speed, n_steady, n_teach = shape["speed"], shape["steady"], shape["teach"]
    used_by_phase = {"speed": set(), "steady": set(), "teach": set()}
    appearances = {}
    slots = []
    shortfall = []
    SCORE_FLOOR = 0

    def light_ok(t):
        # "light <subject>" (e.g. post-test) hard-caps that subject to ONE slot in the whole set
        if light_subject and t["subject"] == light_subject:
            return sum(1 for sl in slots if sl["subject"] == light_subject) < 1
        return True

    def can_use(t, phase):
        return (t["topic"] not in used_by_phase[phase]
                and appearances.get(t["topic"], 0) < 2
                and t["score"] >= SCORE_FLOOR
                and light_ok(t))

    def commit(t, phase):
        used_by_phase[phase].add(t["topic"])
        appearances[t["topic"]] = appearances.get(t["topic"], 0) + 1

    def pick(phase, prefer=None, subject_cap=None):
        subj_count = {}
        for sl in slots:
            if sl["phase"] == phase:
                subj_count[sl["subject"]] = subj_count.get(sl["subject"], 0) + 1
        for t in pool:
            if not can_use(t, phase):
                continue
            if prefer and not prefer(t):
                continue
            if subject_cap and subj_count.get(t["subject"], 0) >= subject_cap:
                continue
            return t
        return None

    boss_mode = shape_key == "boss"

    # 1) REPAIR guaranteed -> steady (confidence captured). REPAIR bypasses the score floor.
    for t in [x for x in pool if x["repair"]]:
        if n_steady <= 0:
            break
        if t["topic"] in used_by_phase["steady"] or not light_ok(t):
            continue
        commit(t, "steady")
        slots.append(_slot("T", 0, "steady", t,
                           extra="GUARANTEED REPAIR — re-teach the concept; do NOT let a fast-correct promote it out; confirm with a right 'Sure'."))
        n_steady -= 1

    # 1b) THROWBACK (SEASONS.md LAW 3) — reserve ONE steady slot for an aged-but-
    # mastered topic, to check retention held. Deliberate inverse of the live pool:
    # pulls from topics that have LEFT active rotation. Only when the ledger has an
    # eligible topic (thin early in history → simply no throwback slot, never padded)
    # and only if steady has room after REPAIR. Skipped on boss (Battleground owns
    # its own topic logic).
    throwback_topic = None
    if not boss_mode and n_steady > 0:
        import throwback as _tb
        cand = _tb.pick(s, ref, exclude_topics=used_by_phase["steady"])
        if cand:
            age = max(0, (ref - dt.date.fromisoformat(cand["last_tested"])).days)
            tw = {"subject": cand["subject"], "topic": cand["topic"],
                  "state": cand["state"], "repair": False,
                  "last_tested": cand["last_tested"], "note": cand.get("note", ""),
                  "fresh": False, "status": None, "assessment": None,
                  "format": None, "score": 0, "_throwback": True}
            commit(tw, "steady")
            slots.append(_slot("T", 0, "steady", tw,
                               extra=_tb.composer_note(cand["topic"], cand["subject"], age)))
            slots[-1]["throwback"] = True
            throwback_topic = cand["topic"]
            n_steady -= 1

    # 2) steady reasoning — top scorers, subject-spread
    while n_steady > 0:
        t = pick("steady", subject_cap=(99 if boss_mode else 2))
        if not t:
            shortfall.append(f"steady short by {n_steady}")
            break
        commit(t, "steady")
        slots.append(_slot("T", 0, "steady", t))
        n_steady -= 1

    # 3) teach — one conceptual explanation (highest-value available)
    if n_teach > 0:
        t = pick("teach")
        if t:
            fmt = t.get("format")
            extra = f"Teach-back format: {fmt}." if fmt else "Reasoning-graded: understanding scores, recitation doesn't."
            commit(t, "teach")
            slots.append(_slot("TB", 0, "teach", t, extra=extra))
        else:
            shortfall.append("teach short by 1")

    # 4) speed recall — spread across LIVE subjects (light-subject cap already enforced globally)
    while n_speed > 0:
        t = pick("speed", subject_cap=3)
        if not t:
            shortfall.append(f"speed short by {n_speed} — live-topic pool thin (recommend a fresh sweep or accept a shorter set)")
            break
        commit(t, "speed")
        slots.append(_slot("S", 0, "speed", t))
        n_speed -= 1

    # renumber cleanly by phase
    counters = {"speed": 0, "steady": 0, "teach": 0}
    prefix = {"speed": "S", "steady": "T", "teach": "TB"}
    ordered = [x for x in slots if x["phase"] == "speed"] + \
              [x for x in slots if x["phase"] == "steady"] + \
              [x for x in slots if x["phase"] == "teach"]
    for sl in ordered:
        counters[sl["phase"]] += 1
        sl["slot"] = f"{prefix[sl['phase']]}{counters[sl['phase']]}"

    final_shape = {"speed": counters["speed"], "steady": counters["steady"], "teach": counters["teach"]}

    # ---- FORMAT ROTATION (SEASONS.md LAW 2) --------------------------------
    # Assign a question format to each speed/steady slot from the bank, so a run
    # isn't 11 identical recall MC. Skipped on boss (Battleground assigns its own
    # per-zone formats via the composer block). On a reversed day, fact-based speed
    # slots may draw the reversed format; we flag eligibility with allow_reversed
    # and let formats.py keep numeric topics safe. Throwback/teach stay recall
    # (handled inside formats.eligible_formats).
    type_summary = ""
    encore_plan = []
    if not boss_mode:
        import formats as _fmt
        reversed_day = "reversed" in (directive or "")
        for sl in ordered:
            if reversed_day and sl["phase"] == "speed":
                sl["allow_reversed"] = True
        # v3.1 INPUT types: standard days only — Wednesday (reversed) and Friday (boss) stay MC.
        if V31_TYPES_LIVE and shape_key == "standard" and not reversed_day:
            import qtypes as _qt
            _qt.assign_types(ordered, student, date_str, tag)
            _qt.assign_x2(ordered, student, date_str, tag)   # one hidden double-XP slot per run
            type_summary = _qt.type_summary(ordered)
            # Optional ENCORE (bonus round): 2 spare topics not already in the run, typed like steady.
            _used = {sl["topic"] for sl in ordered}
            _spare = [t for t in pool if t["topic"] not in _used][:2]
            encore_plan = [_slot("E", i + 1, "steady", t, extra="BONUS encore question (optional extra for bonus XP)")
                           for i, t in enumerate(_spare)]
            if encore_plan:
                _qt.assign_types(encore_plan, student, date_str, tag)
        # Trap-1 cap: never both a tap-to-order slot AND the MC ordering format in one run.
        _excl = {_fmt.ORDERING} if any(sl.get("type") == "order" for sl in ordered) else None
        _fmt.assign_formats(ordered, student, date_str, tag, exclude=_excl)
        format_summary = _fmt.run_format_summary(ordered)
    else:
        format_summary = "boss/battleground (composer-assigned)"

    ci = _composer_instructions(student, day, tag, shape_key, light_subject, ordered, directive)

    return {
        "student": student, "date": date_str, "day": day, "tag": tag,
        "status_gate": "ACTIVE", "directive": directive, "shape": final_shape,
        "requested_shape": dict(shape), "shortfall": shortfall,
        "slots": ordered, "composer_instructions": ci,
        "format_summary": format_summary,
        "type_summary": type_summary,
        "encore": encore_plan,
    }


def _slot(prefix, n, phase, t, extra=""):
    return {
        "slot": f"{prefix}{n}", "phase": phase, "subject": t["subject"], "topic": t["topic"],
        "intent": intent_for(t), "fresh": fresh_flag_for(t), "state": t["state"],
        "score": round(t["score"], 1),
        "guidance": (t["note"] + (" | " + extra if extra else "")).strip(" |"),
    }


def _composer_instructions(student, day, tag, shape_key, light_subject, slots, directive=""):
    lines = [
        f"COMPOSE {tag} for {student} ({day}). Shape: {shape_key}.",
        "Write ONE fresh question per slot below — never reuse a prompt this student has seen (the validator enforces this).",
        "RULES (CONTENT-MODEL): exactly one uncontestable answer; distractors encode the real misconception named in guidance; "
        "each speed/steady has a 'why' that re-teaches; teach-back prompts are reasoning-graded.",
        "ANSWER-LENGTH LAW (SEASONS.md LAW 1 — enforced by review.py, do not breach): the correct option must NOT be the "
        "longest, and must NOT be identifiable by any surface feature (length, grammatical completeness, a lone qualifier, "
        "position). Keep all four options in a SIMILAR length band. Make distractors specific and plausible — never short "
        "throwaways next to a long precise answer. If the correct answer is naturally wordy, pad the distractors to match with "
        "equally concrete detail; if distractors are naturally short, tighten the correct answer to fit. A child must not be able "
        "to score by tapping the longest option without reading.",
    ]
    if light_subject:
        lines.append(f"DIRECTIVE: light on {light_subject} (student just sat its assessment) — keep it to the single slot shown, calm difficulty.")
    if "reversed" in (directive or ""):
        lines.append(
            "REVERSED (this chapter's Wednesday mutator — SEASONS.md): every FACT-BASED speed slot is reversed; steady and teach stay normal.\n"
            "- EXEMPT from reversal: any speed slot whose topic is a CALCULATION (equations, angles, area/volume, percentages —\n"
            "  anything solved with arithmetic). Those slots stay STANDARD multiple-choice recall. Reason: candidate questions for a\n"
            "  numeric answer routinely collide (several equations solving to the same x), which fails review and holds the set.\n"
            "  Reversal trains fact discrimination; calculations don't discriminate, they compute.\n"
            "- Prompt template, exactly: The answer is: \"<fact>\". Which question is this the answer to?\n"
            "- <fact> is a real, checkable fact from that slot's topic (respect the guidance) — short, concrete (a date, term, value, name).\n"
            "- Options: four candidate QUESTIONS from the student's actual study neighbourhood, all phrased as questions.\n"
            "  Exactly ONE is genuinely answered by the stated fact. The other three must be real-sounding questions whose\n"
            "  true answers are clearly DIFFERENT facts — near neighbours that get mixed up under pressure, never absurd fillers.\n"
            "- NUMERIC TOPICS (equations, angles, percentages, any calculation): SOLVE every candidate question yourself BEFORE\n"
            "  output. Each distractor question's true answer must be a DIFFERENT number from the stated fact AND from each other —\n"
            "  two candidates computing to the same value is this format's most common failure and gets the whole set rejected\n"
            "  (e.g. never offer both 'the co-interior partner of 70°' and 'the corresponding partner of 110°' when the stated\n"
            "  fact is 110° — both are answered by it). If a distractor collides, change its NUMBERS, not its topic.\n"
            "- answer = the correct question, verbatim from options.\n"
            "- why = confirm the pair in one line AND state the true answer of the most tempting distractor question, so the near-miss is disarmed.")
    if shape_key == "boss":
        lines.append(
            "BATTLEGROUND (this is Friday's Battleground \u2014 the student's self-contained shot at claiming the ground on the\n"
            "topics they struggled with this week; each STEADY slot is one claimable zone on a flagged weak topic):\n"
            "- Pick the SHARPEST question format for each zone's topic (they can differ zone to zone). Choose from this MC family\n"
            "  (all render as four tappable options \u2014 the shell has no typed-answer input yet, so every format MUST be four options):\n"
            "    * SPOT-THE-LIE \u2014 four statements, three true, one false; prompt ends 'Which one is FALSE?'; answer = the false one.\n"
            "    * TRUE / FALSE \u2014 one statement; options are exactly ['True','False']; answer is whichever is correct. Use for a\n"
            "      single crisp misconception ('True or False: a whale is a fish' -> False).\n"
            "    * MULTIPLE CHOICE \u2014 a normal question, four options, one correct. Use for straight recall or discrimination.\n"
            "    * SUM (as multiple choice) \u2014 a maths problem shown WITH four answer options ('7 x 8 = ?' -> 56 / 54 / 63 / 48),\n"
            "      the distractors being real slips. This is how maths zones are done (do NOT ask them to type \u2014 no typed input yet).\n"
            "- Match format to topic: recognising an error -> spot-the-lie; a crisp true/false misconception -> true/false; recall or\n"
            "  'which one' -> multiple choice; a computation gap -> sum-as-MC. The point is testing the weak spot well, not one format.\n"
            "- Whatever the format: exactly one uncontestable correct option; the distractors are PLAUSIBLE misconceptions the student\n"
            "  actually holds (use the guidance), not howlers or wording tricks. Keep it readable for a kid who has STRUGGLED with this\n"
            "  topic \u2014 just hard enough to make them think, simple enough that claiming the zone builds confidence.\n"
            "- why = state the correct answer, explain WHY, and name the misconception the distractor represents. Resurface this week's\n"
            "  actual misses. Frame as claiming contested ground, not attacking an enemy.\n"
            "- Spread the four zones across the student's DIFFERENT weak subjects wherever the ledger gaps allow, and VARY the formats\n"
            "  across the four (don't make all four the same type). The two SPEED slots stay NORMAL recall (a warm-up). The teach-back\n"
            "  secures the ground claimed (the final push).")
    lines.append("Output must satisfy tools/validate.py before publish.")

    # FORMAT LEGEND (SEASONS.md LAW 2): if any slot carries an assigned non-recall
    # format, tell the composer exactly how to build each format it will encounter.
    used_formats = {sl.get("format") for sl in slots if sl.get("format")}
    non_recall = used_formats - {"recall", None}
    if non_recall:
        import formats as _fmt
        lines.append("")
        lines.append("QUESTION FORMATS (SEASONS.md LAW 2 — each slot below names its 'format'; build it EXACTLY per this legend). "
                     "Every format is still four tappable options with one uncontestable correct answer, a re-teaching 'why', and "
                     "the answer-length law applies to all of them:")
        for f in sorted(non_recall):
            lines.append("- " + _fmt.render_note(f))
        lines.append("- " + _fmt.render_note("recall"))

    # TYPED-INPUT LEGEND (Shell v3.1): slots carrying a `type` take a TYPED answer, not options.
    used_types = {sl.get("type") for sl in slots if sl.get("type") and sl.get("type") != "mc"}
    if used_types:
        lines.append("")
        lines.append("TYPED-INPUT SLOTS (Shell v3.1 — a slot below may name a 'type'; that slot takes a TYPED answer, NOT four "
                     "options. Build it EXACTLY per this legend. There are no options, so the answer-length law does not apply; the "
                     "point of a typed slot is that the student cannot reverse-engineer the answer from choices):")
        if "numeric" in used_types:
            lines.append('- type "numeric": a calculation with ONE numeric answer typed on a keypad. NO options. Emit '
                         '{"prompt","answer","accept","why"}. answer = the canonical value WITH its unit if there is one (e.g. "30 cm\u00b2"). '
                         'accept = every correct written form: ALWAYS include the bare number, plus unit variants and ascii/unicode forms '
                         '(e.g. ["30","30 cm2","30cm\u00b2"]). Never accept a wrong unit. The prompt must have exactly one correct value. why re-teaches the method.')
        if "text" in used_types:
            lines.append('- type "text": a short term / name / date typed by the student. NO options. Emit {"prompt","answer","accept","why"}. '
                         'answer = the canonical wording (keep it SHORT — a few words, typed recall, never an essay). accept = acceptable '
                         'variants: synonyms, shortened forms, common spellings (e.g. answer "War Guilt Clause", accept ["war guilt","guilt clause"]). '
                         'Matching ignores case and punctuation, so do NOT list case/punctuation variants.')
        if "cloze" in used_types:
            lines.append('- type "cloze": a fill-the-blank sentence. Put the blank IN the prompt as ______ (6+ underscores). NO options. '
                         'Emit {"prompt","answer","accept","why"}. answer = the missing word/phrase (SHORT); accept = acceptable variants. '
                         'The sentence around the blank must make the answer determinable for a student who knows the material.')
        if "order" in used_types:
            lines.append('- type "order": the student taps shuffled items back into the correct SEQUENCE. NO options, NO answer. '
                         'Emit {"prompt","sequence","why"}. sequence = 3-5 SHORT, DISTINCT items in the ONE correct order (chronology, '
                         'process steps, smallest-to-largest, etc.). The prompt states what to order by (e.g. "earliest first"). There '
                         'must be exactly one defensible order. why = state the correct order and the reason. Only use this when the '
                         'topic genuinely has a single correct sequence.')
    return "\n".join(lines)


def render(plan):
    out = []
    out.append("=" * 78)
    out.append(f"SET PLAN — {plan['student']}  {plan['tag']}  ({plan['day']} {plan['date']})   gate={plan['status_gate']}")
    if plan["status_gate"] == "FROZEN":
        out.append(f"  FROZEN: {plan['reason']}")
        out.append("  -> compose nothing; publish placeholder.")
        out.append("=" * 78)
        return "\n".join(out)
    sh = plan["shape"]
    rq = plan.get("requested_shape", sh)
    shape_str = f"{sh['speed']} speed / {sh['steady']} steady / {sh['teach']} teach"
    if (sh['speed'], sh['steady'], sh['teach']) != (rq['speed'], rq['steady'], rq['teach']):
        shape_str += f"  (requested {rq['speed']}/{rq['steady']}/{rq['teach']})"
    out.append(f"  directive={plan.get('directive')}   shape={shape_str}")
    if plan.get("format_summary"):
        out.append(f"  formats={plan['format_summary']}")
    if plan.get("type_summary"):
        out.append(f"  input-types={plan['type_summary']}")
    for w in plan.get("shortfall", []):
        out.append(f"  \u26a0 POOL: {w}")
    out.append("-" * 78)
    for sl in plan["slots"]:
        tag = "REPAIR" if sl["intent"] == "repair" else sl["intent"]
        typ = sl.get("type", "mc")
        badge = typ.upper() if typ != "mc" else (("mc:" + sl["format"]) if sl.get("format") and sl.get("format") != "recall" else "")
        if sl.get("x2"):
            badge = (badge + " " if badge else "") + "\u2b50x2"
        out.append(f"  {sl['slot']:<4} {sl['phase']:<6} {sl['subject']:<10} [{tag}/{sl['state']}] score {sl['score']}" + (f"  <{badge}>" if badge else ""))
        out.append(f"        {sl['topic']}")
        if sl["guidance"]:
            out.append(f"        \u21b3 {sl['guidance']}")
    out.append("-" * 78)
    out.append("COMPOSER INSTRUCTIONS:")
    for l in plan["composer_instructions"].split("\n"):
        out.append("  " + l)
    out.append("=" * 78)
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--student", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--day", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--targets", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--directive", default="standard")
    ap.add_argument("--json", dest="json_out")
    a = ap.parse_args()
    targets = json.load(open(a.targets))
    state = json.load(open(a.state))
    plan = plan_set(a.student, a.date, a.day, a.tag, targets, state, a.directive)
    print(render(plan))
    if a.json_out:
        json.dump(plan, open(a.json_out, "w"), indent=2, ensure_ascii=False)
        print(f"\n[plan written -> {a.json_out}]")


if __name__ == "__main__":
    main()
