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
   **Actions: Read and write**, 90-day expiry. (DAILYXP_TOKEN can't dispatch —
   it 403s on the Actions API — mint fresh, don't widen the old one.)
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
