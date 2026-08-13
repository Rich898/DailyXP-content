-- 001_schema.sql — XP Daily Supabase, step 1: THE RESULTS SINK (+ scheduler bookkeeping)
--
-- ROADMAP.md sequencing: the DATABASE use case is what makes the scheduler
-- trustworthy (free-tier projects pause after inactivity; nightly shell POSTs
-- through the REST API are the activity that keeps it awake). So this file is
-- the Saturday paste; 002_scheduler.sql is the Sunday paste.
--
-- Run in: Supabase SQL editor, project `xpdaily` (its OWN account — never
-- inside VitalYOU's; see ROADMAP.md, Privacy Act reasoning).

-- ---------------------------------------------------------------- runs_raw --
-- One row per shell submission, payload verbatim (jsonb). The shell keeps its
-- existing payload shape; indexable columns are GENERATED from it, so the
-- contract stays loose exactly where ingest_results already tolerates drift.
create table if not exists public.runs_raw (
  id          bigint generated always as identity primary key,
  received_at timestamptz not null default now(),
  student     text generated always as (payload->>'student') stored,
  run_date    text generated always as (payload->>'date') stored,
  tag         text generated always as (payload->>'tag') stored,
  payload     jsonb not null
);
create index if not exists runs_raw_student_date on public.runs_raw (student, run_date);
create index if not exists runs_raw_received on public.runs_raw (received_at);

alter table public.runs_raw enable row level security;

-- The quiz shell is a public static page holding only the ANON key, so anon
-- may INSERT and do nothing else — no select, no update, no delete. Reads go
-- through the service key (tools/supabase_pull.py) which bypasses RLS.
drop policy if exists "shell can insert results" on public.runs_raw;
create policy "shell can insert results"
  on public.runs_raw for insert
  to anon
  with check (true);

-- --------------------------------------------------- scheduler bookkeeping --
-- (Tables now, jobs in 002 — creating them here keeps 002 a pure enable-step.)

-- The schedule lives in a TABLE, in Sydney LOCAL time. DST becomes a non-event:
-- the dispatcher compares against now() AT TIME ZONE 'Australia/Sydney', so
-- 14:00 means 2pm in October exactly as it does in August.
create table if not exists public.xp_schedule (
  job        text primary key,
  workflow   text not null,          -- filename in .github/workflows/
  local_time time not null,          -- Australia/Sydney wall clock
  days       int[] not null,         -- ISO dow: 1=Mon .. 7=Sun
  enabled    boolean not null default true
);

-- One row per (job, local date) — the dispatcher's dedupe, so a job fires
-- exactly once per day however often the cron tick runs.
create table if not exists public.xp_dispatch_log (
  job        text not null,
  local_date date not null,
  fired_at   timestamptz not null default now(),
  status     int,
  primary key (job, local_date)
);

-- Seed: the TARGET times only (GitHub's catch-up ladders exist because GitHub
-- drops runs; pg_cron doesn't, and the ladders stay live on GitHub as the
-- demoted backup — every job is cursor-guarded, so double-triggering is a no-op).
insert into public.xp_schedule (job, workflow, local_time, days) values
  ('daily-quiz',        'daily-quiz.yml',        '14:00', '{1,2,3,4,5}'),
  ('kid-nudge',         'kid-nudge.yml',         '16:00', '{1,2,3,4,5}'),
  ('wed-checkin-early', 'wed-checkin.yml',       '18:25', '{3}'),
  ('wed-checkin-cutoff','wed-checkin.yml',       '20:25', '{3}'),
  ('soundbyte-1',       'evening-soundbyte.yml', '18:30', '{1,2,3,4,5}'),
  ('soundbyte-2',       'evening-soundbyte.yml', '20:00', '{1,2,3,4,5}'),
  ('soundbyte-3',       'evening-soundbyte.yml', '21:30', '{1,2,3,4,5}'),
  ('friday-report',     'friday-report.yml',     '20:35', '{5}'),
  ('watchdog-early',    'watchdog.yml',          '17:35', '{1,2,3,4,5}'),
  ('watchdog-late',     'watchdog.yml',          '21:50', '{1,2,3,4,5}'),
  ('watchdog-friday',   'watchdog.yml',          '22:05', '{5}')
on conflict (job) do nothing;
