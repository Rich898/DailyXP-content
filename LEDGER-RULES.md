# Ledger transition rules — how a night's result moves a topic

This is the **promotion logic**: the deterministic rules `tools/state_writer.py` applies to
turn each night's results into ledger state changes. It is intentionally **legible, not
FSRS** — a box model with a confidence + pace overlay — because the ledger stays
human-editable and feeds parent reports. It encodes the rules already visible in the ledger
notes; change the table here and the writer follows.

## Two axes
**Knowledge box** (ordered): `untested(0) → shaky(1) → developing(2) → solid(3)`.
**REPAIR lane** (a flag, `repair:true`): a named/chronic weakness that gets a guaranteed
weekly slot until it *earns its way out* to `developing`. Layered on top of the box.

A topic moves **at most one box per run**. `solid` means *right across spaced reps with
confidence* — so it can only be reached by a confident, calm, **spaced** confirm, never in
one session.

## The signal per question
Read from `results_reader.classify()` (badge) + the raw `confidence`/pace. The shell already
labels each answer; the badges below are that doctrine, encoded.

### Negatives
| Badge | What it means | Box move | Notes |
|---|---|---|---|
| **CW** confident-wrong | "Sure" but wrong — fluency illusion, the priority class | → **shaky** (from any box) | **2nd CW on the topic → set `repair:true`** (chronic, self-invisible). Resets repair confirms. |
| **✗ / SW** considered- / slow-wrong | genuine gap, answered slowly | **demote one box** (solid→developing→shaky→shaky) | re-teach before re-test |
| **GW** guessing-wrong | honest "not sure" miss | **demote one box** | normal re-queue |
| **FW** fast-wrong | wrong because **rushed**, not because unknown | **box UNCHANGED** | pacing not knowledge; stays due, planner re-surfaces (the rush-profile signal). Resets repair confirms. |

### Correct-but-suspect — never promote
| Badge | What it means | Box move |
|---|---|---|
| **LUCKY** | correct but guessing | **unchanged** — re-queue |
| **TRIV✓** | correct but trivially fast | **unchanged** — on a weak/REPAIR topic this is *untested* evidence, not mastery. This is the "don't let a fast-correct promote it out" rule. Does **not** count as a REPAIR confirm. |

### Positives — promote, gated
| Badge + confidence | Box move | REPAIR confirm? |
|---|---|---|
| **✓ "Sure"**, calm (not fast/trivial) | promote one box; `developing→solid` **only if spaced** (prior test on an earlier day) | **Yes** — a calm confident hit is the exit signal |
| **✓ "Think so"** | promote to **developing** at most (never straight to solid) | No |
| **✓** plain (speed slot, no confidence) | promote to **developing** at most (solid needs a steady "Sure") | No |

### Not a test
- **SKIP** (fresh-skip): not tested — no box change, `times_seen` **not** incremented, benched intel.

### Teach-back (graded nightly)
Teach-backs are graded overnight (`tools/grade_teachback.py`); the verdict has a
real box consequence, applied deterministically by the state-writer:

| Verdict | Box consequence | On REPAIR |
|---|---|---|
| **TB✓** explained it well | promote one box; `developing→solid` only if spaced and no repeat-attempt caveat | counts as a confirm (1 of 2) |
| **TB~** partial explanation | `untested→developing` only; otherwise held — a landing, never a promotion | held; confirms untouched |
| **TB✗** couldn't explain it | no promote, holds the box — and it outranks a correct multiple-choice on the same topic that night, blocking that promotion (the fluency-illusion catch). Never demotes. | held; confirms reset |
| **TB** ungraded, or integrity hold | no box change — a grader failure or unattributable text has no ledger consequence | held |

This verdict touches only the confidence box. Depth — the second axis — is
governed by `UNDERSTANDING.md` and never moves from a verdict.

## The REPAIR lane
A topic with `repair:true`:
- **Exits** to `developing` (`repair:false`) after **2 calm confident confirms** (`REPAIR_EXIT_CONFIRMS = 2`) — "keep REPAIR one more cycle to confirm calm holds." One calm ✓"Sure" → `repair_confirms = 1` (holds, "confirm 1/2"); the second → out.
- **Any** wrong, fast-wrong, lucky, or trivial-correct **resets** `repair_confirms` to 0. A REPAIR topic never exits on a rushed or lucky correct.
- **Enters** automatically on the **2nd confident-wrong** on a topic. (A human can also set `repair:true` by hand; the writer respects it.)

## Combining multiple slots on one topic
A topic can be hit by >1 question in a run (e.g. variables in a speed **and** a steady slot).
Take the single **governing** badge by severity:
`CW > ✗/SW > GW > FW > LUCKY > TRIV✓ > ✓"Sure" > ✓"Think so" > ✓plain`.
So a confident-wrong anywhere overrides a correct elsewhere — conservative and correct
(if it's confidently wrong in one place, it isn't fixed).

## Bookkeeping per tested question
`times_seen += 1`; `last_tested = run_date`; write structured `last_result`
`{date, badge, ok, confidence, pace}`. **The human `note` is never overwritten** — qualitative
judgement stays human/LLM-authored. Every change is appended to
`work/state_writer_log.jsonl` with its reason (audit trail). Runs are processed once
(idempotency cursor in `work/state_writer_cursor.json`); only **canonical, non-test** runs count,
and `attempt > 1` canonical carries a caveat (weaker signal — promotes are held to
`developing`, never `solid`).

## Tunables (top of `state_writer.py`)
`REPAIR_EXIT_CONFIRMS = 2` · pace fractions inherited from `results_reader`
(`FAST_FRAC`, `TRIVIAL_FRAC`, `SLOW_FRAC`, `MIN_BASELINE_N`).
