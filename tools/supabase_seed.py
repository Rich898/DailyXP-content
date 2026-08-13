#!/usr/bin/env python3
"""
supabase_seed.py — regenerate private/supabase/seed_runs.sql from runs.json.

The seed carries kid data, so it lives in the PRIVATE repo (two-repo law:
public is code-only). Re-run right before the Saturday migration so the seed
captures every run up to the cutover minute; paste the output file into the
Supabase SQL editor after 001_schema.sql.

Usage: python3 tools/supabase_seed.py --private-dir ../DailyXP-private
"""
import argparse
import json
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private-dir", required=True)
    a = ap.parse_args()
    runs = json.load(open(os.path.join(a.private_dir, "work", "runs.json")))["runs"]
    out = ["-- seed_runs.sql — migrate existing runs into runs_raw (paste after 001_schema.sql)",
           "-- GENERATED FILE (tools/supabase_seed.py) — lives in the PRIVATE repo: it carries kid data.",
           "begin;"]
    for r in runs:
        blob = json.dumps(r, ensure_ascii=False).replace("'", "''")
        out.append(f"insert into public.runs_raw (payload) values ('{blob}'::jsonb);")
    out.append("commit;")
    dest = os.path.join(a.private_dir, "supabase", "seed_runs.sql")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    open(dest, "w").write("\n".join(out) + "\n")
    print(f"wrote {dest}: {len(runs)} runs")


if __name__ == "__main__":
    main()
