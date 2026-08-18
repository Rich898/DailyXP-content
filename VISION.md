# XP Daily — Vision

_The north star. Everything else in this repo serves this._

## The problem

Parents are largely blind to how their child is actually doing at school, day to day. Formal reports
come once or twice a year; grades lag and are coarse; "how was school?" gets "fine." The gap between a
kid's **real, day-to-day understanding** and **what their parent knows** is wide — and it's exactly
where problems hide until they're big.

And most signals that do exist measure the wrong thing: surface recall. A kid can look fine — recite
the fact, pass the low-stakes check — and still not understand it, then fall apart under exam
pressure. That's the **fluency illusion**, and closing the gap it creates is what started XP Daily.

## What we're building

A daily learning **game** that does three things at once — and has to do all three, or it fails:

1. **It's genuinely fun for kids to play.** Gameplay mechanics — not a quiz that feels like homework —
   are what earn daily engagement and drive adoption. **Fun is the distribution strategy, not
   decoration.** Every mechanic is a real game held to a shipping standard.
2. **It helps them actually learn.** Spaced repetition on their real class topics, re-teaching in the
   moment, and a teach-back that forces genuine explanation rather than recall. It targets the fluency
   illusion directly — measuring understanding, not memory.
3. **It gives parents never-before-had visibility.** An honest, specific picture of how their kid is
   doing — day to day and week to week: what's landing, what's shaky, and what they're *confidently
   wrong* about (the sneaky one). Not a grade. A true picture.

## Why it can be honest (the IP)

Under the game sits a deterministic per-topic ledger tracking two independent things: **confidence**
(how sure they are, when to re-test — drives scheduling) and **depth** (how well they understand —
drives what we tell parents). Deterministic code owns all scheduling and state; the LLM only handles
language. That separation is what lets us tell a parent something *true* — "he's solid on X, only
recites Y, and is confidently wrong about Z" — instead of a number. See `UNDERSTANDING.md`,
`LEDGER-RULES.md`.

## The strategy, in one line

**Bring game mechanics to learning so kids play every day → the daily play generates real evidence of
understanding → that evidence becomes the visibility parents have never had.**

## What this is NOT

Not a plain multiple-choice quiz. Not a grade-tracker. Not a homework app. The mechanics are real
games (see `modes/MECHANICS.md`); the reporting is a true picture of understanding, not a score.
