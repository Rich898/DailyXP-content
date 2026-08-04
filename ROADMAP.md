# DailyXP — agreed roadmap (locked Mon 3 Aug 2026)

## This week (w/c 3 Aug) — shell FROZEN at v3.0
Content-level changes only: teach-back prompt variety (argue-against, explain-to-a-younger-kid, mark-the-wrong-answer), difficulty pitched a notch harder (trivially-fast corrects = noise, not signal). Let the new pipeline bed in; keep Week-2 data comparable to Week 1.
**Weekly cadence policy (locked):** Monday quizzes = ledger-driven consolidation by design (teachers rarely post the week's plan by Monday). Fresh Canvas content enters Tue–Fri, after the owner's weekly sweep — automated via student API tokens once the scheduler lands.

### Events this week (locked)
- **Mon / Tue / Thu:** standard 7/4/1 sets — the comparable control.
- **Wed — MUTATOR NIGHT (Blitz):** 10 speed + 2 steady + 1 teach-back; double-XP applied at the family deal layer (weekly tally), not in-app. Announced Tue night via short "patch notes".
- **Fri — BOSS NIGHT:** per-student boss built from that student's ledger weaknesses — a chained 3–4 question steady sequence on the flagged gap, the week's actual misses resurfaced as "attacks", teach-back as the finishing move. Boss composed from ledger state as of Thu night.
- Rationale: events on exactly two nights vs a stable control = honest read on engagement lift. Head-to-head/sibling formats deliberately shelved — mechanics must generalise to single-player universal adoption.

## Next weekend (~8–9 Aug) — shell v3.1
- Universal skip: "haven't covered this yet" button unconditional on every question (no flag dependency)
- Typed answers: numeric entry for maths, short text for terms/dates (normalised accepted-answer lists; instant feedback preserved)
- Ordering items (sequence the causal chain) + spot-the-error / cloze as steady-slot variants
- Hidden double-XP question per night; Friday "Boss Round"; optional 2-question encore after finish
- Skeleton (speed→steady→teach) unchanged — variety lives inside the slots
- **Beta kit (same weekend):** one deploy per year level with per-student `?kid=` codes (link remembers the kid; pseudonymous k-codes in results, name-map kept private); per-family separation in the results store; link-preview branding (OG tags + branded card image so shared links unfurl as DailyXP); onboarding email + parent consent block (drafted); deletion script honouring the export/delete-on-request promise; ledger seeding from intake material
- Ship only with all three tests green + new item-type tests; redeploy into same projects (URLs unchanged)

## Scheduler (build alongside v3.1)
Goal: remove the daily "go". Leading candidate: GitHub Actions cron on this repo — reads results, updates state, composes+publishes daily sets via the Claude API; Canvas via per-student API access tokens (harvest tokens this week: Canvas → Account → Settings → New Access Token). **SMS delivery layer (in scope):** reports go out by text — branded one-way alphanumeric sender via an SMS API (Twilio-class); kid weekly recap + parent weekly summary as short texts, deep-dive report as an unguessable hosted link deployed by the same job; mobile numbers join the data register and deletion promise; provider key lives in Actions secrets. **Parent reporting rhythm — DECIDED (three touchpoints, three jobs):**
- **Daily soundbyte** (completion-triggered, right after a run lands): reassure. Score, streak, done. **Content law: carries NO ammunition** — never misses or gaps, so it cannot fuel nagging.
- **Midweek check-in** (Wed morning): activate. Momentum read + ONE "something to say" (specific, data-grounded praise script) + ONE "area where you can help" (a ~5-minute action). This productises the ledger's sit-down actions.
- **Friday headlines** (+ link to the full report page): judge. 3 headlines, deep dive one tap away.
Per-family config still applies at beta (each touchpoint on/off). Content format is being tested manually on the family this week (drafts delivered with each morning's run; owner forwards by text) before the SMS layer automates delivery. **Delivery idempotency:** results reader dedupes rows by (student, ts) — duplicate posts observed from retry taps; add doPost-side idempotency in v3.1. Guardrails from day one: hard schema validation before publish; failure mode = yesterday's quiz or the no-quiz screen, never a broken one; visible publish log; parent reports stay human-reviewed initially.

## Domain (registered — owner holds it)
Domains purchased: full `xpdaily.*` set EXCEPT `xpdaily.com` (taken by a third party) — so `xpdaily.com.au`, `xpdaily.co.uk`, `xpdaily.net` etc. — PLUS the complete `xp-daily.*` set (`.com`, `.co.uk`, `.com.au`, `.net`, …). **CANONICAL FACE (confirmed): `xpdaily.com.au`** (Australian-first — best local trust + AU carrier link-reputation); `xp-daily.com` = global/backup face; all others 301-redirect to primary, defensive holdings. **Confirm an ABN was supplied for the `.com.au` registrations** (AU-presence requirement). **Brand tiebreaker resolved: standardise on "XP Daily" / xpdaily** — align shell wordmark + SMS sender ID to it in the beta-kit build (retires the DailyXP/XP Daily drift). **Not yet wired — deliberately parked until the beta-kit weekend.** Then: point the per-year quiz sites and the report pages at the custom domain (Netlify custom domain + auto HTTPS, ~20 min), shipped alongside the OG preview cards so branded links go out together. Cures the dead-link disease (repoint the domain, old links keep resolving) and lifts SMS link-trust for non-family texts. `.com.au`/`.au` require an ABN — confirm before relying on them.

## Entity / ABN (admin, this-week, decoupled from code)
Owner has an existing company with an **ACN**. For the branded SMS sender and the `.com.au`, the register/registrar want an **ABN** (not the ACN) — a company can get an ABN free online, issued near-instantly, built from the ACN. Actions: (1) confirm whether the existing company already holds an ABN; if not, apply (10-min form); (2) sanity-check the `.com.au` registration went through on a valid AU-presence (ACN/ABN); (3) use that ABN for the ACMA SMS Sender ID Register so "XP Daily" shows verified, not "Unverified". **Strategic flag (decide before money, not now):** which entity fronts XP Daily — existing company for beta speed, or its own entity later (keep clean of VitalYOU per original principle). Free friends-beta: existing company's ABN is fine.

## Open input
One make-it-more-fun idea per student, collected at the weekly sit-downs.
