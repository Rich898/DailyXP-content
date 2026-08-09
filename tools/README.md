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

## ingest_results.py — limb #1 (headless): Sheet → runs.json

The cron can't read the results Sheet the way a chat session can. This fetches the rows from a
**token-gated, read-only** Apps Script `doGet` endpoint (a *separate* deployment — it never touches
the quiz `doPost` webhook) and refreshes `work/runs.json`. It reuses `results_reader` end to end
(parse payloads → normalise → dedupe → drop SYSTEM TEST → mark canonical → phase medians) and writes
the SAME JSON shape as `results_reader --json`, so nothing downstream changes.

- Endpoint returns `{"rows": [[header…],[row…]]}`; columns mapped by name, payload parsed per row.
- Config (Actions secrets, or `--url/--key`): `RESULTS_URL` (the `/exec`, no key) + `RESULTS_KEY`
  (matches the script's `INGEST_KEY`). Clear errors on unauthorized / non-JSON / empty-tab.
- Runs as step 0 in `run_daily` (gated on the secrets — skipped locally, uses committed runs.json).
- Public-log safe: prints counts and y8/y9 codes only — never names, scores, or payloads.

CLI: `RESULTS_URL=… RESULTS_KEY=… python3 tools/ingest_results.py --private-dir <priv>`.

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

## achievements.py — badge the ledger

Deterministic, idempotent, no AI — the same shape as the state-writer, run right after it. Reads
three event sources and awards any newly-unlocked badges, deduped against a private earned-ledger
so nothing fires twice: `runs.json` for run-shaped badges (First Blood, Clean Run, Boss Slayer,
Blitz Master, Perfect Week, Streak), `state_writer_log.jsonl` for transition badges (Locked It,
Comeback, Untouchable, Calm Hands, Sure Shot), and `state.json` for snapshot badges (Full Clear).
The 12-badge v1 set and its triggers live in **`ACHIEVEMENTS.md`**. Awarded badges feed the
in-quiz end screen and the kid dashboard. Writes `work/achievements_earned.json` (the badge
ledger, private) + `work/achievements_log.jsonl`. Public-log safe (y8/y9 codes + badge names
only). Env `DAILYXP_SKIP_ACHIEVEMENTS=1` bypasses. CLI: `python3 tools/achievements.py
--private-dir <priv> [--dry-run]`. Regression-tested (all 12 badge types + idempotency).

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

---

## soundbyte.py — the evening parent soundbyte (REASSURE)

The daily parent touchpoint from `REPORTING.md`, as its own evening poll job
(`evening-soundbyte.yml`, three polls 6:30/8:00/9:30pm Sydney). First poll that
finds today's run for a boy sends the parents ONE deterministic THREE-BEAT
line: did it + tonight's XP + a verdict closer (the ladder — flew / good
night's work / put in a shift / the set bit back — computed from score/max;
the ratio prints nowhere, the legend in `ONBOARDING.md` defines the words
once). No AI, no percentages, no running totals (Friday owns totals), streaks
under 2 omitted (a "1-day streak" whispers *the streak broke*), silence when
there's no run (absence of the text is the only "not done"
signal). Idempotent via `work/soundbyte_cursor.json` (private); send happens
BEFORE the cursor advances, so a failed send retries next poll. Reads
`runs.json` only — the 2pm pipeline stays the sole owner of the ledger.
Public-log safe (prints y8/y9 + status only; error detail goes to private
`work/soundbyte_last_error.txt`). Tests: `python3 tools/test_soundbyte.py`.
CLI: `python3 tools/soundbyte.py --private-dir ../DailyXP-private [--date
YYYY-MM-DD] [--dry-run]`.

---

## wed_checkin.py — the Wednesday midweek check-in (ACTIVATE + expectation-setter)

The midweek parent touchpoint (`wed-checkin.yml`, Wed 7:30am Sydney = cron
`30 21 * * 2` UTC). One SMS per kid to `parents:<code>`: an honest momentum
read from the SAME week-word engine Friday samples (Mon–Tue vs LAST week's
Mon–Tue, like for like — Wednesday can never contradict Friday), at most ONE
ask (a strength drawn out as a dinner-table question) and ONE five-minute
help action (repair-flag first, then shaky), the gap planted for Friday
("it's the one Friday's wrap will centre on"). Every text ends pointing at
Friday's wrap. Code picks every fact; the model dresses language only; a
deterministic validator gates all outgoing text (no digits, no %, no ratios,
never bare "behind", banned vocab, must name Friday) with the redlined
fallback voices behind it — an API blip can never silence the Wednesday or
push it off-law. Ledger topic names pass through `display_topic()` so raw
names ("Triangle area (½bh) / area recall") never leak into text. Idempotent
via `work/wed_checkin_cursor.json`; reads state.json + runs.json, writes only
its cursor. Public-log safe. Tests: `python3 tools/test_wed_checkin.py`.
CLI: `python3 tools/wed_checkin.py --private-dir ../DailyXP-private [--date
YYYY-MM-DD] [--dry-run] [--no-ai]`.

---

## kid_nudge.py — the 4pm "XP Daily is up" text

The daily kid nudge (`REPORTING.md` week-at-a-glance), decoupled from the 2pm
publish: at 4:00pm (school's out, phones back in hands) it fetches the SAME
raw URL the shell fetches, and only if the live set is verified as *today's*
(and not a placeholder) does it text — a review HOLD or frozen day texts
nobody, and the 2pm→4pm gap is the human-intervention window. Flavoured by the
weekly skeleton (⚡ Wed blitz, 🐉 Fri boss — mirrors `WEEKDAY_DIRECTIVE`;
change both if the skeleton ever changes). Stateless: reads the live URL,
sends, writes nothing. Tests: `python3 tools/test_kid_nudge.py`.
CLI: `python3 tools/kid_nudge.py [--student y8|y9] [--date YYYY-MM-DD] [--dry-run]`.

---

## roster.py + roster.json — the account structure

`roster.json` (repo root) is the single source of truth for WHO EXISTS. Codes
only — names arrive from private runs at runtime; phone numbers live ONLY in
Actions secrets, per seat: `MOBILE_MESSAGE_TO_<CODE>` (the kid's own phone)
and `MOBILE_MESSAGE_PARENTS_<CODE>` (that kid's parent set, comma-separated —
per-kid on purpose: different kids can have different parents, even in one
family). `targets_alias` lets a test player quiz another student's curriculum
(t1 → y8). Adding a player = one roster entry + two secrets + the two matching env lines
in the comms workflows (Actions can't wildcard secrets into env) + a seeded
state.json block + a stamped shell page; no *code* knows the student list.
The soundbyte sends per kid to `parents:<code>` with independent cursors — one
family's failed send never blocks or repeats another's.
