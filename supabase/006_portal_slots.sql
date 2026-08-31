-- 006: parent-portal schedule slots (PARENT-PORTAL-BRIEF wiring; Rich's
-- go-live directive, 31 Aug 2026).
--
-- ADDITIVE: xp_schedule ROWS only — no function, table, or existing-row
-- changes. The dispatcher fires workflows with no inputs, so the behaviour
-- of a scheduled run lives in tools/portal_run.py: every active seat's four
-- pages republish; the Monday pointer SMS sends only for seats in
-- POINTER_LIVE (t1 at go-live; promotion by PR).
--
--   portal-monday    18:45 Mon  after the kid's 4pm quiz (reveal-order law)
--                               and clear of soundbyte-1 at 18:30; the ahead
--                               page carries the sweep's new week + pointer.
--   portal-friday    21:15 Fri  after friday-report's 20:35 target rung, so
--                               the weekly update + overall picture catch the
--                               fresh week even if the report job's own
--                               portal republish (friday_report_run) failed.
--   portal-saturday  08:00 Sat  heal: after friday-report's 07:30 Sat last
--                               resort, the portal catches whatever Friday
--                               data finally landed. No SMS ever (not Monday).
--
-- GitHub backup crons live in parent-portal.yml (19:05 Mon / 21:35 Fri AEST);
-- publishing is idempotent and the pointer is week-cursor-guarded, so any
-- double-fire is a no-op.

insert into public.xp_schedule (job, workflow, local_time, days) values
  ('portal-monday',   'parent-portal.yml', '18:45', '{1}'),
  ('portal-friday',   'parent-portal.yml', '21:15', '{5}'),
  ('portal-saturday', 'parent-portal.yml', '08:00', '{6}')
on conflict (job) do nothing;

-- verify:
--   select job, workflow, local_time, days, enabled
--     from public.xp_schedule where workflow = 'parent-portal.yml'
--    order by days, local_time;
