-- 007: weekly-sweep schedule slot (B6 PROMOTION — Rich's GO, 31 Aug 2026).
--
-- ADDITIVE: one xp_schedule row, nothing else. The Monday Canvas sweep
-- becomes a first-class pg_cron citizen: 07:07 Sydney, TZ-aware (the
-- 4 Oct AEDT change is a non-event), firing sweep-shadow.yml via
-- workflow_dispatch exactly like every other slot. GitHub's own cron in
-- that workflow is DEMOTED to a Sun 22:07 UTC backup (Mon 08:07 AEST) and
-- is guarded: a schedule-event run skips itself when this week's targets
-- file already exists, so scheduler double-fire is a designed no-op.
--
--   sweep-0707-mon  07:07 Mon  fetch -> summarise -> docx alert ->
--                              schedule-pass -> rotation overrides ->
--                              VALIDATE (the gate) -> PROMOTE
--                              targets/<monday>.json -> diff -> commit.
--
-- FAIL = HOLD: a validator FAIL means nothing promotes; the pipeline
-- falls back to the newest existing targets file with its loud staleness
-- warning. LAW preserved: Monday's quiz never depends on the sweep.
-- Teachers post Sun night/Mon morning; 07:07 output feeds Monday's 2pm
-- run onward, and the 18:45 portal-monday slot carries the new week.

insert into public.xp_schedule (job, workflow, local_time, days) values
  ('sweep-0707-mon', 'sweep-shadow.yml', '07:07', '{1}')
on conflict (job) do nothing;

-- verify:
--   select job, workflow, local_time, days, enabled
--     from public.xp_schedule where job = 'sweep-0707-mon';
