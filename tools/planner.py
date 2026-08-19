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
  - day directive   -> standard / boss / light-<subject> reshape the plan
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

# Core academic subjects that must each appear at least once per quiz (when live), so a run can't skew
# entirely to whatever's weakest and starve a subject (e.g. all English/History, no Maths).
CORE_SUBJECTS = ("Maths", "English", "Science", "History")
MAX_PER_SUBJECT = 3               # no single subject takes more than this many MC slots in one quiz

SHAPES = {
    "standard": {"speed": 12, "steady": 6, "teach": 1},   # ~5-6 min (was 7/4/1)
    "boss":     {"speed": 2, "steady": 7, "teach": 1},   # chain-heavy; misses-as-attacks
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


_BLOCKS = {
    "swipe":    {"label": "Swipe Sort",   "hue": "#39A7DE", "icon": "⇆", "sub": "Flick each card up into its bucket", "cta": "Start swiping →"},
    "recall":   {"label": "Quick Recall", "hue": "#16E08C", "icon": "●", "sub": "Four options, one answer — keep it fast", "cta": "Keep going →"},
    "reversed": {"label": "Reversed",     "hue": "#B26BE6", "icon": "⇄", "sub": "Given a detail — name what it belongs to", "cta": "Flip it →"},
    "numeric":  {"label": "Numeric",      "hue": "#14C7C7", "icon": "#",       "sub": "Type the answer", "cta": "Start →"},
    "order":    {"label": "Drag It",      "hue": "#FFB800", "icon": "⇅", "sub": "Drag the tiles into order", "cta": "Start dragging →"},
    "text":     {"label": "Short Answer", "hue": "#E0559B", "icon": "✎", "sub": "Type it — spelling never counts", "cta": "Start →"},
}

def assign_blocks(ordered, student, directive):
    """Deal the speed round into coherent mechanic BLOCKS (the day's loadout).
    Each slot gets a 'mech' (so the composer generates it right) + 'block' metadata
    (so the shell shows the right doorway). Coherent by construction: a block never mixes mechanics."""
    import copy
    speed = [x for x in ordered if x.get("phase") == "speed"]
    if not speed:
        return
    def stamp(slots, mech):
        for x in slots:
            x["mech"] = mech
            x["block"] = copy.deepcopy(_BLOCKS[mech])
            if mech == "swipe":
                x["type"] = "swipe"
    if "reversed" in (directive or ""):
        # Reversed directive: a Quick Recall block, then a CONTAINED Reversed block (~5).
        rev_n = min(5, len(speed))
        stamp(speed[:len(speed) - rev_n], "recall")
        stamp(speed[len(speed) - rev_n:], "reversed")
    elif student == "t1":
        # test seat, standard day: a Swipe block, then Quick Recall.
        sw_n = min(4, len(speed))
        stamp(speed[:sw_n], "swipe")
        stamp(speed[sw_n:], "recall")
        # steady: the Maths slots become a Numeric block (typed answers, no clock); others stay MC.
        for x in [y for y in ordered if y.get("phase") == "steady" and y.get("subject") == "Maths"]:
            x["mech"] = "numeric"; x["type"] = "numeric"; x["block"] = copy.deepcopy(_BLOCKS["numeric"])
        for x in [y for y in ordered if y.get("phase") == "steady" and y.get("subject") == "History"]:
            x["mech"] = "order"; x["type"] = "order"; x["block"] = copy.deepcopy(_BLOCKS["order"])
        for x in [y for y in ordered if y.get("phase") == "steady" and y.get("subject") == "Science"]:
            x["mech"] = "text"; x["type"] = "text"; x["block"] = copy.deepcopy(_BLOCKS["text"])
    # else: boys on a standard day — flat MC, no blocks (swipe not yet rolled to them).


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
    if "boss" in directive:
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

    def can_cover(t, phase):
        # coverage forces a subject in even if its topics are low-priority — bypasses SCORE_FLOOR
        return (t["topic"] not in used_by_phase[phase]
                and appearances.get(t["topic"], 0) < 2
                and light_ok(t))

    def commit(t, phase):
        used_by_phase[phase].add(t["topic"])
        appearances[t["topic"]] = appearances.get(t["topic"], 0) + 1

    def pick(phase, prefer=None, subject_cap=None, relaxed=False):
        subj_count = {}          # this phase (for the per-phase subject_cap)
        total_count = {}         # across ALL slots (for the global MAX_PER_SUBJECT)
        for sl in slots:
            total_count[sl["subject"]] = total_count.get(sl["subject"], 0) + 1
            if sl["phase"] == phase:
                subj_count[sl["subject"]] = subj_count.get(sl["subject"], 0) + 1
        for t in pool:
            usable = can_cover(t, phase) if relaxed else can_use(t, phase)   # relaxed drops the score floor
            if not usable:
                continue
            if prefer and not prefer(t):
                continue
            if subject_cap and subj_count.get(t["subject"], 0) >= subject_cap:
                continue
            if total_count.get(t["subject"], 0) >= MAX_PER_SUBJECT:
                continue          # global balance cap — no subject takes more than MAX_PER_SUBJECT
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

    # 1c) SUBJECT COVERAGE — guarantee each live core subject appears at least once, even if its topics
    # are low-priority. Without this, a subject whose topics are all "untested" (low score) loses every
    # slot to higher-priority subjects and gets starved forever. Runs before the general fill so the
    # reserved slots are locked in; the priority fill then tops up the rest. Skipped on boss.
    if not boss_mode:
        present = {sl["subject"] for sl in slots}
        for subj in CORE_SUBJECTS:
            if subj in present or (n_speed <= 0 and n_steady <= 0):
                continue
            cand = phase = None
            for ph in ("speed", "steady"):                 # prefer speed (recall) for the guaranteed slot
                if (ph == "speed" and n_speed <= 0) or (ph == "steady" and n_steady <= 0):
                    continue
                for t in pool:
                    if t["subject"] == subj and can_cover(t, ph):
                        cand, phase = t, ph
                        break
                if cand:
                    break
            if not cand:
                continue                                    # subject not live / no eligible topic → skip it
            commit(cand, phase)
            slots.append(_slot("S" if phase == "speed" else "T", 0, phase, cand,
                               extra="Subject-coverage slot — guarantees this subject appears in the quiz."))
            present.add(subj)
            if phase == "speed":
                n_speed -= 1
            else:
                n_steady -= 1

    # 2) steady reasoning — top scorers, subject-spread (relaxed fallback keeps the count on a thin pool)
    while n_steady > 0:
        cap = 99 if boss_mode else 2
        t = pick("steady", subject_cap=cap) or pick("steady", subject_cap=cap, relaxed=True)
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

    # 4) speed recall — spread across LIVE subjects (relaxed fallback keeps the count on a thin pool)
    while n_speed > 0:
        t = pick("speed", subject_cap=3) or pick("speed", subject_cap=3, relaxed=True)
        if not t:
            shortfall.append(f"speed short by {n_speed} — pool thin even after relaxing (recommend a fresh sweep)")
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

    assign_blocks(ordered, student, directive)

    final_shape = {"speed": counters["speed"], "steady": counters["steady"], "teach": counters["teach"]}

    # ---- FORMAT ROTATION (SEASONS.md LAW 2) --------------------------------
    # Assign a question format to each speed/steady slot from the bank, so a run
    # isn't 11 identical questions. Speed/steady questions are currently direct,
    # single-fact recall MC (the format bank is intentionally recall-only right now).
    # Typed-input types, MC format variety, hidden x2 and encore were built and removed
    # after review — see git history if ever revisited.
    format_summary = "direct recall"

    ci = _composer_instructions(student, day, tag, shape_key, light_subject, ordered, directive)
    if any(x.get("type") == "swipe" for x in ordered):
        ci += ("\nSWIPE BLOCK: slots with type \"swipe\" use the SWIPE schema (a two-way sort), NOT multiple choice, "
               "and are never reversed regardless of any other directive. Fit each bucket pair to the topic; default True/False.")

    return {
        "student": student, "date": date_str, "day": day, "tag": tag,
        "status_gate": "ACTIVE", "directive": directive, "shape": final_shape,
        "requested_shape": dict(shape), "shortfall": shortfall,
        "slots": ordered, "composer_instructions": ci,
        "format_summary": format_summary,
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
    if any(x.get("mech") == "reversed" for x in slots):
        lines.append("""
REVERSED (a question-type mechanic — SEASONS.md): ONLY the speed slots marked mech "reversed" use the reversed format below (a CONTAINED Reversed block); every OTHER speed slot is a normal recall MC. Steady and teach stay normal.
- EXEMPT from reversal: any CALCULATION topic (equations, angles, area/volume, percentages — anything solved with arithmetic). Those slots stay STANDARD multiple-choice recall. Reversal trains FACT discrimination; calculations compute, they don't discriminate.
- The point: give the student a DISTINGUISHING DETAIL and have them name what it belongs to — a FAST, TIMED, fast-to-READ speed question. This is a speed round, not a reading test.
- Prompt: state the detail as a short statement, then a short category cue. Format: '<detail> — which play?' / 'which event?' / 'which term?' / 'which empire?' / 'which shape?'. Do NOT write "The answer is:", and do NOT append a full question that re-asks for the answer — just the detail plus the short cue.
- HARD ANTI-LEAK RULE: <detail> is a fact ABOUT the correct option (its date, place, trait, quote, value) — it must NEVER be, contain, or paraphrase any of the four option labels, least of all the answer. If the only detail you can give is the option's own name, this topic is WRONG for reversal — make it a STANDARD recall question instead. (Good: 'Ruled from Constantinople, outlasted Rome's western half by ~1000 years — which empire?' -> Byzantine Empire. BAD: 'The answer is: the Byzantine Empire. Which empire survived in the east?' — that hands over the answer.)
- <fact> is a real, checkable fact — short and concrete (a date, term, value, name).
- Options: four short labels — names, terms, or brief phrases naming the THINGS the fact could belong to (NOT questions, NOT full sentences). Length is whatever keeps them GENUINELY DISTINGUISHABLE by a student who knows the material: a proper noun or specific term is fine in 1-2 words (e.g. fact "Verona": Romeo and Juliet / Hamlet / Macbeth / Othello); a subtler concept may need up to ~6 words to stay unambiguous. As short as possible WHILE a knowledgeable student can tell them apart at a glance and a guesser cannot.
- Exactly ONE label is what the fact is the answer to. The other three are real near-neighbours from the same study area whose true match is a DIFFERENT fact — the ones mixed up under pressure, never absurd fillers.
- AMBIGUITY TEST (the real bar): if two options could be confused by a student who genuinely understands the topic — bare abstract look-alikes like 'Cause' vs 'Consequence' with nothing to separate them — the labels are too vague. Add the few words that distinguish them (e.g. 'the resulting event' vs 'the reason it happened'), or pick a fact whose options are naturally distinct. A correct answer must be recoverable by KNOWLEDGE, never only by guessing between look-alikes.
- HARD RULE: if a fair set of options here would need full SENTENCES to make sense (common for numeric / "which scenario" topics), this topic is WRONG for reversal — make it a STANDARD recall question instead.
- answer = the correct label, verbatim from options.
- why = confirm the pair in one line and name the true match of the most tempting distractor.""")
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
    for w in plan.get("shortfall", []):
        out.append(f"  \u26a0 POOL: {w}")
    out.append("-" * 78)
    for sl in plan["slots"]:
        tag = "REPAIR" if sl["intent"] == "repair" else sl["intent"]
        out.append(f"  {sl['slot']:<4} {sl['phase']:<6} {sl['subject']:<10} [{tag}/{sl['state']}] score {sl['score']}")
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
