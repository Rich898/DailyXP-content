# XP Daily — Quiz Flow (working)

_Part 1 is the honest inventory of every part we have. Part 2 (the flow design) is the next
step and lives at the bottom, empty for now. Verified 18 Aug 2026 against the code and real
composed quizzes — not from memory. Sources: CURRENT-STATE.md, SEASONS.md, LEDGER-RULES.md,
modes/MECHANICS.md, the shell, DailyXP-private history._

---

## PART 1 — THE PARTS

### 1. Answer mechanics (how a single question is played)

**Live**
- **Plain MC** — one question, four short options, one answer, a re-teach.
- **Teach-back** — explain in your own words; LLM-graded on verdict + depth (nightly). 1 slot every run.
- **Confidence wager** (steady layer) — pick answer → "How sure?" **Sure / Think so / Guessing** →
  Lock it in. This is the scheduling signal — it **gates ledger promotion** (see §5), not just logged.
- **Reversed** (Wed speed mutator) — prompt states the ANSWER, options are candidate QUESTIONS.
  Fact-based speed slots only; calculation topics stay standard recall.
- **Battleground formats** (Friday-only, all render as 4 options) — spot-the-lie / true-false /
  sum-as-MC / plain MC, varied across the four zones.

**Approved — built & specced, NOT yet integrated** (`modes/MECHANICS.md`)
- **Swipe Sort** — flick a statement into one of two labelled buckets.
- **Numeric** — type the answer; calculator on method Qs, plain pad on mental (scoped + logged).
- **Ordering** — drag scrambled tiles into sequence (live reflow).
- **Short-text** — type a word or two; fuzzy matcher forgives typos/variants.

**Dormant** (built, reverted after review — code inert)
- Standard-run format variety (odd-one-out / spot-the-error / matching), hidden in-app ×2,
  encore bonus round, the old interactive ordering, teach-back three-lights, old typed inputs.

**Parked** — tap-the-diagram (content-sourcing bet, not a shell build).

### 2. Modes (quiz shapes / weekly rhythm)

| Day | Mode | Shape | Total |
|---|---|---|---|
| Mon/Tue/Thu | **Standard** | 7 speed + 4 steady + 1 teach | 12 |
| Wed | **Reversed Blitz** | 10 reversed-speed + 2 steady + 1 teach | 13 |
| Fri | **Battleground** | 2 speed + 4 steady + 1 teach; claim 4 weak-topic zones, never win/lose, "% claimed" | 7 |

- **Boss Nights** — preserved *future* mode (losable, HP, finishing move). NOT wired; NEVER Friday.
- **Season structure** — term → season; chapters → weeks. Constant weekly skeleton (Mon–Fri runs,
  a mid-week mutator slot, a Friday boss slot, weekends off). The **event loadout is a
  chapter-level variable** — novelty from rotation, not constant invention.

### 3. In-quiz tools / systems (features within a run)

- **Heats** — Heat 1 = speed round, Heat 2 = steady round, then the teach-back.
- **Timer** — speed round only (fuse bar + countdown, red under 6s; timeout = miss).
- **Combo** — speed round; ×N with a combo bonus at ≥2.
- **Skip** — "it'll come back around"; on a `fresh` topic, "I'll check when your class gets there."
- **Re-teach** — the "why" shown on every question.
- **XP / scoring**; **Blitz double-XP** at the family weekly-tally layer (never in-app).
- **Achievements / badges** — Sure Shot, Clean Run (no lucky guesses / no sure-but-wrongs),
  Blitz Master/PB, etc.
- **Territory bar / % claimed** — Battleground only.

### 4. Planner intelligence (what picks the questions — generation-side, shapes the run)

- **Subject balance** — every core subject guaranteed, capped per run.
- **Repair** — weakest topics first.
- **Throwback** (LAW 3) — one aged-mastered topic woven into *every* run (continuous, not an event).
- **Fresh** — current class topics from the weekly Canvas sweep.
- **Answer-length gate** (LAW 1) — bans the "tap the longest option" tell.
- **Format bank** (LAW 2) — see the flagged discrepancy below.

### 5. The ledger / IP (the state under everything)

- **Two axes, independent:** **confidence** → scheduling (when to re-test); **depth** → reporting
  (what we tell parents). Solid is reached only by a **confident, calm, spaced** confirm.
- **Promotion logic** (`state_writer.py`, deterministic):
  - **Sure + correct** → can promote toward solid (calm + spaced).
  - **Think so + correct** → **developing at most**, never straight to solid.
  - **Guessing / lucky / trivially-fast correct** → **untested**, no promotion.
  - **Any wrong / fast-wrong / lucky / trivial-correct** → resets a REPAIR topic's confirms to 0.
- Deterministic code owns all scheduling + state; the **LLM only does language**.
- **Curriculum taxonomy** — maps messy Canvas content onto stable, masterable topics (the moat).

### 6. Rules / laws (the constraints everything obeys)

- **Fair judging** — numeric equivalence (0.75 = ¾), fuzzy text matching; a right answer is never
  failed on a technicality.
- **Spelling & punctuation are coaching-only** — never demote mastery (teach-back + short-text).
- **Confidence is the scheduling signal** — the one player input that gates promotion.
- **Calculator use is logged** — a calc-assisted correct answer is never counted as mental mastery.
- **Evidence weight** — a swipe (50/50) is weak; MC is medium; typed / numeric / ordering are strong.
- **No negation framing in the fast rounds** — spot-the-lie is Friday-Battleground-only.
- **Short, fast-to-READ speed questions** — no walls of text, no puzzles in the timed round.
- **Reordering must be real drag** (Pointer Events, live slide) — never tap-to-order or HTML5 drag.
- **Process:** one mechanic at a time → isolated playable prototype → approved for fun AND quality
  → only then integrated. Untested mechanics stay out of live quizzes.
- **Parent comms:** silence is the only "not done" signal; transparency law (parent facts on the
  kid wrap can't be hidden from the kid).
- **SEASONS laws 1–5:** answer-length gate · format bank · throwback continuous · runtime≠target ·
  new input types were deferred to "Shell v3.1" (now being done properly as the approved mechanics).

### ⚠ Flagged discrepancy (found while building this, validated against real output)
**SEASONS.md line 133** says the standard-run format bank rotates 6 MC-family formats so "no run
is 11 identical recall MC." Real standard quizzes (18 Aug) are **11 recall-MC, zero variety** —
the standard-round format rotation was reverted; variety is **Friday-Battleground-only** (which
line 18 correctly states). Line 133 is stale and internally contradicts line 18. **Recommend
reconciling SEASONS.md.**

---

## PART 2 — THE FLOW (to design)

_Empty. This is where we design what a run actually feels like now there's a real set of
mechanics — how the approved mechanics slot into Heat 1 / Heat 2 / teach-back, per mode, without
becoming a confusing pile. This is Layer 2 of MECHANICS.md, finally with enough inputs (§1–6) to
design properly._
