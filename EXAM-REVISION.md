# EXAM REVISION — source of truth

**Status:** DRAFT for Rich's approval (2026-11-25).
**Scope:** The exam-revision system only. This is a *separate* system from the daily
DailyXP game (`QUIZ-GENERATION.md`). See §1.

---

## 1. Two systems, one repo

DailyXP now runs **two** quiz systems. They share nothing except this repo and Supabase.

| | **Daily Quiz** (DailyXP game) | **Exam Revision** (this doc) |
|---|---|---|
| Purpose | Build & hold knowledge over time | Intensive revision before real exams |
| Cadence | Every day, short (~5–10 min) | On demand, in an exam block (~45 min) |
| Coverage | The whole curriculum, spaced | The specific subjects being examined |
| Style | Gamified (swipe/speed/teach-back) | **Mirrors the real exam paper** per subject |
| Marking | Game mechanics | **AI-graded, partial credit** (§6) |
| Source of truth | `QUIZ-GENERATION.md`, `SEASONS.md` | **this file** |
| Data | `roster.json`, `y9.json`, menu/ledger | `revision/*.json` blueprints + Supabase |

**When to use which:** daily quizzing → the daily game. Preparing for a named exam →
the exam system. Do not fold one into the other.

---

## 2. Data model

**Supabase project** `ftknumgdmalxyjxvqlux`. Tables:

- **`revision_quiz`** — the live set. Exactly ONE `active=true` row per student.
  Columns: `student`, `day` (label, e.g. `day36`), `title`, `intro`,
  `questions` (jsonb array), `active`, `updated_at`.
- **`revision_runs`** — a completed sitting. `payload` jsonb holds
  `{student, day, part, total, n, duration_seconds, answers[], bySubject, ts}`.
  Each answer: `{s, t, correct, coach (verdict), text (what they wrote), ...}`.
- **`revision_reteach`** — the Part-2 top-up set (on-conflict `(student,day)`).

**Question JSON schema** (one object per question):
```
{ "s": subject, "t": "mc" | "short" | "tb", "q": prompt, "src": "<source ref>", ... }
  mc:    + "opts": [...], "a": <correct index>, "e": "<why>"
  short: + "keys": [...]  (OPTIONAL rescue only), "model": "<model answer>"
  tb:    + "model": "<model answer>"     (extended written response)
```
`teach` cards exist only in Part-2 reteach, never in Part-1 practice.

**Delivery:** per-student static page on Netlify reads the active row over the REST API
and posts runs back. Roshan → `comfy-gnome-ab3891.netlify.app`. The AI grader is the
Supabase edge function `coach`. Page + function sources are versioned here (§8).

---

## 3. The one principle

> **Everything the student sees must trace to their real exam and their real materials.**
> The questions, the format, and the mark must all be things their teacher would recognise.

Every LAW below exists because this principle was broken at least once, in chat, and it hurt.

---

## 4. THE LAWS

Each law names the real incident that motivates it and where it is enforced.

### LAW E1 — Exact materials only (no invention)
Every question must be grounded in the student's own uploaded materials (Canvas pages,
teacher revision sheets, sample papers, model answers). Each question carries a **`src`**
field naming where it came from. A question that cannot cite a source does not ship.
- *Why:* twice I built from generic/textbook content instead of his Canvas material — the
  English revision (wrong booklet) and the Science "Skills" questions (invented sugar /
  fertiliser / reaction-table scenarios). Both felt "not like the exam" because they weren't.
- *Enforced:* `tools/validate_revision.py` rejects any question with no `src`; blueprint (§5)
  carries the source map.

### LAW E2 — Match the real exam format, per subject
Each subject's section structure, mark split, question **types**, and **whether it has
multiple choice** are defined in the student's blueprint (§5) and MUST be honoured. One
subject's format never bleeds into another.
- *Why:* I treated all three subjects alike. Reality (Roshan, Year 9): **Science** 70 marks,
  Part A/B short+extended + **Part C Skills 20**, **no MC**; **History** 25 marks, short
  written answers, **no MC**; **Geography** 30 marks, **Section I MC (10)** + Section II
  short answers (20). Serving Science as recall quizzes, or Geography with no MC, is a LAW E2
  break.
- *Enforced:* `validate_revision.py` checks the set's type mix against the blueprint's
  per-subject format (e.g. blocks `mc` in a no-MC subject; requires a Skills strand for
  Science).

### LAW E3 — MC fairness (inherits daily LAW 1)
When a subject does use multiple choice, the correct option must not be identifiable by
position or surface feature. Across a set: correct answers spread over A/B/C/D; no single
letter dominates; the correct option is **not** the sole-longest (per-question) and
sole-longest-correct share ≤ 34% (per-set). Same rule as `SEASONS.md` LAW 1 / `QUIZ-GENERATION.md` §6.
- *Why:* an earlier set had **every** correct MC answer = option A.
- *Enforced:* `validate_revision.py` runs the position-distribution and length-tell checks.

### LAW E4 — One question, one judgement (no multi-part)
No question may bundle multiple parts (a/b/c) into a single graded item, because the grader
returns one verdict for the whole thing and a correct part-b is thrown away when part-a slips.
Split each part into its own question (or a short multi-mark item the grader is told to
part-credit — see E5).
- *Why:* Roshan wrote a correct trend **and** a correct interpolation but mislabelled part (a),
  and the whole question scored 0. Repeatedly.
- *Enforced:* `validate_revision.py` flags a `q` that contains "(a)" and "(b)" patterns.

### LAW E5 — Partial-credit marking
A substantially-correct answer must never score zero. The grader returns `got_it` / `partly`
/ `not_yet`; these map to **full / half / none**, and the half counts toward the displayed
score. Marking judges **substance and ideas**, and is lenient on wording, spelling, order and
notation (a right answer phrased differently is right).
- *Why:* my scoring counted `partly` as 0. Roshan earned an exam-equivalent ~13–14/20 but was
  shown **8/20**, which read as "getting worse" and was demoralising. Earlier, over-strict
  keyword matching marked correct-but-reworded answers wrong.
- *Enforced:* `coach` edge-function prompt (substance-over-wording, generous tie-break) +
  page tally (`got_it`=1, `partly`=0.5, `not_yet`=0). Documented in `revision/MARKING.md`.

### LAW E6 — Honest, encouraging score
The number shown to the student must reflect real exam-equivalent performance (a consequence
of E5). Never inflate to flatter, never deflate by technicality. The read-out to Rich reports
the same honest number plus what was genuinely right/wrong.

### LAW E7 — Don't fake what the medium can't do
Some exam tasks (draw & label a fault diagram, graph data with CUTLAS on paper, annotate a
figure) cannot be done in a text box. Do not shoehorn them into a typed answer and pretend.
Either reframe honestly ("explain how you would set up the axes / what the graph would show")
or mark them as paper-only in the blueprint and leave them out.
- *Why:* the "which graph would you draw, describe it in a textbox" questions felt artificial.

---

## 5. The blueprint (`revision/<student>.json`)

The per-student source of truth a session is **built from** (never improvised around).
Shape:
```
{
  "student": "roshan",
  "year": "Year 9",
  "page_url": "comfy-gnome-ab3891.netlify.app",
  "subjects": {
    "Science": {
      "exam": { "time_min": 80, "marks": 70, "multiple_choice": false,
                "sections": [ {"name":"Part A — Chemistry of New Substances","marks":25,"style":"short + extended"},
                              {"name":"Part B — Global Patterns","marks":25,"style":"short + extended"},
                              {"name":"Part C — Skills","marks":20,"style":"short, applied"} ] },
      "sources": ["e4e13da9-Year9_Yearly_Exam_Study_Pack.md §1", "cfb2852f-Roshan_Y9_Revision_Extract.md §SCIENCE"],
      "bank": [ { "topic":"Conservation of mass (open/closed)", "src":"...", "ask":"...", "model":"..." }, ... ],
      "paper_only": ["draw & label the 3 fault types", "graph data with CUTLAS"]
    },
    "History": { ... },
    "Geography": { ... }
  }
}
```
The `bank` is distilled from the real teacher revision sheets / sample papers (e.g. the
Science conservation-of-mass and seafloor calculations, the solubility list; the Geography
Canvas practice-exam MC; the 8 WWII-Pacific History topics). A session samples from the bank,
honours each subject's `exam` format, and copies each item's `src`.

---

## 6. The marking system

- Grader: Supabase edge function `coach`, model **`claude-sonnet-5-5`** (one-line `MODEL`
  const), `effort: low`, `max_tokens: 1024`. Prompt grades substance, ignores
  wording/spelling/order, tie-breaks generous. Returns `{verdict, good, improve}`.
- Page scoring: `got_it`=1, `partly`=0.5, `not_yet`=0; MC auto-marked by position; a short
  answer whose `keys` match is an instant full mark (rescue only, never a false pass on
  multi-point questions — those omit `keys`).
- **Grader health:** the function must not silently fall back. If the Anthropic call fails it
  returns `fallback:true`; a health check (§7) alarms if live grading is returning fallback.
  *Why:* the grader ran on a dead API key for days, silently self-marking everything "fine."

Full detail in `revision/MARKING.md`.

---

## 7. Build & verify workflow

Every time a set is loaded (by hand or by the loader trigger):
1. **Read** `EXAM-REVISION.md` + `revision/<student>.json`.
2. **Compose** the set by sampling the bank, honouring each subject's format (E2), MC fairness
   (E3), single-focus (E4), copying `src` (E1).
3. **Validate** with `tools/validate_revision.py` — must pass, or do not write.
4. **Write** the single `active` row (fresh `day` label to avoid stale state).
5. **Verify** live: the page renders the set, MC options show, and a test fetch returns it.
   Confirm the grader returns a real verdict (not fallback).
6. Never advance a student's day unless a Part-1 run exists for the current day (the guard).

---

## 8. Versioned artifacts & deployment

These stop living only in chat:
- `revision/pages/roshan.html` — the quiz page (source of the Netlify drop).
- `revision/coach/index.ts` — the grader edge function.
- `revision/MARKING.md` — the marking spec.
- `revision/roshan.json` — the blueprint.
- `tools/validate_revision.py` — the gate.
- `RUNBOOK.md` gets an "Exam revision" section: how to redeploy the page (Netlify drop) and
  the function (Supabase), and how to pause/rewire the triggers.

Changes land as commits on the dev branch, reviewable — not blind drag-and-drop.

---

## 9. Scheduled tasks (triggers)

- **Overnight loader** (`trig_01QoA4u…`): currently **paused**. To be rewired so its prompt is
  "read `EXAM-REVISION.md` + the blueprint, follow the LAWS, run `validate_revision.py`,
  then write" — not free-form "invent questions." It stays paused until the blueprint +
  validator exist.
- **Evening read-out** (`trig_012D6eP…`): reports the honest run (E6). May also carry the
  grader health check (§6).

---

## 10. Standing notes

- Exams were **postponed** (Roshan's bike accident / surgery); the formats above are the
  school's yearly-exam formats and still apply for the deferred sitting.
- Harrison is **parked** (stopped using it); his blueprint/page are out of scope until he returns.
- Everything here is Year 9 / Roshan. A second student = a second blueprint, same LAWS.

---

## Appendix — the mistakes this file exists to prevent

1. Built from generic material, not his Canvas uploads (English; Science Skills). → E1
2. Wrong exam format per subject (Science as recall; Geography with no MC). → E2
3. Every correct MC answer was option A. → E3
4. Multi-part questions zeroed when one part slipped. → E4
5. `partly` scored 0 → an honest ~13–14/20 shown as 8/20. → E5, E6
6. Over-strict keyword marking failed correct-but-reworded answers. → E5
7. Faked graph/diagram tasks in a text box. → E7
8. Grader ran on a dead key, silently self-passing everything. → §6 health check
9. Stale Netlify cache / broken bookmark / unverified saves. → §7 verify step
