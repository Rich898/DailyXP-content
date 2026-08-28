#!/usr/bin/env python3
"""test_delivery_confirm.py — the Friday parent send must not mark a report
'sent' unless it truly was.

Two failure modes are locked here:
  1. friday_report_run gated the weekly cursor on `if notify.send_sms(...)` —
     but send_sms returns a (ok, detail) TUPLE, which is always truthy, so the
     cursor advanced even on a hard failure. _send_and_mark must gate on `ok`.
  2. A Mobile Message 2xx means ACCEPTED, not delivered: a bad number / no-credit
     account is a per-message rejection inside a 200 body. notify._delivery_ok
     must catch a recognised rejection, while NEVER false-failing a real success
     (fail-open on any unfamiliar body — a false fail would block a good send).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import notify  # noqa: E402
import friday_report_run as frr  # noqa: E402


def t(name, cond):
    assert cond, f"FAIL: {name}"
    print(f"  [PASS] {name}")


print("notify._delivery_ok — fail on a recognised rejection, fail-open otherwise:")
t("all-success results -> accepted",
  notify._delivery_ok('{"results":[{"status":"success"},{"status":"success"}]}')[0] is True)
t("a rejected message -> NOT accepted",
  notify._delivery_ok('{"results":[{"status":"success"},{"status":"invalid"}]}')[0] is False)
t("'failed' status -> NOT accepted",
  notify._delivery_ok('{"results":[{"status":"failed"}]}')[0] is False)
t("rejection detail is a PII-free summary (no number, no message text)",
  "message(s)" in notify._delivery_ok('{"results":[{"status":"invalid","to":"+61400000000"}]}')[1]
  and "+61400000000" not in notify._delivery_ok('{"results":[{"status":"invalid","to":"+61400000000"}]}')[1])
t("unknown status word is treated as accepted (never false-fail)",
  notify._delivery_ok('{"results":[{"status":"queued"}]}')[0] is True)
t("body with no results list -> accepted (fail-open)",
  notify._delivery_ok('{"status":"ok"}')[0] is True)
t("unparseable 2xx body -> accepted (fail-open)",
  notify._delivery_ok('OK')[0] is True)
t("top-level list of results is read too",
  notify._delivery_ok('[{"status":"success"},{"status":"rejected"}]')[0] is False)


print("\nfriday_report_run._send_and_mark — cursor advances ONLY on ok=True:")


def _run(monkeyed_return):
    calls = {}

    def fake_send(target, text, ref=None, dry_run=False):
        calls["target"] = target
        return monkeyed_return

    orig = notify.send_sms
    notify.send_sms = fake_send
    try:
        cursor, sent, skipped = {}, [], []
        ok = frr._send_and_mark("y8", "body text", cursor, "2026-08-24", sent, skipped)
        return ok, cursor, sent, skipped, calls
    finally:
        notify.send_sms = orig


ok, cursor, sent, skipped, calls = _run((True, '{"results":[{"status":"success"}]}'))
t("success advances the cursor", cursor.get("y8") == "2026-08-24")
t("success marks the seat sent", sent == ["y8"] and skipped == [])
t("success routes to the parent seat", calls["target"] == "parents:y8")

ok, cursor, sent, skipped, _ = _run((False, "HTTP 500: upstream error"))
t("a transport failure does NOT advance the cursor", "y8" not in cursor)
t("a transport failure marks the seat skipped, not sent", sent == [] and skipped == ["y8"])

ok, cursor, sent, skipped, _ = _run((False, "provider rejected 1/1 message(s): ['invalid']"))
t("a per-message rejection does NOT advance the cursor", "y8" not in cursor)

# The original bug in one assertion: a raw (ok, detail) tuple is always truthy.
t("regression: a (False, ...) tuple is still truthy (why `if send_sms(...)` was wrong)",
  bool((False, "anything")) is True)

print("\n✓ all delivery-confirmation tests green")
