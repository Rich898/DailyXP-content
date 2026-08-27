-- 003_dispatch_manners.sql — XP Daily Supabase, step 3: DISPATCHER MANNERS
--
-- HARDENING-BRIEF.md, work item 1. The lesson of 26 Aug 2026: xp_dispatch()
-- stamped its "fired" row BEFORE GitHub answered, and nothing ever read the
-- reply — so 3.5 hours of 401 Bad credentials sat unseen in net._http_response
-- while xp_dispatch_log.status stayed null. This migration makes the dispatcher
-- record GitHub's real answer.
--
-- OBSERVATIONAL ONLY (shadow by nature): nothing here changes WHAT fires or
-- WHEN. xp_dispatch() fires exactly the same jobs at the same times; it only
-- remembers the pg_net request id so the outcome can be read back. A second,
-- separate minutely job (xp_dispatch_check) settles each row's status from
-- net._http_response after the async POST completes. No alerting yet — that is
-- work item 2 (Tripwire 1), and it ships log-only first.
--
-- APPLY: paste in the Supabase SQL editor, project `xpdaily`. Safe to re-run.
-- Do NOT apply during the Sydney evening send window (17:30–22:15 weekdays):
-- this replaces the live send function, so land it in daylight.

-- ---------------------------------------------------------------- columns --
-- status already exists (001_schema.sql) and has always been null — that IS
-- the bug. Add the correlation key and the sweep's timestamp.
alter table public.xp_dispatch_log add column if not exists request_id bigint;
alter table public.xp_dispatch_log add column if not exists checked_at timestamptz;

-- ------------------------------------------------------------- dispatcher --
-- Identical in behaviour to 002_scheduler.sql except: capture the pg_net
-- request id and write it onto the log row, so the reply can be matched back.
-- The insert still happens BEFORE the POST (unchanged) — that ordering is the
-- once-per-day dedupe guard, not the bug; the bug was never reading the reply.
create or replace function public.xp_dispatch()
returns void
language plpgsql
security definer
as $$
declare
  local_now timestamp := (now() at time zone 'Australia/Sydney');
  today date := local_now::date;
  dow int := extract(isodow from local_now)::int;
  r record;
  tok text;
  req_id bigint;
begin
  select decrypted_secret into tok
    from vault.decrypted_secrets where name = 'github_dispatch_pat';
  if tok is null then
    raise warning 'xp_dispatch: vault secret github_dispatch_pat missing — nothing fired';
    return;
  end if;

  for r in
    select s.job, s.workflow
      from public.xp_schedule s
     where s.enabled
       and dow = any (s.days)
       and local_now::time >= s.local_time
       and local_now::time <  s.local_time + interval '10 minutes'
       and not exists (select 1 from public.xp_dispatch_log l
                        where l.job = s.job and l.local_date = today)
  loop
    insert into public.xp_dispatch_log (job, local_date) values (r.job, today);
    select net.http_post(
      url := format('https://api.github.com/repos/Rich898/DailyXP-content/actions/workflows/%s/dispatches', r.workflow),
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || tok,
        'Accept', 'application/vnd.github+json',
        'User-Agent', 'xpdaily-scheduler',
        'X-GitHub-Api-Version', '2022-11-28'
      ),
      body := jsonb_build_object('ref', 'main')
    ) into req_id;
    update public.xp_dispatch_log
       set request_id = req_id
     where job = r.job and local_date = today;
    raise notice 'xp_dispatch: fired % (%) req=%', r.job, r.workflow, req_id;
  end loop;
end;
$$;

-- ----------------------------------------------------------------- sweep --
-- The async follow-up. net.http_post queues the POST and returns immediately;
-- the reply lands in net._http_response seconds-to-minutes later (kept ~6h).
-- This settles every un-checked row that carries a request id:
--   * response present            -> record its HTTP status_code
--                                    (204 = GitHub accepted; 401/404/etc = a
--                                     real dispatch failure — the 26 Aug signature)
--   * response present, code null  -> 0   (network/TLS error, no HTTP status)
--   * no response 5 min after fire -> -1  (never completed)
-- Writes ONLY to xp_dispatch_log.status/checked_at. Touches nothing on the
-- send path. This settled row is what work item 2's checker will read.
create or replace function public.xp_dispatch_check()
returns void
language plpgsql
security definer
as $$
begin
  -- responses that have arrived
  update public.xp_dispatch_log l
     set status = coalesce(r.status_code, 0),
         checked_at = now()
    from net._http_response r
   where r.id = l.request_id
     and l.request_id is not null
     and l.status is null;

  -- fired and correlated, but still no response 5 minutes later = failure
  update public.xp_dispatch_log l
     set status = -1,
         checked_at = now()
   where l.status is null
     and l.request_id is not null
     and l.fired_at < now() - interval '5 minutes'
     and not exists (select 1 from net._http_response r where r.id = l.request_id);
end;
$$;

-- Every minute; a few rows of work, purely observational. Idempotent re-schedule.
select cron.unschedule('xp-dispatch-check')
 where exists (select 1 from cron.job where jobname = 'xp-dispatch-check');
select cron.schedule('xp-dispatch-check', '* * * * *', $$select public.xp_dispatch_check()$$);

-- Verify after the next scheduled slot (or an accept-test fire):
--   select job, local_date, fired_at, request_id, status, checked_at
--     from public.xp_dispatch_log order by fired_at desc limit 10;
--   -- status 204 = GitHub accepted; 401 = the 26 Aug outage signature;
--   -- -1 = no reply (GitHub/network down); null+recent = not yet settled.
