# Numeric / Calculator — mode prototype

**Status: PROTOTYPE — awaiting fun/quality approval. Not wired into anything live.**
Isolated playable preview only (`preview.html`, self-contained).

## What it is
A typed-answer maths mechanic: no options to guess from. The player types the answer on a
keypad. Which keypad depends on what the question is testing:
- **Method questions** (area, %, solving, speed) → a **working calculator** (digits, + − × ÷,
  parentheses, =). The skill is the *setup*; the calculator does the arithmetic (matches how
  secondary maths actually works).
- **Mental-maths questions** (times tables, mental arithmetic) → a **plain number pad** (no
  operators, no =). The arithmetic *is* the skill, so the calculator is off — otherwise the
  mastery signal is worthless.

## The honest-signal rules (why this design, per VISION.md)
- **Scoped:** calculator on/off is set per question (`calc:true/false`). A calculator on a
  mental-arithmetic question would hand the kid the answer and log "mastered" falsely — the
  exact thing the product exists to prevent.
- **Tracked:** every answer logs whether a calculator was available/used. A calc-assisted
  correct answer is recorded as "solved with a calculator," never as mental-arithmetic
  mastery. (Prototype surfaces this on the reveal line and the end screen; the real integration
  writes it to the ledger.)

## Fair judging (what killed the old typed inputs was unfair judging)
Answers compared numerically with tolerance (±0.01). Equivalent forms all pass — `0.75` =
`.75` = `3/4` (the calculator evaluates it), `52.0` = `52`. Units (`$`, `cm²`, `km/h`) are
display-only, never typed. Safe expression evaluator (shunting-yard, no `eval`).

## Ledger note (opposite dial from swipe-sort)
A typed answer has no options to guess from, so numeric is **stronger** mastery evidence than
4-option MC (and a calc-off mental answer is stronger still). Likely weights *more*, where a
swipe (50/50) weights less.

## Open decisions (resolve at integration)
- Exact evidence weight (numeric vs MC vs swipe); how calc-availability annotates the ledger.
- Which topics are tagged mental (no-calc) vs method (calc) — a content/curriculum call.
- Tolerance policy for messier answers (recurring decimals, significant figures).
- Speed-round timing for typed answers (typing is slower than a tap).

## Files
- `preview.html` — the playable prototype (open on a phone).
