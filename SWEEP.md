# Weekly Canvas content sweep — AUTOMATED (promoted 31 Aug 2026)

*The sweep is a scheduled machine job. PROMOTED on Rich's GO after the B6
trust test (Mon 31 Aug 2026): the 07:07 machine run vs Rich's final manual
sweep scored 102/106 raw — **106/106 on adjudication** (all four misses
were fuzzy-matcher phrasing), 7 assessment dates agreed, and the machine
had *corrected* one date the previous manual sweep carried wrong (y9
Science → Tue 8 Sep). Evidence: ACTIONS.md B6 + private
`shadow/sweeps/2026-08-31/DIFF-vs-final-manual.md`. The manual
Chrome-panel drill is retired to the appendix as the outage fallback.*

## How it runs

- **Primary timer — Supabase pg_cron, Monday 07:07 Sydney** (`xp_schedule`
  row `sweep-0707-mon`, `supabase/007_sweep_slot.sql`; TZ-aware, so the
  4 Oct DST change is a non-event) → fires `sweep-shadow.yml` via
  `workflow_dispatch` (filename kept for dispatch + history continuity).
- **Backup timer — GitHub cron Sun 22:07 UTC** (Mon 08:07 AEST, 09:07
  AEDT) in the same workflow, **guarded**: a schedule-event run skips
  itself when this week's `targets/<monday>.json` already exists.
  Scheduler double-fire is a designed no-op.
- **Pipeline:** fetch (per-student tokens; six content surfaces; never
  grades/submissions/inbox) → summarise (code owns structure, LLM writes
  language only; carry-forward law: topics transition, never vanish by
  omission) → **docx alert** (flags NEW assessment paperwork it cannot
  read, vs the previous week's dump) → schedule-pass (year-group
  noticeboard assessment PDFs) → **rotation overrides** (private
  `overrides/rotations.json`) → **validate — the gate** →
  **promote** to `targets/<monday>.json` → diff vs last week's file (the
  weekly-delta record) → commit targets + shadow evidence.
- **FAIL = HOLD.** A validator FAIL turns the run red and nothing is
  promoted: the quiz pipeline falls back to the newest existing targets
  file with its loud staleness warning. **LAW (unchanged): Monday's quiz
  never depends on the sweep** — Monday is ledger-consolidation by design;
  a late or failed sweep costs freshness, never the day.
- **Promote never overwrites.** An existing `targets/<monday>.json` is
  only replaced via an explicit manual dispatch with
  `overwrite_targets=true` (the recovery button).

## The human's Monday (≈5 minutes, not 90)

1. **Docx alerts.** The run flags assessment notifications locked in
   files it cannot read (module-item docs, announcement attachments) —
   names in the dump's `docx-alerts.txt` (private). Open them in Canvas,
   hand the dates to the build chat → the targets file gets patched.
2. **Rotation switches.** When a boy changes Tech rotation (or any
   streamed subject), update the `live` string in private
   `overrides/rotations.json`. Membership is provable only from
   submissions, which the sweep never reads — this fact stays human by
   design.
3. **Eyeball the changelog.** The run summary prints per-subject
   added/transitioned counts; the promoted file's `sweep_update` block
   carries details. Anything odd → dispatch the workflow manually (`seat`
   / `mode` inputs; `overwrite_targets=true` to re-promote).

## Known quirks (still true — now handled by the machine)

- **y9:** Science and English live on per-teacher class pages and daily
  announcements — fetched automatically via the student's own enrollments.
- **y8:** Maths and Science run week-by-week schedules on the course
  HOMEPAGE — front-page bodies are always fetched.
- Per-student rotation/stream membership → the overrides file (above).
- Assessment dates locked in docx attachments → the docx alert (above);
  the schedule-pass itself reads noticeboard PDFs only.

---

## Appendix — manual Chrome-panel drill (outage fallback only)

Use when student tokens die or the workflow is down. Via the
Claude-in-Chrome extension riding the owner's logged-in browser; output is
pasted into the build chat, which writes + commits the targets file.

1. **Panel on the right account** — must match the project chat's account.
2. **Log into the school's Canvas** as the student. Separate logins = one
   run per student.
3. **Paste the instruction** (below) with Canvas open in the tab.
4. **Sanity-check:** every subject present (incl. the per-teacher ones),
   dot points per subject, assessment dates captured.
5. **Bring the output to the project chat** — the paste is the bridge.

```
Sweep this week's Canvas content for the students. For every active course,
open the current week's modules/pages and summarise per subject as dot
points: topic names, key concepts/skills, and anything assessment-related
(dates, task types, notifications). For y9, ALSO check the per-teacher class
pages for Science and English — their content doesn't live on the shared
module pages. For y8, sweep the Maths and Science course HOMEPAGES (weekly
schedules live there, not in modules) and the per-teacher English page.

If page-walking is slow, use the Canvas API instead:
GET /api/v1/courses?enrollment_state=active&per_page=50 for course IDs, then
/courses/[ID]/modules — batch in groups of four with ~1.5s pauses.

Output: one section per student, one sub-section per subject, dot points
only. End with "NEW OR CHANGED vs last week" and any assessment dates found.
```
