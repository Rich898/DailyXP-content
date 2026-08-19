# integration/ — WIP: bringing approved mechanics into the live shell

**Nothing here is wired into the live shell yet.** This is staging/proof work. The live
`shell/template_v3.html` and the boys' quizzes are untouched until a mechanic is fully proven
and deliberately switched on — and the composer will emit new mechanics for the `t1` test seat
first, never the boys.

## Swipe integration — stage tracker
- [x] **1a. Embeddable widget** — `swipe-widget.html`: `mountSwipe(container, q, onDone)` renders one
  swipe question (real drag physics, fly-into-bucket, fx), reports `{ok, sideLabel}`. Proven in a
  harness (mounts, plays a 3-question block, reports each result). Schema:
  `{ type:'swipe', prompt, left, right, answer:<the correct label>, why }`.
- [x] **1b. Wired into a STAGING copy of the shell** — `shell-staging.html`: `qType(q)==="swipe"` in
  `renderSpeed` mounts the widget; an `onCommit` hook stops the timer on commit; `finishSwipe` records +
  scores + advances through the existing path. Proven: swipe + MC coexist in one speed round, scores accrue,
  hands off to steady (confidence wager intact), **zero JS errors**. ⚠ **Follow-up: theme mismatch** — the
  widget is dark-arcade-tuned but the shell's standard speed screen is LIGHT, so the buckets look washed on
  the cream background. Needs a light-theme pass on the widget before it looks shippable.
- [ ] **2. Composer** — teach `compose.py` to emit swipe questions when the plan declares a swipe
  slot; deterministic gate (affirmative single-fact statement, valid 2-way bucket pair, balanced sides).
- [ ] **3. Planner** — mark slots `type:swipe`, **t1 seat only** at first.
- [ ] **4. State-writer** — weight swipe as WEAK evidence (a 50/50 correct isn't strong mastery).
- [ ] **5. Test end-to-end + dogfood on t1** → only then enable for the boys.
