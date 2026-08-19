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


## Dark design-system overhaul (staging)
- [x] Repainted the whole quiz shell to the dark design system (dark field + grid, light text,
  mechanic/accent colours, gold CTAs, card craft) in `shell-staging.html`. Resolves the swipe
  theme mismatch by pulling everything UP to dark rather than the widget down to light. Verified:
  start / swipe / MC / steady all render dark + coherent, selected/reveal states themed, zero JS errors.
- [ ] **Codify tokens** as the ONE canonical design system so every surface uses the same values.
- [ ] **Apply to the LIVE shell** (`shell/template_v3.html`) — carefully, tested, dogfooded on t1.
- [ ] **Extend to other surfaces** — parent report page, kid weekly wrap, and the event-night
  banners (Blitz's "inverted ink plate" needs a dark rethink; Battleground is already dark).


## Block model (staging — shell side)
- [x] **Shell renders BLOCKS with doorway cards.** Questions carry `block:{label,hue,icon,sub,cta}`;
  the config-driven transition fires whenever the block changes (block boundary) as well as at Heat
  boundaries. Proven: a 2-block speed round (Quick Recall x5 → **Reversed x5 block**) shows a
  "NEXT UP · REVERSED" doorway mid-round, progress rail correct, zero JS errors. Generalises to any
  mechanic-as-block (swipe/numeric/etc.).
- [ ] **Reveal previews the blocks** (route by block, not just Heat) — refinement.
- [ ] **Pipeline generates block-structured quizzes** — planner declares blocks + marks only the
  Reversed block's slots as reversed; composer reverses only those. (The big remaining piece — makes
  it real, not synthetic.)
- [ ] Merge to live + dogfood on t1.


## Swipe LIVE + block model merged (this session)
- [x] Composer generates swipe questions (True/False sorts when a topic has no natural split); validator accepts swipe.
- [x] Planner declares a Swipe block for the **t1 test seat** (front of speed round) + Quick Recall block; swipe slots exempt from reversal.
- [x] State-writer weights swipe as WEAK evidence: a correct swipe raises one box (untested->shaky->developing) but NEVER solid alone; a miss holds.
- [x] Block model MERGED into the live template (config-driven doorways). Backward-compatible: block quizzes get block+Heat doorways, no-block quizzes get Heat doorways only (boys' quizzes unaffected). Verified both, zero JS errors.
- [ ] **Deploy to t1 + dogfood** (play the swipe block end-to-end with real backend), then roll to the boys.


## Numeric mechanic — stage tracker (2nd mechanic, after swipe)
- [x] **1a. Embeddable widget** — `numeric-widget.html`: `mountNumeric(container, q, {onCommit,onDone})`.
  Scoped input: number pad for MENTAL (calc:false), full calculator for METHOD (calc:true). Safe
  shunting-yard evaluator (no eval), 0.01 tolerance, pre/post units, calc-use logged (`usedCalc`).
  Reports `{ok, value, usedCalc}`. Proven: 2 mental + 2 method, 4/4, both keypads, zero JS errors.
  Schema: `{ type:'numeric', subject, prompt, answer:<number>, calc:<bool>, pre, post, why }`.
- [x] **1b. Wired into the STEADY round** — `renderSteadyNumeric` mounts the widget (no confidence wager, no clock);
  `finishNumericSteady` records + advances. Proven: mental -> number pad, method -> calculator, both scored,
  records carry `usedCalc` (calc:False for mental, calc:True for method), advances to teach, zero JS errors.
- [x] **2. Composer** generates numeric (method/mental split, numeric answer, units). Validated: real numeric block composes.
- [x] **3. Planner** slots a Numeric block (t1, the Maths steady slots).
- [x] **4. Validator** accepts numeric (number answer + calc bool).
- [x] **5. State-writer**: numeric is strong (typed, no guessing) — promotes, capped at developing (no wager); usedCalc preserved for the parent report.


## Full run + steady doorways
- [x] Steady block doorways added (advanceSteady detects block change; Heat-2 doorway reflects the first steady block).
- [x] Full run proven end-to-end: Swipe block -> Quick Recall -> **Numeric** -> Checkpoint -> Teach-back, coherent doorways throughout, numeric records carry usedCalc, zero JS errors.
- [ ] Merge numeric + steady doorways into the LIVE template (currently staging only), then dogfood on t1.
