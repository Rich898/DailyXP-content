# UNDERSTANDING.md — the depth ladder

**Status: ratified (11 Aug 2026).** The second axis of the ledger. `SEASONS.md`
owns rhythm, `CONTENT-MODEL.md` owns what we teach, `REPORTING.md` owns what we
say. This file owns **how well a student understands a topic**, and it governs
the planner, the grader, and the Friday report alike.

---

## 1. Two axes, not one

The ledger now carries two independent readings per topic. Conflating them is
the single most likely way to break this system.

| Axis | Field | Question it answers | What it drives |
|---|---|---|---|
| **Confidence** | `state` | *How sure are we he knows it, and when should we re-test?* | **Scheduling** — spaced repetition, REPAIR, boss selection |
| **Depth** | `depth` | *How well does he understand it?* | **Reporting** — what we claim to a parent; what the planner asks next |

They are orthogonal, and the gap between them is the whole reason this project
exists. A student can be **solid** (confident, consistently right) at **can list
it** (shallow) — confidently shallow. That is precisely the school-report
finding that started XP Daily: *strong surface recall, weak evidenced
explanation under exam pressure.* One axis alone cannot see it:

* Confidence alone says "he's got it" — and is wrong about what "it" is.
* Depth alone loses the scheduler its input (depth moves slowly; re-test timing
  needs recency and consistency).

**Law: `state` never reads `depth`, and `depth` never reads `state`.** They are
written by different evidence and consumed by different surfaces. This law binds
the ledger **writers**. The planner is a consumer and legitimately reads both
axes — confidence to schedule, depth to choose what to ask next.

---

## 2. The ladder

Grounded in the **SOLO taxonomy** (Biggs & Collis, 1982 — Structure of Observed
Learning Outcomes), which we chose over Bloom's because it grades *observable
outcomes* rather than inferred internal processes, and because it separates
**depth of knowledge from difficulty** — a hard question and a deep question are
not the same thing.

We publish it in our own words. The SOLO column is internal and for credibility
with teachers; **parents and kids only ever see the left column.**

| Our words (`depth`) | Internal | Meaning |
|---|---|---|
| **Not yet** (`not_yet`) | Pre-structural | Answer misses the point, or no correct evidence yet |
| **Knows it** (`knows`) | Uni-structural | One right idea, one facet of the topic |
| **Can list it** (`lists`) | Multi-structural | Several parts right, but held separately — unjoined |
| **Can connect it** (`connects`) | Relational | Explains how the parts relate; causal, integrated |
| **Can apply it elsewhere** (`applies`) | Extended abstract | Uses it in a context it wasn't taught in |

Wording is **fixed**. Not "mastered", not "level 3", not "relational" — those
either overclaim or need explaining. If a surface needs a verb, use the phrase
as-is: *"he can connect it"*.

---

## 3. What can evidence what — THE CEILING LAW

This is the load-bearing rule. **A question type can only evidence the rungs it
is capable of probing.** Grading above a question's ceiling is a false claim
about a child's understanding, and is forbidden.

| Question type (phase) | Ceiling | Why |
|---|---|---|
| **Speed MCQ** (`speed`) | `knows` | Four options ⇒ ~25% guessable; one facet; no reasoning shown |
| **Steady MCQ** (`steady`) | `lists` | Harder, confidence-paired, multi-facet across a set — but still recognition, not explanation |
| **Teach-back** (`teach`) | `connects` | Free text; the only place relational reasoning is visible |
| **Reversed** (`mech: reversed`) | `knows` | Recognition in reverse — "here's the answer, name what it belongs to" is still recognition, whatever day it runs |
| **Transfer** (future, tagged) | `applies` | Not yet built. Requires a deliberately designed, explicitly tagged question type ("given the area, find the width"); until it exists, `applies` is unreachable — which is honest |

Consequences, all binding:

1. **MCQs alone can never push a topic past `can list it`.** A student who has
   only ever answered multiple choice on a topic is capped there, however many
   he gets right and however confident he is. The report must not imply more.
2. **Only a teach-back can move a topic to `connects`.** We run roughly one or
   two a night, so depth moves *slowly* — weeks, not days.
3. **Only a transfer question can move a topic to `applies`.** These must be
   deliberately planned; they don't occur by accident. The teach-back path to
   `applies` is closed in code (`cap_depth`, 20 Aug 2026), not just in doctrine.
4. **Therefore the ladder is a planning instruction, not just a label.** If a
   topic sits at `lists` and we want to know whether he can connect it, the
   planner must *schedule a teach-back on it*. The next rung dictates the next
   question type.

---

## 4. Promotion and demotion rules

Depth is **evidence-gated and slow**. It is not a running average.

**Promotion** requires evidence at the rung being claimed, from a question type
whose ceiling reaches it:

* → `knows` — one correct answer on the topic at any phase.
* → `lists` — correct on **two or more distinct facets** of the topic across
  different runs (not the same question twice). Operationally: correct on two
  **different question prompts** on the topic, on two **different run dates**.
* → `connects` — a teach-back graded as relational: the answer **links** ideas
  (cause→effect, part→whole, comparison), not merely enumerates them.
* → `applies` — correct on an explicitly **tagged transfer** item ONLY. A
  teach-back can never evidence `applies` — the ceiling is HARD, enforced at the
  instrument (`grade_teachback.cap_depth` caps any `applies` verdict at
  `connects`) and again in the depth writer. (No transfer item type exists yet
  — see §3 — so `applies` is currently unreachable, which is honest.)

**What counts as evidence.** Only a **clean correct** evidences depth. Lucky
corrects, trivially-fast corrects, and integrity-held answers never count. A
swipe (a 50/50 sort) never evidences depth on its own.

**Seeding.** Depth is never seeded from intake material — not from school
reports, not from teacher comments. A report grade cannot distinguish `lists`
from `connects`, so a seeded rung would be a claim with no evidence behind it.
Intake material may seed the **confidence** axis only. Every rung a parent ever
sees was earned inside the system.

**Demotion** is deliberately reluctant:

* Depth **never demotes on a single wrong answer.** A slip is a slip; the
  confidence axis (`state`) already handles wobble, and that's its job.
* Depth demotes **one rung** only on repeated failure *at that rung's own
  evidence type* — e.g. two consecutive teach-backs on a `connects` topic that
  come back merely listing.
* A `REPAIR` flag on the confidence axis does **not** demote depth. He may still
  understand it well and simply be out of practice — that's exactly the
  distinction the two axes exist to preserve.

**Under-claim rule.** Where evidence is thin or ambiguous, record the **lower**
rung. Every rung on this ladder is a claim about a child that a parent may repeat
to a teacher. We would rather be quietly right than confidently generous.

---

## 5. How depth appears in reporting

Governed by `REPORTING.md`'s no-ammunition law, with these additions:

* **Movement is the story, position is the context.** "Moved from listing the
  causes to explaining why they mattered" beats "is at 'can connect it'."
* **Never a bare rung as a verdict.** `not_yet` never appears alone; it appears
  with what will be asked next.
* **Never a rung as a label for the child.** Depth attaches to a *topic*, never
  to a person. "He's a 'can list it' kid" is a banned construction.
* **Name the ladder's source once, in the footer, never in the body.** Parents
  get the four phrases; the credibility line ("based on the SOLO taxonomy, a
  standard framework for assessing depth of understanding") lives in reading
  notes for the parent who wants to check we didn't invent it.
* **Week 1 shows the bottom rungs and says so.** Since MCQs cap at `lists` and
  teach-backs are sparse, an early report that showed lots of `connects` would
  be lying. Under-claim, and explain *why* the ceiling exists if it's visible.

---

## 6. Grader implications (`grade_teachback.py`)

The teach-back grader becomes the instrument that reads depth, so its rubric
must grade **structure, not correctness alone**:

* Does the answer state one thing (`knows`), several unlinked things (`lists`),
  or link them into an explanation (`connects`)?
* Linking markers are the signal: *because, so, which meant, whereas, this led
  to, the difference is*. Enumeration markers (*also, and, another*) without
  linkage indicate `lists`.
* Correct-but-shallow is a real and common result: a factually right answer that
  merely enumerates is `lists`, not `connects`. **Grading it higher because it
  is correct is the single most likely failure mode of this rubric.**
* Grader output is a **rung plus the evidence phrase** that justified it, so the
  claim is auditable and the calibration dial is visible.
* The grader is LLM-run and therefore **language only**: it returns a rung; the
  deterministic state writer decides whether that rung promotes the ledger,
  applying the rules in §4.

---

## 7. Open

* Rubric calibration against real teach-backs before depth is shown to the
  family. The gate covers **every family-facing surface**, the kid wrap
  included — until calibration passes, no rung renders anywhere; the kid page's
  teach-back stamp waits with the rest.
* A genuine transfer question type — designed, explicitly tagged at generation,
  accepted by the validator, recognised by the state writer — is its own future
  build. Reversed does not qualify (§3).
* Confidence is currently captured on the steady phase only — calibration
  (confidence vs correctness) is a *third* reading and is not part of this
  ladder; it stays out until instrumentation is even.
