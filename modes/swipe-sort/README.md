# Swipe Sort — mode prototype

**Status: PROTOTYPE — awaiting fun approval. Not wired into anything live.**
Isolated playable preview only (`preview.html`, fully self-contained). Nothing here is
imported by the pipeline, the planner, or any deployed shell.

## What it is
A speed-round mechanic: a short statement card appears, the player flicks it left or right
into one of two labelled buckets (True/False, Metal/Non-metal, Simile/Metaphor,
Primary/Secondary…). Correct = XP pop and the next card slides up; wrong or too slow = a
one-line re-teach strip, then keep moving.

## Deliberate design decisions (judge these in the preview)
- **Real physics, Pointer Events only.** Card tracks the finger 1:1, tilts with the drag,
  springs back if released early, commits on distance OR flick velocity. No HTML5 drag.
- **Bucket colours are neutral-valenced** (reef blue / bolt amber). Red and green are
  reserved exclusively for wrong/right feedback so colour never leaks the answer.
- **Buckets are stable within a round and change only at an announced interstitial**
  ("Round 2 · Metal vs Non-metal"). Labels never switch mid-flow.
- **Stamp on the card** inks in as you drag, mirroring the bucket you're heading to —
  you always know what you're about to commit before you let go.
- **7s per-card timer** (bar turns flare-red in the last 2s). Timeout counts as a miss
  with a re-teach line.
- **Tap fallback**: tapping a bucket pill answers too (accessibility + desktop testing).
- **Statements are short, affirmative, single-fact.** No negation framing anywhere.
- Misses are re-taught twice: inline strip in the moment, and a revisit list at the end.
- Haptics via `navigator.vibrate` where supported; `prefers-reduced-motion` respected.

## Open questions — must be answered before integration
1. **Ledger weighting.** A swipe is a 50% coin-flip guess. A single swipe must count for
   less mastery evidence than a 4-option MC (25% guess rate). Options: weight per-swipe
   evidence lower, or require N-of-M within a topic before it moves the ledger. Planner /
   ledger decision, not a shell decision.
2. **Composer requirements.** The LLM must generate: short affirmative single-fact
   statements, a valid bucket pair per topic, and a roughly balanced L/R split per round
   (an all-one-side round teaches players to spam one direction). Needs the same
   deterministic gate treatment as answer_length.py had.
3. **Which slots.** Proposed: swipe-sort cards live inside the 7-slot speed round as a
   grouped run (e.g. 3–4 cards on one topic), never scattered one-offs, so bucket labels
   stay stable. Steady and teach-back untouched.
4. **Timing tune.** 7s is a placeholder. Real value comes from watching play.

## Files
- `preview.html` — the playable prototype (open on a phone).
- Tests come at integration time, per process; the gate for this stage is fun.
