# SCRUB-WIDGET-BRIEF.md

**Mechanic:** Scrub It — a new delivery mode for the existing multiple-choice question type
**Status:** LIVE IN THE SHELL TEMPLATE 31 Aug 2026. Pipeline integration (planner → composer → validator → state-writer) had shipped 27 Aug and the published sets carried `mode:"scrub"` for all seats — but the widget + wiring had only ever been merged into `integration/shell-staging.html`, never into `shell/template_v3.html`, so every deployed shell fell back to plain tap MC (caught live-fire by Rich on t1, T6.1). The merge is now in the template, locked by `shell/test_scrub.js` (stub-DOM contract) and `shell/browser_proof_scrub.js` (real-Chromium play-through), both reading the TEMPLATE. ⚠ A template fix reaches a kid only when their Netlify site is re-deployed — `python3 tools/stamp_shell.py` builds the three drag-deploy zips.
**Process law:** isolated widget → approval → pipeline integration (widget → shell → composer → planner → validator → state-writer). One mechanic at a time. Verify against a real browser run — never a mental audit.

---

## What this is

The existing 4-option MC question type, dealt through a new delivery mode: rub out the wrong answers with your finger; the last one standing auto-commits and turns green. The ledger never learns the delivery mode. Evidence value, ceiling, and state-writer treatment are unchanged from tap MC: recognition evidence, 25% guess floor, capped at "knows it", depth stays teach-back's job.

**Circle skin retired (25 Aug 2026):** the tap-with-ink-circle variant was built, playtested, and cut before pipeline. Scrub It is the sole new delivery mode from this exploration.

---

## Block identity (shell block-object shape)

- **label:** Scrub It
- **sub:** Rub out the wrong answers with your finger
- **icon:** ⌫  · **hue:** #B18CFF *(ratified 25 Aug 2026; violet avoids clashing with the five existing block hues)*
- **cta:** Start scrubbing →

The intro/doorway card is built into the widget in the shell's transition-card format (eyebrow → hue icon tile → name → sub → count pill → CTA), so the block identity ships ready for the planner.

---

## Gesture + laws (all ratified 25 Aug 2026)

- **Deliberate-stroke law:** a stroke only ever erases the tile it *started* on — sweeping across other tiles does nothing to them, not even smudges. One-go multi-tile sweeping was built, played, and reversed the same day: it let a stroke transit-kill the right answer, and protecting the answer instead was rejected as unsound (a tile that refuses to crumble under a sweep reveals itself as the answer, letting probing collapse the 25% guess floor). Per-tile strokes make every erase a deliberate judgment and keep the elimination telemetry honest.
- A fully erased tile is committed. **No undo.** Partial scrubs never heal; abandoning a half-scrubbed tile is legal (and is signal).
- Survivor auto-commits as the answer and turns green — no confirm tap, and **no ink circle on the win**.
- If the **correct** tile is fully erased → immediate miss. Input locks, the answer un-crumbles in green, standard miss strip fires.

---

## Break-apart (RATIFIED 25 Aug 2026: Shards)

Three styles were built and play-compared (crumble / shards / dust); Rich picked **Shards**: three big slabs crack off the tile and drop with a slow rotation, plus a small crumb burst. The losing styles were removed from the widget so the approved artifact carries exactly the approved behaviour.

Ratified feel constants (the ER_TUNE defaults, locked by playtest): brush 22 · erase threshold 62% · min scrub reversals 2 · crumb density 2.

Fragments render as a solid paper base carrying whatever ink remained, so the break reads chunky rather than ghostly. The emptied slot becomes a faint dashed ghost outline. Reduced-motion preference suppresses all debris.

---

## Feedback ownership (ratified 25 Aug 2026)

Verdict-level reward feedback (burst, XP payout, double-XP flash) is **shell-owned** and fires on `onDone` at integration, identical to every mode. **Shake remains miss-only** per shell convention; Scrub It adds no shake of its own — the shards and the haptic buzz carry break impact. The widget owns mechanic-level juice only; the shell owns the universal reward layer. Build session: wire the win payout deliberately, not by accident.

---

## Telemetry (per question)

`mode:'scrub'` · elimination order with per-tile scrub start → commit (hesitation) · longest-lived distractor · final-two pairing · standing distractors on a miss. Confidence-axis data only; nothing writes to depth.

---

## Composer / validator rules (locked, built at pipeline stage)

- Exactly one unambiguous correct answer; distractors mutually exclusive with it.
- Three distractors, same category as the answer; prefer common misconceptions over random wrong facts.
- Similar length and format across all four tiles — no length or formatting giveaway.
- No "all of the above" / "none of the above" / compound options.
- No negative stems ("Which is NOT…") — they invert the scrub metaphor.

---

## Acceptance

- `scrub-widget.html` — self-contained, offline-playable: intro card → 4-question block → replay door. Full real-browser play-through with zero JS errors (done 25 Aug 2026), including deliberate-stroke law, miss rule, all three break styles, and replay reset.
- Widget stage CLOSED. Hand `scrub-widget.html` + this brief to the pipeline-integration build session; nothing reaches the boys until proven on t1.

## Out of scope

Missing-word (cloze — next in the queue), block/loadout placement, chapter debut timing, live template merge.
