# XP Daily — Mechanics Toolbox

The catalogue of quiz mechanics we can draw from. The vision: grow this over time, and
launch with a decent variety. Each mechanic earns its place the same way — prototyped in an
isolated playable preview, approved for **fun AND product quality**, then given a spec entry
here before it's ever wired into live quizzes.

## Two layers of "usage rules" (why this file looks the way it does)

- **Layer 1 — per-mechanic spec (defined at approval, while fresh).** What each mechanic is
  for, what content it needs, how it scores, where it slots. Intrinsic to the mechanic;
  mostly independent of the others. Captured here, one entry per mechanic.
- **Layer 2 — the mechanic MIX policy (deferred until the launch set exists).** How many
  mechanics per quiz, rotation, pacing, slot budget, avoiding clashes. Can't be designed from
  a sample of one — it's assembled once, from the Layer-1 specs, when we choose the launch
  line-up. See the placeholder at the bottom. **Do not pre-write this.**

## Spec format (every mechanic fills these in)

1. **What it is** — one line.
2. **Content fit** — when to reach for it.
3. **Content constraints** — rules the content must obey.
4. **Answer mode** — swipe / tap / type / speak.
5. **Ledger rule** — how much mastery evidence one answer is worth (protects the IP).
6. **Slotting** — which round/slot, and how cards group.
7. **Composer needs** — what the LLM must generate + the deterministic gate that enforces it.
8. **Scale / generalisation** — does it work across subjects/curricula/many users.
9. **When NOT to use** — anti-patterns.
10. **Status / preview / open decisions.**

## Registry

| Mechanic    | Status              | One-liner                                                        |
|-------------|---------------------|------------------------------------------------------------------|
| Plain MC    | LIVE                | One question, four short options, one answer, a re-teach.        |
| Teach-back  | LIVE                | "Explain it in your own words," graded on verdict + depth.       |
| Swipe Sort  | LIVE (20 Aug 2026)  | Flick a statement into one of two labelled buckets.              |
| Numeric     | LIVE (20 Aug 2026)  | Type the maths answer — calculator on method Qs, number pad on mental; decimals + a/b fractions since 31 Aug. |
| Ordering    | LIVE (20 Aug 2026)  | Drag scrambled tiles into the correct sequence (live reflow). |
| Short-text  | LIVE (20 Aug 2026)  | Type a word or two; a fuzzy matcher forgives typos/variants. |
| Scrub It    | LIVE (31 Aug 2026)  | MC delivery mode: rub out the wrong answers; last one standing wins. See `SCRUB-WIDGET-BRIEF.md`. |

---

## Swipe Sort — spec

**Status:** APPROVED for fun/quality (v9). NOT yet integrated into live quizzes.
**Preview / full build:** `modes/swipe-sort/` (README has the build history and feel notes).

1. **What it is.** A timed speed-round mechanic: a short statement card appears, the player
   flicks it left or right into one of two labelled buckets. Card shrinks toward the bucket
   as it's slid, the bucket opens and swallows it, correct = confetti + XP + streak, wrong =
   a one-line re-teach.

2. **Content fit.** Any topic with a **clean, uncontestable two-way split**:
   True/False, Metal/Non-metal, Prime/Composite, Simile/Metaphor, Primary/Secondary source,
   Acid/Base, Noun/Verb, Fact/Opinion. The two categories must be exhaustive and unambiguous
   for the item.

3. **Content constraints.** Statements are **short, affirmative, single-fact, fast to READ**
   (it's a timed round, not a puzzle). **No negation framing** ("which is NOT…"). Membership
   must be clear-cut — no fuzzy-boundary items. Within a run, sides should be **roughly
   balanced** (an all-one-side run teaches players to spam one direction).

4. **Answer mode.** Swipe (Pointer-Events drag, real physics) with a tap-a-bucket fallback.

5. **Ledger rule.** A swipe is a ~50% guess vs a 4-option MC's ~25% — so **one correct swipe
   is weaker mastery evidence than one correct MC.** Rule: discount per-swipe evidence and/or
   require **N-of-M correct on a topic** before it moves the ledger meaningfully. Deterministic
   scoring owns this; the LLM never touches it. (Exact weighting/threshold = decide at
   integration, may want data.)

6. **Slotting.** Lives in the **timed speed round**. Deploy as a **grouped run of ~3–4 cards
   on one categorical scheme** so the bucket labels stay stable through the run — never
   scatter single swipe cards with labels changing card-to-card. Steady + teach-back untouched.

7. **Composer needs.** Generate: affirmative single-fact statements, a valid 2-way bucket pair
   per topic, and a balanced L/R split per run. Needs a **deterministic gate** (same spirit as
   `tools/answer_length.py`) to reject negation, over-long statements, ambiguous membership,
   and lopsided runs before anything ships.

8. **Scale / generalisation.** Strong. Works for any subject that has a clean binary; the
   split and scoring are deterministic, the LLM only writes language. Performant on mobile
   (GPU-composited drag). Maintainable (one shell mechanic, content-driven).

9. **When NOT to use.** More than two categories (not supported — it's strictly binary);
   ambiguous/fuzzy membership; anything that needs negation to be made binary; calculation
   items whose answer is a number (that's keypad territory, not a sort).

10. **Open decisions (resolve at integration).** Exact ledger weighting / N-of-M threshold;
    composer gate implementation; timing tune (7s per card is a placeholder); how a run of
    swipe cards counts against the 7 speed slots.

---

## Numeric / Calculator — spec

**Status:** LIVE since 20 Aug 2026 (Maths steady slots). Pads upgraded 31 Aug 2026: decimal point
and a/b fraction entry on BOTH pads (live-fire fix — a mental slot with answer 0.4 had been
unanswerable, and "as a fraction" questions had no way to write one). Locked by `shell/test_numeric.js`.
**Preview / full build:** `modes/numeric/` (README has the design rationale).

1. **What it is.** A typed-answer maths mechanic — no options to guess from. The player types
   the answer on a keypad; which keypad depends on what the question tests (see Content fit).

2. **Content fit.** Maths questions with a **single numeric answer**, in two sub-types:
   **method / applied** (area, %, solving, speed, rates) → a **working calculator**, because the
   skill is the *setup*; and **mental-arithmetic** (number facts, times tables, mental sums) →
   a **plain number pad**, because the arithmetic *is* the skill.

3. **Content constraints.** The answer is one number (with an optional *display-only* unit —
   `$`, `cm²`, `km/h` — never typed). Each question is tagged **calc** (method) or **no-calc**
   (mental). Tag it wrong and you either hand a kid the answer (calc on a fact) or make a
   method question needlessly painful.

4. **Answer mode.** Typed on a keypad: a computing calculator (`+ − × ÷`, parens, `=`, plus the
   `a/b` fraction key) for method Qs; a plain number pad (digits, `.`, `a/b`, `±`, no operators)
   for mental Qs. **Equivalence law (31 Aug 2026):** any equivalent form of the value earns
   credit — `0.4`, `2/5` and `4/10` are the same answer. The fraction key writes an answer, it
   never computes — it does NOT flip the calc-used flag (honest-signal law, item 5). An authored
   `frac` field carries the canonical fraction the reveal displays ("2/5 (= 0.4)"), validated
   for equivalence by `tools/validate.py`.

5. **Ledger rule (two parts).** (a) A typed answer has no options to guess from, so numeric is
   **stronger** mastery evidence than 4-option MC — a calc-off mental answer is stronger still.
   Likely weights *more* (opposite end of the dial from a 50/50 swipe). (b) **Honest-signal
   law:** calculator availability/use is **logged per answer**; a calc-assisted correct answer
   is recorded as *"solved with a calculator,"* NEVER as mental-arithmetic mastery. Different
   skills; the parent sees the true one. This is non-negotiable — it's the whole reason the
   calculator is scoped.

6. **Slotting.** Natural fit for the **steady round** (typing is a beat slower than a tap).
   Quick mental-arithmetic numeric *could* work in the speed round with timing tuned for typing;
   method/calculator questions need thinking time → steady. (Exact call = mix policy.)

7. **Composer needs.** Generate a maths question with one numeric answer, the correct value, any
   display unit, the **calc / no-calc tag**, and a re-teach `why`. Deterministic gate: answer is
   numeric; the tag matches the question type (arithmetic-is-the-skill → no-calc); units are
   display-only; answer is unambiguous under the tolerance policy.

8. **Scale / generalisation.** Maths-specific by nature (numeric answers). Strong within maths;
   deterministic judging via a safe expression evaluator (shunting-yard, no `eval`); performant.

9. **When NOT to use.** Non-maths / non-numeric answers; answers that aren't a single value
   (ranges, multi-part); anything where a written *explanation* is the point (that's teach-back);
   answers sensitive to significant-figures/rounding beyond the tolerance policy.

10. **Open decisions (resolve at integration).** Exact evidence weight (numeric vs MC vs swipe)
    and how calc-availability annotates the ledger; which topics are tagged mental vs method
    (a curriculum call); tolerance policy for messier answers; speed-round timing for typing.



---

## Ordering — spec

**Status:** APPROVED for fun/quality (v1). NOT yet integrated into live quizzes.
**Preview / full build:** `modes/ordering/` (README has the drag-feel notes).

1. **What it is.** Drag scrambled tiles into the correct sequence — real live-reflow drag
   (tiles slide out of the way under your finger). Tests sequencing, not recall.

2. **Content fit.** Anything with a single correct linear order: **chronology** (timelines),
   **method / process** steps, **size / magnitude**, **structure** (e.g. plot stages), rankings.

3. **Content constraints.** A set of short items (**4 is the sweet spot; 5 max on a phone**)
   with **one unambiguous correct order — no ties**. The ordering dimension is stated in the
   instruction ("smallest → largest", "earliest → latest", "start → end").

4. **Answer mode.** Drag-to-reorder — **Pointer Events, live reflow** (the swipe-sort physics).
   **Not** tap-to-order, **not** HTML5 drag — that combination is what got the old one binned.

5. **Ledger rule.** Guessing the whole order is 1/N! (1/24 for four tiles), so a correct
   arrangement is **strong** mastery evidence — weights *more* than a 4-option MC, well above a
   50/50 swipe. (Open: partial credit vs all-or-nothing, and how partial maps to evidence.)

6. **Slotting.** **Steady round** — arranging takes time, so it's wrong for the timed speed round.

7. **Composer needs.** Generate the items **in correct order** + the ordering dimension /
   instruction + a re-teach `why`. Deterministic gate: exactly one unambiguous order (reject
   ties / multiple valid orders), items short enough for a tile, 3–5 items.

8. **Scale / generalisation.** Strong — works across subjects on any orderable dimension;
   deterministic judging (compare to the canonical order); performant (`translate3d`).

9. **When NOT to use.** Content with no single correct order (ties, multiple valid orders);
   more than ~5 items (unwieldy on a phone); relationships that aren't linear/orderable.

10. **Open decisions (resolve at integration).** Partial credit vs all-or-nothing + evidence
    weight; tile count; which topics are tagged ordering (a curriculum call); confirm steady-slot
    timing.

---

## Short-text — spec

**Status:** APPROVED for fun/quality (v1). NOT yet integrated into live quizzes.
**Preview / full build:** `modes/short-text/` (README has the matcher details).

1. **What it is.** Type a one-or-few-word answer — no options to guess from. For terms, vocab,
   key names, one-word definitions. The input is trivial; **the fuzzy matcher is the mechanic.**

2. **Content fit.** Questions with a short canonical answer (~1–3 words) and a clear intended
   term: key vocabulary, names, units, one-word concepts.

3. **Content constraints.** A **canonical answer + a list of accepted variants/synonyms**
   (`accept[]`) — including irregular plurals and symbol forms the matcher can't infer
   (mitochondria/mitochondrion, oxygen/O2, question mark/?). Answer short enough to type fast.

4. **Answer mode.** Free-text typed, judged by the **fuzzy matcher**: normalise (case, spacing,
   punctuation, leading article, accents) → plural-fold → length-scaled edit distance, with **no
   typo tolerance on words ≤3 chars**. Device autocorrect/autocapitalise/spellcheck **off** so
   the kid's real answer is judged. Non-exact accepts are shown ("counted 'oxigen' as 'oxygen'").

5. **Ledger rule.** No options to guess from → **strong** mastery evidence, above MC and well
   above a 50/50 swipe. **Spelling never affects correctness** (same law as the teach-back).

6. **Slotting.** **Steady round** (typing takes a beat). Short one-word answers *might* suit the
   speed round with timing tuned.

7. **Composer needs.** Generate the question, the canonical answer, a sensible **`accept[]`**
   (synonyms, symbol forms, irregular plurals), and a re-teach `why`. Deterministic gate: one
   clear intended term; `accept[]` well-formed; answer short.

8. **Scale / generalisation.** Strong across subjects; the matcher is deterministic and
   universal. The per-question risk is **accept-list quality** — the composer must supply the
   variants the matcher can't infer.

9. **When NOT to use.** Numeric answers (→ Numeric); long/open explanations (→ Teach-back);
   questions with many equally-valid answers; and **anything where exact spelling IS the skill**
   (a spelling test) — there "spelling never counts" would defeat the point.

10. **Open decisions (resolve at integration).** Typo-threshold tuning + the `accept[]`
    conventions the composer must follow; multi-answer support; evidence weight vs the others;
    confirm steady-slot timing.

---

## Layer 2 — Mechanic MIX & variety policy — TO DEFINE (placeholder, do not pre-write)

Fill this in **once the launch set of mechanics exists**, using the specs above as inputs.
Questions it will answer:
- How many distinct mechanics appear in one quiz, and how many of the 12 slots each may take.
- Rotation/variety across a session and across days (avoid the same mechanic every day; avoid
  two mechanics that feel too similar back-to-back).
- Which mechanics are speed-round-eligible vs steady-eligible.
- How difficulty/《stakes》 escalate across a quiz.
- Fallbacks when a topic doesn't suit the day's chosen mechanic.

Attempting to design this now, with one mechanic, would be guesswork — deferred by design.
