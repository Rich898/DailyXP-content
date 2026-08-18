# Short-text — mode prototype

**Status: PROTOTYPE — awaiting fun/quality approval. Not wired into anything live.**
Isolated playable preview only (`preview.html`, self-contained).

## What it is
Type a one-or-few-word answer — no options to guess from. For terms, vocab, key names,
one-word definitions. The input is trivial; **the fuzzy matcher is the mechanic.**

## The fuzzy matcher (the whole point — what killed the old typed inputs was unfair judging)
A deterministic, forgiving matcher. Same rule as the teach-back: **spelling never fails a kid
who knows it.** It accepts:
- **case / spacing / surrounding punctuation** ("Oxygen ", "oxygen.").
- **a leading article** ("the mitochondria" → mitochondria).
- **valid synonyms / variants** the composer supplies (`accept[]`): oxygen/O2, question mark/?,
  Neil Armstrong/Armstrong.
- **light plural↔singular** folding (regular cases; irregulars go in `accept[]`).
- **close typos** via edit distance, length-scaled (oxigen→oxygen, mitocondria→mitochondria).
- **Safety:** words ≤3 chars get NO typo tolerance (so "cot" ≠ "cat"). Genuinely wrong answers
  reject (nitrogen, aldrin, full stop).

When a non-exact form is accepted, the reveal says so — *"counted 'oxigen' as 'oxygen'"* — so
the kid sees the forgiveness and isn't left unsure. Unit-tested: 18/18 cases (typos accept,
wrong answers reject, tiny-word safety).

## Fair-input details
Device autocorrect / autocapitalise / spellcheck are **off**, so the kid's real answer is what's
judged (the matcher does the forgiving, not the keyboard) — and no red-squiggle pressure.

## Ledger note (strong evidence, like numeric/ordering)
No options to guess from → **stronger** mastery evidence than a 4-option MC, well above a
50/50 swipe. Recalling a term cold is a high bar.

## Open decisions (resolve at integration)
- Tuning the typo threshold + the accept-list conventions the composer must follow.
- Whether to accept multi-answer questions (currently single canonical + variants).
- Evidence weight vs MC / numeric / ordering.
- Slotting: steady round (typing takes a beat); short one-word answers *might* suit speed with
  timing tuned.

## Files
- `preview.html` — the playable prototype (open on a phone).
