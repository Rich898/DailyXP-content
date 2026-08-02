# DailyXP — agreed roadmap (locked Mon 3 Aug 2026)

## This week (w/c 3 Aug) — shell FROZEN at v3.0
Content-level changes only: teach-back prompt variety (argue-against, explain-to-a-younger-kid, mark-the-wrong-answer), difficulty pitched a notch harder (trivially-fast corrects = noise, not signal). Let the new pipeline bed in; keep Week-2 data comparable to Week 1.

## Next weekend (~8–9 Aug) — shell v3.1
- Typed answers: numeric entry for maths, short text for terms/dates (normalised accepted-answer lists; instant feedback preserved)
- Ordering items (sequence the causal chain) + spot-the-error / cloze as steady-slot variants
- Hidden double-XP question per night; Friday "Boss Round"; optional 2-question encore after finish
- Skeleton (speed→steady→teach) unchanged — variety lives inside the slots
- Ship only with all three tests green + new item-type tests; redeploy into same projects (URLs unchanged)

## Scheduler (build alongside v3.1)
Goal: remove the daily "go". Leading candidate: GitHub Actions cron on this repo — reads results, updates state, composes+publishes daily sets via the Claude API; Canvas via per-student API access tokens (harvest tokens this week: Canvas → Account → Settings → New Access Token). Guardrails from day one: hard schema validation before publish; failure mode = yesterday's quiz or the no-quiz screen, never a broken one; visible publish log; parent reports stay human-reviewed initially.

## Open input
One make-it-more-fun idea per student, collected at the weekly sit-downs.
