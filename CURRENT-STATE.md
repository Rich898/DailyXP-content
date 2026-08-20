# XP Daily — Current State (authoritative)

_Last updated 18 Aug 2026. The source of truth for what the quiz actually is today. Verified against
the deployed shell (`shell/template_v3.html`), the generator (`scripts/run_daily.py` +
`tools/planner.py`), and real composed quizzes + plans in `DailyXP-private/`. Where any other doc
disagrees, this wins. For **why** the product exists, see `VISION.md`._

## What XP Daily is

A daily learning **game** that measures how well a student actually understands their real school
topics, and turns that into visibility a parent has never had before — day to day and week to week.
Game mechanics are the engagement layer that earns daily play; underneath sits a deterministic
per-topic **confidence + depth ledger** (the IP) that separates real understanding from surface
recall. Deterministic code owns all scheduling and state; the LLM only handles language. **It is not,
and never was, a plain multiple-choice quiz.** See `VISION.md`.

## Quiz shapes — a live weekday event rhythm

| Day | Directive | Shape | Total |
|---|---|---|---|
| Mon–Thu | standard | 12 speed + 6 steady + 1 teach-back | 19 |
| **Fri** | "boss" → **BATTLEGROUND** | **2 speed + 7 steady + 1 teach-back** | 10 |

Frozen students (e.g. a kid away at camp) → placeholder, no quiz.

## Live mechanics

- **Speed round (Heat 1)** — 4-option MC, and: **timed** per question (fuse + countdown, red under 6s;
  timeout = miss); a **combo** meter (`×N`, with a combo bonus at ≥2); a **skip** ("comes back
  around"; on a `fresh` topic, "I'll check when your class gets there").
- **Steady round (Heat 2)** — MC, no clock, plus the **confidence wager**: pick answer →
  **"How sure?"** → **Sure / Think so / Guessing** → **Lock it in**. Confidence is written to the
  ledger and drives the reports.
- **Teach-back (1 slot)** — explain it in your own words; **LLM-graded on verdict + depth**
  (`grade_teachback`, nightly pipeline, when the API key is set). Spelling/grammar never count.

## Live planner intelligence (what chooses the questions)

Subject balance (every core subject guaranteed, capped); **repair** (weakest topics first);
**throwback** (aged-mastered topics resurface); **fresh** (current class topics from the weekly
Canvas sweep). Deterministic **state-writer** ledger; the teach-back grade feeds it.

## Live payoff surfaces

- **Achievements** (Sure Shot, Clean Run — "no lucky guesses, no sure-but-wrongs"…).
- **Friday report** surfaces the metacognition quadrants: **"Felt sure, wasn't — the sneaky one"**
  (confidently wrong) and **lucky guesses** (right but "Guessing").

## The two axes (why the parent picture is honest)

The ledger tracks **confidence** (`state` — how sure, when to re-test → scheduling) and **depth**
(`depth` — how well understood → reporting) independently. That is what lets us tell a parent
something true — "solid on X, only recites Y, confidently wrong about Z" — instead of a number.
See `UNDERSTANDING.md`, `LEDGER-RULES.md`.

## In the shell but DORMANT (built, then reverted after review — harmless, not exercised)

Verified against real composed quizzes: the generator never emits these, so no live quiz
triggers them — **numeric typed input** (`type:numeric`), **hidden double-XP** (`x2`; the
in-shell mechanic — one random question per run, secretly doubled), **encore** bonus round, **interactive ordering** (drag slots), the
**standard-round format variety** (odd-one-out / spot-the-error / matching / ordering-as-MC),
and the **teach-back three-light** display. The code + CSS remain but stay inert.

> **NOT dormant — Friday Battleground varies question formats live.** Its four claimable
> zones deliberately mix **spot-the-lie / true-false / multiple-choice / sum-as-MC** (all
> render as four options — the variety is in the prompt, not a `type` field). Validated
> against real output (14 Aug) and locked by `tools/test_planner_events.py`. See SEASONS.md.

## Separate / not wired

- **Boss Night** (losable, HP bar, spot-the-lie) — `modes/boss-battle/`. A preserved **future** mode,
  not scheduled. **Not** the live Friday **Battleground** (which has no lose-state). *Naming trap:*
  Friday's internal directive is literally `"boss"`, but it produces Battleground.
- **Swipe Sort** — first entry in the mechanics toolbox (`modes/MECHANICS.md`); prototype (v9)
  approved for fun, **not yet integrated**.

## The mechanics process (non-negotiable)

New mechanics are built **one at a time**, prototyped in an **isolated playable preview** that is
approved for **fun AND product quality**, and kept **out of live quizzes** until approved. See
`modes/MECHANICS.md`.
