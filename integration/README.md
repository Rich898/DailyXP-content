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
- [ ] **1b. Wire into a STAGING copy of the shell** — `qType(q)==="swipe"` in `renderSpeed` mounts
  the widget; its `onDone` scores + advances exactly like an MC answer. Test the staged shell with a
  synthetic swipe quiz; confirm nothing else breaks.
- [ ] **2. Composer** — teach `compose.py` to emit swipe questions when the plan declares a swipe
  slot; deterministic gate (affirmative single-fact statement, valid 2-way bucket pair, balanced sides).
- [ ] **3. Planner** — mark slots `type:swipe`, **t1 seat only** at first.
- [ ] **4. State-writer** — weight swipe as WEAK evidence (a 50/50 correct isn't strong mastery).
- [ ] **5. Test end-to-end + dogfood on t1** → only then enable for the boys.
