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
| Swipe Sort  | APPROVED (not live) | Flick a statement into one of two labelled buckets.              |
| Numeric     | APPROVED (not live) | Type the maths answer — calculator on method Qs, number pad on mental. |

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

**Status:** APPROVED for fun/quality (v1). NOT yet integrated into live quizzes.
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

4. **Answer mode.** Typed on a keypad: a computing calculator (`+ − × ÷`, parens, `=`) for
   method Qs; a plain number pad (digits, `.`, `±`, no operators) for mental Qs.

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



Fill this in **once the launch set of mechanics exists**, using the specs above as inputs.
Questions it will answer:
- How many distinct mechanics appear in one quiz, and how many of the 12 slots each may take.
- Rotation/variety across a session and across days (avoid the same mechanic every day; avoid
  two mechanics that feel too similar back-to-back).
- Which mechanics are speed-round-eligible vs steady-eligible.
- How difficulty/《stakes》 escalate across a quiz.
- Fallbacks when a topic doesn't suit the day's chosen mechanic.

Attempting to design this now, with one mechanic, would be guesswork — deferred by design.
