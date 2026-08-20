# DAILY PUBLISHING & OPERATIONS — source of truth

_How the quiz is generated, published, and communicated each day: every trigger, clock,
store, message, and failure mode. Derived by tracing the actual code and workflows on
**20 Aug 2026** (commit `d346320`) and verified against the live repos, the live quiz
files, and the git commit history. Where this document and any other doc disagree, **this
document reflects the code**; disagreements are listed at the bottom. Companion:
`QUIZ-GENERATION.md` (how the quiz's content is decided)._

---

## 1. The pipeline, end to end (`scripts/run_daily.py`)

One run of the pipeline, per school day, does the following **in order**. Weekends exit
immediately (`run_daily.run`, `date.weekday() > 4`).

| # | Stage | Code | Reads | Writes |
|---|---|---|---|---|
| 0 | **Ingest results** | `tools/ingest_results.py` (`ingest`) | The Apps Script read-only `doGet` endpoint (`RESULTS_URL`+`RESULTS_KEY`) and/or the Supabase `runs_raw` sink (`SUPABASE_URL`+`SUPABASE_SERVICE_KEY`); the existing `runs.json` (to carry grade annotations forward) | Rebuilds `private/work/runs.json` wholesale (normalised, deduped by (student, ts), SYSTEM-TEST rows dropped, canonical marked per (student, set_date) = lowest attempt then earliest ts, phase medians attached) |
| 0b | **Teach-back grade** | `tools/grade_teachback.py` (`annotate_runs`) — runs only when `ANTHROPIC_API_KEY` is set and `DAILYXP_SKIP_TB_GRADE≠1` | canonical, non-test runs in `runs.json` | Deterministic `tb_integrity` on every teach-back (via `tools/integrity.py`), then an LLM `tb_grade` (verdict + depth + evidence) on each ungraded, non-quarantined one; written back into `runs.json` |
| 1 | **State-writer** | `tools/state_writer.py` (`process`) — skipped if `DAILYXP_SKIP_STATE_WRITE=1` | `runs.json`, the persisted plans (`private/plans/<s>/<date>.json`) for the slot→topic join, `state.json`, its cursor | `private/work/state.json` (ledger transitions), `state_writer_cursor.json`, appends to `state_writer_log.jsonl` |
| 2 | **Achievements** | `tools/achievements.py` (`process`) — skipped if `DAILYXP_SKIP_ACHIEVEMENTS=1` | `runs.json`, `state_writer_log.jsonl`, `state.json`, `achievements_earned.json` | `private/work/achievements_earned.json`, appends to `achievements_log.jsonl` |
| 3 | **Seed the menu** | `tools/seed_menu.py` (`seed_player`), per student | all `private/targets/*.json`, in-memory state | ⚠️ in-memory state only — **never persisted** (QUIZ-GENERATION §C1) |
| 4 | **Plan** | `tools/planner.py` (`plan_set`), per student | targets (newest file), state | The plan dict; **persisted** to `private/plans/<s>/<date>.json` (written even for FROZEN and dry runs — it is the results→topic join) |
| 5 | **Compose** | `tools/compose.py` (`compose_set`) | plan + the student's full prompt history (`validate.seen_prompts` over `private/history/<s>/`) | The candidate set (validated in-loop, ≤2 retry rounds). FROZEN → placeholder, no API call |
| 6 | **Review** | `tools/review.py` (`review_set`) + the recompose loop in `run_daily` (≤`MAX_REVIEW_ROUNDS=2`) | the set + curriculum context from targets | verdict; flagged slots recomposed with the objection fed back; still blocking → **HOLD** (skip publish) |
| 7 | **Publish** | `tools/publish.py` (`publish`) | the final set | `<student>.json` in the public repo (commit+push), the archive copy in `private/history/`, a line in `publish_log.jsonl` (⚠ never persisted — §O8), then **VERIFY**: fetch the raw URL and assert the live tag matches intent |
| 8 | **Commit private** | the workflow's "Commit private state back" step | the private checkout | one commit: history archive + state/cursor/log/plan changes → pushed to `DailyXP-private@main` |

There is **no SMS in the pipeline** — comms are decoupled by design (see §6).

The pipeline processes students in roster order: `roster.active()` = **y8, y9, t1** (all
three are `active:true` in `roster.json`). A `--student` flag (or the workflow's `student`
input) restricts it to one.

## 2. Triggers — what fires what

**Two independent schedulers exist, both live:**

1. **Supabase pg_cron (the primary, DST-proof).** `supabase/002_scheduler.sql`: pg_cron
   ticks every minute; `xp_dispatch()` compares the **Sydney wall clock** against the
   `xp_schedule` table and fires each due job **once per local day** (deduped in
   `xp_dispatch_log`, 10-minute due window) by POSTing GitHub's `workflow_dispatch` API via
   pg_net, using the Vault secret `github_dispatch_pat` (currently holding
   `DAILYXP_TOKEN` — the RUNBOOK's mint-a-scoped-PAT TODO is still open). The schedule
   table (Sydney local, ISO weekdays):

   | job | workflow | local time | days |
   |---|---|---|---|
   | daily-quiz | daily-quiz.yml | 14:00 | Mon–Fri |
   | kid-nudge | kid-nudge.yml | 16:00 | Mon–Fri |
   | wed-checkin-early / -cutoff | wed-checkin.yml | 18:25 / 20:25 | Wed |
   | soundbyte-1/2/3 | evening-soundbyte.yml | 18:30 / 20:00 / 21:30 | Mon–Fri |
   | friday-report | friday-report.yml | 20:35 | Fri |
   | watchdog-early / -late / -friday | watchdog.yml | 17:35 / 21:50 / 22:05(Fri) | Mon–Fri |

2. **GitHub's own `schedule:` crons (the demoted backup)** remain **enabled in every
   workflow**, in fixed UTC: daily-quiz `0 4 * * 1-5` (14:00 AEST); kid-nudge retry ladder
   16:00/16:20/16:45/17:15 AEST; soundbyte 18:30/20:00/21:30; wed-checkin 18:25/20:25 Wed;
   friday-report 20:35/21:05/21:45 Fri + 07:30 Sat last-resort; watchdog 17:35/21:50 +
   22:05 Fri; heartbeat Sun+Wed 18:00.

   > ⚠️ The double-scheduler design is safe only for jobs with a per-day **cursor**. All
   > comms jobs have one. **daily-quiz does not** — it genuinely runs twice most weekdays
   > and publishes twice. See §O1, the headline operational finding.

**Manual `workflow_dispatch`** exists on every workflow. daily-quiz's inputs: `date`
override, `student` (both / y8 / y9 / t1), `dry_run`. Note "both" is just the default label
— a scheduled (non-dispatch) run passes **no** student filter and therefore runs **all
three seats including t1**. The handoff's claim that "t1 is manual-only" is **false in
code** (§O3): t1 is `active:true` and has published on the cron every school day
(commit history verified).

**Concurrency:** daily-quiz, evening-soundbyte and wed-checkin share the concurrency group
`daily-quiz` (`cancel-in-progress: false` — runs queue, never cancel), so they serialise on
the shared private files. friday-report and watchdog have their own groups. **kid-nudge has
no concurrency group** (it only writes its own cursor and does `git pull --rebase` before
pushing, so collisions self-heal).

## 3. Timing — clocks, DST, dedup

- **The intended local rhythm (Sydney):** 14:00 publish → 16:00 kid nudge (the 2-hour gap
  is the human-intervention window after a HOLD) → evening soundbyte polls → Wed check-in →
  20:35 Fri report → watchdog sweeps.
- **DST fidelity is mixed** (§O6): pg_cron compares against
  `now() AT TIME ZONE 'Australia/Sydney'` — DST is a non-event. `kid_nudge.py`,
  `soundbyte.py`, `wed_checkin.py` use `ZoneInfo("Australia/Sydney")` — correct year-round.
  GitHub's crons are fixed UTC — from 4 Oct (AEDT) every GitHub-cron time slides one hour
  later in local terms unless the UTC hours are edited (noted inline in each yml).
  `watchdog.syd_now()` is hardcoded UTC+10 — its deadlines also drift one hour in AEDT.
- **Per-local-day dedup:** pg_cron's `xp_dispatch_log` (one row per job per Sydney date)
  guarantees the *dispatcher* fires each job once a day. Downstream, each comms job has its
  own cursor (§6) making re-runs no-ops. The pipeline itself has **no** daily cursor.
- **Shell-side dedup:** each run carries a stable `runId` (generated once, reused on
  offline-outbox retries) and the ingest path dedupes on exact (student, ts). ⚠️ The shell
  comment claims "a unique index on payload->>'runId' dedupes" in the database — no such
  index exists in `supabase/001_schema.sql` (§O9).

## 4. What's published where

- **The quiz JSON** → the public repo root as `<student>.json` (y8.json / y9.json /
  t1.json), committed and pushed by `publish.py` (message `publish <student> <tag>`).
  **The exact raw URL every deployed shell fetches** (and publish VERIFYs, and kid-nudge
  and watchdog re-check):
  `https://raw.githubusercontent.com/Rich898/DailyXP-content/main/<student>.json`
  (constant `RAW` in `publish.py`, `kid_nudge.py`, `watchdog.py`; `CONFIG.QUESTIONS_URL` in
  the shell, fetched with a cache-buster and `cache:"no-store"`).
- **State / plans / history / cursors / logs** → the private repo, committed by each
  workflow's "commit private" step (see the store map, §7).
- **Results** → dual-write from the shell (`sendPayload` in `shell/template_v3.html`):
  fire-and-forget insert into Supabase `runs_raw` (anon key, RLS insert-only) **plus** the
  authoritative POST to the Apps Script webhook → the Google Sheet, which owns the success
  callback. Failures queue in a localStorage outbox and flush on next open.
- **Friday hosted pages** → a single Netlify **reports** site via `tools/netlify_deploy.py`
  (digest deploy, additive so past weeks stay live): parent report at `/r/<slug>/`, kid
  wrap at `/w/<slug>/`, slugs generated once per kid and stored privately
  (`work/report_slugs.json`). Pages are fully self-contained (zero fetch calls).
- **The heartbeat** → `heartbeat.yml` inserts one row into Supabase `public.heartbeat`
  twice weekly (Sun + Wed 18:00 AEST). It existed to defeat the free-tier 7-day pause;
  **on Pro tier it is redundant but still cron-active** (harmless — §O7).

**How each per-seat Netlify shell loads its JSON:** each kid has one permanent Netlify site
(roster `play_url`: dailyxp-harrison / daily-xproshan / xpdaily-t1 .netlify.app). The site
is a stamped copy of `shell/template_v3.html` with `__STUDENT__` and `__NAME__` replaced
(RUNBOOK: build the copy, zip as index.html, drag-deploy to that student's project — URL
never changes; stamped builds are gitignored because they carry real names). On load the
shell fetches the raw `<student>.json`, renders the run, and auto-submits results on
finish. `status:"placeholder"` or empty questions → "No quiz posted yet".

## 5. Failure behaviour (everything fails soft)

- **Compose fails** (after retries) → that student is skipped; **yesterday's set stays
  live** (`run_daily`: "COMPOSE FAILED … Skipping publish").
- **Review HOLD** (still blocking after 2 recompose rounds) or **review unavailable** (API
  error / no verdict) → NOT published; yesterday's set stays live; "needs a human". The
  4pm nudge then refuses to text (live date ≠ today), and the watchdog's 15:00 publish
  check texts Rich.
- **FROZEN student** (absence) → a placeholder set IS published (so the shell honestly
  shows "no quiz" instead of a stale set); the nudge suppresses; the soundbyte stays
  silent; the ledger is untouched.
- **Thin pool** → the planner fills what it can, logs `shortfall`, never pads; LAW 6's
  seeding makes genuine shortage rare.
- **Publish verify fails** (live tag ≠ intent) → loud fail, non-zero exit (the 5 Aug
  rollback fix).
- **Ingestion unreachable** → warned and skipped; the run proceeds on the committed
  `runs.json`; the state-writer is a no-op for anything unseen.
- **A comms send fails** → the cursor is NOT advanced, so the next ladder rung / poll
  retries. Failure detail lands privately (`work/soundbyte_last_error.txt`,
  `work/wed_checkin_last_error.txt`), never in public logs.
- **Silence is the only "not done" signal** for the daily soundbyte; the Wednesday
  check-in is the one scheduled touchpoint that must not go silent (cutoff law, §6).

## 6. Daily comms — every message, who, when, channel, rules

All SMS goes through `tools/notify.py` → Mobile Message
(`api.mobilemessage.com.au/v1/messages`, basic auth, unicode on). **Numbers live only in
GitHub Actions secrets**, resolved per seat: `MOBILE_MESSAGE_TO_<CODE>` (the kid),
`MOBILE_MESSAGE_PARENTS_<CODE>` (that kid's parent seat), with a legacy fallback to
`MOBILE_MESSAGE_TO_PARENTS` when a per-kid parent secret is unset (⚠ §O13). The live seat
map (private `COMMS-SEATS.md`): TO_Y8→Harrison; PARENTS_Y8→Melina; TO_Y9→**empty by
design** (Roshan's US phone; the nudge skips him gracefully — the icon is his channel);
PARENTS_Y9→Rich; TO_T1→Rich; PARENTS_T1→Melina (deliberately — the multi-kid-parent
experience under test).

| When (Sydney) | Message | To | Code | Content rules |
|---|---|---|---|---|
| Mon–Fri 16:00 (+ ladder 16:20/16:45/17:15) | **Kid nudge** — "XPDaily is up 👊" (+ play_url); Fri: "⚔ BATTLEGROUND — win the week…" | each kid seat (all active roster codes, t1 included) | `tools/kid_nudge.py` / kid-nudge.yml | **VERIFY BEFORE TEXT**: fetches the live raw JSON; texts only if `date == today` and not a placeholder. One nudge per kid per day (cursor `work/kid_nudge_cursor.json`, advanced only on a confirmed send). No names, no scores. |
| Mon–Fri evenings, on completion (polls 18:30/20:00/21:30) | **Parent soundbyte** — exactly three beats: did it ✅ + tonight's +XP + a verdict closer; streak appended only when ≥2 | `parents:<code>` per kid who completed | `tools/soundbyte.py` / evening-soundbyte.yml | **No AI** — a deterministic template (two rotating phrasings per band, picked from the date). **No-ammunition law**: never misses, subjects, percentages, ratios, running totals, or day-vs-day. Tone band from best_score/max (≥85 huge / ≥70 strong / ≥50 solid / else hard; sets under `MIN_BANDED_MAX=1500` max carry no band); the ratio itself is printed nowhere. Ingests fresh results first; silence = not done; cursor `work/soundbyte_cursor.json` per (kid, date). |
| Wed, on completion (18:25 poll) or the 20:25 cutoff | **Merged Wednesday check-in** — the soundbyte's three beats on top + a check-in body: honest momentum (week-word, Mon–Wed vs last Mon–Wed), at most ONE ask or five-minute action, ends pointed at Friday | `parents:<code>` | `tools/wed_checkin.py` / wed-checkin.yml | Code picks every fact; the model (claude-sonnet-5) dresses the BODY only; a deterministic validator bans digits/%/ratios/bare "behind" in the body, with redlined fallback voices behind it (the fallback must validate — asserted). Cutoff law: past 20:15 with no run, send the Mon–Tue read + "tonight's run isn't in yet — if it lands later this evening, the usual text will follow", and ONLY if the set was verifiably published today (our gaps never reported as the kid's). A merged send advances BOTH the check-in and soundbyte cursors; the 21:30 soundbyte poll keeps the late-run promise. |
| Fri 20:35 (+ ladder 21:05/21:45/Sat 07:30) | **Friday report** — parent SMS (lead line + three headlines + season XP total + link) + hosted parent report page; the kid wrap page is built by the same job | `parents:<code>`; pages via Netlify | `tools/friday_report_run.py` → `friday_report` (facts) + `report_stories` (narrative) + `report_page`/`kid_wrap` (render) + `friday_sms` (SMS) / friday-report.yml | Grades teach-backs first (integrity + quality) so quotes pass the gate. Page deployed and VERIFIED live before the SMS; deploy failure → SMS still goes, without the link (the SMS is the tier-1 report). Friday law: the XP total is the ONE permitted number in the SMS; % and score-slashes stay banned; every flagged area arrives with its fix; banned words (miss/wrong/fail/dumb/lazy). Hard-aborts if the parent seat is unresolved (never falls through to another recipient). Cursor: one send per kid per week (`work/friday_report_cursor.json`); writes the weekly snapshot `work/report_snapshots/<week>.json` — next Friday's trajectory source. |
| Mon–Fri 17:35 & 21:50 (+ Fri 22:05) | **Watchdog alert** — "something that should have happened, didn't" | **Rich only** (`ALERT_SEAT="t1"` — ops never lands on a family seat) | `tools/watchdog.py` / watchdog.yml | Checks the CURSORS (never run conclusions) against the day's promises: live set = today by 15:00; nudge cursor by 17:30; soundbyte cursor by 21:45 for anyone who played; Friday cursor by 22:00. Silent when healthy; one alert per item per day (`work/watchdog_cursor.json`); detects only, never fixes. |

There is no separate "~4pm kid nudge" vs "daily soundbyte" pathway beyond the above — those
five are the complete outgoing-message set (plus `test-sms.yml` for manual test sends).

## 7. What's captured where — the store map

| Store | Where | Holds | Written by |
|---|---|---|---|
| **The ledger** `work/state.json` | private | per-topic mastery state per student + ACTIVE/FROZEN status (schema: QUIZ-GENERATION §3) | `state_writer.process` (only writer today — seeding never persists, §C1) |
| `work/runs.json` | private | every normalised run (canonical-marked, deduped) + phase medians + `tb_integrity`/`tb_grade` annotations | `ingest_results.ingest` (wholesale rebuild, annotations carried forward), `grade_teachback.annotate_runs` |
| `work/state_writer_log.jsonl` | private | one audit line per ledger transition (from→to, badge, reason) | `state_writer.process` |
| `work/state_writer_cursor.json` | private | processed (student\|ts) keys — the writer's idempotency | `state_writer.process` |
| `work/achievements_earned.json` + `achievements_log.jsonl` | private | the badge ledger per kid + award log | `achievements.process` |
| `plans/<s>/<date>.json` | private | the slot→topic plan for every run — the results join | `run_daily.run` |
| `history/<s>/<date>_<tag>.json` | private | every published set — feeds the no-repeat gate and misconception diagnosis | `publish.publish` (via `DAILYXP_HISTORY_DIR`) |
| `targets/<monday>.json` | private | the weekly Canvas scrape | the manual sweep (SWEEP.md) |
| comms cursors (`kid_nudge_cursor` / `soundbyte_cursor` / `wed_checkin_cursor` / `friday_report_cursor` / `watchdog_cursor` .json) | private | per-day / per-week sent-state — what makes retry ladders safe | each comms tool |
| `work/report_snapshots/<week>.json` + `work/report_slugs.json` | private | weekly per-topic state (+ depth, currently always empty — §C11) snapshot; stable unguessable page slugs | `friday_report_run` |
| **Supabase `runs_raw`** | Supabase (own project, Pro) | one row per shell submission, payload verbatim jsonb; anon key insert-only via RLS; read via service key | the shell's dual-write; read by `supabase_pull.py` / `ingest_results.fetch_supabase` |
| Supabase `xp_schedule` / `xp_dispatch_log` / `heartbeat` | Supabase | the timetable, the per-day dispatch dedup, the keep-alive rows | `002_scheduler.sql`, `xp_dispatch()`, heartbeat.yml |
| **The Google Sheet** | Apps Script | the raw results event log — still the ingestion source of record in automation (§O2) | the shell's webhook POST |
| `<student>.json` | public repo root | the live quiz set | `publish.publish` |
| `publish_log.jsonl` | ⚠ nowhere durable | the publish audit line | `publish.publish` — gitignored AND written to the ephemeral CI checkout, so it evaporates (§O8) |

## 8. Infrastructure & deploy

- **GitHub Actions** (public repo): 8 workflows — daily-quiz, kid-nudge,
  evening-soundbyte, wed-checkin, friday-report, watchdog, heartbeat, test-sms. Every job
  that pushes checks out with `token: DAILYXP_TOKEN` + `persist-credentials: false`
  (gotcha #5). Secrets in use: `DAILYXP_TOKEN` (fine-grained PAT, both repos),
  `ANTHROPIC_API_KEY`, `RESULTS_URL`/`RESULTS_KEY` (Sheet ingest), `MOBILE_MESSAGE_*`
  (API key/secret/sender + per-seat numbers), `NETLIFY_AUTH_TOKEN`/`NETLIFY_SITE_ID`
  (reports site), `SUPABASE_URL`/`SUPABASE_ANON_KEY` (heartbeat only — ⚠ no workflow
  forwards the service key, §O2).
- **Supabase** (project `ftknumgdmalxyjxvqlux`, XP Daily's own account, **Pro tier since
  17 Aug**): the results sink + the scheduler (§2). New API-key mode (`sb_publishable_*` /
  `sb_secret_*`): the role rides the `apikey` header alone — never also send
  `Authorization: Bearer` on REST (the shell's Edge Function call is the one place a Bearer
  header is used, correctly, for Functions). The `grade-teachback` **Edge Function** (the
  in-quiz three-light marking) lives only in Supabase — not versioned in either repo (§O10).
- **Netlify**: three per-kid quiz sites (drag-deploy of the stamped shell; URLs permanent)
  + one reports site (API digest deploys from friday-report; additive, past weeks stay
  live at their slugs).
- **Mobile Message**: the SMS provider (AU); sender = the dedicated number secret
  (`MOBILE_MESSAGE_SENDER`) until the ACMA "XPDaily" sender ID is approved. Dashboard
  timestamps render AEST/AEDT inconsistently — trust the payload `ts` (UTC ISO), per
  RUNBOOK.
- **Credentials on Rich's machine**: `~/.dailyxp_env` (sourced for local runs);
  `~/.ghtoken` is publish.py's local fallback. Rotation is flagged as needed. Local-run
  law: always `git pull --rebase origin main` first (gotcha #8 — the remote moves while
  you work; never force-push).

---

## Contradictions & gaps found

**O1 — THE PIPELINE PUBLISHES TWICE MOST WEEKDAYS (the headline ops finding).**
`002_scheduler.sql` keeps GitHub's cron "enabled as the demoted backup — every downstream
job is cursor-guarded so a double trigger is a no-op". That claim is true for every comms
job and **false for daily-quiz**, which has no per-day cursor. daily-quiz.yml's `schedule:`
block is live (the surrounding comments say "to auto-fire, uncomment the two lines below",
but the cron line IS uncommented), so pg_cron dispatches at 14:00 Sydney and GitHub's own
cron fires at 04:00 UTC (14:00 AEST — same hour in winter, typically 30–60 min late).
**Verified in the commit history:** two full publish rounds on Tue 18 Aug (04:01–04:02 and
04:44–04:45 UTC) and Thu 20 Aug (04:03–04:06 and 04:47–04:50 UTC). Consequences of the
second run: (a) doubled compose+review API spend every school day; (b) the no-repeat gate
forces the second set's questions to differ, so the set the kids play at 4pm is the
*second* composition; (c) `publish.py` archives to the **same** history filename
(`<date>_<tag>.json`), so the first set's prompts are overwritten out of the no-repeat
history — those exact questions can legally reappear later; (d) the 14:00→16:00
"human-intervention window" is half-consumed by run two; (e) if a kid ever plays between
the two runs, the plans file and live set shift under the result. From 4 Oct (AEDT) the
GitHub cron slides to 15:00 local, making the two runs a clean hour apart. **Fix options:**
delete daily-quiz's GitHub `schedule:` (RUNBOOK already says to, "after a full clean week
on pg_cron" — that week has passed), or give run_daily a per-(student, date) published
cursor like the comms jobs.

**O2 — Automated ingestion still reads the SHEET; the Supabase "settling week" never ran
in CI.** RUNBOOK says `ingest_results` auto-runs `both` mode (Sheet = truth, Supabase
compared and reported) when both credential sets are present, and that the flip to
`INGEST_SOURCE=supabase` waits on a clean week of agreement. But **no workflow forwards
`SUPABASE_URL` / `SUPABASE_SERVICE_KEY` / `INGEST_SOURCE` into any job's env** —
daily-quiz.yml and evening-soundbyte.yml pass only `RESULTS_URL`/`RESULTS_KEY`. So every
automated ingest since the 17 Aug cutover has been Sheet-only, the "supabase sink: N/N
run-days present — agrees" comparison has never printed in CI, and there is no data behind
the planned flip. `tools/supabase_pull.py` is called by nothing in automation. Fix: add the
two Supabase secrets (and optionally `INGEST_SOURCE`) to the env blocks of daily-quiz and
evening-soundbyte (wed-checkin and friday-report read the committed runs.json and don't
ingest).

**O3 — t1 is NOT manual-only.** `roster.json` marks t1 `active:true`; scheduled runs pass
no student filter, so t1 is planned, composed, reviewed and published on every cron fire
(commit history: `publish t1 T4.x` daily). t1 also receives the 16:00 nudge (TO_T1 = Rich)
and generates a parent soundbyte/check-in/report to PARENTS_T1 (= Melina) whenever Rich
plays. If manual-only is the intent, the clean lever is `active:false` in roster.json plus
a t1 override path — but note `roster.active()` also drives the nudge, soundbyte, watchdog
and Friday jobs, and the watchdog would then need to stop expecting a t1 publish (today it
would text Rich daily about a "missing" t1 set).

**O4 — daily-quiz.yml's own comments are self-contradictory.** Header: "Runs the whole loop
for both boys" (three seats run). Cron block: "Cron ENABLED at go-live" three lines above
"to auto-fire, uncomment the two lines below" around an already-live cron entry. Cosmetic,
but this file is exactly where a future session will look first.

**O5 — kid-nudge.yml's header is stale on three counts:** "Stateless — reads the live URL,
sends, writes nothing" (it has had a cursor since 11 Aug and commits it); "Flavoured by the
weekly skeleton (Wed blitz, Fri boss)" (Blitz retired; code has no Wednesday flavour);
REPORTING.md likewise still promises "⚡ Wed, 🐉 Fri" while the code sends 👊 standard / ⚔
BATTLEGROUND Friday (`kid_nudge.NUDGE`).

**O6 — Mixed DST fidelity.** pg_cron and the three Python comms clocks are
Sydney-timezone-true; GitHub's backup crons and `watchdog.syd_now()` (hardcoded UTC+10)
are not. After 4 Oct: the primary dispatch times hold; every GitHub backup rung and every
watchdog deadline drifts one hour later in local terms. Either fix watchdog to ZoneInfo
and edit the UTC crons in October, or delete the GitHub crons once pg_cron is trusted
(same lever as O1).

**O7 — The heartbeat is redundant but still firing.** RUNBOOK says it is "left inert" —
in fact its crons are live and it inserts a row twice a week. On Pro tier the pause it
guards against no longer exists. Harmless; retire or keep as a cheap liveness canary —
but the doc and the yml should agree.

**O8 — The publish audit log doesn't persist.** `publish.py` appends to
`publish_log.jsonl` at the PUBLIC repo root with the comment "audit log (private)". The
file is gitignored in the public repo, never copied to the private repo, and in Actions it
is written to an ephemeral checkout — so no publish audit trail survives any CI run. Point
it at `DAILYXP_HISTORY_DIR/../work/publish_log.jsonl` (the private checkout) if the trail
is wanted.

**O9 — The shell claims a DB-level runId dedupe that the schema doesn't create.**
`buildPayload`'s comment: "a unique index on payload->>'runId' dedupes". `001_schema.sql`
creates no such index (only student/date and received_at indexes). Ingest-side dedupe on
(student, ts) covers retries in practice; either add the index to the SQL or fix the
comment — an unversioned dashboard-only index is exactly the kind of drift this audit
exists to catch.

**O10 — The live in-quiz teach-back grader is unversioned and diverges from the nightly
one.** The shell POSTs to the Supabase Edge Function `grade-teachback` for the immediate
three-light screen (accuracy/spelling/punctuation — coaching only, never mastery). That
function's code and prompt exist only inside Supabase — in neither repo. Its output rides
the payload as run-level `tbGrade`, which `results_reader.normalise` **drops** (records are
rebuilt from `records[]`), so the live grade has zero downstream effect and the nightly
`grade_teachback.py` (a different prompt, with the depth axis, without spelling/punctuation)
re-grades authoritatively. That division is sound — but it is documented nowhere, and the
Edge Function should be committed to the repo.

**O11 — run_daily's docstring describes a manual world that no longer exists.** "State
ingestion … is deliberately a STUB here — this week that stays human-reviewed: the reader's
output is applied to the private ledger/state by hand." In the same file, ingestion, the
teach-back grader, the state-writer and achievements all run automatically. The docstring
predates roadmap #2 landing; rewrite it.

**O12 — The completion record is frozen in week 2.** `SCHEDULE.md`/`schedule.json`
(generated 5 Aug by `tools/schedule_build.py`) stop at w/c 3 Aug; nothing regenerates them.
Either schedule the rebuild or mark the record as superseded by runs.json + the Friday
snapshots.

**O13 — The legacy parent fallback can misroute a new player's comms.**
`notify._recipients("parents:<code>")` falls back to the shared `MOBILE_MESSAGE_TO_PARENTS`
secret when `MOBILE_MESSAGE_PARENTS_<CODE>` is unset. For a future added player whose
parent secret is forgotten, soundbytes/check-ins would silently go to the legacy family
group instead of failing loudly (friday_report_run alone hard-aborts, but its abort check
uses the same fallback, so it too would "resolve" and send). Given gotcha #9's history
(parent report nearly routed to a kid), consider removing the fallback now that per-kid
seats exist.

**O14 — The 19 Aug gap y8 never published.** Commit history shows no `publish y8` on Wed
19 Aug (y9 published a placeholder; t1 published) — consistent with a compose-fail or HOLD
during the mid-build day, meaning Harrison's live set that evening was Tuesday's. The
fail-soft behaved as designed (no nudge promise broken), but it's worth knowing the
Wednesday run was a casualty of the build session.

**O15 — Minor:** the daily-quiz "commit private" step pushes without a `git pull --rebase`
(kid-nudge and watchdog have one) — safe today only because of the shared concurrency
group; friday-report and watchdog sit in different groups and could in principle race a
manual pipeline run on the private repo.

## Open questions for Rich

1. **O1 — pick the fix:** delete daily-quiz's GitHub `schedule:` cron now (pg_cron has run
   clean since 17 Aug), or add a per-day publish cursor to run_daily? (Doing both is also
   fine; the cursor also protects against accidental manual double-fires.)
2. **O2 — wire the Supabase creds into the workflow env blocks** and run the settling-week
   comparison for real before flipping `INGEST_SOURCE=supabase` and retiring the Sheet —
   confirm the sequencing.
3. **O3 — t1's status:** keep t1 on the nightly cron (current behaviour, and your daily
   canary seat), or make it manual-only — and if the latter, agree the roster/watchdog
   changes that go with it.
4. **O6 — October plan:** delete the GitHub backup crons entirely, or keep them and book
   the UTC-hour edits + the watchdog ZoneInfo fix before 4 Oct?
5. **O8 — do you want the publish audit trail?** If yes, it needs a private home.
6. **O9/O10 — Supabase drift:** add the runId unique index to `001_schema.sql` (or delete
   the shell comment), and commit the `grade-teachback` Edge Function source to the repo.
7. **O12 — completion record:** regenerate `SCHEDULE.md` weekly, or formally retire it?
8. **O13 — remove the legacy `MOBILE_MESSAGE_TO_PARENTS` fallback** now that every kid has
   a per-seat parent secret?
9. **Docs cleanup:** approve the banner/retirement pass on RUNBOOK's stale sections,
   SYSTEM-MAP, kid-nudge.yml/REPORTING.md's nudge-flavour claims, and run_daily's
   docstring, all superseded by this document.
