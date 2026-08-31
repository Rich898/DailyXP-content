#!/usr/bin/env python3
"""Regression test for notify._recipients — focus: the kid_comms_via redirect
(31 Aug 2026: the y9 US-phone gap — a kid seat with no number of its own rides
its OWN parent seat, by explicit roster opt-in, never by silent fallback).

Runnable in CI: `python3 tools/test_notify_routing.py` (exit 0 = all pass).
Fake numbers only; env is patched and restored.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import notify  # noqa: E402

KEYS = ("MOBILE_MESSAGE_TO_Y8", "MOBILE_MESSAGE_TO_Y9", "MOBILE_MESSAGE_TO_T1",
        "MOBILE_MESSAGE_PARENTS_Y8", "MOBILE_MESSAGE_PARENTS_Y9",
        "MOBILE_MESSAGE_TO_PARENTS", "SECRETS_CONTEXT")
_saved = {k: os.environ.get(k) for k in KEYS}
for k in KEYS:
    os.environ.pop(k, None)

cases = []
def check(name, cond, detail=""):
    cases.append((name, cond))
    if not cond:
        print(f"  FAIL {name}  [{detail}]")


try:
    # the real roster carries the y9 flag — the redirect reaches THAT kid's parent seat
    os.environ["MOBILE_MESSAGE_PARENTS_Y9"] = "+61400000001"
    got = notify._recipients("y9")
    check("y9 (no TO_Y9, roster flag) -> its own parent seat", got == ["+61400000001"], str(got))

    # a real kid number ALWAYS wins over the redirect
    os.environ["MOBILE_MESSAGE_TO_Y9"] = "+61400000002"
    got = notify._recipients("y9")
    check("TO_Y9 set -> the kid's own number wins", got == ["+61400000002"], str(got))
    del os.environ["MOBILE_MESSAGE_TO_Y9"]

    # no roster flag, no number -> empty (senders abort loudly; never a silent fallback)
    os.environ["MOBILE_MESSAGE_PARENTS_Y8"] = "+61400000003"
    got = notify._recipients("y8")
    check("y8 (no flag) -> empty, parent secret NOT borrowed", got == [], str(got))

    # the parent seat itself is untouched by the flag
    got = notify._recipients("parents:y9")
    check("parents:y9 resolves its own secret as before", got == ["+61400000001"], str(got))

    # legacy shared group unchanged
    os.environ["MOBILE_MESSAGE_TO_PARENTS"] = "+61400000004,+61400000005"
    got = notify._recipients("parents")
    check("legacy 'parents' group unchanged", got == ["+61400000004", "+61400000005"], str(got))

    # an unknown code never redirects
    got = notify._recipients("zz")
    check("unknown seat -> empty", got == [], str(got))
finally:
    for k, v in _saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

ok = all(c for _, c in cases)
print("notify routing:")
for n, c in cases:
    print(f"  [{'PASS' if c else 'FAIL'}] {n}")
print("ALL PASS ✓" if ok else "FAILURES ✗")
sys.exit(0 if ok else 1)
