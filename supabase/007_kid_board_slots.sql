-- 007: kid-board pg_cron slots (APPLIED 31 Aug 2026 via MCP, verified).
-- The Monday board publish (KID-WEEKLY-FRAMEWORK.md) joins xp_schedule as
-- pg_cron primary per the B1 doctrine — everything schedules from Supabase;
-- GitHub crons in kid-board.yml remain the demoted, cursor-guarded backup.
-- Two rungs, both before the 16:00 kid-nudge slot; publishing is idempotent
-- + stamp-verified, so a double fire is a no-op.
insert into xp_schedule (job, workflow, local_time, days, enabled) values
  ('kid-board-1440', 'kid-board.yml', '14:40:00', '{1}', true),
  ('kid-board-1510', 'kid-board.yml', '15:10:00', '{1}', true);
