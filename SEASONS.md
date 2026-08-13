# Seasons — the live-game content calendar

*Principle: run the school year like a live-service game. (Mechanics doctrine only — commercial strategy stays off-repo.)*

- **Term = season.** Each season splits into **chapters** (2–3 per term); chapters into weeks. All students ride the same arc together.
- **Mechanics arrive at chapter boundaries** — staged tutorialisation, never everything at once. Each new mechanic joins a permanent **mechanics bank**.
- **The event loadout is a chapter-level variable.** Each chapter ships its own lineup of weekly events, drawn and remixed from the bank — Term 1 Chapter 2's Wednesday mutator is not Term 2 Chapter 1's. Novelty comes from rotation, not constant invention, so content economics *improve* as the bank grows.
- **Constants vs variables.** Constant: the weekly skeleton (daily runs Mon–Fri, a mid-week event slot, a Friday boss slot, weekends off) and the boss formula (each student's boss is built from their own ledger — the week's misses as attacks, a teach-back as the finishing move). Variable by chapter: which mutator fills Wednesday, which theme/mechanic skins the boss, seasonal cosmetics and XP economics.
- **Retention logic:** something is always coming (the next chapter reveal); returning mechanics feel like old friends; the calendar can be authored a term ahead.

## Mechanics bank (named, permanent)

- **Blitz** — tempo mutator: 10 speed / 2 steady / 1 teach; double-XP at the family deal layer (weekly tally, never in-app). High score ceiling → Blitz Master badge.
- **Reversed** — direction mutator: the prompt states the ANSWER; the four options are candidate QUESTIONS; pick the one it belongs to. Applies to FACT-BASED speed slots only — calculation topics (equations, angles, area) stay standard recall, because candidate questions for a numeric answer routinely collide (several equations solving to the same x; the 12 Aug y8 HOLD). Trains discrimination between near-neighbour facts (the exam failure mode where facts "swap houses" under pressure) — the deliberate inverse of pure recall. Composition doctrine lives in planner/_composer_instructions; the review gate has reversed-aware category mapping. Structurally pure MC — no shell/schema cost.
- **Boss chain** — the Friday constant: chained steady questions on the student's own ledger gap, misses as attacks, teach-back as finishing move. (Formula constant; theme/skin is the chapter variable.)
- **Battleground (Friday)** — the Friday constant, self-contained: the student's weekly shot at claiming the ground on topics they struggled with. Four claimable zones on their flagged weak topics; each zone is a question in the best format for that topic (spot-the-lie / true-false / multiple-choice / sum-as-MC — composer's choice, varied across the four; typed-number sums deferred to Shell v3.1). Land a zone -> claimed; miss -> contested, no penalty, truth shown. Territory bar fills; ends on "% claimed this week" with loud tiers (100% = the field is yours). NEVER win/lose — a struggling kid can't fail their own weak spots; progress is the number. Replaced the Boss/HP-drain framing (binary beat/lose felt hollow and punished strugglers). Varied formats are Friday-only for now.
- **Boss Nights (future / not live)** — a win/lose event mode preserved in `modes/boss-battle/` (frozen shell + design doc `BOSS-NIGHTS.md`). Real fail state (you beat the boss or you don't; XP either way), built from ledger weaknesses. NEVER the Friday slot — losing on your worst subjects as the week's verdict discourages the kids it targets. Works only as a **campaign**: run as a seasonal Boss block where you win some / lose some, and the season record ("won 3 / lost 2 → new target next season") is the motivator. Unlocks richer badging/stats (win streaks, comebacks, nemesis subjects). Revive later for a season or beta phase; keep off Friday.

**Current live loadout** — Season "Term 3," chapter of w/c 3 Aug: Wed mutator = **Reversed Blitz** (10 reversed speed / 2 steady / 1 teach) with double-XP at the family deal layer · Fri boss = ledger-built chain. *(Reversed joined mid-chapter by design call — family beta is the design lab; the chapter-boundary rule holds for staged rollout beyond the family.)*

---

## Friday, as of 11 Aug 2026 — three things now land on Friday

Friday is the busiest day in the skeleton. It carries **three separate clocks**,
and they must not be confused:

| Time (AEST) | What | Audience | Trigger |
|---|---|---|---|
| 2pm | Daily publish (Battleground set) | kid | scheduled, `daily-quiz.yml` |
| 4pm | Kid nudge | kid | scheduled, `kid-nudge.yml` |
| ~on completion | Evening soundbyte (reassure) | parent | `evening-soundbyte.yml` |
| **8:35pm** | **Weekly report — SMS + hosted page** | **parent** | **`friday-report.yml`** |

**Friday sends TWO parent texts.** The on-completion soundbyte (that day's run,
reassure-only) and the scheduled weekly report (the week's verdict, judge). They
are different messages on different clocks and neither replaces the other.

The report fires at 8:35pm so the day's run is usually already in. If it isn't,
the report honestly reads four days instead of five — it never waits, and it
never claims a day that didn't happen.

**One send per kid per week**, enforced by `work/friday_report_cursor.json`, so a
manual re-dispatch after a partial failure is a no-op for anyone already sent.

**The weekly snapshot** (`work/report_snapshots/<week_of>.json`) is written at the
end of every Friday run. That file is what makes the NEXT Friday's trajectory and
depth movement computable — week 1 has no trend precisely because no snapshot
exists yet. If a Friday run is skipped entirely, the following week loses its
comparison baseline.
