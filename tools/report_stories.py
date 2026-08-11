#!/usr/bin/env python3
"""
report_stories.py — the NARRATIVE layer of the Friday report.

friday_report.py answers "what is true this week". This module answers
"what HAPPENED this week" — it turns the week's per-question results into a
small number of STORY CARDS, each with a status, a per-day strip, a diagnosis,
and a what-happens-next. That narrative is what makes the report a report
rather than a status dashboard.

CODE DECIDES, LANGUAGE DRESSES (REPORTING.md): every function here is
deterministic. Code detects the SHAPES in the data, assigns the status, ranks
the stories and picks the top few; the LLM only writes them into prose. A model
never decides what this week's story was.

THE SHAPES (each maps to a status tag):
  RESOLVED      a topic that was going wrong early and came good later — the
                strongest story, because it's learning happening inside a week.
  TRENDING WELL a previously-flagged topic with a clean run of correct answers.
  WATCHING      a tendency worth noticing but NOT worth intervening on — e.g.
                confident-and-wrong. Framed as a tendency, never a trait.
  TO CLOSE      a specific fresh gap, small and fixable, with the fix attached.
  DEEPENED      a topic that moved UP the depth ladder (UNDERSTANDING.md) —
                the one story only this product can tell.

MISCONCEPTION DIAGNOSIS: the archived set (private/history/{student}/{date}_{tag}.json)
carries each question's options, correct answer and a `why` explaining the common
mistake. Joined to the run's `picked`, that turns "got an equation wrong" into
"chose the subtract-before-the-bracket answer" — the difference between a parent
being told to practise equations (wasteful) and being told the one thing to fix.

NO-ANXIETY (REPORTING.md): every story carries its own next step. A story with
nothing to do about it is not shipped. Under-claim on thin evidence: a single
data point is never a "pattern".

INTEGRITY GATE (UNDERSTANDING.md + integrity.py): a teach-back that failed the
integrity check can never be quoted back to a parent, nor evidence a depth
story. We do not put words in a child's mouth that we cannot attribute to them.
"""
import json
import os
from datetime import date

# status tags, in ranked order — earlier is a stronger story
STATUS_ORDER = ["RESOLVED", "DEEPENED", "TRENDING WELL", "WATCHING", "TO CLOSE"]


# --------------------------------------------------------------------------- #
# Set archive lookup (for misconception diagnosis)

def load_set(private_dir, student, run_date, tag):
    """The archived question set for one run, or None."""
    p = os.path.join(private_dir, "history", student, f"{run_date}_{tag}.json")
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except (ValueError, OSError):
        return None


def question_index(set_blob):
    """{question id -> question dict} from an archived set."""
    if not set_blob:
        return {}
    return {q.get("id"): q for q in set_blob.get("questions", []) if q.get("id")}


def misconception(q_result, q_set):
    """Why THIS wrong answer was wrong, in diagnostic terms.

    Returns {"picked", "correct", "why"} or None. `why` is the set's own
    explanation of the common mistake — authored when the question was written,
    so it is curriculum-grounded rather than invented after the fact.
    """
    if not q_set or q_result.get("ok") is not False:
        return None
    picked = q_result.get("picked")
    if picked is None:
        return None
    return {"picked": str(picked),
            "correct": str(q_set.get("answer", "")),
            "why": (q_set.get("why") or "").strip()}


# --------------------------------------------------------------------------- #
# Per-topic week trace — the ✓/✗ strip behind every story card

def topic_traces(runs, plans, student, week_days):
    """{topic: [{"day","ok","subject","q","misc","phase"}...]} across the week.

    Joins each answered question to the ledger topic the planner aimed it at
    via the SLOT ID (S1/T1/TB1) — the same join the state writer uses. Runs
    whose plan wasn't persisted simply contribute no topic stories, which is
    correct: without the plan we cannot say which topic a question tested.
    """
    traces = {}
    for r in runs:
        if r.get("student") != student or r.get("run_date") not in week_days:
            continue
        plan = plans.get(r.get("set_date") or r.get("run_date")) or {}
        slots = {sl.get("slot"): sl for sl in (plan.get("slots") or [])}
        if not slots:
            continue
        for q in r.get("questions", []):
            slot = slots.get(q.get("id")) or {}
            topic = slot.get("topic")
            if not topic:
                continue
            day = date.fromisoformat(r["run_date"]).strftime("%a")
            traces.setdefault(topic, []).append({
                "day": day, "date": r["run_date"], "ok": q.get("ok"),
                "subject": q.get("subject") or slot.get("subject"),
                "phase": q.get("phase"), "confidence": q.get("confidence"),
                "picked": q.get("picked"), "id": q.get("id"),
                "tag": r.get("tag"), "skipped": q.get("skipped"),
            })
    return traces


# --------------------------------------------------------------------------- #
# Shape detectors — each returns a story dict or None. All deterministic.

def _seq(trace):
    """Correctness sequence, skipping unanswered."""
    return [t["ok"] for t in trace if not t.get("skipped") and t["ok"] is not None]


def detect_resolved(topic, trace, subject):
    """Wrong early, right later, within the same week — learning visible."""
    seq = _seq(trace)
    if len(seq) < 3:
        return None
    firsts, lasts = seq[:len(seq) // 2], seq[len(seq) // 2:]
    if any(x is False for x in firsts) and lasts and all(x is True for x in lasts):
        return {"status": "RESOLVED", "topic": topic, "subject": subject,
                "trace": trace, "weight": 100 + len(seq),
                "next": "stays in the rotation once more to confirm it holds"}
    return None


def detect_trending(topic, trace, subject, was_flagged):
    """A previously-weak topic with a clean run this week."""
    seq = _seq(trace)
    if not was_flagged or len(seq) < 2 or not all(x is True for x in seq):
        return None
    return {"status": "TRENDING WELL", "topic": topic, "subject": subject,
            "trace": trace, "weight": 70 + len(seq),
            "next": "drops to light maintenance; the freed slots go to newer content"}


def detect_to_close(topic, trace, subject, misc):
    """A single fresh gap — small, specific, fixable."""
    seq = _seq(trace)
    if len(seq) > 2 or not seq or seq[-1] is not False:
        return None
    return {"status": "TO CLOSE", "topic": topic, "subject": subject,
            "trace": trace, "misconception": misc, "weight": 40,
            "next": "re-tested next week, and tonight's note covers it"}


def detect_deepened(topic, subject, before, after, evidence):
    """A topic that moved UP the depth ladder — the story only we can tell."""
    from friday_report import LANDED  # noqa: F401  (kept for symmetry of imports)
    ladder = ["not_yet", "knows", "lists", "connects", "applies"]
    if before is None or after is None:
        return None
    try:
        if ladder.index(after) <= ladder.index(before):
            return None
    except ValueError:
        return None
    return {"status": "DEEPENED", "topic": topic, "subject": subject,
            "from": before, "to": after, "evidence": evidence, "trace": [],
            "weight": 90, "next": "the next question on it aims a rung higher"}


def detect_watching(confident_wrong, total_confident):
    """A tendency, not a trait — and only when there is enough to speak about.
    Requires at least two instances; one is an incident, not a pattern."""
    if confident_wrong < 2:
        return None
    return {"status": "WATCHING", "topic": None, "subject": None, "trace": [],
            "count": confident_wrong, "of": total_confident, "weight": 50,
            "next": "no intervention — the quiz keeps pairing confidence with "
                    "correctness, so any repeat shows up immediately"}


# --------------------------------------------------------------------------- #
# The quote — integrity-gated

def pick_quote(runs, student, week_days, min_chars=80):
    """The best AUTHENTIC teach-back of the week, for 'in his own words'.

    Gated three ways: it must be graded well, it must be long enough to be worth
    quoting, and it MUST have passed the integrity check. Quarantined or held
    text is never quoted — attributing words to a child that they may not have
    written is the worst failure this report could make.
    """
    best = None
    for r in runs:
        if r.get("student") != student or r.get("run_date") not in week_days:
            continue
        for q in r.get("questions", []):
            if q.get("phase") != "teach":
                continue
            text = (q.get("text") or "").strip()
            g = q.get("tb_grade") or {}
            integ = q.get("tb_integrity") or {}
            if not text or len(text) < min_chars:
                continue
            if integ.get("verdict") == "quarantine" or g.get("integrity_hold"):
                continue                      # never quote unattributable text
            if g.get("verdict") not in ("solid", "partial"):
                continue
            score = (2 if g.get("verdict") == "solid" else 1) * 1000 + len(text)
            if best is None or score > best["score"]:
                best = {"score": score, "text": text, "subject": q.get("subject"),
                        "secs": q.get("secs"), "depth": g.get("depth"),
                        "date": r["run_date"]}
    return best


# --------------------------------------------------------------------------- #
# Accuracy by subject (a safe, useful figure on the Friday surface)

def subject_accuracy(runs, student, week_days):
    """{subject: {"right","asked"}} for the week — scored questions only."""
    out = {}
    for r in runs:
        if r.get("student") != student or r.get("run_date") not in week_days:
            continue
        for q in r.get("questions", []):
            if q.get("phase") == "teach" or q.get("skipped") or q.get("ok") is None:
                continue
            s = q.get("subject") or "Other"
            row = out.setdefault(s, {"right": 0, "asked": 0})
            row["asked"] += 1
            if q.get("ok"):
                row["right"] += 1
    return out


def confident_wrong(runs, student, week_days):
    """(confident_and_wrong, total_confident) — the calibration signal.
    Confidence is captured on the steady phase only, so this is a partial view
    and must be reported as such."""
    cw = tot = 0
    for r in runs:
        if r.get("student") != student or r.get("run_date") not in week_days:
            continue
        for q in r.get("questions", []):
            if (q.get("confidence") or "").strip().lower() != "sure":
                continue
            tot += 1
            if q.get("ok") is False:
                cw += 1
    return cw, tot


# --------------------------------------------------------------------------- #
# Assembly

def build_stories(private_dir, runs, plans_by_date, student, week_days,
                  topics, depth_before=None, max_stories=4):
    """The ranked story cards for one kid's week. Deterministic throughout."""
    depth_before = depth_before or {}
    traces = topic_traces(runs, plans_by_date, student, week_days)

    # index archived sets once, for misconception lookup
    set_idx = {}
    for r in runs:
        if r.get("student") != student or r.get("run_date") not in week_days:
            continue
        blob = load_set(private_dir, student, r.get("set_date") or r["run_date"], r.get("tag") or "")
        if blob:
            set_idx[r["run_date"]] = question_index(blob)

    state_by_topic = {t.get("topic"): t for t in topics}
    stories = []

    for topic, trace in traces.items():
        subject = trace[0].get("subject") if trace else ""
        tp = state_by_topic.get(topic) or {}
        was_flagged = tp.get("state") in ("shaky", "REPAIR") or bool(tp.get("repair"))

        # misconception for the most recent wrong answer on this topic
        misc = None
        for t in reversed(trace):
            if t.get("ok") is False:
                qset = (set_idx.get(t["date"]) or {}).get(t.get("id"))
                misc = misconception(t, qset)
                if misc:
                    break

        for s in (detect_resolved(topic, trace, subject),
                  detect_trending(topic, trace, subject, was_flagged),
                  detect_to_close(topic, trace, subject, misc)):
            if s:
                # the ledger position travels with the story so the page can show
                # it as a SCALE (where it sits) rather than a verdict
                s["state"] = tp.get("state")
                s["depth"] = tp.get("depth")
                stories.append(s)
                break                      # one story per topic — the strongest

    # depth movement stories
    for tp in topics:
        name = tp.get("topic")
        after = tp.get("depth")
        s = detect_deepened(name, tp.get("subject"), depth_before.get(name), after,
                            tp.get("depth_evidence"))
        if s:
            stories.append(s)

    cw, tot = confident_wrong(runs, student, week_days)
    w = detect_watching(cw, tot)
    if w:
        stories.append(w)

    stories.sort(key=lambda s: -s.get("weight", 0))
    return stories[:max_stories]
