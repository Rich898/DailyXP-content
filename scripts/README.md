# Automation — the cron skeleton (status + weekend fill-in)

The scaffold the daily loop hangs off. Built ahead so the weekend is wiring +
testing, not designing.

## The pipeline (scripts/run_daily.py)
For each school day, for each boy:

    INGEST results (ingest_results.py: Sheet → runs.json) →
    STATE-WRITER (state_writer.py: results → ledger, the return leg) →
    derive tag  →  PLAN (planner.py)  →  COMPOSE (compose.py, API)  →
    REVIEW (review.py, stronger model — recompose flagged slots or HOLD)  →
    PUBLISH (publish.py: validate→write→archive→commit→VERIFY)  →  NOTIFY (notify.py, SMS)

The loop is closed: ingestion pulls last night's results from the Sheet, the state-writer moves
the ledger, then we plan against the fresh state — adaptive, not just composing. Ingestion is
gated on `RESULTS_URL`/`RESULTS_KEY` (skipped locally → uses the committed runs.json).

- FROZEN boy → placeholder, no API call, no SMS.
- Weekends → skipped.
- Compose or publish failure → **yesterday's set stays live**, never a broken one.
- Directive by weekday: Mon/Tue/Thu standard, Wed blitz, Fri boss (override per boy with flags).

Triggered by `.github/workflows/daily-quiz.yml`: weekday cron at 14:00 AEST, plus a
manual **Run workflow** button (with date / student / dry-run inputs) for supervised runs.

## Wired and tested ✓
- `planner.py` — slot planning (FROZEN gate, REPAIR guaranteed, assessment-aware).
- `validate.py` — the publish gate (schema, answer∈options, fresh, no-repeat).
- `review.py` — the SECOND-PASS review gate (meaning-level faults the validator can't
  see: multiple-true / factual-error / off-syllabus / trivial). Stronger model than
  compose, adaptive-thinking. On a BLOCK, run_daily recomposes only the flagged slots and
  re-reviews; still blocking after 2 rounds → HOLD (yesterday's set stays live). Prior-term
  revision is treated as on-syllabus. Env: `DAILYXP_REVIEW_MODEL`, `DAILYXP_REVIEW_EFFORT`,
  and `DAILYXP_SKIP_REVIEW=1` as an emergency bypass. Regression-tested against the 6 Aug
  y8 T2 bug (blocks the broken version, passes the fix).
- `publish.py` — atomic publish + live-URL verify; history dir configurable (`DAILYXP_HISTORY_DIR`).
- `compose.py` — plan → API → assembled+validated set, retrying on validation failure.
  Structure proven; the live API call runs once `ANTHROPIC_API_KEY` is in the environment.
- `run_daily.py` — orchestration, tag derivation, weekend skip, dry-run, single-boy shadow mode.
  Persists each run's plan (slot→topic) into the private repo and runs the state-writer first.
- `state_writer.py` — the RETURN LEG: results (runs.json) + persisted plan + current state →
  updated state.json (promotions/demotions/REPAIR in&out/spacing). Deterministic, no API;
  reuses `results_reader` for the per-question verdict and applies `LEDGER-RULES.md`. Idempotent
  (cursor), preserves the human `note`, logs every transition. Transition table regression-tested
  (10/10 cases: REPAIR confirm→exit, fast-wrong-holds, trivial-correct-no-promote, 2nd-CW→REPAIR,
  spaced-Sure→solid). Env: `DAILYXP_SKIP_STATE_WRITE=1` bypass.
- `ingest_results.py` — headless ingestion: fetches the results Sheet from a token-gated read-only
  Apps Script `doGet` (separate from the quiz webhook) and refreshes `runs.json`, reusing
  `results_reader` (dedupe / drop SYSTEM TEST / mark canonical / medians) and writing the same JSON
  shape. Parsing pipeline regression-tested; prints counts + y8/y9 codes only (public Actions logs).
  Config: `RESULTS_URL` + `RESULTS_KEY` (gated — skipped when unset).
- `achievements.py` — badges the ledger after the state-writer (deterministic, idempotent): reads
  runs.json + the state-writer log + state.json, awards the 12-badge set (`ACHIEVEMENTS.md`) deduped
  against a private earned-ledger. Feeds the in-quiz screen + kid dashboard. Regression-tested (all
  12 badge types + idempotency). Env `DAILYXP_SKIP_ACHIEVEMENTS=1` bypass.
- The workflow — both-repo checkout, secret injection, private-state commit-back.

## Stubs to finish this weekend
0. **Second-pass review before publish — ✅ DONE (`tools/review.py`, wired into run_daily).**
   `validate.py` checks the answer is one of the options — it CANNOT tell when a *distractor*
   is also true, or when a question is factually wrong, off-syllabus, or trivially easy.
   Real examples this gate catches: (i) the first dry-run's H2.4 variables question that had
   two defensible "controlled variable" answers; (ii) the 6 Aug H2.4 T2 that taught a false
   rule ("must expand brackets first") in its `why` while keying a correct answer. The
   reviewer reads each composed set with a stronger model (adaptive-thinking) and flags
   multiple-true / factual-error / off-syllabus / trivial, with block vs warn severity. On a
   block, run_daily recomposes ONLY the flagged slots and re-reviews; still blocking after 2
   rounds → HOLD (yesterday's set stays live, flagged for a human). Prior-term revision is
   explicitly on-syllabus. This is what lets the cron run without a human reading every set —
   though reports stay human-reviewed and the first live runs still get a morning glance.
1. **Results → state loop — ✅ DONE (closed end-to-end).** The writer (`tools/state_writer.py`) applies
   `results_reader` verdicts to `state.json` per `LEDGER-RULES.md`; ingestion (`tools/ingest_results.py`)
   refreshes `runs.json` from the results Sheet via a token-gated read-only Apps Script `doGet`
   endpoint (separate from the quiz webhook — the webhook is never touched). run_daily runs
   ingest → state-writer as steps 0–1 before planning. Both are idempotent; the workflow commits the
   refreshed `runs.json`, `state.json`, cursor and log back to the private repo. Owner set-up (one-off,
   done): deploy the read-only endpoint, add `RESULTS_URL` + `RESULTS_KEY` as Actions secrets. If those
   secrets are absent (e.g. local runs) ingestion is skipped and the committed `runs.json` is used —
   the loop still applies whatever is already there.
2. **SMS live send** — `notify.py` is built; confirm Mobile Message's exact request shape
   against their docs and add the secrets. Without the secrets it safely dry-runs (no send).
3. **Canonical topic IDs** — shared by `state.json` and `targets/` (the planner join is
   tolerant for now; IDs are the real fix).

## Secrets to add (repo → Settings → Secrets and variables → Actions)
| secret | for | when |
|---|---|---|
| `DAILYXP_TOKEN` | checkout private repo + push both | now (the "DailyXP both" PAT) |
| `ANTHROPIC_API_KEY` | compose | now (you have it) |
| `MOBILE_MESSAGE_API_KEY` / `_API_SECRET` / `_SENDER` | SMS | when MM is set up |
| `MOBILE_MESSAGE_TO_Y8` / `_TO_Y9` / `_TO_PARENTS` | SMS recipients | when MM is set up |

## Rollout (supervised-autonomous → hands-off)
1. **This week:** shadow-run the planner/compose against manual composition (dry-run, single
   boy). Confirm the machine agrees with the manual calls.
2. **Monday:** flip the cron on but keep a morning thumbs-up — the machine composes+publishes;
   you glance at the publish log + texts before the boys are home. Kill-switch: disable the
   workflow.
3. **Within a week:** once it's boringly reliable, drop the thumbs-up. Reports stay
   human-reviewed until the reporting layer is proven separately.

## Local dry run (no publish, no SMS)
    python3 scripts/run_daily.py --private-dir ../DailyXP-private --date 2026-08-06 --dry-run
    # single boy: add --student y8   (needs ANTHROPIC_API_KEY for an active boy)
