# DailyXP — shell & pipeline runbook (public repo copy — no secrets, no personal URLs)

## Architecture (v3.0, live since 3 Aug 2026)
- **This repo** holds each student's current question set: `y9.json`, `y8.json`. Publishing = committing a new file version via the GitHub contents API.
- **Permanent quiz shells** (one static Netlify site per student) fetch `raw.githubusercontent.com/<this repo>/main/<student>.json` on load with a cache-buster, render the run, and auto-POST full results to a private Google Apps Script webhook → Google Sheet. Offline runs queue in localStorage and flush on next open.
- **The LLM never holds state.** Sheet = raw event log. Mastery ledgers (kept privately) = curated state.

## Shell source & tests (in /shell)
- `template_v3.html` — canonical shell. Build a student copy: replace `__STUDENT__` (y9|y8) and `__NAME__`, set the webhook URL constant, zip as `index.html`, deploy to that student's Netlify project (Deploys → drag zip → same project, URL unchanged).
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
- Weekly content sweep drill: see `SWEEP.md`.
- Content sourcing doctrine: see `CONTENT-MODEL.md`.
- Family comms cadence + purpose: see `REPORTING.md`.
- Season/chapter content calendar: see `SEASONS.md`.
- Absence & streak handling: see `ABSENCE.md`.
- localStorage keys are namespaced per student: `dxp_attempts_*`, `dxp_name_*`, `dxp_outbox_*`.
- Repo files are public: student files stay `y9`/`y8`, never names; no results, no secrets, ever, in this repo.
- Publish auth: fine-grained GitHub PAT (Contents R/W, this repo only), held by the project owner, expires ~90 days from 2026-08-02.
