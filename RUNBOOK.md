> ⚠️ **PARTIALLY SUPERSEDED (20 Aug 2026).** Operating truth now lives in **DAILY-PUBLISHING.md** (and **QUIZ-GENERATION.md** for content rules). Known-stale items here: tools/formats.py (deleted), the 7/4/1 shape, the fresh:true-on-everything law, the 'review prints longest-is-correct rate' claim. The gotchas sections remain valuable history.

> **Start here:** see **CURRENT-STATE.md** for what the quiz is today (a daily learning game — timed speed round with combos, a confidence-wager steady round, teach-back, and weekday events), and **VISION.md** for why it exists. Parts of this runbook predate the 18 Aug 2026 cleanup.

# DailyXP — shell & pipeline runbook (public repo copy — no secrets, no personal URLs)

## Architecture (v3.0, live since 3 Aug 2026)
- **This repo** holds each student's current question set: `y9.json`, `y8.json`. Publishing = committing a new file version via the GitHub contents API.
- **Permanent quiz shells** (one static Netlify site per student) fetch `raw.githubusercontent.com/<this repo>/main/<student>.json` on load with a cache-buster, render the run, and auto-POST full results to a private Google Apps Script webhook → Google Sheet. Offline runs queue in localStorage and flush on next open.
- **The LLM never holds state.** Sheet = raw event log. Mastery ledgers (kept privately) = curated state.

## Shell source & tests (in /shell)
- `template_v3.html` — canonical shell. Build the student copies with `python3 tools/stamp_shell.py --names "y8=<Name>,y9=<Name>,t1=<Name>"` (stamps `__STUDENT__`/`__NAME__`, writes one drag-deploy zip per seat into gitignored `shell/build/`), then deploy each zip to that student's Netlify project (Deploys → drag zip → same project, URL unchanged). ⚠ A template fix reaches NOBODY until all three sites are re-deployed — the shells are static copies, not readers of this repo (the 31 Aug Scrub-It lesson).
- `test_timing.js` — proves the timing invariants (active ≤ elapsed etc.) against the extracted TIMING-CORE.
- `test_integration.js` — jsdom plays a full run against the built shell, captures the webhook POST, asserts payload + invariant. Needs `npm i jsdom` and a built `roshan/index.html` + `y9.json` beside it.
- `test_offline.js` — send-fails → outbox → flush-on-open path.
- Run all three green before deploying any shell change.

## Question JSON schema
```json
{
  "student": "y9",
  "date": "2026-08-03",
  "dateLabel": "Mon 3 Aug 2026",
  "day": "MON",
  "tag": "R2.1",
  "title": "optional",
  "questions": [
    {"id":"S1","phase":"speed","subject":"Maths","prompt":"…","options":["…"],"answer":"…","why":"…","fresh":true,"repair":true},
    {"id":"T1","phase":"steady", "...":"same fields"},
    {"id":"TB1","phase":"teach","subject":"…","prompt":"…"}
  ]
}
```
- **System rule: the no-penalty "haven't covered this yet" skip must exist on EVERY question.** Until shell v3.1 makes the button unconditional, every published speed/steady question MUST carry `fresh:true`. Skips are logged and benched for verification against class — never scored as misses.
- Standard run: 7 speed + 4 steady + 1 teach. `fresh:true` shows the "haven't covered this yet" skip. `answer` must exactly match one option. Empty `questions` or `status:"placeholder"` → shell shows "No quiz posted yet".
- `day`/`dateLabel`/`tag` are display-only and come from this file — never hardcode dates in the shell.

## Timing model (do not regress)
One rule: a question's clock starts when it renders (once — re-renders don't restart), stops when answered/locked/submitted. active = Σ question clocks; elapsed = wall clock; idle = gap (reveal-reading, walk-aways). Invariant: active ≤ elapsed. The TIMING-CORE markers in the template delimit the tested code.

## Results payload (what lands in the Sheet per run)
`{shell, student, name, date, day, tag, deviceDate, ts, attempt, attemptsAllTime, score, maxScore, speed{right,of}, steady{right,of}, teach{done,chars,text}, flags{skips,confidentWrong,slowWrong,fastWrong,luckyGuess}, records[], timing{elapsedSecs,activeSecs,idleSecs,phases,perQuestion[]}, summaryText}`
Note: trust `ts` (UTC ISO) over the sheet's local received_at column (sheet timezone may be offset).

## Ops notes
- **Publishing is now `tools/publish.py <set.json>` — never hand-edit `y8.json`/`y9.json`.** It validates → writes → archives → commits → and VERIFIES the live raw URL serves the intended tag (the fix for the 5 Aug rollback, where a re-push silently overwrote the published set). `--no-push` for a local dry run.
- Before publish, a set must pass `tools/validate.py` (schema, answer∈options, `fresh:true`, no-repeat vs `history/`). The planner and publish-op both call it.
- **Second-pass review: `tools/review.py`** runs between compose and publish (wired into `run_daily`). It catches the meaning-level faults the validator can't — a distractor that's also true, a false `why`, off-syllabus, trivially-easy — using a stronger model. On a block it recomposes the flagged slots and re-reviews; still blocking after 2 rounds → HOLD (yesterday's set stays live). Two things the recompose MUST do (both learned the hard way on the first live run, 10 Aug — see "First-run gotchas" below): (1) keep the mini-set VALID — it borrows the teach slot for context so compose doesn't reject it for "0 teach", then swaps back only the flagged slots; (2) feed review's objection back — each flagged slot's `guidance` carries the review note ("REVIEW REJECTED [category]: …"), so compose fixes the specific fault instead of retrying blind. Emergency bypass: `DAILYXP_SKIP_REVIEW=1`. See `tools/README.md`.
- Slot planning (which topics get slots today): `tools/planner.py` — the deterministic brain. FROZEN→empty (absence gate in code), REPAIR guaranteed, assessment-aware, day-directive driven. Reads the private `targets/` + `work/state.json`. See `tools/README.md`.
- **Keep names out of published `title` fields** (legacy sets embedded them; the shell renders the title publicly). Use a neutral title.
- Morning results read: `tools/results_reader.py` (dedupe, signal extraction, ledger implications) — see `tools/README.md`.
- Weekly content sweep drill: see `SWEEP.md`.
- Content sourcing doctrine: see `CONTENT-MODEL.md`.
- Family comms cadence + purpose: see `REPORTING.md`.
- Season/chapter content calendar: see `SEASONS.md`.
- Absence & streak handling: see `ABSENCE.md`.
- localStorage keys are namespaced per student: `dxp_attempts_*`, `dxp_name_*`, `dxp_outbox_*`.
- Repo files are public: student files stay `y9`/`y8`, never names; no results, no secrets, ever, in this repo.
- Publish auth: fine-grained GitHub PAT (Contents R/W, this repo only), held by the project owner, expires ~90 days from 2026-08-02.

---

## First-run gotchas (first scheduled run, 10 Aug 2026)

The first real scheduled run held/failed four times, **every time behind a green ✓** — the workflow
succeeded while nothing published. Root causes, all fixed; keep this list for future CI debugging:

1. **A green run ≠ a published set.** `run_daily` catches compose/review/publish failures and exits
   0 ("yesterday's set stays live"). **Always verify the LIVE set date** (fetch the raw `y8.json`/
   `y9.json` and check `date`), never trust the run conclusion. This is the first thing to check.
2. **Recompose crashed on a non-teach block** — it rebuilt a set from only the flagged slots, which
   had no teach question, so compose rejected it ("exactly ONE teach required, got 0"). Now it
   borrows the teach slot for validity and swaps back only the flagged slots (see review note above).
3. **Blind recompose looped** on the same subtle error — fixed by feeding review's objection into the
   flagged slot's `guidance` (see review note above).
4. **CI commit failed "Author identity unknown"** — a fresh checkout has no git identity.
   `publish.py` now sets a local `user.name`/`user.email` before committing.
5. **CI push 403 "denied to github-actions[bot]"** — `actions/checkout` with no token persists a
   read-only bot credential as an `http.extraheader`, which git prefers over the write token in the
   push URL. **Any repo you PUSH to in CI must be checked out with the write token** (`token:
   DAILYXP_TOKEN` + `persist-credentials: false`), as the private-repo checkout already did.

Also observed: **GitHub's scheduler runs late/skips** — the "2pm" cron fired at 3:38pm and the 4pm
nudge didn't self-fire. This is now SOLVED at the trigger layer: **Supabase pg_cron is the primary
scheduler** (see "Supabase scheduler" below), firing each slot via `workflow_dispatch` on the Sydney
wall clock. GitHub's own `schedule:` crons stay ENABLED as a demoted backup — every job is
cursor-guarded, so the two schedulers double-firing is a designed no-op. `workflow_dispatch` (manual
or via the API) remains the reliable fallback for any specific day.

The three clocks (all GitHub-owned, Mon–Fri): **2:00pm** pipeline (plan→compose→review→publish),
**4:00pm** kid nudge (verifies the live set is today's BEFORE texting), **6:30/8:00/9:30pm**
soundbyte polls (first poll that sees a completed run texts that kid's parent seat).

**Monday 07:07 sweep — AUTOMATED (promoted 31 Aug 2026, B6):** pg_cron slot
`sweep-0707-mon` fires `sweep-shadow.yml` (GitHub cron demoted to a guarded Mon 08:07
AEST backup): fetch → summarise → docx alert → schedule-pass → rotation overrides →
validate (gate) → PROMOTE `targets/<monday>.json` → diff → commit. FAIL = HOLD (no
promote; newest-file fallback + loud staleness warning). Human Monday = docx alerts +
`overrides/rotations.json` on rotation switches + a changelog eyeball; the manual
Chrome-panel drill is the outage fallback in SWEEP.md's appendix.
LAW unchanged: Monday's quiz never depends on it (newest-file fallback).

**Everything fails soft:** a held/red 2pm run → the 4pm nudge refuses to text; no run played →
soundbyte stays silent; a failed send → retried next poll, cursor untouched. A red day is a
quiet day, never a wrong text. Check: repo → Actions tab; comms failure detail lands in the
PRIVATE repo (`work/soundbyte_last_error.txt`), never in public logs.

**Editing workflow YAML (hard-won law):** hand-write, strict-validate locally (single doc,
duplicate-key check), push, confirm GitHub lists the workflow by NAME (not path) before any
dispatch. No regex surgery on YAML.

### Gotcha #7 — module-scope env capture (found 11 Aug 2026)

**`publish.py` read `HISTORY_DIR` at IMPORT time**, but `run_daily` sets
`DAILYXP_HISTORY_DIR` *after* `import publish`. So since the two-repo split every
set archived into `DailyXP-content/history/` — the public checkout, which nothing
commits and CI discards.

Two silent consequences, the second worse:
1. No archived sets from 7 Aug to 10 Aug → misconception diagnosis had no data.
2. **`validate_set`'s no-repeat check was reading an EMPTY history** — nothing
   was preventing duplicate questions across days.

Fixed via a call-time `history_dir()`. Archives were recovered from the public
repo's git history (every published set survives as a commit of `{student}.json`
— a useful recovery route to remember).

**Rule: never bind an env-derived path at module scope.** Resolve it in a
function. Anything `run_daily` sets after its imports is invisible to a module
that captured it at import.

### Gotcha #8 — the remote moves while you work

Two pushes were rejected in one session because the live pipeline had advanced
the remote (a run ingested; three sets published). **Never force-push to
resolve this.** Fetch, inspect what actually changed, and if the same file
diverged, take the remote as truth and re-apply your change on top. A force
rebase in that session would have destroyed a real ingested run.

Corollary to gotcha #1: **a `git push` reporting success is not proof the file
is live.** Verify with `api.github.com/repos/.../contents/<path>` after pushing.

### Gotcha #9 — a new workflow must copy its secret names from a PROVEN one

`friday-report.yml` was written referencing `MOBILE_MESSAGE_USER` / `_PASS`
(invented — the real pair is `MOBILE_MESSAGE_API_KEY` / `_API_SECRET`) and, worse,
passed `MOBILE_MESSAGE_TO_Y8/Y9/T1` — **the boys' numbers** — to a job that texts
parents. GitHub silently resolves a missing secret to an empty string, so this
fails quietly at best, and is the exact shape of mistake that ends with a parent
report on a kid's phone.

Caught by listing the repo's actual secrets (`api.github.com/repos/.../actions/secrets`
returns names only) and diffing against the workflow.

**Rules:**
1. When writing a new comms workflow, copy the `env:` block from the nearest
   working one (`evening-soundbyte.yml`) — never write secret names from memory.
2. List the repo's real secret names and diff before the first run.
3. Parent-facing jobs pass `MOBILE_MESSAGE_PARENTS_*`, never `MOBILE_MESSAGE_TO_*`.
   `friday_report_run.py` now hard-aborts if the parent seat is unresolved rather
   than letting `notify` fall through to any other recipient.

### Gotcha #10 — `--no-sms` still DEPLOYS to the live per-kid URLs (28 Aug 2026)

A supervised `--no-sms` Friday dispatch is not a rehearsal: it renders AND
publishes real pages at the real per-kid slugs. On 27 Aug one was run from a
branch that predated the dark repaint, putting light pages live at the
canonical URLs the night before the real send. Rules:

1. **Inspection = `--dry-run`** (renders to `private/work/preview_report_*`,
   collected by the workflow's dry-run artifact; deploys nothing, texts
   nothing). Use `--no-sms` only when the deploy itself is the thing under
   test — and then only from `main`.
2. Never run any deploying dispatch from a branch that predates a pending
   family-facing visual change.
3. Every page now bakes in a `xpdaily-build` stamp (commit + render time) and
   `netlify_deploy.verify()` requires that exact stamp back from the live URL
   — so a stale page can no longer pass as a green deploy (the 28 Aug
   Netlify-side publish failure rode exactly that blindness). View Source →
   `xpdaily-build` answers "which build am I looking at" in one look.

### Gotcha #11 — Netlify lowercases paths; mixed-case slugs can never replace themselves (29 Aug 2026)

The 28 Aug light-theme incident's true root cause (Netlify itself was healthy —
auto-publish on, nothing locked). Netlify normalises every URL path to
lowercase and its files API lists live pages under lowercase paths; our report
slugs were mixed-case `token_urlsafe`. So from the moment carry-forward
deploys began re-listing live pages (the 21 Aug fix), every manifest contained
the OLD page at its lowercase path AND the new render at a mixed-case path —
one normalised path, two entries, and the stale one won. Consequence: **a page
only ever landed when it was NEW to the site.** Thursday's run *added* y8/y9
(wiped in the 21 Aug incident) — light builds that then looked "fresh" — while
t1 served its 21 Aug survivor through every green deploy since; verify()'s
brand-string check waved all of it through.

Fixes (all in `netlify_deploy.py` + `friday_report_run.py`): every path and
URL is lowercased at use; the live-manifest read-back lowercases its keys; new
slugs generate as `token_hex` (naturally lowercase); the build-stamp verify
(Gotcha #10) would now fail such a deploy loudly at send time. Recovery
button: dispatch **Friday report** with `redeploy=true` — re-renders and
re-deploys the already-sent week's pages with no SMS and no private-state
writes. The 21-Aug lesson generalised: the carry-forward fix INTRODUCED this
bug — any fix that re-lists live state must speak the platform's canonical
form.

---

## Supabase scheduler + results DB (live 17 Aug 2026)

XP Daily has its OWN Supabase (separate account/email from VitalYOU — Privacy
Act separation; ROADMAP.md). It does two jobs: the results DATABASE (`runs_raw`)
and the SCHEDULER (`pg_cron` → GitHub `workflow_dispatch` via `pg_net`). Full
setup runbook: `supabase/SUPABASE.md`. Schema in `supabase/001_schema.sql`,
scheduler in `supabase/002_scheduler.sql`.

**The scheduler.** `xp_dispatch()` runs every minute, compares the Sydney wall
clock against the `xp_schedule` table (11 slots), and fires each due job once
per local day, deduped in `xp_dispatch_log`. Timezone-aware by construction, so
the 4 Oct AEDT change is a non-event (14:00 means 2pm in October exactly as in
August). Verified live 17 Aug: a test slot fired `test-sms.yml` with event
`workflow_dispatch`, logged in `xp_dispatch_log`, zero human input.

**Editing the timetable** is now a SQL `update` on `xp_schedule` — no YAML, no
UTC arithmetic. GitHub's `schedule:` crons stay enabled as backup; delete them
only after a full clean week on pg_cron.

**The token.** The dispatcher reads a Vault secret named exactly
`github_dispatch_pat`. **Correction to an earlier note:** `DAILYXP_TOKEN` CAN
fire `workflow_dispatch` — proven live 13 Aug (HTTP 204, run started 1s later)
and again 17 Aug. It only 403s on Actions *log downloads*. The Vault currently
holds `DAILYXP_TOKEN`. **TODO this week:** mint a fine-grained PAT scoped to
`Rich898/DailyXP-content` with Actions: Read+write only, swap it into Vault,
and stop reusing the broad token for dispatch.

**New Supabase API-key mode.** This project was created after Supabase's key
format change: the keys are `sb_publishable_...` (anon role) and `sb_secret_...`
(service role), NOT the legacy `eyJ...` JWTs. Consequence for REST: the role is
carried by the `apikey` header alone — do NOT also send `Authorization: Bearer
<key>` (that header is now reserved for user JWTs and will misbehave). All three
call sites were adapted accordingly: `shell/template_v3.html` dual-write,
`tools/ingest_results.py`, `tools/supabase_pull.py`, and `heartbeat.yml`.

**Dual-write.** `shell/template_v3.html` `sendPayload()` mirrors every result
into `runs_raw` (fire-and-forget, anon key, insert-only via RLS) alongside the
Google Sheet write. The Sheet stays source of truth and owns the callback — the
Supabase write can never block or fail a submission. Proven live 17 Aug with a
t1 warm-up: row landed in `runs_raw`. Timestamps in `runs_raw.received_at` are
UTC (Sydney = UTC+10); only the scheduler's wall-clock comparison is localised.

**Reading results.** `tools/supabase_pull.py` (service key; Actions secrets
`SUPABASE_URL` + `SUPABASE_SERVICE_KEY`) emits the same payloads the Sheet
reader does. `tools/ingest_results.py` auto-runs `both` mode when both credential
sets are present: Sheet stays truth, and each run prints "supabase sink: N/N
run-days present — agrees" (or names gaps). Settling week runs `both`; flip
`INGEST_SOURCE=supabase` only after a clean week of agreement (target: next Mon).

**Tier: PRO ($25/mo), from 17 Aug.** Rich upgraded ahead of the ROADMAP trigger
("go Pro when a second family pays"). Pro removes the 7-day free-tier inactivity
pause entirely and adds daily backups. **Consequence:** `heartbeat.yml` is now
REDUNDANT (it existed only to keep a free-tier project awake over term breaks)
and is left inert — no need to wire the `SUPABASE_URL`/`SUPABASE_ANON_KEY`
secrets for its sake, though they're set anyway for `pull`/`both`-mode ingest.

---

## Quiz variety & answer-integrity (live 17 Aug 2026)

Three mechanics run on every standard set, all deterministic, all no-shell-cost
(pure four-option MC; ledger/grading read ok/picked only). Full doctrine and the
originating beta feedback: SEASONS.md LAWS 1–5. Where they live in code:

- **Answer-length gate (LAW 1)** — `tools/answer_length.py`, wired into
  `tools/review.py` as a BLOCKING check that overrides the LLM verdict. Blocks any
  slot where the correct option is conspicuously the longest, and blocks a run
  whose correct-answer length-rank piles on #1. Composer constraint also added in
  `planner._composer_instructions`. Metric: review prints longest-is-correct rate
  (target ~25%; was 70% pre-fix). Tests: `test_answer_length.py` (incl. the real
  17-Aug failing sets).
- **Format bank (LAW 2)** — `tools/formats.py`. Assigns one of 6 MC-family formats
  (recall, spot-the-lie, spot-the-error, odd-one-out, ordering-as-MC, matching-as-MC;
  reversed when a reversed day) to each speed/steady slot, AFTER topic selection,
  seeded by student+date+tag (stable on re-plan, varies by day). Calc topics
  restricted to numeric-safe formats (recall/spot-the-error/ordering) — same rule
  as the reversed exemption. Throwback + teach-back stay recall. Planner injects a
  per-format legend into `composer_instructions`; `format_summary` prints in plan
  logs. Skipped on boss (Battleground self-assigns per-zone formats). Tests:
  `test_formats.py`.
- **Throwback (LAW 3)** — `tools/throwback.py`. Reserves ONE steady seat per run for
  a topic that is solid/developing, aged >=10 days since last_tested, and NOT a
  repair thread — the deliberate inverse of the live-topic pool. Never pads (no
  eligible topic -> no throwback slot; thin early in history). `fresh:false` on the
  slot; `validate.py` exempts throwback from the fresh:true law; `compose.assemble`
  carries the flag through. Held -> stays solid; decayed -> state_writer demotes it
  as any miss. Tests: `test_throwback.py` + throwback block in
  `test_planner_events.py`.

**Key seam to remember:** `compose.assemble()` is where plan metadata (fresh,
throwback, repair) is stitched onto the LLM's language. It previously hardcoded
`fresh:true`; it now carries fresh/throwback from the plan slot. Any future per-slot
flag must be threaded through there too, or it is silently dropped.