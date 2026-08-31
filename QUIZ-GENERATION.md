# QUIZ GENERATION — source of truth

_How a quiz's content comes to exist: from the weekly Canvas scrape to the validated,
reviewed question set. Derived by tracing the actual code on **20 Aug 2026** (commit
`d346320`), not from the older docs — every rule below carries its code location so it can
be verified. Where this document and any other doc disagree, **this document reflects the
code**; the disagreements are listed at the bottom in "Contradictions & gaps found".
Companion: `DAILY-PUBLISHING.md` (how the quiz is published, triggered, and communicated)._

---

## 1. The outline — where the curriculum comes from

**The weekly Canvas sweep produces one targets file per week** in the private repo:
`targets/YYYY-MM-DD.json` (dated the Monday of the sweep). It is produced manually — Rich
opens Canvas in Chrome with the Claude extension, runs the sweep instruction in `SWEEP.md`,
and the build chat writes + commits the file. There is no automated Canvas integration yet.

**What a scrape contains** (shape read by `planner.load_targets_for`, planner.py):

```
{ "students": { "y8": { "subjects": {
    "<Subject>": {
      "assessment_format": "...",              (optional, subject level)
      "topics": [ { "topic": "...",
                    "status": "live" | "upcoming" | "not_yet_posted" | "prior_term",
                    "fresh": true|false,        (newly introduced this week)
                    "assessment": {"date": "...", ...} (optional) } ] } } } } }
```

**How the pipeline picks a targets file:** `run_daily.py` sorts `targets/*.json` by filename
and takes the newest (`run_daily.run`, "pick the newest targets file"). **Monday's quiz never
depends on the sweep** — if the sweep is late, the previous week's file is used. If the
newest file is more than 7 days old, the run prints a loud staleness warning
(`run_daily.run`, the `t_age > 7` check) but continues.

**A topic's "week"** is derived from the targets filename date: week 1 = w/c Mon 27 Jul 2026
(`W1_MONDAY` in both `run_daily.py` and `seed_menu.py`; `seed_menu.week_of`).

**Aliasing:** t1 (Rich's test seat) quizzes the y8 curriculum. `roster.targets_alias("t1")`
returns `"y8"`; `run_daily` injects y8's targets block under the `t1` key so the planner
never needs to know about aliasing (`run_daily.run`, "Test/aliased players" block).

## 2. The menu & seeding (`tools/seed_menu.py`)

**Doctrine (SEASONS.md LAW 6, ratified 20 Aug):** the MENU is the whole covered curriculum —
every topic that has ever appeared with `status:"live"` in ANY weekly scrape. It only grows.

**How the menu is built:** `seed_menu.build_menu(alias, targets_dir)` walks every scrape file
oldest→newest and collects each `status=="live"` topic the first time it appears, recording
`{subject, introduced_week}`. Topics whose status is `upcoming` / `not_yet_posted` /
`prior_term` are **never** put on the menu (only `live` counts — `build_menu`, the
`status != "live"` skip).

**How seeding works:** `seed_menu.seed_player(state, player, alias, targets_dir)` adds every
menu topic missing from the player's ledger as
`{state:"untested", repair:false, last_tested:null, times_seen:0, note:"", introduced_week}`,
and back-stamps `introduced_week` on existing topics. It never touches an existing topic's
mastery. It is called from `run_daily.run` ("SEED THE MENU" block) for every student, every
run, before planning.

> ⚠️ **CRITICAL BUG (confirmed live):** `run_daily` seeds the **in-memory** state dict and
> **never writes state.json back to disk**. The seeded topics exist only for that run's
> planning and are discarded. See Contradictions §C1 — this silently breaks the feedback
> loop for every seeded topic.

> ⚠️ `introduced_week` is written by `seed_menu` and **read by no code anywhere**. The
> two-tier sort does not use it (see §5). See Contradictions §C2.

## 3. The ledger (`DailyXP-private/work/state.json`)

**What it is:** the per-topic mastery record — the IP. One block per student:

```
students.<code>: {
  "status": "ACTIVE" | "FROZEN",       ← the absence gate (hand-set)
  "status_reason": "...",              (optional, shown in the placeholder plan)
  "topics": [ {
      "subject": "...", "topic": "...",
      "state": "untested" | "shaky" | "developing" | "solid" | "REPAIR",
      "repair": true|false,            ← the REPAIR lane flag
      "repair_confirms": 0..2,         ← confirms toward REPAIR exit
      "last_tested": "YYYY-MM-DD" | null,
      "times_seen": n,
      "note": "...",                   ← human-authored; the writer NEVER overwrites it
      "last_result": {date, badge, ok, confidence, pace, from}   (written by the writer)
  } ] }
```

Verified against the live file (20 Aug): y8 has 23 topics, y9 27, t1 16; **no topic carries
`depth` or `introduced_week`** (both are supposed to exist — see §9 and Contradictions).

**What the ledger IS responsible for:** ranking. It tells the planner which topics are
weakest / most due, guarantees REPAIR slots, and drives spacing and throwback selection.

**What the ledger is NOT responsible for:** capping the set (LAW 6 — the outline is the
menu; a thin ledger never shortens a run), holding question text, or holding any depth/SOLO
data (today, none exists in it — see §9).

**How mastery is updated — the state-writer (`tools/state_writer.py`):**

The writer runs at the start of each pipeline run (before planning), applying any new
**canonical, non-test** runs from `runs.json` that its cursor
(`work/state_writer_cursor.json`) hasn't seen. Per run:

1. **Join** — it loads the persisted plan `plans/<student>/<set_date>.json` to map each
   result question id → the topic it tested (`state_writer.load_plan`). No plan file → the
   whole run is skipped with a warning.
2. **Badge** — each question gets a badge via `state_writer.badge_for`, built on
   `results_reader.classify` (one source of doctrine):
   - Skips: `SKIP` (fresh topic — benched intel, no ledger effect) or `SKIP✗` (skip on an
     already-taught topic — a soft miss, demotes one box).
   - MC wrong: `CW` confident-wrong ("Sure" or shell flag), `GW` guessing-wrong, `FW`
     fast-wrong (relative to the kid's own phase median — `results_reader.relative_speed`,
     thresholds `FAST_FRAC=0.50`, `TRIVIAL_FRAC=0.35`, `SLOW_FRAC=1.80`, needs
     `MIN_BASELINE_N=4` timed answers), `SW` slow-wrong, `✗` considered-wrong.
   - MC correct: `LUCKY` (guessing), `TRIV✓` (trivially fast), else `✓_sure` / `✓_think` /
     `✓_plain` split by the confidence wager.
   - Mechanics: `SWIPE✓/✗`, `NUM✓/✗`, `ORD✓/✗`, `TXT✓/✗` (by the record's `type`).
   - Teach-back: `TB✓` / `TB~` / `TB✗` from the nightly grade (`tb_grade.verdict` via
     `state_writer.verdict_badge`), or plain `TB` (no-op) when ungraded or integrity-held.
3. **Govern** — if several questions hit one topic, the single governing badge is chosen by
   the `PREC` severity list (`state_writer.PREC`):
   `CW > ✗ > SW > GW > SKIP✗ > FW > LUCKY > TRIV✓ > TB✗ > ✓_sure > TB✓ > ✓_think > TB~ >
   ✓_plain > TB > SKIP`. ⚠️ The mechanic badges (SWIPE/NUM/ORD/TXT) are **not in this list**
   — they all rank equal-last (see Contradictions §C9).
4. **Transition** (`state_writer.transition`) — the box model
   (`untested(0)→shaky(1)→developing(2)→solid(3)`), at most one box per run:
   - **Swipe** is weak 50/50 evidence: a correct gently raises (untested→shaky,
     shaky→developing) but never reaches solid alone and never confirms a REPAIR; a wrong
     swipe holds (never punishes).
   - **Numeric / order / text** are typed, strong evidence: a correct promotes
     untested/shaky→developing but is **capped at developing** (no confidence wager → solid
     needs deeper evidence); a wrong demotes one box; on REPAIR they hold (a wrong resets
     confirms).
   - **CW** → shaky; a CW whose topic's *immediately prior* `last_result.badge` was also CW
     → REPAIR (chronic, self-invisible). Note: this is *consecutive* CW, not "2nd CW ever"
     — an intervening correct clears it.
   - **✗ / SW / GW / SKIP✗** → demote one box (floor is shaky: `IBOX[max(1, box-1)]`, so a
     wrong on an *untested* topic actually moves it UP to shaky — "now measured, weak").
   - **FW / LUCKY / TRIV✓** → box unchanged (rush/luck, not knowledge), REPAIR confirms
     reset.
   - **✓** — first clean correct on untested → developing; shaky → developing; the ONLY
     route to solid is `✓_sure` + calm pace + currently developing + **spaced** (prior
     `last_tested` strictly before this run's date) + no canonical-caveat.
   - **TB✓** (teach-back solid) — routes like a calm confident correct (incl. the spaced
     route to solid); **TB~** is a landing only; **TB✗** holds the box and BLOCKS promotion
     (the fluency-illusion catch — sits above the correct badges in PREC).
   - **REPAIR lane** — exits to developing only after `REPAIR_EXIT_CONFIRMS = 2` confirms;
     a confirm is a calm `✓_sure` or a `TB✓`; anything wrong/fast/lucky/trivial resets
     confirms to 0.
   - `attempt > 1` canonical ("canonical-by-default") caps promotions at developing.
5. **Bookkeeping** — tested topics get `times_seen += 1`, `last_tested = run_date`, a
   structured `last_result`; every transition is appended to `work/state_writer_log.jsonl`
   with its reason; the run is added to the cursor; `state["generated"]` advances.

`LEDGER-RULES.md` documents an older version of this table (no TB consequences, no mechanic
or SKIP✗ badges) — see Contradictions §C10.

## 4. Loadouts & shape

**The weekly skeleton** is `WEEKDAY_DIRECTIVE` in `scripts/run_daily.py` (mirrored in
`tools/kid_nudge.py` — change both together):
`{Mon:standard, Tue:standard, Wed:standard, Thu:standard, Fri:"boss"}`. **Blitz is retired
(20 Aug)** — Wednesday is a plain standard day; Reversed survives only as a dormant
per-slot mechanic (see §7).

**The shapes** (`planner.SHAPES`):
- `standard`: **12 speed / 6 steady / 1 teach** (19 questions, ~5–6 min).
- `boss` (Friday → Battleground): **2 speed / 7 steady / 1 teach**.

**How a day's shape is chosen** (`planner.plan_set`): the directive comes from
`WEEKDAY_DIRECTIVE` unless overridden per student (`--directive-<code>` /
`directives_override` in `run_daily`). `"boss"` anywhere in the directive → boss shape;
everything else → standard. A `light <subject>` / `post-test <subject>` directive hard-caps
that subject to ONE slot in the whole set (`light_ok`) and adds a calm-difficulty line to
the composer instructions.

**Weekends:** `run_daily.run` exits before doing anything (`date.weekday() > 4`).

**FROZEN students** (`state.students.<code>.status == "FROZEN"`): `planner.plan_set` returns
an empty placeholder plan with `status_gate:"FROZEN"`; `run_daily` publishes a placeholder
set with no compose call. Untested topics stay due and resurface on return; never nag.

## 5. Topic selection (the planner — `tools/planner.py`)

### 5.1 Eligibility (`planner.eligible_pool`)

A state topic enters the pool if it **resolves to any row in the current targets file**
(via `resolve_target` — exact match, then substring, then ≥2-word stem overlap; this
tolerant matching compensates for wording drift between the hand-built files) **or** it is
a REPAIR thread. ⚠️ The docstrings say "subject is LIVE in targets" but the code admits any
resolvable topic of any status, including `prior_term` (Contradictions §C3).

### 5.2 The two-tier sort (LAW 6, the outline-drives-the-quiz rule)

- **Tier 1 (THIS WEEK):** the topic's name is an **exact** match for a topic with
  `status:"live"` in the **latest scrape** (`current` set in `eligible_pool`). Exact on
  purpose — tolerant matching would let a prior topic borrow "live" and jump tiers.
- **Tier 2 (PRIOR WEEKS):** everything else that passed eligibility.
- Sort key: `(tier, -score)` — tier is PRIMARY, so this-week always outranks prior-week;
  the priority score orders only *within* a tier.

Note: tier is computed from the latest scrape's live set, **not** from `introduced_week`
(which nothing reads — §C2).

### 5.3 The priority score (`planner.score_topic`)

`STATE_PRIORITY` base: REPAIR 100 > shaky 70 > developing 45 > untested 30 > solid 12.
Plus: spacing (+2/day since `last_tested`, capped +24 — longer-unseen ranks higher);
targets status (live +15; upcoming/not_yet_posted +6; prior_term or unresolved −8);
assessment proximity (+30−days when an assessment is within `ASSESS_HORIZON_DAYS = 16`);
untested topics that aren't live/upcoming take −25 (untested only earns a slot if fresh).

### 5.4 Slot allocation order (`planner.plan_set`)

A topic may take at most ONE slot per phase and TWO across the whole set. Topics scoring
below `SCORE_FLOOR = 0` are never slotted by the normal fill (a relaxed fallback and the
coverage/REPAIR paths bypass the floor). Global cap: no subject takes more than
`MAX_PER_SUBJECT = 3` slots in one quiz.

1. **REPAIR guaranteed** — every REPAIR topic gets a steady slot (confidence captured),
   bypassing the score floor, with the "do NOT let a fast-correct promote it out" guidance.
2. **Throwback (LAW 3)** — skipped on boss days; otherwise ONE steady slot is reserved via
   `throwback.pick`: eligible = state in {solid, developing}, not a repair thread,
   `last_tested` ≥ `THROWBACK_MIN_AGE_DAYS = 10` days ago. Score = age + mastery bonus
   (solid 6 / developing 2) + min(times_seen, 6); deterministic tie-breaks. No eligible
   topic → simply no throwback slot (never padded). The slot is stamped
   `throwback:true, fresh:false` and carries the retention-check composer note
   (`throwback.composer_note`).
3. **Subject coverage** — each of `CORE_SUBJECTS = (Maths, English, Science, History)` that
   is live but not yet present gets one guaranteed slot (speed preferred), bypassing the
   score floor, so an all-untested subject can't be starved forever. Skipped on boss.
4. **Steady fill** — top scorers, per-phase subject cap 2 (99 on boss), with a relaxed
   (floor-dropping) fallback so a thin pool still fills the count.
5. **Teach** — one slot, highest-value available topic; guidance carries the subject's
   `assessment_format` when the sweep captured one.
6. **Speed fill** — top scorers, per-phase subject cap 3, relaxed fallback; a still-short
   pool logs "recommend a fresh sweep".

Any unfilled slots are recorded in `plan.shortfall` and WARNed, never padded. Slots are
renumbered S1…/T1…/TB1 by phase; the plan carries `requested_shape` vs final `shape`.

### 5.5 What the plan is

One slot = `{slot, phase, subject, topic, intent, fresh, state, score, guidance}`
(`planner._slot`). `intent` = repair / throwback / consolidate (shaky) / confirm
(developing) / maintenance (solid) / fresh (untested). `fresh` is the honest sweep flag
(throwbacks are always `fresh:false`). The plan also carries `composer_instructions` — the
full language brief including the answer-length law, plus reversed/Battleground briefs when
applicable. **The plan is persisted to `plans/<student>/<date>.json` before compose**
(`run_daily.run`) — it is the join the state-writer needs (results carry id+subject but not
topic), and it is written even for FROZEN/dry runs.

## 6. The laws (SEASONS.md LAWS 1–6) — plain English + enforcement point

| Law | Plain English | Enforced at |
|---|---|---|
| **1 — answer-length tell banned** | The correct MC option must not be identifiable by length (or any surface feature). | Composer constraint: `planner._composer_instructions`. Per-slot blocking gate: `answer_length.sole_longest_violation` (sole longest by >15% over the runner-up; 2-option slots exempt), wired into `review.normalise` as a BLOCK that overrides the LLM verdict → recompose. Per-run distribution rule: `answer_length.audit` (share of sole-longest correct answers must be ≤ 34%; random = 25%). ⚠️ In code the run-level rule is computed but **neither blocks nor prints** — see §C6. |
| **2 — variety is structural (format bank)** | REVERTED 19 Aug: standard speed/steady are direct recall MC; varied MC formats are Friday-Battleground-only. Daily variety comes from the answer mechanics (§7) instead. | `planner.plan_set` sets `format_summary = "direct recall"`; the format bank module (`tools/formats.py`) was deleted. RUNBOOK.md still cites it — §C15. |
| **3 — continuous throwback** | One aged-but-mastered topic resurfaces per standard run to check retention held; never padded, never themed. | `tools/throwback.py` + step 1b of `planner.plan_set`; `validate.py` enforces `throwback → fresh:false`. |
| **4 — variety, not runtime, is the target** | Never pad a run to hit a duration. | Design law only; no code enforcement needed. |
| **5 — new input types were Shell v3.1** | Typed/drag inputs were deferred to a shell rebuild. | Delivered 19–20 Aug: Shell v3.1 renders swipe/numeric/order/text; `SHELL-3.1-SPEC.md` is now historical (and differs from what was built — §C8). |
| **6 — the outline drives the quiz; the ledger only ranks** | The scraped curriculum is the menu; every scraped topic is seeded and askable; the planner fills THIS-WEEK-FIRST; the ledger orders within tiers and never caps the set. | `seed_menu.py` + the seed step in `run_daily.run` + the two-tier sort in `planner.eligible_pool`. ⚠️ The "seed on sight → tracked" half is broken by the persistence bug (§C1). |

## 7. Mechanics — each answer type, where it applies, where it's assigned

**Assignment lives in `planner.assign_blocks`** (called at the end of `plan_set`), which
deals the run into coherent blocks — a block never mixes mechanics — and stamps each slot
with `mech` + `block` metadata (label/hue/icon/sub/cta from `planner._BLOCKS`) that drives
the shell's doorway cards. **Since 20 Aug this applies to ALL seats** (the t1-only gate was
lifted, commit `c50e296`).

**Standard day:**
- Speed: a **Swipe** block of `min(4, speed)` slots at the front (`type:"swipe"` — a
  two-way sort, never reversed), then **Quick Recall** (plain 4-option MC), then a
  **Scrub It** tail block of `min(3, remainder)` slots (27 Aug 2026, all seats): plain MC
  dealt through the erase delivery mode — the slot gets `mode:"scrub"` from the PLAN (never
  the model); `type` stays MC so the ledger never learns the mode. ⚠ The shell side of scrub
  was only merged into `shell/template_v3.html` on **31 Aug 2026** — before that the deployed
  shells silently fell back to tap MC (the t1 live-fire catch). A template change reaches a
  kid only when their Netlify shell is re-deployed (`tools/stamp_shell.py` builds the zips).
- Steady, by subject: **Maths → Numeric** (typed number, calculator on `calc:true` method
  questions, number pad on mental), **History → Drag It** (`order` — drag tiles into an
  unambiguous sequence), **Science → Short Answer** (`text` — typed word-or-two with a
  fuzzy-matched `accept` list; spelling never counts). All other steady subjects stay MC.
- Steady is the deliberate home of the typed mechanics: no clock, no confidence wager.

**Reversed** (dormant — no schedule slot uses it since Blitz retired): if a directive
contains `"reversed"`, the speed round becomes Quick Recall then a CONTAINED Reversed block
of `min(5, speed)` slots. The current composer brief (`planner._composer_instructions`) is
"state a distinguishing detail, then a short category cue — '<detail> — which play?'" with
four short THING labels as options, a hard anti-leak rule, an ambiguity test, and a
calculation-topic exemption. ⚠️ SEASONS.md and `review.py` still describe the *old* Reversed
("prompt states the ANSWER; options are candidate QUESTIONS") — §C4. ⚠️ On a reversed
directive, `assign_blocks` skips the steady mechanic assignment entirely (only the `else`
branch assigns numeric/order/text) — §C4.

**Battleground (Friday, directive "boss"):** the two speed slots are normal recall warm-ups;
each steady slot is a claimable zone on a flagged weak topic, in the sharpest MC-family
format per zone — spot-the-lie / true-false / plain MC / sum-as-MC — varied across zones
(`planner._composer_instructions` boss brief; `review.py` has Battleground-aware verdict
mapping). ⚠️ The brief says "the four zones"; the boss shape gives **seven** steady slots —
§C5.

**Question schemas the composer must produce** (`compose.SYSTEM`; enforced by
`validate._check_ss_answer`):
- MC: `{prompt, options[≥2], answer∈options, why, fresh:bool}`
- swipe: `{type, prompt, left, right, answer∈{left,right}, why, fresh}`
- numeric: `{type, prompt, answer:NUMBER, calc:bool, pre, post, why, fresh}` + optional
  `frac:"a/b"` — the canonical fraction display form, deterministically checked for
  equivalence with `answer` by the validator (31 Aug 2026; review can't see numeric
  answers — §C7 — so the validator owns this). The shell accepts any equivalent typed
  form (`0.4` == `2/5` == `4/10`): both pads carry a decimal point and an a/b fraction
  key since 31 Aug 2026 (before that the MENTAL pad had digits only — a decimal answer
  on a mental slot was unanswerable, the second t1 live-fire catch).
- order: `{type, prompt, sequence[≥2, unique], top, bot, why, fresh}`
- text: `{type, prompt, accept[≥1 strings, accept[0]=canonical], why, fresh}`
- teach: `{prompt}` only.
Throwback questions must be `fresh:false` (validator error otherwise).

**State-writer weights** (the ledger rule per mechanic) are in §3 step 4: swipe = weak
50/50; numeric/order/text = typed, strong, capped at developing.

## 8. The two axes — confidence and depth (SOLO)

**Axis 1 — confidence (`state`)** drives **scheduling**. Fully implemented: §3 and §5.

**Axis 2 — depth (SOLO ladder, UNDERSTANDING.md)** drives **reporting**. Rungs:
`not_yet < knows < lists < connects < applies` (`grade_teachback.DEPTH_LADDER`).

**What's implemented today:**
- The nightly teach-back grader (`tools/grade_teachback.py`) returns BOTH axes per
  teach-back: `verdict` (solid/partial/none — consumed deterministically by the
  state-writer) and `depth` (a rung + a verbatim `evidence` quote), annotated onto the
  question in `runs.json` as `tb_grade`. A deterministic ceiling (`cap_depth`) lowers
  `connects`/`applies` to `lists` when the answer contains no linking language
  (`LINK_MARKERS`) — it can only lower, never raise. Non-English → verdict none,
  depth not_yet. Integrity is checked BEFORE grading: `grade_teachback.attach_integrity` +
  `tools/integrity.py` (deterministic authenticity signals — typing rate vs the kid's own
  baseline, register, US spellings, suspicious polish; verdicts ok/review/quarantine).
  Quarantined teach-backs are never sent for grading, never quoted, never credit depth.
- The Friday surfaces read `tb_grade.depth` from runs (`report_stories.pick_quote`,
  `build_stories` DEEPENED shape, `friday_report_run` depth snapshot).

**The separation law — confidence and depth never read each other:** holds in code. The
state-writer consumes only `verdict` (`state_writer.verdict_badge`); nothing on the depth
path reads `state`.

**What is NOT implemented (confirmed by trace — this is the SOLO gap):**
- **No code writes `depth` onto a ledger topic.** The live `state.json` has zero topics
  with a `depth` field. UNDERSTANDING.md §4's promotion/demotion rules
  (→knows on one correct, →lists on two facets, →connects on a relational teach-back,
  reluctant demotion) exist nowhere in code. Consequence: `friday_report_run`'s depth
  snapshot (`snap[code+"_depth"]`) is always empty, `report_stories.week_over_week` depth
  movement and the DEEPENED story that read *ledger* depth can never fire from the ledger
  (only the per-run `tb_grade.depth` inside `build_stories` can) — §C11.
- **The planner does not read depth.** UNDERSTANDING.md §3.4 ("the ladder is a planning
  instruction — schedule a teach-back on a `lists` topic") is unimplemented.
- **Transfer questions are not tagged**, so `applies` has no legitimate instrument
  (UNDERSTANDING.md §7 open item). Worse, the grader's `TEACH_CEILING = "connects"`
  constant is **dead code** — `cap_depth` only drops connects/applies to lists when there
  is *no* link language, so a teach-back containing any "because" can be graded `applies`,
  which §3 forbids — §C11.
- **Intake seeding of both axes** is not built.

## 9. Division of labour — deterministic code vs the LLM

**Deterministic code owns every decision** (the IP): the ledger and every transition
(`state_writer.py` — "no API, no language"), scheduling and topic choice (`planner.py` —
"no LLM, no network"), throwback selection (`throwback.py` — pure functions), the
answer-length gate (`answer_length.py`), teach-back integrity (`integrity.py` — "no model
judges a child's honesty"), badges (`achievements.py`), and set structure —
`compose.assemble` takes ids/phases/subjects/flags straight from the plan so the model
cannot drift the schema.

**The LLM does language only, and never holds state.** Exactly four call sites:
1. `compose.py` — writes question language to the plan's spec (default model
   `claude-sonnet-5`, override `DAILYXP_MODEL`).
2. `review.py` — the critic (a deliberately STRONGER model, default `claude-opus-4-8`,
   adaptive thinking at `DAILYXP_REVIEW_EFFORT=high`; override `DAILYXP_REVIEW_MODEL`).
3. `grade_teachback.py` — the one language judgement in ingestion (`claude-sonnet-5`,
   override `DAILYXP_GRADE_MODEL`); its output is consumed deterministically.
4. The comms dressers (`wed_checkin.compose_ai`, `friday_sms`, `kid_wrap.compose_coaching`)
   — code picks every fact; the model dresses sentences; a deterministic validator gates
   every body with redlined fallbacks behind it. The daily soundbyte and kid nudge are
   AI-free by construction.
(Plus a fifth, in-shell: the Supabase Edge Function `grade-teachback` for the live
three-light display — cosmetic only; the nightly grader remains authoritative. See
`DAILY-PUBLISHING.md` §7 and §C-ops.)

## 10. Composition & quality gates

**Compose (`tools/compose.py`, `compose_set`):** builds one user payload = the composer
instructions + the slot list + the student's full `already_seen_prompts` (from the private
history archive via `validate.seen_prompts`). The model returns per-slot language;
`assemble` stitches it onto the plan's structure; the result must pass `validate_set`, with
up to 2 retries feeding the exact validation errors back to the model. A FROZEN plan
returns the placeholder without any API call. Failure after retries → `(None, errors)` and
run_daily skips publish (yesterday's set stays live).

**Validate (`tools/validate.py`)** — the mechanical gate, run inside compose AND again
inside publish:
ERRORs (block): bad student code (vs `roster.students()`); missing date/day/tag on real
sets; missing id/phase/subject/prompt; per-type schema rules (§7); answer not exactly one
of options; missing `why`; missing/non-boolean `fresh` on speed/steady; throwback not
`fresh:false`; duplicate ids; **prompt repeats anything this student has ever been served**
(normalised match against `history/<student>/*.json` — the hard no-repeat gate);
**exactly ONE teach question** (the shell unconditionally enters the teach screen — learned
9 Aug). WARNs: non-standard shape (known shapes 12/6/1 and 2/7/1). Placeholder sets are
valid by design.

**Review (`tools/review.py`)** — the meaning gate the validator can't be. A stronger model
reads every question as a critic (never an editor) and returns per-slot verdicts in
categories: multiple_answers / factual_error / off_syllabus (judged against
`review.curriculum_context` — live + upcoming topics, with prior_term listed as legitimate
revision) / trivial / ambiguous, severity block or warn. Conservative by instruction: a
false block costs a child their quiz. Fail-safe: a slot the model forgot is held as warn,
never silently clean. The deterministic answer-length gate is applied on top (§6 LAW 1).
⚠️ Blind spot: `review.build_user` sends `options/answer/why` only for MC questions —
swipe/numeric/order/text are reviewed on their **prompt alone**, so a wrong keyed bucket,
wrong number, wrong sequence, or wrong accept-list is invisible to this gate (§C7).

**The recompose loop (`run_daily.run`):** on a BLOCK verdict, only the flagged slots are
recomposed — each with review's specific objection appended to its guidance ("REVIEW
REJECTED [category]: … fix exactly this") so compose doesn't retry blind; a teach slot is
borrowed for context if none was flagged (compose requires exactly one) and only the
flagged slots are swapped back. Re-review; at most `MAX_REVIEW_ROUNDS = 2` rounds; still
blocking → **HOLD** (not published; yesterday's set stays live; needs a human). Review
unavailable (API error / no verdict) → also HOLD, fail-safe. Emergency bypass:
`DAILYXP_SKIP_REVIEW=1` publishes unreviewed, loudly.

---

## Contradictions & gaps found (code vs docs, and code vs itself)

**C1 — SEEDED TOPICS ARE NEVER PERSISTED (critical; breaks the feedback loop).**
`run_daily.run` loads `state.json`, calls `seed_menu.seed_player` on the in-memory dict,
plans, and never writes the state back. Verified live 20 Aug: the on-disk ledger is missing
33 of y8's 49 menu topics, 56 of y9's 72, 40 of t1's 49, and no topic anywhere carries
`introduced_week`. Tonight's published y8 set (H4.4) tests seeded-only topics in **13 of 19
slots including the teach-back** — when those results are ingested, `state_writer.find_topic`
will not find the topics and will print "not in ledger — skipped": the answers will never
move the ledger. LAW 6's "seed on sight … instantly askable **and tracked**" is only half
true — askable yes, tracked no. Fix shape: after the seed loop, write `state.json` back
(and let the workflow's commit-private step carry it), or seed on disk before the writer
runs.

**C2 — `introduced_week` is write-only.** Stamped by `seed_menu`, read by no code. The
two-tier sort keys on the *latest scrape's live set* instead (`eligible_pool`). Either wire
the stamp into tiering/reporting or stop claiming (SEASONS LAW 6, the 20 Aug handoff) that
the stamp is what lets the planner tell this week from prior weeks. Related: only
`status:"live"` topics are ever seeded — `upcoming`/`not_yet_posted` topics are invisible
to the menu until they flip live (may be intended; not documented).

**C3 — Eligibility is broader than documented.** `planner.py`'s header ("only topics whose
subject is LIVE in targets") and the variable name `subject_live` are both wrong: the check
is "this topic tolerantly resolves to ANY target row of ANY status". prior_term topics are
eligible (score −8), which is how revision threads work — fine, but the doc should say so.

**C4 — Reversed has two conflicting definitions and a broken review hook.** The planner's
current brief (19 Aug): detail + category cue, options are short THING labels. SEASONS.md's
mechanics-bank entry and `review.py`'s SYSTEM prompt still describe the old form (prompt
states the ANSWER; options are candidate QUESTIONS). Additionally `review.py` only applies
its reversed-aware mapping when *the set tag contains "REVERSED"* — tags no longer carry
that suffix (only "· BATTLEGROUND" exists in `run_daily.derive_tag`), so if the dormant
reversed directive is ever used, the reviewer will judge reversed questions as normal MC
and likely mass-flag them. And `assign_blocks`' reversed branch skips the steady
numeric/order/text assignment (only the standard-day `else` branch assigns them).

**C5 — "Four zones" vs seven.** The Battleground composer brief and SEASONS.md both say
four claimable zones; `SHAPES["boss"]` gives 7 steady slots (+2 speed +1 teach). The shell
and validator accept 2/7/1. Decide the number and align the brief.

**C6 — LAW 1's run-level distribution rule neither blocks nor prints.** SEASONS.md LAW 1
(§3–4) and RUNBOOK.md claim the per-run skew "blocks a run" and that "review prints
longest-is-correct rate … watched every day". In code (`review.normalise`),
`run_distribution_violation` only populates `length_run_flag`/`length_audit`, which
`review.print_verdict` and `run_daily` never print, and `ok` ignores it. Only the per-slot
sole-longest gate actually blocks.

**C7 — The review gate cannot see non-MC answers.** `review.build_user` includes
options/answer/why only when a question has `options`. Swipe/numeric/order/text questions
— now most of every steady round — are reviewed on prompt text alone. A factually wrong
numeric `answer`, a wrong `order` sequence, a wrong swipe key, or a bad `accept` list
passes the meaning gate untouched (the validator checks only shape). This is the exact
fault class review exists for.

**C8 — validate/spec drift on question types.** `validate.py`'s docstring lists
`mc|numeric|text|cloze`; the code implements mc/swipe/numeric/order/text, has no cloze, and
has no explicit unknown-type error (an unknown type falls into the MC branch and fails on
"needs an options list" — works by accident). `SHELL-3.1-SPEC.md` (banner: SUPERSEDED)
specifies a different numeric schema (string answer + accept list) than what was built
(number + pre/post + calc), plus cloze/x2/encore that don't exist in the composer.

**C9 — Mechanic badges have no defined precedence.** `state_writer.PREC` omits
SWIPE✓/✗, NUM✓/✗, ORD✓/✗, TXT✓/✗; all rank 99, so when two mechanics hit one topic the
"governing" badge is insertion-order luck, and ANY listed badge — including a plain MC
`✓_plain` — outranks a typed-mechanic WRONG on the same topic (an MC correct silently wins
over a numeric miss). Probably not intended given "typed = strong evidence".

**C10 — LEDGER-RULES.md is partially stale.** The teach-back row was fixed mid-audit
(commit `2223bb9`, 20 Aug — the graded TB✓/TB~/TB✗ table now matches the writer). Still
stale: the precedence list omits SKIP✗ and all mechanic badges; "2nd CW on the topic" is
really *consecutive* last-result CW in code; and it doesn't mention that a wrong on an
`untested` topic moves it UP to shaky (the demotion floor).

**C11 — The SOLO/depth pipeline stops at runs.json.** No writer puts `depth` on ledger
topics (live state verified: zero), so the Friday depth snapshot is always empty and any
ledger-depth reporting can never fire; UNDERSTANDING.md §4's promotion rules and §3.4's
"ladder steers the planner" are unimplemented; transfer questions are untagged so `applies`
is unreachable legitimately. (Fixed 20 Aug: `grade_teachback.cap_depth` now enforces
TEACH_CEILING as a hard cap — `applies` can no longer escape a teach-back — and the
shadow depth writer (`tools/depth_writer.py`, landed same day) caps it independently;
UNDERSTANDING.md's ceiling table corrected per the reversed-is-not-transfer ruling.) Also `state_writer.verdict_badge` checks a
`grade["integrity_hold"]` key that nothing ever writes (the hold actually works by
quarantined rows never being graded) — harmless but misleading. Note: the 19-Aug SOLO
acting-end doctrine (LEDGER-RULES, commit `2223bb9`) ratifies the build order for the
depth writer (shadow mode → calibration → gate → live+backfill → planner targeting) and
rules that **reversed does NOT qualify as a transfer instrument (ceiling `knows`)** —
which now contradicts UNDERSTANDING.md §3's own ceiling table ("Reversed / transfer →
applies"). UNDERSTANDING.md needs that row corrected.

**C12 — CURRENT-STATE.md ("authoritative", 18 Aug) is now materially wrong.** It says the
typed mechanics, swipe, and the teach-back three-light display are dormant/not integrated;
since 19–20 Aug all four mechanics are live for all seats (`assign_blocks`; live sets
verified: today's y8 = 4 swipe / 9 mc / 2 text / 2 order / 2 numeric) and the three-light
display is live via the Supabase Edge Function. Its "the generator never emits these" claim
is false. (Hidden x2 and the encore genuinely are absent from the composer.)

**C13 — SEASONS.md carries a "SUPERSEDED" banner yet hosts current doctrine.** LAW 6
(ratified 20 Aug) and the LAW 1/3 mechanics live inside a file whose first line tells the
reader to ignore it. Same banner sits on SHELL-3.1-SPEC.md (correctly). Move the live laws
out or fix the banner.

**C14 — planner's `format_summary` is hardcoded** to "direct recall" even when a run is 4
swipe + numeric/order/text blocks — the plan log line under-reports what was planned.

**C15 — RUNBOOK.md stale items:** cites `tools/formats.py` + `test_formats.py` (deleted);
"standard run: 7 speed + 4 steady + 1 teach" (now 12/6/1); "every published speed/steady
question MUST carry fresh:true" (superseded by honest fresh + the universal skip); the
review "prints longest-is-correct rate" claim (see C6). SYSTEM-MAP.md's entire
"Built vs not built" section predates the comms/report builds and the mechanics rollout.

**C16 — compose's SYSTEM prompt says "two secondary-school boys"** while three seats (incl.
an adult) are composed for nightly. Cosmetic, but the model is being told the audience
wrong for t1.

## Open questions for Rich

1. **Seeding persistence (C1):** confirm the fix — write state.json back after seeding in
   `run_daily` (the commit-private step already carries it) — and whether to back-fill the
   results that will be skipped in the meantime.
2. **`introduced_week` (C2):** keep and actually use it (e.g. weight tier-2 toward recent
   weeks, per LAW 6's "weighted to recent weeks" clause — currently not implemented), or
   delete the stamp and the claim?
3. **Should `upcoming` topics seed** onto the menu (askable early) or stay invisible until
   live?
4. **Reversed (C4):** which definition is canonical — the planner's 19 Aug
   detail→label form, or SEASONS'/review's answer→candidate-questions form? And should
   review detect reversed by slot `mech` rather than by tag?
5. **Battleground zones (C5):** 7 steady zones (current shape) or 4 (the brief)? Pick one.
6. **LAW 1 run-level rule (C6):** should the distribution violation BLOCK (as the doctrine
   says) or stay advisory — and either way, wire the metric into the printed verdict?
7. **Review for mechanics (C7):** extend `review.build_user` to pass answer/sequence/
   accept/left-right for non-MC types so the critic can check them?
8. **Mechanic badge precedence (C9):** where should SWIPE/NUM/ORD/TXT sit in PREC —
   e.g. NUM✗/ORD✗/TXT✗ near ✗, SWIPE✗ near FW, NUM✓ near ✓_think, SWIPE✓ below ✓_plain?
9. **Depth-to-ledger (C11):** ratify the writer design for UNDERSTANDING §4 (which
   component writes `depth` onto topics — a depth pass inside `state_writer`, reading
   `tb_grade.depth` deterministically?) and whether to enforce the teach ceiling in
   `cap_depth` until transfer tagging exists.
10. **Untested + wrong → shaky:** intended (a miss makes an untested topic *higher*
    priority) or should untested hold on a miss?
11. **Docs cleanup:** approve retiring/banner-fixing CURRENT-STATE.md, SEASONS.md's banner,
    RUNBOOK's stale sections, LEDGER-RULES, and SYSTEM-MAP in favour of this document +
    `DAILY-PUBLISHING.md`.
