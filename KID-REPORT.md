# KID-REPORT.md — the kid's weekly wrap

**Status: brief, ratified 11 Aug 2026. Not yet built.**

The third Friday surface (`REPORTING.md` surface C). The parent report judges the
week; **this celebrates and re-arms the player.** It is the kid's own page,
hosted at `/w/<slug>/` on the reports site, linked from his Friday surface and
from the foot of the parent report.

`REPORTING.md` owns the parent surfaces. `UNDERSTANDING.md` owns the depth
ladder. This file owns what the KID sees, and where his page must deliberately
differ from his parents'.

---

## 1. The one-line test

> **A player card, not a report card.**

If a line would sit comfortably in a school report, it is wrong for this page.
If it would sit comfortably in a game's end-of-week summary, it is right.

The voice is a **fellow player**, never a teacher and never a parent. It knows
the season, respects the effort, and is straight about what's coming. It never
congratulates him on being clever, never tells him to try harder, and never
speaks on behalf of his parents.

---

## 2. The transparency law — the load-bearing rule

**Nothing in the parent report is hidden from the kid.**

The two Friday surfaces describe the same week in different languages. They must
never describe *different weeks*. If Harrison reads Melina's report over her
shoulder — and one day he will — he must find the same facts he already saw on
his own page, dressed differently. The moment the parent surface holds a secret
about him, the whole system becomes something done *to* him rather than *for*
him, and a teenager will disengage from it permanently.

So:

* Every gap on the parent report appears on the kid page — as a **target**, not
  a failing.
* The week-word is the same word, computed by the same engine.
* The kid page may add things the parent page doesn't have (XP, streaks, badges,
  boss results). It may never subtract a fact.

**The single exception: integrity flags.** A quarantined teach-back is never
surfaced to the kid, in any form, ever. No "this one didn't count", no silent
score gap he can infer. That is a human conversation between a parent and their
child, and an automated system accusing a teenager of cheating — even gently,
even correctly — is unrecoverable if it is wrong, and damaging if it is right.
The row is simply excluded, exactly as it is from the figures.

---

## 3. What lives here that is NOT on the parent report

Deliberately relocated from the parent surface (see `REPORTING.md`, Friday
section) because they are **game metrics** — motivating to a player, misleading
to a parent:

* **XP by day** — the bar chart. Points vary with difficulty, which makes them a
  poor measure of learning but a perfectly good measure of showing up. That's
  what a player wants to see.
* **Streak** — nights in a row. The single most motivating number in the system.
* **Season total and level** — the long arc.
* **Badges earned this week** — with the specific act that earned them.
* **Boss / blitz results** — the week's set-piece events, won or survived.

Note the asymmetry and keep it: the parent report **leads with mastery** and
demotes points; the kid page **leads with the game** and carries mastery inside
it. Same week, different entry point.

---

## 4. Structure

1. **The week-word, as a verdict on the run** — same word as the parent report,
   game-flavoured ("Strong week", "Quiet week"). Never "well done".
2. **The run** — XP by day, streak, season total, level. Visual, quick.
3. **What you beat** — topics that came good this week, boss cleared, badges
   earned. Named specifically: *what* he beat, not that he "did well".
4. **Your own words** — the same teach-back the parent report quotes (integrity
   gate applies identically). Seeing his own explanation quoted back is the
   strongest single moment on either page.
5. **What's stalking you next week** — the targets. Named topics, framed as the
   things coming back for another go. This is where gaps live, and the framing is
   *pursuit*, not *deficit*.
6. **The one move** — a single concrete thing that would most change next week.
   Process-level, never person-level.

---

## 5. Language laws

* **Praise the move, never the player.** (Hattie & Timperley: feedback about the
  person is the weakest kind.) "You linked two ideas — that's the move that gets
  marks" not "you're smart". This matters *more* here than on the parent page,
  because this is the surface he actually reads.
* **Difficulty belongs to the set, effort belongs to the player.** Same law as
  the daily soundbyte. The quiz was hard; he was not bad at it.
* **Hard is the point, and say so.** Learning that sticks *feels* harder than
  learning that doesn't (the desirable-difficulties finding). When a week got
  harder, the page says that's the system working — and it says it in a way a
  fourteen-year-old believes, i.e. without sounding like a consolation prize.
* **Depth rungs attach to TOPICS, never to him.** "Crusades: you can connect it
  now" — never "you're a can-list-it kid". Banned construction (see
  `UNDERSTANDING.md`).
* **No guilt, no nagging, no comparison.** Not against his brother, not against
  a class, not against last week's better self. The only comparison is topic vs
  its own previous position.
* **Never speak for his parents.** No "your mum will be pleased". The parent
  channel is separate and stays separate.

---

## 6. The depth ladder, kid-side

Same ladder, same plain words (`UNDERSTANDING.md`): **not yet / knows it / can
list it / can connect it / can apply it elsewhere.**

For a kid this is the most motivating thing on the page **if framed as a level-up
track**, because it is one: it is the only progression in the system that cannot
be gamed by grinding easy questions. It is also the honest explanation of why the
quiz keeps asking him to *write* things:

> Multiple choice can only ever show you know it or can list it. To get to *can
> connect it*, you have to explain it. That's why the teach-back exists.

Telling him the rule makes the teach-back feel like a boss fight rather than
homework — and a player who understands the scoring system engages with it.

---

## 7. Week 1

No trend, no streak history, no prior. Say so plainly and make it a start line
rather than an empty dashboard: first week on the board, here's the map, here's
what's coming. Under-claim exactly as the parent page does.

---

## 8. Build notes

* Self-contained HTML, zero fetch, `noindex` — identical privacy model to the
  parent report (`report_page.py`). Deployed by the same Friday job to
  `/w/<slug>/`; the slug already exists in `work/report_slugs.json`.
* Reuse the fact card and stories from `friday_report.py` / `report_stories.py` —
  **the same facts, re-dressed.** Building a second facts layer would let the two
  surfaces drift apart, which §2 forbids.
* Visual language: the quiz shell (`shell/template_v3.html`), not the parent
  report. This should feel like the game, because it is.
* `friday_report_run.py` already generates the wrap URL and passes
  `kid_wrap_url` into the parent page — currently `None` until this is built.

## 9. Open

* Does the kid page show accuracy figures? Leaning yes, as a target to beat
  rather than a mark — but it risks becoming a report card. Decide with Rich.
* Does it name the assessment radar? A test in 6 days is useful information but
  may induce anxiety in a way the parent framing doesn't. Probably yes, framed as
  a countdown to a boss fight.
