# Swipe Sort — mode prototype

**Status: PROTOTYPE — awaiting fun approval. Not wired into anything live.**
Isolated playable preview only (`preview.html`, fully self-contained). Nothing here is
imported by the pipeline, the planner, or any deployed shell.

## What it is
A speed-round mechanic: a short statement card appears, the player flicks it left or right
into one of two labelled buckets (True/False, Metal/Non-metal, Simile/Metaphor,
Primary/Secondary…). Correct = XP pop and the next card slides up; wrong or too slow = a
one-line re-teach strip, then keep moving.

## v8 changes (18 Aug) — "lands in the bucket" fix
Playtest feedback (Rich's wife nailed it): it didn't feel like the card went INTO the
bucket. Root causes: the card faded out mid-air (vanished NEAR the bucket, not into it) and
stayed too big to fit, covering the bucket. Reworked the landing (drag itself untouched):
- **Card shrinks to fit INSIDE the bucket** (scale .26, was .42) and **stays fully visible**
  the whole way — no mid-air fade.
- **Bucket opens to receive** (a "catching" state: lifts, brightens, inner-shadow mouth) as
  the card arrives, then **catches and swallows** it (a squash "catch" animation) while the
  bucket rises IN FRONT of the card (z-index) so the card is visibly taken in, not just gone.
- Confetti + XP + streak now fire on the swallow, anchored at the bucket. Confetti still
  correct-only. Wrong answers swallow into the chosen bucket too, then red-flash/shake/re-teach.
- Verified: card now nests inside the bucket at arrival.

## v7 changes (18 Aug) — card craft
Direction chosen: **card craft (type, finish, layout)**. Only the content card changed;
playfield, streak, drag all untouched.
- **Card-stock finish**: warm ivory with a top-lit sheen, a faint woven texture, a subtle
  inner bevel (thickness), plus the existing hard drop-shadow. Reads as a physical object.
- **Inset keyline frame** (double rule) — the hallmark of a well-made card.
- **Considered layout**: a letterspaced subject eyebrow up top with a short divider rule,
  the statement set as the hero, and a collectible-style card index (01–16) in the corner.
- **Type hierarchy**: mono for meta (eyebrow / index), Archivo Black for the hero statement.
- Subject colour now lives in the eyebrow (understated on purpose — this pass was card craft,
  not the subject-identity/icon system, which stays a separate future option).
- Verified across an equation card and a word card; eyebrow colour tracks subject.

## v6 changes (18 Aug) — arcade visual delivery + ring removed
Direction chosen by Rich: **arcade energy — bold, punchy, motion-heavy**. Drag/commit logic
left byte-for-byte identical (it was signed off); everything visual rebuilt around it.
- **Dark energised playfield** in brand navy (not neon-on-black cliche), keeping the
  bolt/blue/red palette. Subtle animated grid + a central glow that responds to play.
- **Signature: streak charge-up.** Chaining correct sorts fills a heat meter (blue→orange),
  brightens the playfield glow, lights the flame counter, and fires milestone callouts
  (×3 / On Fire / Blazing / Unstoppable / Flawless) with a centre confetti burst. This is
  spectacle only — it does NOT touch XP or the mastery ledger. XP per correct stays flat at 10.
  (A *visible* combo multiplier would be a separate, deliberate decision, not snuck in here.)
- Chunkier arcade buckets with glow, a dramatic glowing timer, punchy round-stage interstitial,
  glowing +XP, subject-coloured accent bar on each card, best-streak stat on the end screen.
- **Diagnostic finger-ring removed** now that the drag is signed off.

Open question this raises: if streak should ever carry a real reward, that's an XP/ledger
decision (and re-opens the hidden-multiplier caution from the 17–18 Aug purge). Deferred.

## v5 changes (18 Aug) — responsiveness pass 2 + diagnostic
Still chasing drag lag. Two things this build:
- **`translate3d` on the card (and the fly animation)** instead of 2D `translate`. This
  forces the browser to composite the card on the GPU every frame. With a plain 2D
  translate, an unpromoted layer repaints the whole card (text/border/shadow) each frame —
  the most likely cause of "it trails my finger the entire drag." translate3d is the
  reliable force-GPU trick; `will-change` alone was evidently not being honoured here.
- **Finger-tracking ring (diagnostic, temporary).** A ring marks the exact touch point,
  moved with the same translate3d path. Purpose: isolate code-lag from environment-lag. If
  the RING itself trails the finger, the latency is the in-app preview viewer (iframe/webview)
  and the deployed shell in a real browser will be smooth. If the ring is glued but the card
  trails, the card still needs work. Remove once the drag is signed off.

If v5 still feels laggy INSIDE the file viewer but the ring is glued to the finger: the next
step is to open the file in real mobile Safari/Chrome (outside the in-app viewer) as the
definitive test, and/or deploy to a throwaway Netlify site for a true-browser check.

## v4 changes (18 Aug) — dragging responsiveness pass
Target: kill the "card lags behind my finger" feel. (Visual polish deliberately deferred to
a later pass per Rich.)
- **`touch-action:none` down the whole play stack** (body → app → stage → stack → card),
  not just the card. On touch devices this removes the browser's scroll-intent delay that
  made the first part of every drag feel laggy.
- **Full 1:1 finger tracking in both axes** (was 55% vertical). The card now sits directly
  under the thumb on diagonal moves instead of trailing it.
- **Coalesced pointer events** so we paint from the freshest sample on high-refresh screens.
- **Dropped the blurred drop-shadow while dragging** (kept the hard offset shadow) so the
  moving layer stays cheap to composite — smoother on lower-end phones.
- Tighter anchor (scale 1.02) and gentler tilt so the grab point barely shifts.

## v3 changes (18 Aug)
- **Card shrunk to a compact tile** (264×188) and **buckets enlarged into deep
  container-style targets** — fixes the "huge card into a tiny pill" jank. The landing tile
  now nests *inside* the bucket (lands at ~0.42 scale) instead of shrinking to a dot.

## v2 changes (18 Aug, after first play)
- **Cards now fly INTO the chosen bucket** (shrink into the pill), not off-screen — the
  swipe/sort connection is now literal. Answers Rich's "feels like I have to swipe past the
  frame" note directly.
- **Commit is far more eager**: shorter travel (~26% of card width, 88px cap) and a lower
  flick-velocity bar, so a decisive nudge sends it. Card also lifts (scale + shadow) the
  instant you touch it, and tracks the finger more fully.
- **Buckets pulled inward** from the frame edge.
- **Landing FX**: correct = confetti burst from the bucket + pill pop + XP float; wrong (or
  timeout) = screen shake + red edge-flash + pill shake + re-teach strip. Valence stays
  strict — confetti only ever fires on correct.

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
