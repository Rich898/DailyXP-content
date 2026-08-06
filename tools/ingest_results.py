#!/usr/bin/env python3
"""
ingest_results.py — headless results ingestion (closes the results→state loop).

The cron can't read the results Sheet the way a chat session can. This fetches the rows from
a token-gated Apps Script endpoint (a standalone READ-ONLY doGet — it never touches the quiz
webhook) and refreshes `{private}/work/runs.json`, which the state-writer then applies.

It reuses results_reader end-to-end (parse payloads → normalise → dedupe → drop SYSTEM TEST →
mark canonical → phase medians) and writes the SAME JSON shape results_reader --json produces,
so nothing downstream changes.

Config (env, injected as Actions secrets; or CLI flags):
  RESULTS_URL   the /exec endpoint (WITHOUT the key)
  RESULTS_KEY   the shared secret (matches the script's INGEST_KEY property)

This runs inside the PUBLIC repo's workflow, whose logs are public — so it prints only counts
and y8/y9 codes, never names, scores, or payloads.

Usage:
  RESULTS_URL=… RESULTS_KEY=… python3 tools/ingest_results.py --private-dir ../DailyXP-private
  python3 tools/ingest_results.py --private-dir ../DailyXP-private --url … --key …
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from results_reader import normalise, dedupe, mark_canonical, phase_medians  # noqa: E402


def fetch_rows(base_url, key, timeout=45):
    """GET base_url?key=… and return the 2-D `rows` array. Raises with a clear message."""
    sep = "&" if "?" in base_url else "?"
    url = base_url + sep + urllib.parse.urlencode({"key": key})
    req = urllib.request.Request(url, headers={"User-Agent": "dailyxp-ingest/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
    except Exception as e:
        raise SystemExit(f"ingest: could not reach RESULTS_URL ({e}). "
                         "Check the endpoint is deployed and the URL secret is correct.")
    stripped = body.strip()
    if stripped == "unauthorized":
        raise SystemExit("ingest: endpoint returned 'unauthorized' — RESULTS_KEY does not match "
                         "the script's INGEST_KEY. Re-check both values.")
    try:
        data = json.loads(body)
    except Exception:
        raise SystemExit("ingest: endpoint did not return JSON (got HTML/error). "
                         "Open the URL+key in a browser to see what it says.")
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise SystemExit("ingest: endpoint returned no rows. Is the 'results' tab empty, "
                         "or is TAB_NAME wrong in the script?")
    return rows


def rows_to_dicts(rows):
    """2-D sheet array (row 0 = header) → the row-dicts results_reader.normalise expects."""
    header = [str(h).strip() for h in rows[0]]
    idx = {name: i for i, name in enumerate(header)}
    # payload column by name, else the last column, else the first cell that looks like JSON
    pay_i = idx.get("payload_json")
    out, errors = [], []

    def cell(r, name):
        i = idx.get(name)
        return "" if i is None or i >= len(r) else r[i]

    for n, r in enumerate(rows[1:], start=2):
        if not any(str(c).strip() for c in r):
            continue  # blank trailing row
        raw = r[pay_i] if (pay_i is not None and pay_i < len(r)) else ""
        if not str(raw).strip():
            # fall back: first cell containing a JSON object
            raw = next((c for c in r if isinstance(c, str) and c.lstrip().startswith("{")), "")
        try:
            payload = json.loads(raw)
        except Exception as e:
            errors.append(f"row {n}: payload not JSON ({e})")
            continue
        out.append({
            "received_at": cell(r, "received_at"),
            "student": cell(r, "student"),
            "quiz_date": cell(r, "quiz_date"),
            "day": cell(r, "day"),
            "attempt": cell(r, "attempt"),
            "score": cell(r, "score"),
            "payload": payload,
        })
    return out, errors


def _ser(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError


def ingest(private_dir, url, key):
    rows = fetch_rows(url, key)
    row_dicts, errors = rows_to_dicts(rows)
    runs = [normalise(r) for r in row_dicts]
    runs, dropped = dedupe(runs)
    tests = [r for r in runs if r["is_test"]]
    runs = mark_canonical([r for r in runs if not r["is_test"]])
    medians = phase_medians(runs)

    out_path = os.path.join(private_dir, "work", "runs.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"runs": runs, "medians": {f"{k[0]}:{k[1]}": v for k, v in medians.items()}},
                  f, default=_ser, indent=2, ensure_ascii=False)

    # public-safe summary: counts + student codes only (no names/scores/payloads)
    per_student = {}
    for r in runs:
        per_student[r["student"]] = per_student.get(r["student"], 0) + 1
    by = ", ".join(f"{s}: {n}" for s, n in sorted(per_student.items())) or "none"
    summary = (f"ingest: {len(rows) - 1} data row(s) → {len(runs)} run(s) kept ({by}); "
               f"{len(dropped)} duplicate(s) dropped; {len(tests)} test row(s) ignored"
               + (f"; {len(errors)} parse error(s)" if errors else ""))
    return summary, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--url", default=os.environ.get("RESULTS_URL"))
    ap.add_argument("--key", default=os.environ.get("RESULTS_KEY"))
    a = ap.parse_args()
    if not a.url or not a.key:
        raise SystemExit("ingest: RESULTS_URL / RESULTS_KEY not set (env or --url/--key).")
    summary, errors = ingest(a.private_dir, a.url, a.key)
    print(summary)
    for e in errors:
        print(f"  ⚠ {e}")


if __name__ == "__main__":
    main()
