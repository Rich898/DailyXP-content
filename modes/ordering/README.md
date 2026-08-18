# Ordering — mode prototype

**Status: PROTOTYPE — awaiting fun/quality approval. Not wired into anything live.**
Isolated playable preview only (`preview.html`, self-contained).

## What it is
Drag scrambled tiles into the correct sequence (timelines, method steps, size/magnitude,
plot order). Tests sequencing knowledge, not recall.

## Deliberate design decisions (this is the one that was reverted before — judge the FEEL)
- **Real live-reflow drag, Pointer Events only** (the swipe-sort physics reused). Press a tile
  and it lifts (scale + shadow) and tracks your finger 1:1 via `translate3d`; the other tiles
  **slide out of the way in real time** as you cross slots, and the rank badges (1–4)
  renumber live. **No tap-to-order, no HTML5 drag** — the exact thing that killed the old one.
- `touch-action:none` down the stack (no scroll-intent lag on phones).
- **Teach-back beat on a miss:** wrong → tiles flash red/green by position, then physically
  **slide into the correct order** while the re-teach shows — the correction is a motion, not
  just text.

## Fair judging
Perfect order = win. On a miss it shows **"X of N in place"**, the full correct sequence, and
the `why`. (Open question: whether to award partial credit or keep it all-or-nothing.)

## Ledger note (strong evidence, like numeric)
Guessing the full order is 1/N! (1/24 for four tiles), so a correct arrangement is **strong**
mastery evidence — weights *more* than a 4-option MC, well above a 50/50 swipe.

## Open decisions (resolve at integration)
- Partial credit vs all-or-nothing; exact evidence weight.
- Tile count (4 is the sweet spot on a phone; 5 max).
- Which topics suit ordering (chronology, method/process, magnitude, structure) — content call.
- Slotting: steady round (arranging takes time — wrong for the timed speed round).

## Files
- `preview.html` — the playable prototype (open on a phone; the feel is the whole test).
