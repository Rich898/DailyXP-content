> ⚠️ **SUPERSEDED (18 Aug 2026).** The typed inputs / MC format variety described here were built and REMOVED after review. See **CURRENT-STATE.md** for what actually runs today. Kept for historical reference.

# Seasons — the live-game content calendar

*Principle: run the school year like a live-service game. (Mechanics doctrine only — commercial strategy stays off-repo.)*

- **Term = season.** Each season splits into **chapters** (2–3 per term); chapters into weeks. All students ride the same arc together.
- **Mechanics arrive at chapter boundaries** — staged tutorialisation, never everything at once. Each new mechanic joins a permanent **mechanics bank**.
- **The event loadout is a chapter-level variable.** Each chapter ships its own lineup of weekly events, drawn and remixed from the bank — Term 1 Chapter 2's Wednesday mutator is not Term 2 Chapter 1's. Novelty comes from rotation, not constant invention, so content economics *improve* as the bank grows.
- **Constants vs variables.** Constant: the weekly skeleton (daily runs Mon–Fri, a mid-week event slot, a Friday boss slot, weekends off) and the boss formula (each student's boss is built from their own ledger — the week's misses as attacks, a teach-back as the finishing move). Variable by chapter: which mutator fills Wednesday, which theme/mechanic skins the boss, seasonal cosmetics and XP economics.
- **Retention logic:** something is always coming (the next chapter reveal); returning mechanics feel like old friends; the calendar can be authored a term ahead.

## Mechanics bank (named, permanent)

- **Blitz** *(retired 20 Aug 2026)* — was a speed-heavy tempo mutator with family-tally double-XP and a Blitz Master badge. Removed as the Wednesday event; the Reversed mechanic it carried is being repurposed as a daily question-type. Kept here only as history.
- **Reversed** — direction mutator: the prompt states the ANSWER; the four options are candidate QUESTIONS; pick the one it belongs to. Applies to FACT-BASED speed slots only — calculation topics (equations, angles, area) stay standard recall, because candidate questions for a numeric answer routinely collide (several equations solving to the same x; the 12 Aug y8 HOLD). Trains discrimination between near-neighbour facts (the exam failure mode where facts "swap houses" under pressure) — the deliberate inverse of pure recall. Composition doctrine lives in planner/_composer_instructions; the review gate has reversed-aware category mapping. Structurally pure MC — no shell/schema cost.
- **Boss chain** — the Friday constant: chained steady questions on the student's own ledger gap, misses as attacks, teach-back as finishing move. (Formula constant; theme/skin is the chapter variable.)
- **Battleground (Friday)** — the Friday constant, self-contained: the student's weekly shot at claiming the ground on topics they struggled with. Four claimable zones on their flagged weak topics; each zone is a question in the best format for that topic (spot-the-lie / true-false / multiple-choice / sum-as-MC — composer's choice, varied across the four; typed-number sums deferred to Shell v3.1). Land a zone -> claimed; miss -> contested, no penalty, truth shown. Territory bar fills; ends on "% claimed this week" with loud tiers (100% = the field is yours). NEVER win/lose — a struggling kid can't fail their own weak spots; progress is the number. Replaced the Boss/HP-drain framing (binary beat/lose felt hollow and punished strugglers). Varied formats are Friday-only for now.
- **Boss Nights (future / not live)** — a win/lose event mode preserved in `modes/boss-battle/` (frozen shell + design doc `BOSS-NIGHTS.md`). Real fail state (you beat the boss or you don't; XP either way), built from ledger weaknesses. NEVER the Friday slot — losing on your worst subjects as the week's verdict discourages the kids it targets. Works only as a **campaign**: run as a seasonal Boss block where you win some / lose some, and the season record ("won 3 / lost 2 → new target next season") is the motivator. Unlocks richer badging/stats (win streaks, comebacks, nemesis subjects). Revive later for a season or beta phase; keep off Friday.

## Quiz variety & answer-integrity law (ratified 17 Aug 2026)

*Origin: the two boys' own feedback in beta — "same questions every day," "not
enough variety," "topics always feel the same," "needs more types of quizzes and
puzzles," "throwback Thursday where we retest what you did weeks prior," and the
sharpest one — "it feels like AI because often the answer is the longer text."
The last was measured and CONFIRMED: in the 17 Aug live sets the correct MC
answer was the longest option 70% of the time (100% in English/Geography, 91% in
History) against a 25% random baseline. A child could score ~70% by tapping the
longest option WITHOUT READING — that partly invalidates the recall signal the
ledger is built on. These are laws, not preferences; they exist so the failure is
never silently reintroduced.*

### LAW 1 — the answer-length tell is banned (P0, integrity)

The correct option must NOT be identifiable by length. This is enforced in CODE,
never left to the language layer (the LLM naturally writes precise = long correct
answers and terse distractors; it cannot self-police this):

1. **Composer constraint** (planner `_composer_instructions`): the correct answer
   may not be the longest option; all four options sit in a similar length band;
   distractors are made *specific and plausible*, not short throwaways.
2. **Deterministic per-slot gate** (`review.py`): after composition, measure
   option character lengths. A slot where the correct answer is the sole longest
   by a meaningful margin is a BLOCKING flag → recompose with a targeted note.
3. **Per-RUN distribution rule** (`review.py`, whole-set view): forcing "correct
   is never longest" would just teach "never tap the longest" — a new tell. The
   real target is a FLAT distribution: across a run's MC slots, the correct
   answer's length-rank must spread across positions 1–4, not pile on rank 1.
4. **Metric**: the validator/reviewer prints the run's longest-is-correct rate so
   it is watched every day; target ≈ 25% (random), hard ceiling well below 70%.

This law generalises: the correct answer must never be guessable from ANY
surface feature — not length, not grammatical completeness, not "the only one
with a qualifier," not option position. Length is the one we caught and measure;
the principle covers the rest.

### LAW 2 — variety is structural, driven by a FORMAT BANK

> **Status (19 Aug 2026):** the standard-run format rotation described below was **reverted after review** — standard runs are direct recall MC (validated). Varied formats are **Friday-Battleground-only**; Reversed remains the **Wed mutator only**. The concept below is kept as design intent, not current live behaviour. The current path to daily variety is the approved answer mechanics (`modes/MECHANICS.md`).

"Same every day" is a structural fact when every slot is 4-option recall MC on the
same handful of weak topics. Fix: the **daily format mix becomes a planner
variable**, extending the existing SEASONS principle ("the event loadout is a
chapter variable") down to the day. Novelty comes from ROTATION across a bank,
not constant invention — content economics improve as the bank grows.

**Format bank — all render as four tappable options, so ZERO shell/schema cost
and ledger/grading untouched (they read ok/picked only):**
- **Spot-the-lie** — four statements, one false; tap it. (Also breaks the length tell.)
- **Spot-the-error** — a worked solution with one wrong step; tap the bad line. (Maths.)
- **Odd-one-out** — four items, one doesn't belong; trains categorisation.
- **Ordering-as-MC** — "which sequence is correct?" four candidate orders. (Chronology, method, steps.)
- **Matching-as-MC** — "which pairing is right?"
- **Reversed** — existing mechanic (answer stated, options are candidate questions); promoted from Wed-only into daily rotation. Fact-based slots only; numeric-distinctness rule stands.

The planner draws a format lineup per day from the bank; the composer renders each
in the format the plan declares. Mon/Tue stop being 11 identical taps. NEW formats
that need typed input, dragging, or multi-select are NOT in this bank — they need
Shell v3.1 (see LAW 4).

### LAW 3 — Throwback is a continuous daily mechanic (NOT an event)

Aged-but-mastered topics resurface **every run**, driven by the ledger's spacing
math, to check retention held. This is the confidence-weighted spaced-repetition
engine — the product's actual differentiator — made VISIBLE, and the direct answer
to "same topics every day" (which is caused by over-weighting current weak topics).

*Design note: an earlier draft framed this as a themed "Throwback Thursday" weekly
event. Rejected — the name was a placeholder example. A calendar-only throwback
would be a WORSE version of the spacing engine that already exists: it would let a
decayed topic sit undetected for up to a week, and leave Mon/Tue/Wed/Fri still
samey. Continuous beats weekly on both learning outcome (earlier decay-catch) and
variety (every night's topic mix shifts). No theatrics, no badge, no Thursday.*

Mechanics:
- **~1 slot per run** (never more than 2 — beyond that starves current coursework)
  is reserved for a topic that is currently `solid`/`developing` AND whose
  `last_tested` has aged past a spacing threshold. Selection is deterministic in
  the planner (own eligibility pool + own score: older + more-mastered = more due).
- **Ignores live-in-class status** — the whole point is topics that have LEFT
  active rotation. This is the deliberate inverse of the normal eligibility pool
  (which requires a live target row).
- **Held it** → the topic stays solid, `last_tested` refreshes, spacing interval
  extends (seen recently → won't return as soon). Small "still solid" signal.
- **Decayed** (missed) → the state_writer demotes it exactly as any miss does, and
  it re-enters the normal weak-topic rotation. This is the ledger doing its job.
- **Framing** is light and factual ("a topic from a while back"), never a fail
  state — a decayed throwback is a normal, useful find, not a loss.
- **History-bounded**: reaches only as far back as the ledger allows (thin at
  first, deepens automatically). Ship early so history compounds.

### LAW 4 — the runtime is NOT the target; variety is

Measured 17 Aug: mean run 4.1 min (median 3.7), active 3.8 min. The teach-back is
~40% of the run on a SINGLE question; the 11 MC together take less time than it.
So "not using the full 5 minutes" is really "the MC body is thin and samey," not a
duration problem. **The target metric is format variety + a flat answer-length
distribution, NOT runtime.** Varied formats will drift the run toward ~4.5–5 min as
a side effect; we do not pad to hit a number. A struggling kid is never made to sit
longer as an end in itself.

### LAW 5 — new INPUT types are Shell v3.1, deliberately deferred

Typed numeric answers, drag-to-order, tap-multiple etc. need a shell rebuild AND
grading changes (they do not reduce to ok/picked) and MUST NOT be rushed alongside
an integrity fix. They are their own scheduled build (v3.1), evaluated after Laws
1–3 land. ~90% of the variety win (Laws 2–3) needs no shell change — that is why we
ship variety now and stage v3.1 separately.

### LAW 6 — the OUTLINE drives the quiz; the ledger only ranks (ratified 20 Aug 2026)

The scraped weekly outline (Canvas) is the MENU the quiz fills from — the whole covered
curriculum, cumulative across the term, not just this week. The ledger (per-topic mastery)
sets PRIORITY only — which topics lead, which need the most attention — it NEVER caps the set.
A thin "due" list changes a run's emphasis, never its length. Corollary rules:

- **Seed on sight.** Every scraped topic is written into the ledger as `untested` the first time
  it appears, stamped with `introduced_week`, so it is instantly askable and tracked — new
  material is never invisible. (`tools/seed_menu.py`, wired into `scripts/run_daily.py` before
  planning; additive + idempotent, never touches mastery.)
- **Two tiers.** THIS WEEK (topics live in the latest scrape) is the priority and fills the bulk
  of every run; PRIOR WEEKS (covered before, not in the current scrape) come in only as a bounded
  throwback dose (LAW 3), weighted to recent weeks. Tier is the PRIMARY sort key in
  `planner.eligible_pool` — this-week always outranks prior-week; mastery orders only WITHIN a tier.
- **Always fill to shape.** The run fills every slot from the menu; it cannot go short because the
  due-list is thin.

Why this is a law: for weeks the quiz pulled questions from the *ledger*, not the *outline*, so
new topics were never asked and the boys saw the same handful repeat ("you keep asking the same
things"), and thin due-lists produced short/empty sets that failed to publish (the 20 Aug incident).
The composer generates content from the outline on demand — there is never a content shortage.
Source of truth: `tools/seed_menu.py` + `planner.eligible_pool` + the seed step in `run_daily.py`.

---

**Current live loadout** — Season "Term 3": **Wednesday is a standard day** (Blitz retired 20 Aug 2026 — the mid-week event slot is currently unfilled) · Fri boss = ledger-built chain (Battleground). *(Reversed is being repurposed from the retired Wednesday event into a daily question-type mechanic — a separate build; the mechanic is kept intact but dormant meanwhile.)*

**Live since 17 Aug 2026 (every standard run, all seats):** the answer-length gate (LAW 1) blocks the "tap the longest" tell, and the throwback mechanic (LAW 3) weaves one aged-mastered slot into every run as a spacing-driven retention check. Both are no-shell-cost and ledger-transparent, seeded deterministically. Origin: the boys' own beta feedback. Full doctrine: LAWS 1–5 above.

**20 Aug 2026 — the answer mechanics rolled to all seats.** Swipe / Numeric / Drag-to-order / Short-answer were t1-only (dogfood gate). After t1 proved them end-to-end (planner → compose → publish → shell render), the gate in `planner.assign_blocks` was lifted so Harrison and Roshan now get the full mechanic mix on standard days. Shell v3.1 (which renders them) must be deployed per seat for the mechanics to show. Same day: the outline-drives-the-quiz fix landed (LAW 6).

> **LAW 2 status — corrected 19 Aug 2026:** the standard-run format-bank rotation was **reverted after review** (varied MC-family formats read as confusing / wall-of-text in a fast round). Standard speed/steady slots are **direct recall MC** — validated against real quizzes (18 Aug: all recall-MC; see `CURRENT-STATE.md`). Varied formats survive **Friday-Battleground-only** (see the Battleground entry above). Reversed is being **repurposed from the retired Wednesday event (Blitz retired 20 Aug 2026) into a daily question-type mechanic** — a separate build. Daily variety is delivered by the approved answer mechanics — Swipe / Numeric / Ordering / Short-text (see `modes/MECHANICS.md`) — with Reversed to join them as a daily card.

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