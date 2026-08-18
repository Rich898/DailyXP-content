# XP Daily — What's actually LIVE (shell audit)

_18 Aug 2026. Verified against the deployed shell (`shell/template_v3.html`), the generator
(`scripts/run_daily.py` + `tools/planner.py`), and **real composed quizzes + plans** in
`DailyXP-private/history/` and `DailyXP-private/plans/`. Where this disagrees with
CURRENT-STATE.md, this is right — see the discrepancy note at the bottom._

## Quiz shapes — there's a live weekday EVENT rhythm (docs omit this entirely)

| Day        | Directive       | Shape                          | Total |
|------------|-----------------|--------------------------------|-------|
| Mon/Tue/Thu| standard        | 7 speed + 4 steady + 1 teach   | 12    |
| **Wed**    | reversed blitz  | **10 speed + 2 steady + 1 teach** | 13 |
| **Fri**    | "boss" → **BATTLEGROUND** | **2 speed + 4 steady + 1 teach** | 7 |

Frozen students (e.g. Roshan on camp) → placeholder, no quiz. Confirmed from real plans:
Wed 12 Aug = REVERSED BLITZ (13 slots), Fri 14 Aug = BATTLEGROUND (7 slots).

## Live mechanics (these fire in real quizzes)

**Speed round (Heat 1)** — all 4-option MC, and:
- **Timed** per question (fuse bar + countdown clock, both turn red under 6s; timeout = auto-miss).
- **Combo** — `COMBO ×N LIVE` once you're on ≥2 correct, with a combo bonus added to points.
- **Skip** — "it'll come back around"; on a `fresh` topic it says "I'll check when your class gets there."

**Steady round (Heat 2)** — MC, no clock, plus the **confidence wager** (THE thing I nearly rebuilt):
- Pick answer → **"HOW SURE?"** → **Sure / Think so / Guessing** → **Lock it in**.
- Confidence is written to the ledger (`questionDone(…{confidence})`) and drives the reports.

**Teach-back (1 slot)** — explain in your own words; **LLM-graded on verdict + depth**
(`grade_teachback` runs in the nightly pipeline when the API key is set). Spelling/grammar never count.

## Live planner intelligence (what chooses the questions)
- **Subject balance** (every core subject guaranteed, capped per quiz).
- **Repair** (weakest topics first), **throwback** (aged-mastered topics resurface — a steady slot),
  **fresh** (current class topics from the weekly Canvas sweep).
- Deterministic **state-writer** ledger; the teach-back grade feeds it.

## Live payoff surfaces
- **Achievements**: Sure Shot, Clean Run ("no lucky guesses, no sure-but-wrongs"), Blitz PB, etc.
- **Friday report** surfaces the metacognition quadrants: **"Felt sure, wasn't — the sneaky one"**
  (confidently wrong) and **lucky guesses** (right but "Guessing").

## In the shell but DORMANT (code + CSS present, generator never produces it → never fires)
Confirmed: the 18 Aug composed quiz has `type:(none)` on all 12 questions and none of the flags below.
- **Numeric typed input** (`type:numeric`, `.ninput`) — no numeric questions generated.
- **Hidden double-XP** (`q.x2`, "DOUBLE XP" flash) — no `x2` flags generated.
- **Encore** bonus round (`encoreOffer`, `encoreQs`) — no encore questions generated.
- **Ordering** (`.oslot`/`.ochip`, `state.order`) — no order questions generated.
- **Format variety** (odd-one-out / spot-the-lie / …) — present on the 17 Aug plan (`format` field),
  gone by the 18th; not generated.
- **Teach-back three-light** (`.tblights`) — CSS present, render doesn't use it. Grading stays; the
  in-shell lights were removed.

These match the "built then reverted" history. Inert, harmless, just not exercised.

## Separate / not wired
- **Boss Night** (losable, HP bar, spot-the-lie) — `modes/boss-battle/boss-shell.html`. A preserved
  **future** mode, not scheduled. **Naming trap:** Friday's internal directive is literally `"boss"`,
  but it produces the no-lose **BATTLEGROUND** — a different thing from the losable Boss Night.
- **Swipe Sort** — our new prototype (v9), approved for fun, **not yet integrated**.

## Discrepancy — the thing that nearly cost us a duplicate build
CURRENT-STATE.md says the quiz is _"plain, direct multiple-choice … nothing else."_ That's stale.
It omits every live mechanic above: the confidence wager, combo, the timer, the weekday events
(Reversed Blitz, Battleground), throwback, repair, fresh, teach-back grading, achievements and the
report quadrants. It is only correct about the **dormant** list. **Recommend replacing CURRENT-STATE.md
with this.**
