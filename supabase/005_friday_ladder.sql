-- 005_friday_ladder.sql — XP Daily Supabase, step 5: THE FRIDAY CATCH-UP LADDER
--
-- PARENT-COMMS-BUILD-BRIEF.md, work item W1 (ACTIONS.md B1). GitHub skipped all
-- three Friday-report crons on 28 Aug — the send only landed because Rich pressed
-- the button. pg_cron already fires the 20:35 rung (proven live 28 Aug: job
-- 'friday-report', req 86, HTTP 204), but the seed carried only that ONE rung,
-- while friday-report.yml runs a FOUR-rung GitHub ladder (20:35 / 21:05 / 21:45
-- Fri + 07:30 Sat) so a dropped or 401'd first fire is retried. This migration
-- gives pg_cron the same ladder, so the Friday send no longer depends on
-- GitHub's flaky scheduler for its resilience either. The weekly send cursor
-- (one send per kid per week, tools/friday_report_run.py) makes every extra rung
-- a no-op once the report is out — exactly as the GitHub ladder has always been.
--
-- Naming normalises to the time-suffixed convention the brief specifies:
-- friday-report-2035 / -2105 / -2145 / -0730-sat. Nothing keys off the old
-- 'friday-report' job string (Tripwire 1 reads xp_dispatch_log by status, not by
-- job; watchdog.py's "friday-report" is display text) — verified before renaming.
--
-- OBSERVATIONAL/ADDITIVE: touches only xp_schedule ROWS. It does not change the
-- dispatcher function or any send code. Safe to re-run (rename is a no-op once
-- applied; inserts are on-conflict-do-nothing). Apply outside the Sydney evening
-- send window (17:30–22:15 weekdays) as a matter of habit; this one is data-only.

-- 20:35 Fri — the target rung, renamed in place (same workflow, time and day).
update public.xp_schedule
   set job = 'friday-report-2035'
 where job = 'friday-report';

-- The catch-up rungs: identical to GitHub's, cursor-guarded no-ops once sent.
insert into public.xp_schedule (job, workflow, local_time, days) values
  ('friday-report-2105',    'friday-report.yml', '21:05', '{5}'),  -- catch-up
  ('friday-report-2145',    'friday-report.yml', '21:45', '{5}'),  -- catch-up
  ('friday-report-0730-sat','friday-report.yml', '07:30', '{6}')   -- last resort
on conflict (job) do nothing;

-- Verify:
--   select job, workflow, local_time, days, enabled
--     from public.xp_schedule where workflow = 'friday-report.yml' order by days, local_time;
--   -- expect four rows: 20:35 {5}, 21:05 {5}, 21:45 {5}, 07:30 {6}
