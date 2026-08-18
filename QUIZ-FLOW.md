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

_These are the live quiz shapes as they run today. Part 3 reimagines them as **frames** filled by the
loadout — the target model._

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

## PART 2 — THE FLOW

_Designed with Rich, 19 Aug 2026. The brief in his words: **"fun, and you don't quite know what
today holds vs it being the same format every day."** Mock: `flow/run-mock.html`._

### The idea in one line
**Same three modes — but the mechanics that fill them are dealt from a rotating daily loadout.**
Every day feels different at the door; the learning machine underneath is identical. Novelty comes
from *rotation of a fixed bank*, not constant invention (the seasons doctrine — sustainable, and it
avoids the confusing pile we reverted).

### The block model
- A run is a sequence of **blocks**. Each block = **one mechanic, ~3 questions** (3 is the starting
  bet — a real dial, tuned on the boys).
- Blocks sit inside the mode's fixed skeleton: **Heat 1 (speed) blocks → Heat 2 (steady) blocks →
  teach-back finale.**
- **The core rule: unpredictable day-to-day, coherent within a run.** The gesture never changes
  *inside* a block — a block is one clear thing. The surprise is at the **doorway between blocks,
  never mid-question.** (This is exactly what the reverted "one new mechanic every question" pile
  got wrong.)
- Meeting a topic three ways across a run (swipe it, type it, order it) is deliberate
  **interleaving** — better for retention and transfer than drilling one gesture.

### The daily loadout
- The loadout **deals which blocks, in which order**, into today's mode — like a daily-challenge /
  roguelike seed.
- Mon/Tue/Thu = **Standard** mode, a different loadout each day. Wed = **Reversed Blitz**, Fri =
  **Battleground** (the two landmark events).
- Speed-eligible mechanics (fast gestures: **Swipe, Quick Recall**) fill Heat 1; steady-eligible
  (**Numeric, Ordering, Short-text, Confidence-MC**) fill Heat 2. Which mechanic lands where, and
  the rotation algorithm, is the **mix policy** (MECHANICS.md Layer 2) — still to detail.

### The curated frame (the polish)
- **"Today's run" reveal** — the run laid out as a *route* (its blocks, colours, counts, length).
  The anticipation beat: *"ooh, what've I got today."* A different route tomorrow.
- **Transition cards** ("loading cards") **between blocks** — Heat label, *block N of N*, the
  mechanic (icon + **colour** + name), a one-line what's-next, the count, and a **progress rail**
  showing where they are in the whole run. This doorway makes a gesture-switch feel *intentional*
  and gives the run **chapters**. Signal the change; never switch cold mid-flow.

### Length driven by signal (not padding)
- The everyday run **extends modestly — mid-teens, not 12** — tolerable *only because* it's varied.
- Extra slots weight toward **signal**: a confidence-tagged steady question or a teach-back tells the
  ledger far more than another plain MC (it separates *knows it* from *got lucky*). **Quantity of
  answers ≠ quantity of signal.**
- **Length flexes by day** (another "what's today" lever): some days a quick 10, some a meaty 16;
  Wed is a fast 13, Fri a focused 7.
- **The real ceiling is the streak.** The run must be finished *every* day — the whole product (the
  day-to-day parent picture, the spaced repetition) depends on it. A 12 they always finish beats a
  20 they bail on twice a week. **The number is set by watching the boys' completion, not guessed** —
  the day Harrison groans or skips is the number.

### The mechanic colour system (a visual language)
Each mechanic has a **signature colour, used everywhere it appears** — the reveal, the transition
card, the mechanic's own screen accents, and the parent/kid reports. The colour becomes *learnable*
("violet = type a word"), and the whole product coheres into one system.

| Mechanic | Signature colour | Hex |
|---|---|---|
| Quick Recall (Plain MC) | green | `#16E08C` |
| Swipe Sort | blue | `#39A7DE` |
| Numeric | teal | `#14C7C7` |
| Ordering | gold | `#FFB800` |
| Short-text | violet | `#B26BE6` |
| Teach-back | coral | `#FF6A45` |

_(Colours are tunable.)_ **Next step to complete the system:** thread each colour back into its
mechanic's own preview — right now the colours only debut in the flow mock; the mechanic screens
don't yet carry them.

### The honest dependency
This is only **real as the mechanics go live.** Today the deck has ~one card (MC), so every Standard
day looks the same. **Each integration adds a card to the daily deck** — so this vision *is* the
argument for integration, one at a time.

### Open (to detail next)
- Exact block sizes (3 is the starting bet); the rotation algorithm; which mechanic → which Heat
  (the mix policy, MECHANICS.md Layer 2); per-day loadout design; final colour assignments.

---

## PART 3 — FRAMES × LOADOUT (events, reimagined)

_19 Aug 2026. Rich's question: now the loadout makes every day varied, does that change Wednesday
and Friday? Yes — it frees them to become what events are actually for._

### The insight
The events were doing **two jobs at once**, now worth pulling apart:
1. **Variety** — "today ≠ yesterday."
2. **Occasion** — "today is a *landmark*: purpose, stakes, emotion."

The **loadout now owns variety** (every day differs), so events no longer need to be "the different
day." What's left — and what events are *for* — is **occasion**. Variety is spice; occasion is a
landmark. The loadout can't manufacture occasion; events shouldn't waste themselves on variety.

The tell that the old events were mis-defined — *"both are just different ways of doing MC"* — is
that they were named after a **legacy mechanic**, not their **essence**:
- **Battleground's essence** = *your own weak topics, no-lose, claim the ground, end-of-week
  redemption.* MC was incidental — you could claim a topic by swiping / typing / ordering it.
- **Reversed Blitz** = **Blitz** (a tempo/energy frame) **+ Reversed** (one MC mechanic). The energy
  is the event; Reversed is just a card.

### The model: two independent layers
- **Frame** = what *kind* of day it is — its purpose, stakes, emotion. Neutral (a normal daily run)
  or an **event frame** (a landmark).
- **Loadout** = which *mechanics* fill it, from the rotating deck.
- **Independent.** A frame says "redemption day"; the loadout says "today's gestures are swipe +
  type." Any frame can be filled by any mechanics.

**Event frames are special frames; the loadout fills them — with the FULL deck now, not just MC.**
Events don't *compete* with the loadout; the loadout *powers* them.

### Two rotation clocks (the seasons doctrine, made concrete)
- **Mechanics rotate daily** — the deck (Part 2).
- **Event frames rotate by chapter** — a *bank of frames* (energy, redemption, boss, mystery…).
- Wednesday and Friday become **frame slots** that different frames rotate through over a term — so
  even the events stay fresh, instead of "reversed-blitz + battleground forever." (This realises
  SEASONS' "the event loadout is a chapter-level variable.")

### Battleground, reimagined — concrete
Frame unchanged: **4 claimable zones on the kid's flagged weak topics, no-lose, territory bar,
"% claimed this week."** The loadout now fills each zone with the **best mechanic for that topic**,
from the full deck — and each zone wears that mechanic's **signature colour**, so the board reads at
a glance:

| The weak topic is… | Claim it by… | Zone colour |
|---|---|---|
| a vocab / key term | **typing it** (Short-text) | violet |
| a sequence / timeline / method order | **ordering it** (Ordering) | gold |
| a maths method | **solving it** (Numeric) | teal |
| a true/false-able fact | **swiping it** (Swipe) | blue |
| a plain fact / concept | picking it (MC / spot-the-lie) | green |

So "claim your ground" becomes a **varied, multi-gesture redemption run** — far richer than four MC.
The **teach-back finishing move stays** (explain the topic you just reclaimed).

### Blitz, reimagined — concrete
Frame = **tempo/energy**: fast, high-score, midweek. The loadout fills it with **fast** mechanics
(rapid swipes, quick MC, mental Numeric) — Blitz becomes "a *fast day*," not "an MC day."
**Reversed** becomes a **card in the deck** (a mechanic), featured on Blitz day but free to appear
occasionally elsewhere — decoupled from Wednesday.

### Bonus: this fixes the naming trap
Wed/Fri are **frame slots**; the frame currently in each is "Blitz" and "Battleground" — and those
can rotate. No more "Friday's directive is literally called `boss` but produces Battleground."

### The risk to hold onto
Events derive power from **contrast**. Now the baseline is genuinely exciting, an event has to be a
real **step-change** — higher stakes / distinct frame / bigger reward — or it blends into "another
varied day." Protections: keep normal days a comfortable *daily run* (routine cadence) so events
stand out; make each event a clear jump in **stakes/purpose**, not just different mechanics.

### Open (event model)
- The **bank of event frames** (energy, redemption, boss, mystery/mixed…).
- **Chapter rotation** schedule for frames.
- **2 events/week** (midweek energy + Friday consolidation — a natural arc) vs fewer, to protect the
  baseline. Lean: keep both.
- How the loadout picks the **best mechanic per Battleground zone**.

