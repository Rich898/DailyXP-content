#!/usr/bin/env python3
"""
supabase_pull.py — read new shell results from Supabase (the runs_raw sink)
and hand them to the SAME ingest path the Apps Script sheet feeds today.

The cutover shape (ROADMAP.md): the shell dual-writes to Supabase + Apps Script
for a settling week; this reader runs alongside the sheet reader; when the two
agree for a week, the sheet retires. One payload contract, two transports.

Env:
  SUPABASE_URL          https://<project-ref>.supabase.co
  SUPABASE_SERVICE_KEY  service_role key (Dashboard → Settings → API). Server
                        secret ONLY — Actions secret, never the shell, never
                        the public repo. (The shell holds the ANON key, which
                        RLS restricts to insert-only.)

Usage:
  python3 tools/supabase_pull.py --private-dir ../DailyXP-private            # print + advance cursor
  python3 tools/supabase_pull.py --private-dir ../DailyXP-private --dry-run  # print only

Output: one JSON payload per line on stdout — exactly what the shell POSTed —
for ingest_results.py to consume. Cursor: work/supabase_pull_cursor.json
(last runs_raw id seen), so every pull is idempotent and re-runs are no-ops.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

CURSOR = os.path.join("work", "supabase_pull_cursor.json")


def _cursor_path(private_dir):
    return os.path.join(private_dir, CURSOR)


def load_cursor(private_dir):
    try:
        return int(json.load(open(_cursor_path(private_dir))).get("last_id", 0))
    except (OSError, ValueError):
        return 0


def save_cursor(private_dir, last_id):
    p = _cursor_path(private_dir)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump({"last_id": int(last_id)}, open(p, "w"), indent=2)


def fetch_new(url, key, after_id, limit=200):
    """Rows with id > after_id, oldest first. PostgREST over the REST API —
    service key bypasses RLS (this is the read side the anon key never gets)."""
    q = urllib.parse.urlencode({
        "select": "id,received_at,payload",
        "id": f"gt.{after_id}",
        "order": "id.asc",
        "limit": str(limit),
    })
    req = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/runs_raw?{q}",
        headers={"apikey": key})  # sb_secret_* key: role from apikey; no Bearer
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    ap.add_argument("--dry-run", action="store_true", help="print, don't advance the cursor")
    a = ap.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("SUPABASE_URL / SUPABASE_SERVICE_KEY not set", file=sys.stderr)
        return 2

    last = load_cursor(a.private_dir)
    rows = fetch_new(url, key, last)
    for row in rows:
        print(json.dumps(row["payload"], ensure_ascii=False))
    if rows and not a.dry_run:
        save_cursor(a.private_dir, rows[-1]["id"])
    print(f"supabase_pull: {len(rows)} new row(s) after id {last}"
          + (" (dry-run, cursor held)" if a.dry_run else ""), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
