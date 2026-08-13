-- 002_scheduler.sql — XP Daily Supabase, step 2: THE SCHEDULER
--
-- pg_cron ticks every minute; xp_dispatch() compares Sydney wall-clock time
-- against the xp_schedule table and fires each due job ONCE per local day via
-- GitHub's workflow_dispatch API (pg_net). GitHub cron stays enabled as the
-- demoted backup — two independent schedulers, and every downstream job is
-- cursor-guarded so a double trigger is a no-op.
--
-- BEFORE RUNNING: store the GitHub token in Vault (Dashboard → Project
-- Settings → Vault → New secret), name it exactly:  github_dispatch_pat
-- The token must be a fine-grained PAT scoped to Rich898/DailyXP-content with
-- Actions: Read and write. (The existing DAILYXP_TOKEN can't dispatch — it
-- 403s on the Actions API — so mint this one fresh.)

create extension if not exists pg_cron;
create extension if not exists pg_net;

create or replace function public.xp_dispatch()
returns void
language plpgsql
security definer
as $$
declare
  syd timestamptz := now() at time zone 'utc';   -- placeholder, real calc below
  local_now timestamp := (now() at time zone 'Australia/Sydney');
  today date := local_now::date;
  dow int := extract(isodow from local_now)::int;
  r record;
  tok text;
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
    perform net.http_post(
      url := format('https://api.github.com/repos/Rich898/DailyXP-content/actions/workflows/%s/dispatches', r.workflow),
      headers := jsonb_build_object(
        'Authorization', 'Bearer ' || tok,
        'Accept', 'application/vnd.github+json',
        'User-Agent', 'xpdaily-scheduler',
        'X-GitHub-Api-Version', '2022-11-28'
      ),
      body := jsonb_build_object('ref', 'main')
    );
    raise notice 'xp_dispatch: fired % (%)', r.job, r.workflow;
  end loop;
end;
$$;

-- Every minute. The 10-minute due-window above means a paused/slow tick can't
-- silently skip a slot, and the dispatch_log dedupe means it can't double-fire.
select cron.schedule('xp-dispatcher', '* * * * *', $$select public.xp_dispatch()$$);

-- Verify after a scheduled slot passes:
--   select * from public.xp_dispatch_log order by fired_at desc limit 10;
--   select * from net._http_response order by created desc limit 10;  -- 204 = dispatched
