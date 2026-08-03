# Content intelligence model — how quizzes stay relevant and accurate

*The doctrine behind question generation. Companion to RUNBOOK.md (mechanics) and SWEEP.md (content capture).*

## The two-layer principle
**School LMS data = the targeting layer. Model knowledge = the substance layer.**
The classroom tells the system *what* to quiz and *when* it's live (current units, page sequence, what's posted vs frozen, assessment dates/formats). The substance of questions comes from stable curriculum knowledge — school-level content is commodity knowledge with official syllabus outcomes to aim at. The system never invents *what's being taught*; it supplies *the material for what's confirmed live*.

## Source fidelity ladder (use the highest rung available)
1. **Verbatim classroom content** — actual page bodies, a teacher's specific framing or angle (e.g. a named theory applied to a text). When captured, use it faithfully: matching the classroom's dialect is the highest-value material there is.
2. **Sweep-level structure** — unit/page titles, topic sequence, syllabus outcome codes, assessment types and dates. Sets targets and shapes formats.
3. **Syllabus knowledge** — the default ammunition: stable, state-curriculum-aligned subject knowledge at year level.
4. **Ledger state** — decides *which* targets get tonight's slots: repair queues, spacing schedule, confidence history, no-repeat rule.

## Accuracy rules
- **Sweep metadata drifts; corroborate before trusting.** Index-level reads mislabel dates and weeks. Treat topics as reliable, dates as approximate unless they match a second source (ledger, prior sweep, a human).
- **Answers must be uncontestable.** Exactly one clearly correct option; if a question needs a debate to defend, rewrite it.
- **Distractors encode real misconceptions** (the forgot-the-half area trap, the add-instead-of-multiply volume trap, the close-cousin fact). Wrong options should diagnose, not pad.
- **Every question re-teaches in its `why`.** A miss must leave the student knowing the answer and the reason.
- **Assessment format shapes question format.** If the class assessment is extract analysis, teach-backs rehearse extract analysis. Quizzing converges on how the student will actually be tested.

## Drift absorbers (when classroom ≠ model framing)
- **`fresh` flag** absorbs sequencing drift — anything class may not have reached is skippable, penalty-free, and benched for verification.
- **Reasoning-graded teach-backs** absorb wording drift — understanding scores, recitation doesn't.
- **The ledger is the drift detector** — repeated misses on topics the class has definitely taught signal a framing gap, and trigger escalation.

## Escalation path for depth
Sweep index → targeted depth pass (open the specific high-value pages, capture full bodies) → automated API page-body ingestion (token-based scheduler). Each rung raises fidelity; the doctrine above holds at every rung.

## Relevance guarantees
Only live/confirmed units get quizzed · every set is unique per student, built from that student's ledger · no question repeats · repair items get guaranteed slots until resolved.
