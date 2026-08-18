# XP Daily — Current State (authoritative)

_Last updated: 18 Aug 2026. This file is the source of truth for what the quiz actually is today. Where any
other doc disagrees with this one, this one wins._

## The quiz, as it runs today

Every quiz is **plain, direct multiple-choice** — one short question, four short options, one uncontestable
answer, plus a re-teaching `why`. Nothing else. A standard quiz is **12 questions**: 7 speed + 4 steady +
1 teach-back.

- **Brevity is enforced by the composer prompt**: every question is short and about ONE thing; options are
  1–4 word answers, never compound multi-fact sentences. Applies to speed and steady.
- **Subject balance is enforced by the planner** (`tools/planner.py`):
  - Each live core subject (Maths, English, Science, History) is **guaranteed at least one slot** per quiz
    (`CORE_SUBJECTS`, the coverage pass) — even if its topics are low-priority/untested, which would
    otherwise starve a subject.
  - **No subject takes more than 3 MC slots** (`MAX_PER_SUBJECT`).
  - A **relaxed fallback** fills the full 12 even when the eligible pool is thin (bypasses the score floor
    for coverage/top-up), so a quiz never shortfalls below 12 on a thin ledger.
  - Within those rules, the weakest topics (REPAIR → shaky → developing → untested → solid) are prioritised.
- **Teach-back** ("explain it in your own words") is one slot per quiz, graded for mastery on **verdict +
  depth** only (`tools/grade_teachback.py`). Substance over style; spelling/grammar never matter.

## The pipeline

- `scripts/run_daily.py` runs at **2pm Sydney, weekdays**, both students by default. It auto-selects the
  **newest** `targets/<date>.json` from the PRIVATE repo (warns if >7 days stale) and produces plain-MC,
  subject-balanced quizzes from it.
- **Harrison (y8)** is ACTIVE. **Roshan (y9)** is FROZEN for school camp (resumes on return, streak intact).
  **t1** is Rich's dogfood test seat (aliased to the y8 curriculum).
- GitHub Actions cron is best-effort; the watchdog texts if a run fails to publish.

## What was built and REMOVED (17–18 Aug 2026)

A large set of alternative question mechanics was built, played, and rejected as confusing / not fun, then
removed from the codebase. **All of it is in git history** if any single piece is ever revisited deliberately:

- **Typed input types** — numeric keypad, short-text, cloze (fill-blank), tap-to-order. (`tools/qtypes.py`,
  deleted.)
- **MC "format variety"** — odd-one-out, spot-the-lie, spot-the-error, matching, ordering-as-MC.
  (`tools/formats.py`, deleted.)
- **Hidden ×2** (ledger-invisible double-XP) and the optional **encore** bonus round.
- **Teach-back instant three-light display** and its **Supabase Edge Function** (`gen_edge_function.py` +
  `supabase/functions/grade-teachback/`, deleted — the function was never deployed). The teach-back itself
  stays and is still graded for mastery; only the live in-shell lights were removed.
- **Idempotency SQL** (`supabase/runs_raw_idempotency.sql`, deleted — never run).

### Known dormant code (not yet stripped)

`shell/template_v3.html` still contains the rendering code for the removed types (keypad/text/order/×2/
encore/teach-back-lights). It is **harmless** — plain-MC quizzes never trigger those branches — and the
deployed Netlify shells match this file. Fully removing it would require a careful shell pass **and a
re-deploy of all three Netlify shells**, for no functional change. Left as a deliberate future cleanup.

## The process lesson (why the above was reverted)

New quiz modes/mechanics must be built **one at a time**, prototyped in an **isolated preview the user
taps through and approves for FUN**, and kept **out of the kids' live quizzes** until approved. Shipping a
stack of untested mechanics straight into live quizzes is what produced the wasted work here.
