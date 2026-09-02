-- 008_security_hardening.sql — XP Daily Supabase, step 8: CLOSE THE OPEN TABLE
--
-- Trigger: Supabase security-advisor email, 31 Aug 2026 — CRITICAL
-- `rls_disabled_in_public` on `public.xp_alert_log`. The quiz shells publish
-- the ANON key by design (SUPABASE.md step 4), and PostgREST exposes every
-- table in `public` to whoever holds it. runs_raw and heartbeat shipped with
-- RLS + insert-only policies from day one (001); xp_schedule and
-- xp_dispatch_log got RLS switched on from the dashboard when the advisor
-- first complained; xp_alert_log arrived later (004_tripwire1.sql) without it
-- — so anyone with the public page's anon key could read, edit or delete the
-- alert log through the REST API. This file closes that, codifies the two
-- dashboard toggles so the repo is the truth again, and locks the two other
-- advisor findings on the same surface.
--
-- What it does:
--   * RLS ON for the three ops tables, deliberately with NO policies —
--     deny-by-default IS the design. Nothing browser-side touches them (the
--     repo's only anon REST targets are runs_raw + heartbeat inserts).
--     pg_cron runs as postgres, the table owner, which RLS never restricts;
--     tools read via the service key, which bypasses RLS. The dashboard's
--     "RLS enabled, no policy" INFO notice on these tables is intentional.
--   * Belt and braces: revoke the API roles' table privileges too, so the
--     grant layer agrees with the RLS layer.
--   * The three scheduler functions were SECURITY DEFINER and PUBLIC-
--     executable — the anon key could call /rest/v1/rpc/xp_dispatch and
--     friends (advisor WARNs 0028/0029). Revoked; only pg_cron (postgres,
--     their owner) ever calls them, and owner rights survive the revoke.
--   * Pin search_path='' on those functions (advisor WARN 0011, mutable
--     search_path on SECURITY DEFINER). Safe: every object they and
--     net.http_post touch is schema-qualified — verified against the LIVE
--     function bodies, not just this repo's copies. ALTER sets only the
--     attribute; no function body is replaced.
--
-- What it deliberately does NOT do: move pg_net out of `public` (advisor
-- WARN extension_in_public). That is a drop-and-recreate of a live send-path
-- extension for no exposure change (its callable surface lives in the `net`
-- schema, which PostgREST does not expose). Revisit some quiet daylight hour
-- if the notice nags.
--
-- APPLY: paste in the Supabase SQL editor, project `xpdaily`. Safe to re-run.
-- Pure grant/RLS/attribute DDL — but it wraps the live dispatcher, so land it
-- in daylight, never in the evening send window (17:30–22:15 Sydney).
-- Verify a minute later:
--   select jobname, status, return_message from cron.job_run_details
--    order by start_time desc limit 6;          -- all three jobs succeeded
--   select public.xp_tripwire_check();          -- runs clean (healthy = no-op)

-- --------------------------------------------------------- tables: RLS on --
-- xp_alert_log is the critical fix; the other two restate the dashboard
-- toggles so a rebuilt project gets them from this folder alone.
alter table public.xp_alert_log    enable row level security;
alter table public.xp_schedule     enable row level security;
alter table public.xp_dispatch_log enable row level security;

-- ---------------------------------------------- tables: revoke API roles --
revoke all on table public.xp_alert_log    from anon, authenticated;
revoke all on table public.xp_schedule     from anon, authenticated;
revoke all on table public.xp_dispatch_log from anon, authenticated;

-- ------------------------------------------ functions: owner-only execute --
revoke execute on function public.xp_dispatch()       from public, anon, authenticated;
revoke execute on function public.xp_dispatch_check() from public, anon, authenticated;
revoke execute on function public.xp_tripwire_check() from public, anon, authenticated;

-- --------------------------------------------- functions: pin search_path --
alter function public.xp_dispatch()       set search_path = '';
alter function public.xp_dispatch_check() set search_path = '';
alter function public.xp_tripwire_check() set search_path = '';
