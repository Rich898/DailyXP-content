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


def fetch_supabase(sb_url, sb_key, timeout=45):
    """All rows from the Supabase sink (runs_raw), oldest first. Service key —
    server secret only. Returns [{'received_at', 'payload'}...]."""
    q = urllib.parse.urlencode({"select": "id,received_at,payload",
                                "order": "id.asc"})
    req = urllib.request.Request(
        f"{sb_url.rstrip('/')}/rest/v1/runs_raw?{q}",
        # New Supabase API-key mode (sb_secret_*): the role is derived from the
        # apikey header itself; Authorization is reserved for user JWTs.
        headers={"apikey": sb_key, "User-Agent": "dailyxp-ingest/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except Exception as e:
        raise SystemExit(f"ingest: could not reach Supabase ({e}). "
                         "Check SUPABASE_URL / SUPABASE_SERVICE_KEY.")


def sb_rows_to_dicts(rows):
    """Supabase rows → (row_dicts for normalise, prenormalised runs, errors).

    Two payload shapes coexist in the sink: RAW shell payloads (the live
    write path) and PRE-NORMALISED runs (the migration seed came from
    runs.json). Pre-normalised rows skip normalise() — re-normalising an
    already-normalised run would mangle it — and rejoin at the dedupe step.
    """
    raw_dicts, pre, errors = [], [], []
    for n, r in enumerate(rows, start=1):
        p = r.get("payload")
        if not isinstance(p, dict):
            errors.append(f"supabase row {n}: payload not an object")
            continue
        if "run_date" in p and "questions" in p:      # pre-normalised (seeded)
            pre.append(p)
            continue
        raw_dicts.append({
            "received_at": r.get("received_at") or "",
            "student": p.get("student", ""),
            "quiz_date": p.get("date", ""),
            "day": p.get("day", ""),
            "attempt": p.get("attempt", ""),
            "score": p.get("score", ""),
            "payload": p,
        })
    return raw_dicts, pre, errors


def carry_annotations(private_dir, runs):
    """Grades survive the rebuild: tb_grade / tb_integrity written by Friday's
    grading pass live in runs.json, which this ingest regenerates wholesale.
    Carry them forward onto the matching (student, ts) rows so a Monday ingest
    never wipes a Friday's judgements."""
    try:
        old = json.load(open(os.path.join(private_dir, "work", "runs.json")))["runs"]
    except Exception:
        return 0
    keyed = {}
    for r in old:
        tq = next((q for q in r.get("questions", []) if q.get("phase") == "teach"), None)
        if tq and (tq.get("tb_grade") or tq.get("tb_integrity")):
            keyed[(r.get("student"), r.get("ts") or r.get("ts_raw"))] = tq
    carried = 0
    for r in runs:
        src = keyed.get((r.get("student"), r.get("ts") or r.get("ts_raw")))
        if not src:
            continue
        tq = next((q for q in r.get("questions", []) if q.get("phase") == "teach"), None)
        if tq is None:
            continue
        for k in ("tb_grade", "tb_integrity"):
            if src.get(k) and not tq.get(k):
                tq[k] = src[k]
                carried += 1
    return carried


def _ser(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError


def ingest(private_dir, url=None, key=None, sb_url=None, sb_key=None, source=None):
    """source: 'sheet' | 'supabase' | 'both' (both = sheet is truth, supabase
    is compared and reported — the settling-week mode). Default: whichever
    credentials exist; both sets present -> 'both'."""
    have_sheet, have_sb = bool(url and key), bool(sb_url and sb_key)
    source = source or ("both" if have_sheet and have_sb
                        else "supabase" if have_sb else "sheet")
    if source in ("sheet", "both") and not have_sheet:
        raise SystemExit("ingest: RESULTS_URL / RESULTS_KEY not set.")
    if source in ("supabase", "both") and not have_sb:
        raise SystemExit("ingest: SUPABASE_URL / SUPABASE_SERVICE_KEY not set.")

    agree = ""
    if source == "supabase":
        sb_raw, pre, errors = sb_rows_to_dicts(fetch_supabase(sb_url, sb_key))
        runs = [normalise(r) for r in sb_raw] + pre
        n_in = len(sb_raw) + len(pre)
    else:
        rows = fetch_rows(url, key)
        row_dicts, errors = rows_to_dicts(rows)
        runs = [normalise(r) for r in row_dicts]
        n_in = len(rows) - 1
        if source == "both":
            try:
                sb_raw, pre, sb_err = sb_rows_to_dicts(fetch_supabase(sb_url, sb_key))
                sheet_keys = {(r.get("student"), r.get("run_date")) for r in runs}
                sb_runs = [normalise(r) for r in sb_raw] + pre
                sb_keys = {(r.get("student"), r.get("run_date")) for r in sb_runs}
                missing = sorted(sheet_keys - sb_keys)
                agree = (f"; supabase sink: {len(sb_keys & sheet_keys)}/{len(sheet_keys)} "
                         f"run-days present" + (f", MISSING {missing}" if missing else " — agrees"))
            except SystemExit as e:
                agree = f"; supabase sink UNREACHABLE ({e}) — sheet remains truth"

    runs, dropped = dedupe(runs)
    tests = [r for r in runs if r["is_test"]]
    runs = mark_canonical([r for r in runs if not r["is_test"]])
    carried = carry_annotations(private_dir, runs)
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
    summary = (f"ingest[{source}]: {n_in} row(s) → {len(runs)} run(s) kept ({by}); "
               f"{len(dropped)} duplicate(s) dropped; {len(tests)} test row(s) ignored"
               + (f"; {carried} grade annotation(s) carried forward" if carried else "")
               + (f"; {len(errors)} parse error(s)" if errors else "") + agree)
    return summary, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--url", default=os.environ.get("RESULTS_URL"))
    ap.add_argument("--key", default=os.environ.get("RESULTS_KEY"))
    ap.add_argument("--source", default=os.environ.get("INGEST_SOURCE"),
                    choices=[None, "sheet", "supabase", "both"],
                    help="sheet | supabase | both (default: whichever credentials exist)")
    a = ap.parse_args()
    summary, errors = ingest(a.private_dir, a.url, a.key,
                             sb_url=os.environ.get("SUPABASE_URL"),
                             sb_key=os.environ.get("SUPABASE_SERVICE_KEY"),
                             source=a.source)
    print(summary)
    for e in errors:
        print(f"  ⚠ {e}")


if __name__ == "__main__":
    main()
