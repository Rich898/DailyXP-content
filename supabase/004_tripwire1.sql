-- 004_tripwire1.sql — XP Daily Supabase, step 4: TRIPWIRE 1 (Supabase-side)
--
-- HARDENING-BRIEF.md, work item 2. Item 1 (003_dispatch_manners.sql) made
-- xp_dispatch_log.status tell the truth; this reads that truth on its OWN
-- pg_cron timer and texts Rich the moment a dispatch comes back as anything
-- other than "accepted".
--
-- Independent of the thing it guards — THE lesson of 26 Aug 2026. The old
-- watchdog rode github_dispatch_pat, so the dead token killed the guard and the
-- guarded together. This path touches GitHub not at all:
--     Supabase -> pg_net -> Mobile Message, authed by its OWN Vault secrets.
-- A dead dispatch token cannot silence it. (Blind spot by design: it dies if
-- Supabase itself dies — that half is Tripwire 2's job, work item 3.)
--
-- SHADOW-FIRST. It cannot text until the Mobile Message creds are in the Vault.
-- Until Rich adds them (his hands, dashboard only — secrets law — AFTER a clean
-- observation window), every would-be alert is written to xp_alert_log with
-- shadow=true / sent=false and NOTHING goes out. Adding the creds IS the
-- promotion; no code change flips it.
--
-- PROMOTION — Rich adds these to the Supabase Vault (Dashboard -> Project
-- Settings -> Vault -> New secret), named exactly:
--     mobilemessage_api_key       \  the basic-auth pair — same values the
--     mobilemessage_api_secret    /  GitHub Actions MOBILE_MESSAGE_API_* hold
--     mobilemessage_to_ops         Rich's own handset (the MOBILE_MESSAGE_TO_T1
--                                  number — ops alerts never touch a kid/parent)
--     mobilemessage_sender         optional; defaults to 'XPDaily'
--
-- APPLY: paste in the Supabase SQL editor, project `xpdaily`. Safe to re-run.
-- It only reads the send path, but land it in daylight anyway.

-- --------------------------------------------------------------- alert log --
-- One row per distinct failure (job + local_date + status). The unique key is
-- the dedupe: a failure is alerted once, not every minute the cron ticks. It
-- also means a failure first seen in shadow is already logged, so promotion
-- will NOT retro-text old failures — arming affects only failures seen after.
create table if not exists public.xp_alert_log (
  id          bigint generated always as identity primary key,
  job         text not null,
  local_date  date not null,
  status      int,
  detected_at timestamptz not null default now(),
  sent        boolean not null default false,
  shadow      boolean not null default false,
  detail      text,
  unique (job, local_date, status)
);

-- ---------------------------------------------------------------- tripwire --
create or replace function public.xp_tripwire_check()
returns void
language plpgsql
security definer
as $$
declare
  key       text;
  secret    text;
  sender    text;
  recipient text;
  armed     boolean;
  auth      text;
  msg       text;
  req_id    bigint;
  r         record;
begin
  select decrypted_secret into key       from vault.decrypted_secrets where name = 'mobilemessage_api_key';
  select decrypted_secret into secret    from vault.decrypted_secrets where name = 'mobilemessage_api_secret';
  select decrypted_secret into sender    from vault.decrypted_secrets where name = 'mobilemessage_sender';
  select decrypted_secret into recipient from vault.decrypted_secrets where name = 'mobilemessage_to_ops';
  armed := key is not null and secret is not null and recipient is not null;

  for r in
    select l.job, l.local_date, l.status
      from public.xp_dispatch_log l
     where l.status is not null
       and (l.status < 200 or l.status > 299)          -- non-2xx = failure (401/404/0/-1)
       and l.fired_at > now() - interval '24 hours'
       and not exists (select 1 from public.xp_alert_log a
                        where a.job = l.job and a.local_date = l.local_date and a.status = l.status)
  loop
    msg := format('XP Daily alert: dispatch %s on %s returned %s (expected 204). Check github_dispatch_pat and net._http_response.',
                  r.job, r.local_date, r.status);

    if armed then
      -- strip the newlines Postgres' base64 inserts every 76 chars, else the
      -- Authorization header is malformed.
      auth := translate(encode((key || ':' || secret)::bytea, 'base64'), E'\n\r', '');
      select net.http_post(
        url := 'https://api.mobilemessage.com.au/v1/messages',
        headers := jsonb_build_object(
          'Authorization', 'Basic ' || auth,
          'Content-Type', 'application/json'
        ),
        body := jsonb_build_object(
          'enable_unicode', true,
          'messages', jsonb_build_array(jsonb_build_object(
            'to', recipient,
            'message', msg,
            'sender', coalesce(sender, 'XPDaily'),
            'custom_ref', 'tripwire1'
          ))
        )
      ) into req_id;
      insert into public.xp_alert_log (job, local_date, status, sent, shadow, detail)
        values (r.job, r.local_date, r.status, true, false, 'sent, req=' || req_id);
      raise notice 'xp_tripwire: SENT alert — % % status %', r.job, r.local_date, r.status;
    else
      insert into public.xp_alert_log (job, local_date, status, sent, shadow, detail)
        values (r.job, r.local_date, r.status, false, true, 'SHADOW (unarmed) would send: ' || msg);
      raise notice 'xp_tripwire: SHADOW — would alert % % status % (creds not in Vault)', r.job, r.local_date, r.status;
    end if;
  end loop;
end;
$$;

-- Its OWN timer (not the dispatcher's). Every minute; the dedupe keeps it quiet.
select cron.unschedule('xp-tripwire')
 where exists (select 1 from cron.job where jobname = 'xp-tripwire');
select cron.schedule('xp-tripwire', '* * * * *', $$select public.xp_tripwire_check()$$);

-- --------------------------------------------------- shadow acceptance test --
-- Prove detection + the would-send path WITHOUT sending anything (the system is
-- healthy, so there are no real failures to watch). Run by hand in the SQL editor:
--
--   -- 1. plant a fake 401 for today
--   insert into public.xp_dispatch_log (job, local_date, fired_at, status)
--     values ('accept-fail', current_date, now(), 401);
--   -- 2. run the tripwire once
--   select public.xp_tripwire_check();
--   -- 3. see the shadow would-send row (sent=false, shadow=true, detail = the text)
--   select * from public.xp_alert_log where job = 'accept-fail';
--   -- 4. clean up
--   delete from public.xp_alert_log   where job = 'accept-fail';
--   delete from public.xp_dispatch_log where job = 'accept-fail';
--
-- When healthy and unarmed, xp_alert_log simply stays empty — that is correct:
-- nothing failed, so there is nothing to say.
