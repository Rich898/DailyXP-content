# SUPABASE.md — the weekend setup, click by click

**Goal (ROADMAP.md, ratified 11 Aug):** XP Daily gets its own Supabase — the
results DATABASE first (that's what keeps the project awake), then the
SCHEDULER (pg_cron → GitHub `workflow_dispatch`), with GitHub cron demoted to
backup. DST solved, dropped triggers solved. The ledger stays in git.

**Why both jobs, in this order:** free-tier projects pause after ~7 days of
inactivity and pg_cron pauses with them. A scheduler-only Supabase can switch
itself off. Nightly shell POSTs through the REST API are real activity — the
database use case is what makes the scheduler trustworthy.

---

## Saturday — the database (results sink)

1. **New account, new email** — not a project inside VitalYOU's org (Privacy
   Act separation; ROADMAP has the reasoning). Project name `xpdaily`, region
   **Sydney (ap-southeast-2)**, free tier.
2. **SQL editor → paste `supabase/001_schema.sql`** (public repo). Creates
   `runs_raw` (insert-only for the anon key via RLS) + the scheduler tables,
   seeded with the Sydney-local timetable.
3. **Migrate the existing runs:** on your machine,
   `python3 tools/supabase_seed.py --private-dir ../DailyXP-private`, then
   paste `DailyXP-private/supabase/seed_runs.sql` into the SQL editor.
   (The seed lives in the PRIVATE repo — it carries kid data.)
4. **Shell dual-write.** In `shell/template_v3.html`, next to `WEBHOOK_URL`
   in CONFIG add:

   ```js
   SUPABASE_URL: "https://<project-ref>.supabase.co",
   SUPABASE_ANON: "<anon key — Settings → API>",
   ```

   and at the top of `sendPayload(p, cb)` add the fire-and-forget second write
   (the Apps Script sheet stays the source of truth until cutover):

   ```js
   try {
     fetch(CONFIG.SUPABASE_URL + "/rest/v1/runs_raw", {
       method: "POST",
       headers: {
         "Content-Type": "application/json",
         "apikey": CONFIG.SUPABASE_ANON,
         "Authorization": "Bearer " + CONFIG.SUPABASE_ANON,
         "Prefer": "return=minimal"
       },
       body: JSON.stringify({ payload: p })
     }).catch(function(){});
   } catch (e) {}
   ```

   Then re-stamp and redeploy the three shells (tools/README.md, roster
   section). The anon key in a public page is by design — RLS limits it to
   insert-only on this one table.
5. **Verify:** run a warm-up on t1, then in the SQL editor:
   `select id, student, run_date, tag from runs_raw order by id desc limit 3;`

## Sunday — the scheduler

6. **Mint the dispatch PAT:** fine-grained, `Rich898/DailyXP-content` only,
   **Actions: Read and write**, 90-day expiry. (NOTE, corrected 17 Aug:
   `DAILYXP_TOKEN` CAN dispatch — proven live 13 + 17 Aug, HTTP 204 — it only
   403s on Actions *log downloads*. The cutover put `DAILYXP_TOKEN` in Vault to
   go live; still mint a scoped Actions-RW PAT this week and swap it, so the
   broad token isn't the dispatcher long-term.)
7. **Vault:** Dashboard → Project Settings → Vault → new secret named exactly
   `github_dispatch_pat`, value = the PAT.
8. **SQL editor → paste `supabase/002_scheduler.sql`.** The dispatcher ticks
   every minute, fires each due job once per Sydney-local day, dedupes in
   `xp_dispatch_log`.
9. **Verify Monday 2pm:** `select * from xp_dispatch_log;` should show
   `daily-quiz` fired at 14:00 local, and the Actions tab shows the run with
   event `workflow_dispatch`. `select * from net._http_response order by
   created desc limit 5;` — 204 means GitHub accepted.

## Rules of the cutover

* **GitHub crons stay ON as backup.** Every job is cursor-guarded, so the two
  schedulers double-firing is a designed no-op. Demote (delete the `schedule:`
  blocks) only after a full clean week on pg_cron.
* **Reading results:** `tools/supabase_pull.py` (service key, Actions secrets
  `SUPABASE_URL` + `SUPABASE_SERVICE_KEY`) emits the same payloads the sheet
  does. Run it alongside the sheet reader for a settling week; retire the
  sheet when they agree.
* **The service key is a server secret** — Actions only, never the shell,
  never the public repo.
* **Editing the timetable** is now a SQL update on `xp_schedule` — no YAML,
  no UTC arithmetic, DST-proof by construction.
* **Go Pro when a second family pays** (removes pausing, adds daily backups —
  both wanted before holding someone else's child's data).

---

## Verified 13 Aug (before you spend the weekend)

The full chain was stood up and fired for real — Postgres 16 with pg_cron 1.6
and pg_net 0.20.4 (built from Supabase's own source), running the exact SQL in
this folder:

* **Logic:** the dispatcher's due-selection swept across nine scenarios — fire
  window, once-per-day dedupe, Wednesday-only jobs, weekend exclusion, and both
  sides of the 4 Oct DST change (14:00 Sydney fires at 04:00 UTC in August and
  03:00 UTC in October, same schedule row). All correct.
* **End to end, live:** pg_cron ticked → dispatcher selected + deduped →
  pg_net POSTed to api.github.com → **204** in 8ms → the daily-quiz workflow
  **started 1 second later** and published all three sets. The mechanism is
  not theoretical; it has already deployed a real quiz day.
* **Platform facts (official docs):** pg_cron ships on every project including
  free ("only limited by the resources it uses… on any tier" — Supabase org);
  Supabase Cron supports sub-minute schedules; pg_net handles 200 req/s and
  keeps responses for 6 hours (so check `net._http_response` same-day).
  Ignore third-party posts claiming pg_cron is Pro-only — and step 1 of the
  acceptance test proves it on your project in one click anyway.
* **The holiday trap (closed):** term breaks outlast the 7-day free-tier
  pause, and a paused project stops pg_cron. `heartbeat.yml` inserts one REST
  row twice a week from GitHub — the two schedulers cover each other: GitHub
  keeps Supabase awake (weekly, days of tolerance), Supabase keeps GitHub
  punctual (minutely, seconds of tolerance). Set the `SUPABASE_URL` +
  `SUPABASE_ANON_KEY` Actions secrets on Saturday and it arms itself.

## Sunday acceptance test (5 minutes, before trusting it)

1. `create extension if not exists pg_cron; create extension if not exists pg_net;`
   — succeeding at all proves tier availability.
2. Vault secret in place, then insert a one-off row:
   `insert into xp_schedule (job, workflow, local_time, days) select 'accept-test',
   'test-sms.yml', ((now() at time zone 'Australia/Sydney') + interval '90 seconds')::time,
   array[extract(isodow from now() at time zone 'Australia/Sydney')::int];`
3. Two minutes later: `select * from xp_dispatch_log;` shows the fire,
   `select status_code from net._http_response order by id desc limit 1;`
   shows **204**, and the Actions tab shows a `workflow_dispatch` run.
4. `delete from xp_schedule where job='accept-test';` Done — the same chain
   that just passed is the one that runs Monday 2pm.

## Retiring Google entirely (the checklist)

Google's whole footprint here is Sheets/Apps Script; nothing else in the
pipeline touches it. The exit runs on the settling-week pattern, then delete:

1. **Saturday:** shell dual-writes (step 4 above). Ingest automatically runs
   in `both` mode once the `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` Actions
   secrets exist — the Sheet stays the truth and every run prints
   "supabase sink: N/N run-days present — agrees" (or names what's missing).
2. **After a clean week of agreement:** set repo variable/env
   `INGEST_SOURCE=supabase`. The Sheet is no longer read. Grades written by
   Friday's pass survive rebuilds (annotation carry-forward is built in).
3. **Delete, in order:** the `WEBHOOK_URL` line + dual-write's Apps Script
   half from the shell CONFIG (one re-stamp of the three shells); the two
   Apps Script deployments (quiz webhook doPost + the read-only doGet); the
   results Sheet itself; the `RESULTS_URL` / `RESULTS_KEY` Actions secrets.
4. `results_reader.py`'s manual Sheet-dump entry point goes quiet on its own —
   the parsing library inside it is what Supabase ingestion reuses, so the
   file stays; only the Google transport dies.

What deliberately does NOT move (ROADMAP.md): the ledger (`state.json`),
plans, targets and history stay in git — version history, atomic commits and
rollback for free. Supabase owns the event stream (runs) and the clock;
git keeps owning the brain.
