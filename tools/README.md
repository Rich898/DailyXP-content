# tools/ — scheduler limbs (assisted-manual mode)

## results_reader.py — limb #1: the morning read

Replaces the by-hand reading of the results Sheet. Stateless, no network, no
secrets: it parses a *saved dump* of the Sheet and prints the morning summary.

**Morning-go workflow (in-chat):**
1. Claude reads the results Sheet via the Drive connector (`read_file_content`,
   fileId held in the private handoff doc — never in this repo).
2. Save the connector output verbatim to a local file (e.g. `work/sheet_dump.md`).
3. `python3 tools/results_reader.py work/sheet_dump.md --since <last-ledger-date>`
4. Apply the emitted ledger implications to the private mastery ledgers by hand
   (the reader deliberately does not write ledgers — see BUILD-results-reader.md).

Accepts either the connector's markdown-table dump or a CSV export with columns
`received_at, student, quiz_date, day, attempt, score, payload_json`.

**What it encodes (doctrine, see BUILD brief + CONTENT-MODEL + ABSENCE):**
- Dedupe by (student, ts); retry-taps post exact duplicates.
- SYSTEM TEST rows ignored.
- Canonical run per set = lowest attempt then earliest ts; a lone attempt>1 is
  canonical-with-caveat (contamination possible).
- Timing invariant check (active ≤ elapsed); phase sums printed.
- Kid-relative speed flags per phase (fast ≤50% / slow ≥180% / trivial ≤35% of
  the student's own median, min 4 samples) — printed alongside the shell's
  fixed-cutoff flags; raw seconds always shown so a human can overrule.
- Four-way wrongness: confident-wrong ≠ guessing-wrong ≠ slow-wrong ≠
  fast-wrong → four different ledger responses.
- Correct-but-trivially-fast on a known weakness = UNTESTED, not mastered.
- Lucky guesses never promote. Fresh-skips are benched intel, never misses.
- Absence is neutral: a student with no runs in the window gets a calm note,
  not an alarm.
- Cross-run signals: repeat confident-wrong in a subject, and subject misses
  across ≥2 runs (ledger-as-drift-detector escalation).

`--json out.json` writes normalised runs + per-student phase medians for the
next limb (question composer).

**Not in scope (by design):** composing questions (limb #2), cron/API
autonomy (limb #3), writing ledger files.

Repo law reminder: no results data, no names, no secrets in this repo — the
reader takes names from the payload at runtime and nothing here hardcodes them.

---

## validate.py — the publish gate

Hard checks before any set goes live (ERROR blocks, WARN informs): schema;
every question has id/phase/subject/prompt; speed/steady have options(≥2) +
answer∈options + `why` + `fresh:true`; no duplicate ids; and **no prompt the
student has already seen** (checked against the private `history/` archive).
Placeholders (`status:"placeholder"`, empty questions) validate as the no-quiz
state. Importable: `from validate import validate_set → (errors, warns)`.

## review.py — the SECOND-PASS review gate (the eyes the validator isn't)

The validator is mechanical — schema, answer∈options, no-repeat. It waves through a
question whose keyed answer is right but whose *other* options are also defensible, whose
`why` teaches something false, that's off-syllabus, or that's trivially easy. `review.py`
is the critic for exactly that class: it reads each composed set with a **stronger model
than compose** (default `claude-opus-4-8`, adaptive-thinking on — the reasoning is what
lets it recompute a `why` and notice it's wrong) and returns a per-slot verdict:
`clean` / `flag` + severity (`block`|`warn`) + category + a one-line note.

Categories: `multiple_answers`, `factual_error`, `off_syllabus`, `trivial`, `ambiguous`.
Severity law: any multiple-true, any factual error, and clear off-syllabus are **block**
(must not go live); mild stuff is **warn** (publish, but worth a glance). It is told to be
conservative — a false block costs a kid their quiz — so borderline → warn, not block.
Prior-term topics (spaced-repetition revision) are **on-syllabus** and never off_syllabus.
Teach-back slots are judged for factual soundness + clarity only.

It is a CRITIC, not an editor — it never rewrites. The recompose-or-hold loop lives in
`run_daily`: on a block it rebuilds only the flagged slots (a reduced plan through
compose, seeded so the new slot can't collide with kept siblings) and re-reviews; still
blocking after `MAX_REVIEW_ROUNDS` (2) → HOLD, leaving yesterday's set live. Fail-safe: if
the reviewer can't return a verdict at all, that's a HOLD too (unknown safety ≠ publish).

`review_set(cset, curriculum=…) -> (verdict, error|None)`; `curriculum_context(targets,
student)` builds the compact live+revision context for the off-syllabus check. Env knobs:
`DAILYXP_REVIEW_MODEL`, `DAILYXP_REVIEW_EFFORT` (default `high`), and
`DAILYXP_SKIP_REVIEW=1` for an emergency bypass. CLI: `python3 tools/review.py <set.json>
[--targets <week>.json]` (exit 0 = pass, 1 = hold, 2 = error).

## planner.py — limb #2a: the scheduler BRAIN

Deterministic, no LLM, no network. Reads the private `targets/<week>.json`
(what's LIVE in class + assessment dates) and the private `work/state.json`
(per-topic state + per-boy ACTIVE/FROZEN) and emits a **set plan**: N slots
tagged subject/topic/intent/fresh, plus a composer-instruction block. That
block is the LLM contract — identical in-chat now and via API at limb #3, so
nothing here is throwaway.

Doctrine enforced in code:
- **FROZEN student → empty plan.** The ABSENCE gate lives in the scheduler, not
  in a human remembering a kid is sick.
- **REPAIR topics guaranteed a slot** (placed in steady so confidence is
  captured); a fast-correct never promotes them out.
- Eligibility = subject LIVE in targets (+ REPAIR / prior-term threads).
- Priority: REPAIR > shaky > developing(spacing-weighted) > untested-if-fresh >
  solid(maintenance). Spacing uses `last_tested`.
- **Assessment-aware:** a subject with an assessment inside the horizon gets
  boosted, and the assessment *format* shapes the teach-back.
- Day directive reshapes: `standard` 7/4/1, `blitz` 10/2/1, `boss` chain,
  `light <subject>` = global cap of one slot (post-test days).
- Tolerant topic join (exact→substring→stem) survives wording drift between the
  two files — but canonical topic IDs shared by both is the proper fix (the moat).
- Thin live pool → `⚠ POOL` shortfall warning instead of padding.

`--json plan.json` writes the plan for the composer step.

## state_writer.py — limb #2b: the RETURN LEG (results → ledger)

The other half of the loop. planner reads state; this **writes** it. Deterministic,
no LLM, no network. Takes the results (`work/runs.json`), the persisted plan for each
run (`plans/<student>/<set_date>.json` — the join from question→topic, since a result
carries id+subject but not topic), and current `work/state.json`, and applies the
transition table in **`LEDGER-RULES.md`**:

- Box model `untested→shaky→developing→solid` with a **REPAIR** lane (a flag, not a box).
- Verdict per question comes from **`results_reader.classify()`** — one source of doctrine,
  not re-implemented here: CW→shaky (2nd CW→REPAIR), ✗/SW/GW demote one box, **FW leaves the
  box unchanged** (rush ≠ gap), LUCKY/TRIV✓ never promote, ✓"Sure" calm+**spaced** is the only
  route to `solid`, ✓"Think so"/plain cap at `developing`.
- **REPAIR exits** after 2 calm confident confirms; any wrong/fast/lucky/trivial resets the count.
  A fast-correct never promotes a REPAIR topic out (the whole point of the chronic cases).
- Multi-slot same topic → governing badge by severity precedence.
- **Human `note` is never overwritten** — the writer moves structured fields, adds a factual
  `last_result`, bumps `times_seen`/`last_tested`. Every change is appended to
  `work/state_writer_log.jsonl`. Idempotent via `work/state_writer_cursor.json` (only canonical,
  non-test runs, processed once); `attempt>1` canonical caps promotions at `developing`.

Runs first inside `run_daily` (state current before planning), dry-run-aware. Env
`DAILYXP_SKIP_STATE_WRITE=1` bypasses. CLI: `python3 tools/state_writer.py --private-dir <priv>
[--dry-run]`. Transition table regression-tested (10/10 doctrine cases). The one piece still
manual is **ingestion** — refreshing `runs.json` from the Sheet (see scripts/README Stubs #1);
the writer no-ops on a stale runs.json until then.

## publish.py — limb #1.5: the ONE atomic publish

Replaces hand-editing `y8.json`/`y9.json` (the path that caused the 5 Aug
rollback). Five steps: **VALIDATE → WRITE → ARCHIVE** (to `history/`, feeds
no-repeat) **→ COMMIT+push → VERIFY**. Verify fetches the raw URL the shell
fetches and asserts the live tag equals the intended tag; a silent overwrite,
cache, or wrong-branch push now fails LOUD in the same call. Token from
`GH_TOKEN` or `~/.ghtoken`. `--no-push` = local dry run (validate+write+archive).

---

### Private companions (NOT in this repo — see .gitignore → private repo)
- `work/state.json` — machine twin of the ledgers (per-topic state, per-boy status).
- `work/runs.json` — normalised results (the state-writer's input).
- `plans/<student>/<set_date>.json` — the persisted plan per run (slot→topic); the
  state-writer's join from a result question back to its topic.
- `work/state_writer_cursor.json` / `work/state_writer_log.jsonl` — the writer's
  idempotency cursor and per-transition audit trail. Carry scores/timing → private.
- `targets/<week>.json` — curriculum targeting layer (topic/status/fresh/assessment).
- `schedule.json` / `SCHEDULE.md` (+ `tools/schedule_build.py`) — the permanent
  completion record with the DONE / DONE-LATE+n / MISSED / NOT-PUBLISHED / ABSENT
  vocabulary. Carries scores + names → private.
- `publish_log.jsonl` — per-publish audit trail.

**Note going forward:** keep names OUT of published set `title` fields (legacy
sets had them). The shell renders the title publicly — a neutral title like
"DailyXP · Wed Blitz ⚡" is fine.
