"""Tests for compose.py's no-repeat retry behaviour — the y8 H6.5 seat-down fix
(4 Sep 2026): repeat-only failures extend the retry budget, every retry names all
of a slot's rejected prompts, and a mis-shaped single-slot splice reply is rescued
instead of silently burning the round.

call_api is stubbed with a scripted list of replies; validation runs for real
against a temp history dir, so the no-repeat gate is exercised honestly.
"""
import json
import os
import tempfile

import compose


SEEN = ["Seen Q1", "Seen Q2", "Seen Q3"]


def _mc(prompt):
    return {"prompt": prompt, "options": ["a", "b", "c", "d"], "answer": "a",
            "why": "because a."}


def _plan():
    return {"student": "y8", "date": "2026-09-04", "day": "FRI", "tag": "H6.5",
            "slots": [
                {"slot": "S1", "phase": "speed", "subject": "English",
                 "topic": "Romeo and Juliet", "intent": "test", "guidance": ""},
                {"slot": "TB", "phase": "teach", "subject": "English",
                 "topic": "Romeo and Juliet", "intent": "teach", "guidance": ""},
            ]}


def _history_dir(tmp):
    """A real archive so validate's no-repeat gate flags SEEN prompts."""
    d = os.path.join(tmp, "y8")
    os.makedirs(d)
    with open(os.path.join(d, "2026-08-01_H1.1.json"), "w") as f:
        json.dump({"questions": [{"prompt": p} for p in SEEN]}, f)
    return tmp


class _FakeAPI:
    """Serves scripted reply payloads in order; records every user message."""

    def __init__(self, replies):
        self.replies = [json.dumps(r) for r in replies]
        self.users = []

    def __call__(self, system, user, model, api_key):
        self.users.append(user)
        if not self.replies:
            raise AssertionError("compose called the API more times than scripted")
        return self.replies.pop(0)


def _run(replies, plan=None):
    fake, real = _FakeAPI(replies), compose.call_api
    compose.call_api = fake
    try:
        with tempfile.TemporaryDirectory() as tmp:
            s, errs = compose.compose_set(plan or _plan(), api_key="test-key",
                                          history_dir=_history_dir(tmp))
    finally:
        compose.call_api = real
    return s, errs, fake


# ------------------------------------------------- repeat pressure earns budget --

def test_repeat_only_failure_extends_budget_past_default():
    # Rounds 1-3 all collide with seen prompts — the old budget (2 retries) gave up
    # here. Round 4 lands a fresh prompt and must be allowed to run.
    s, errs, fake = _run([
        {"S1": _mc("Seen Q1"), "TB": {"prompt": "Explain the brawl."}},
        {"S1": _mc("Seen Q2")},
        {"S1": _mc("Seen Q3")},
        {"S1": _mc("Fresh question about the Prince's decree?")},
    ])
    assert s is not None, f"compose should have succeeded on the 4th attempt: {errs}"
    assert len(fake.users) == 4
    assert s["questions"][0]["prompt"] == "Fresh question about the Prince's decree?"


def test_retry_names_every_rejected_prompt():
    s, errs, fake = _run([
        {"S1": _mc("Seen Q1"), "TB": {"prompt": "Explain the brawl."}},
        {"S1": _mc("Seen Q2")},
        {"S1": _mc("Seen Q3")},
        {"S1": _mc("A fresh one?")},
    ])
    assert s is not None
    # the 4th call must carry the full reject history, not just the last one
    last = fake.users[-1]
    assert "ALL were rejected as repeats" in last
    for p in ("Seen Q1", "Seen Q2", "Seen Q3"):
        assert p in last, f"retry objection should name {p!r}"


def test_non_repeat_failure_keeps_the_small_budget():
    # An answer-shape error (not REPEATS) must NOT earn extra rounds: default budget
    # is 2 retries -> exactly 3 API calls, then give up.
    bad = {"prompt": "Fine prompt?", "options": ["a", "b", "c", "d"],
           "answer": "not-an-option", "why": "w"}
    s, errs, fake = _run([
        {"S1": dict(bad), "TB": {"prompt": "Explain."}},
        {"S1": dict(bad)},
        {"S1": dict(bad)},
    ])
    assert s is None
    assert len(fake.users) == 3
    assert any("answer" in e for e in errs)


# ------------------------------------------------- mis-shaped splice reply rescue --

def test_bare_object_splice_reply_is_accepted_for_a_single_slot():
    # The retry asks for {"S1": {...}} but the model sends the bare question object.
    # Before the fix this changed nothing and the round burned with the same error.
    s, errs, fake = _run([
        {"S1": _mc("Seen Q1"), "TB": {"prompt": "Explain the brawl."}},
        _mc("A genuinely new question?"),          # bare — no slotId key
    ])
    assert s is not None, f"bare single-slot reply should be rescued: {errs}"
    assert len(fake.users) == 2
    assert s["questions"][0]["prompt"] == "A genuinely new question?"


def test_keyed_splice_reply_still_works():
    s, errs, fake = _run([
        {"S1": _mc("Seen Q1"), "TB": {"prompt": "Explain the brawl."}},
        {"S1": _mc("A genuinely new question?")},  # properly keyed
    ])
    assert s is not None
    assert len(fake.users) == 2
    assert s["questions"][0]["prompt"] == "A genuinely new question?"
