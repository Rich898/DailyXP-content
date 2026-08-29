# PARENT-COMMS-BUILD-BRIEF.md — execute the aligned parent-comms program

Bootstrap doc for fresh sessions. Written 29 Aug 2026. Read `WORKING-MODEL.md`
first and follow it. Then this file: it is the BUILD PLAN for the parent
communication & reporting redesign Rich reviewed and aligned on 29 Aug
("the Full Picture" — decisions 1–8). The strategy itself (the what and why,
touchpoint by touchpoint, with the laws) is **`PARENT-COMMS-V2.md`** — read it
before building anything; where this brief is thin, that file is the detail.
**`ACTIONS.md`** is the live tracker: update its rows as items land, add rows
for anything new. Nothing here re-opens the strategy — the arguing is done.

**First message to Rich, every session: "Which work item today?"** — then do
that one well. Do not attempt the whole program in one session.

## How to work with Rich (non-negotiable, same as every brief)
- Plain English before technical detail. One small action, confirm, next.
- Honest pushback over agreement. He is the decision-maker; not an engineer;
  voice dictation (expect typos, never comment on them).
- Shadow-first, t1-gated (t1 = Rich's own test seat); promote only on his
  explicit word. New/changed parent-facing formats go through the preview
  window: `dry_run=true` dispatch → previews land as a private workflow
  artifact → Rich eyeballs → then live.
- Never edit the live send path during Sydney evening send windows
  (~17:30–22:15 weekdays).
- Every change: tests green on Python 3.11 (CI's version), then merge on
  Rich's word, then verify LIVE (build stamps make this checkable), then tick
  the ACTIONS.md row. A chat message is never "done".

## What is already DONE (merged to main 29 Aug, PR #16/#17 — do not redo)
- Stale-page root cause fixed: Netlify lowercases paths; everything now speaks
  lowercase (`RUNBOOK.md` Gotcha #11). Pages replace correctly again.
- Build stamp on every report page + `netlify_deploy.verify(expect=stamp)` —
  a deploy can only go green if the live URL serves the exact render just
  uploaded. Reuse `report_page.build_stamp()` on every new page kind.
- `redeploy=true` input on the Friday workflow: re-render + re-deploy an
  already-sent week, no SMS, no state writes. The recovery / rollout button.
- Public Actions logs are PII-free (codes only — never names, never per-kid
  URLs); dry-run SMS bodies go to preview files, collected by the dry-run
  artifact step.
- `notify.py`: `parents:<code>` resolves to its own secret or nobody (the
  cross-household misroute fallback is deleted).
- `friday_report.py`: excused days (pipeline HOLD / recorded absence) leave
  the activity denominator; a fully-excused shortfall can't verdict "quiet".
- Live state: all three report pages dark + stamp-verified; test SMS to
  parents:t1 delivered.

## The work items, in recommended order

### W1 — Scheduler migration (decision 7, part 1) — APPROVED, ready
GitHub skipped all three Friday-send crons on 28 Aug; its clock also drifts an
hour when DST starts 4 Oct. Move the Wednesday + Friday sends to the Supabase
scheduler (pg_cron → `xp_dispatch()` → workflow_dispatch), GitHub crons
demoted to cursor-guarded backup — the daily-quiz pattern exactly.
- Convention (`supabase/002_scheduler.sql`): `xp_schedule(job, workflow,
  local_time, days int[], enabled)`, Sydney-local, ISO dow, one row per slot
  with a distinct job name (dedupe is one fire per job per local day).
- Rows: `wed-checkin-1825` + `wed-checkin-2025` → wed-checkin.yml, `{3}`;
  `friday-report-2035` / `-2105` / `-2145` → friday-report.yml, `{5}`;
  `friday-report-0730-sat` `{6}`.
- Verify end-to-end with a TEMPORARY row firing friday-report a few minutes
  ahead (the weekly cursor makes a same-week dispatch a safe no-op; watch
  `xp_dispatch_log` + the Actions run), then delete the temp row.
- Update SYSTEM-MAP.md's trigger lines. Done means: rows live, one observed
  dispatch, tracker B1 ticked.

### W2 — Ship the kid wrap (Rich's "badges that nothing shows them" item)
The kid's weekly page (`KID-REPORT.md`, ratified spec: a player card, not a
report card) is built (`tools/kid_wrap.py`) and script-tested
(`tools/test_kid_wrap.py`) but has NEVER been deployed —
`friday_report_run.py:213` computes `wrap_url`, line 215 passes
`kid_wrap_url=None`, `kid_wrap` is never imported. Badges kids earn have no
surface; also a transparency-law breach in practice (parents get Friday detail
the kid's mirror never shows). In order:
1. Dark repaint (`kid_wrap.py:402` still `--paper:#F7F8F4`; `:971` light
   theme-color) — colours only, same treatment commit `728ab0d` gave
   `report_page.py` (#0B1220 radial ground, shell accents).
2. Cabinet reconcile (`CABINET` at :138-140): drop retired "Boss Slayer", add
   **Full Claim** + **Personal Best** (icons + earn-lines, dicts at :146/:158)
   — verify names against `tools/achievements.py`, the runtime truth.
3. Add the build stamp (import `report_page.build_stamp`), early in `<head>`.
4. Wire deploy in `friday_report_run.py`: render wrap, publish to
   `slugs[code]["wrap"]` kind `"w"` BEFORE the report, pass real
   `kid_wrap_url` only if the wrap verified live (never link a 404). Wrap
   slugs already exist in private `work/report_slugs.json`. Logs: codes only.
   Dry-run: write `preview_wrap_<code>.html`; widen the workflow artifact
   glob `preview_report_*` → `preview_*`.
5. Verify: suites green (3.11) → dry-run artifact eyeballed → merge on
   Rich's word → `redeploy=true` puts wraps live for all seats same day.
- Laws: `KID-REPORT.md` in full — transparency law; integrity-quarantined
  teach-backs NEVER surface to the kid in any form; praise the move never the
  player; no comparisons; wrap rides the SAME fact card as the parent report,
  never a second facts layer.
- Ask Rich during the build: does the kid get his own Friday text with the
  wrap link now, or with the board (W7)? One recommendation, his call.

### W3 — Friday report: subject spine (decision 1)
Reorganise the page around per-subject blocks that close Monday's loop: what
school set (targets) → what his sets actually worked (bullets from
`plans/<seat>/` + published quiz JSON — NEVER intent) → per-topic position
(band) + depth where evidenced → at most one misconception detail (the
archived set's own `why`) → next week for that subject. Keep hero, win, quote,
say/do, radar, week-on-week; add the cumulative footer strip ("Maths 4 of 6
topics landed…"). Narrate the fluency-illusion catch when it fired. Laws that
survive: positions weekly / per-subject trends monthly; depth ceiling; gaps
arrive with their fix. Files: `friday_report.py` (much is computed already —
`snapshot()`, `standing_detail` are unrendered), `report_stories.py`,
`report_page.py`. Ship through the preview window, t1 first. On Rich's
ratification, land the REPORTING.md amendment with supersession scope.

### W4 — The always-available page (decision 2)
New `tools/portal_page.py`, deployed to `/p/<slug>/` on the reports site
(new slug kind in `report_slugs.json`, lowercase). Sections top to bottom:
NOW (per-subject class focus + assessment radar) · THIS WEEK (sweep diff
"NEW OR CHANGED" + what the sets will do — this panel is Monday's content as
pull) · SUBJECT CARDS (position + depth side by side, incl. solid×lists →
"strong recall; hasn't yet shown he can explain it") · TERM TRENDS (from
`work/report_snapshots/`, render only at 4+ weeks, say so) · ARCHIVE (needs
dated report paths `/r/<slug>/<week>/` with the bare slug serving latest) ·
footer legend + "updated <date>" stamp. Laws: judgment recomputes Friday
only; This-Week refreshes Monday; NEVER same-night results; aging rule
(repaired topics collapse into wins); quotes rotate, and a quote ARCHIVE
waits on the outstanding APP 8 privacy advice. Republish from the Monday seed
job + the Friday job. t1 first.

### W5 — Slug rotation + "bookmark this" (B4/B5)
Current slugs leaked into old public Actions logs — burned. Rotate all slugs
in private `report_slugs.json` (new ones auto-generate lowercase token_hex),
redeploy via `redeploy=true`, THEN send each family the one-time "bookmark
this — {name}'s page is always there" text (Rich approves copy). Order
matters: rotate before telling anyone to bookmark.

### W6 — Monday Week-Ahead SMS (decisions 3 + 4) — GATED
Arms only after TWO consecutive clean automated-sweep Mondays (first live
trust test: Mon 31 Aug). Until then Monday's content lives on the W4 panel.
Build dark, ready to arm: wed_checkin architecture (deterministic fact card →
dresser → validator → deterministic fallback), own cursor + watchdog rung +
pg_cron slot. The Monday law (validator-enforced): forward-looking only —
no verdicts, no standing words ("solid", "building", "behind", "close to
locking in"), no digits except an assessment date; facts from the sweep diff
+ plan files only; per-teacher subjects hedged unless verified; fail-soft
honest continuation copy when the sweep is stale; kid sees his week in the
quiz before any parent text mentions it; merged with a Monday soundbyte when
the run is already in (the Wednesday-merge precedent). **Household
consolidation ships with it (decision 4):** one text per household, one
sentence per kid, no juxtaposed verdicts — and Friday sends consolidate the
same way. t1 first, then household.

### W7 — The weekly board (decision 5) — kid-first, sit-down gated
"Up for grabs this week": deterministic Monday offers written to private
`weekly_offers.json`, embedded in the published quiz JSON (no new fetches),
resolved by the nightly achievements pass (`Contract|{iso_week}|{name}`
keys), rendered on quiz start/end screens + the wrap. Standing contracts:
ON THE BOARD (4 of 5 nights) · CLEAN HANDS WEEK (3 nights, zero lucky + zero
confident-wrong — NO raw-% accuracy badge, ever) · IN YOUR OWN WORDS (a
teach-back graded solid; gold at connects). Named offers (≤2): LOCK IT /
BOUNCE BACK, picked from the ledger's within-reach topics
(`kid_wrap.badge_hints` prototypes this). Untaken offers roll forward, never
"fail". Parents: offers forward + stories backward, NEVER tallies. Kid sees
the board before any parent mention. Supersedes the parked deal card.
Harrison & Roshan's sit-down reaction gates parent-visible offers. Amend
`ACHIEVEMENTS.md` on ratification.

### W8 — Guarantees, rest of (decision 7): as capacity allows
Term `calendar.json` gating EVERY scheduled send — BEFORE spring break
(~25 Sep) — plus the end-of-term cumulative wrap; `EXAM-MODE.md` (referenced
in SYSTEM-MAP, doesn't exist); Mobile Message delivery webhook (accepted →
delivered); per-family per-touchpoint on/off as real private config + a
documented opt-out path; measurement (delivery rate, link taps, opt-outs,
completion latency, fortnightly parent pulse) with go/no-go thresholds for
the ten-family beta.

## The kill list (decision 8 — refuse these, with the reasons in PARENT-COMMS-V2 §10)
A rename now · parent-visible badge counts/tallies · a raw-accuracy badge ·
a Monday SMS before the sweep gate · same-night results on the portal ·
a second weekly channel (email waits for magic-link auth + a monthly digest) ·
lightening Wednesday · custom auth of any kind.

## Ratification bookkeeping
Rich is aligned on direction (29 Aug). Each work item that changes a ratified
doctrine still lands its own amendment (REPORTING.md / ACHIEVEMENTS.md /
WORKING-MODEL.md) in the same PR as the build, with explicit supersession
scope — the docs are law; code must not outrun them again.
