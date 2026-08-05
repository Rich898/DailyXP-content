# Shell v3.1 — build spec (scope: LARGE, game-only)

*Goal: kill format monotony and deepen engagement for both boys. Skeleton (speed → steady → teach) stays; variety lives inside the slots. Beta kit SPLIT OUT into its own later build — v3.1 is purely the game upgrade.*

## New question types (render + score + timing + tests each)
1. **Typed numeric (maths)** — number keypad, no options. Kills the reverse-engineer-from-choices loophole (both boys' flagged weakness). Matching: per-question `accept` list; normalise spacing/units so "30", "30 cm²", "30cm2" all pass; **moderate strictness default** — accept the bare number OR number+correct unit; wrong unit alone ≠ full credit. Instant feedback preserved. JSON: `"type":"numeric","answer":"30","accept":["30","30 cm2","30cm²"]`.
2. **Typed short-text (terms/dates)** — same engine, looser: case-insensitive, trims, small synonym/spelling-tolerance list. JSON: `"type":"text","answer":"War Guilt Clause","accept":["war guilt","guilt clause"]`.
3. **Ordering** — tap/drag to sequence (e.g. WWI → Versailles → Depression → Hitler). Roshan's headline skill AS a mechanic. Scored exact-sequence right/wrong. JSON: `"type":"order","sequence":["A","B","C","D"]` (store correct order; shell shuffles for display).
4. **Cloze** (fill-the-blank) — reuses typed engine. **Spot-the-error** — reuses MC rendering, pick the wrong word/step. Both steady-slot variants.
- Back-compat: existing `"options"/"answer"` questions default to `type:"mc"`. All types carry the universal skip.

## Event / game layer
5. **Hidden double-XP question** — one per run, secretly 2×, revealed on answer with a flourish. JSON flag `"x2":true` (shell doesn't betray it pre-answer).
6. **Friday Boss Round** — chained 3–4 steady questions on the kid's ledger gap, themed wrapper; misses-as-attacks framing; teach-back = finishing move. Distinct visual treatment so it reads as an event, not a normal run. Driven by JSON (a boss block), minimal new logic.
7. **Optional 2-question encore** — after the finish screen, "want bonus XP?" → 2 extra Qs. Skippable.

## Owed fixes (non-negotiable)
8. **Universal skip structural** — button on EVERY question regardless of flags; retire the `fresh:true`-on-everything workaround.
9. **doPost idempotency** — webhook dedupes on (student, date, ts) so retry-taps don't double-insert (belt-and-braces with the reader-side dedupe).

## Non-negotiables at ship
- Skeleton unchanged; timing invariant (active ≤ elapsed) preserved across ALL new types — each type extends the same clock discipline.
- All existing tests stay green + a new test per new type (render, correct/incorrect scoring, timing, payload shape).
- Payload/summaryText extended to carry the new answer kinds without breaking the ledger reader.
- Deploy = same two Netlify projects, URLs unchanged. Full test suite green before deploy.

## Explicitly deferred
Beta kit (kid `?kid=` codes, per-family results separation, OG preview cards, deletion script, ledger seeding) → own build near onboarding. Domain wiring → with beta kit. SMS pipe/scheduler → separate, and Roshan's US-phone SMS gap noted (kid-facing texts need a non-SMS fallback; gameplay unaffected).
