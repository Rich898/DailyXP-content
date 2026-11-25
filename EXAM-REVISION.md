# EXAM REVISION — source of truth

**Status:** APPROVED by Rich (2026-11-25).
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
`teach` cards (the "what you need to know" cards) appear in **coaching/learn modes** — the
Part-2 top-up and dedicated learn-first sessions — and **never in a graded exam-sim Part 1**
(a test contains no teaching). See §6A.

**Delivery:** per-student static page on Netlify reads the active row over the REST API
and posts runs back. Roshan → `comfy-gnome-ab3891.netlify.app`. The AI grader is the
Supabase edge function `coach`. Page + function sources are versioned here (§8). The page
**must confirm a completed sitting saved, and tell the student if it didn't** — never silently
drop a run. *(Why: a completed day34 sitting never reached the DB and nobody knew.)*
There is **one canonical page URL per student** (the blueprint's `page_url`); old Netlify
generations are retired so a stale bookmark can't serve a dead page. *(Why: Harrison's old
bookmark pointed at a retired page.)*

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

### LAW E4 — Multi-part questions must be part-credited (never all-or-nothing)
Keep multi-part items where the real exam bundles them (Science and Geography both do); prefer
one focus where the parts are independent and splitting is clean. Whatever the shape, a
multi-part answer is **never** scored all-or-nothing — the grader credits each part, so a
2-of-3 answer scores half (E5), not zero.
- *Why:* Roshan wrote a correct trend **and** a correct interpolation but mislabelled part (a),
  and the whole thing scored 0 — the harm was the **zero**, not the multi-part shape. Banning
  multi-part would also make practice less like the real paper (fights E2).
- *Enforced:* E5 partial credit (grader prompt + page tally); `validate_revision.py` surfaces
  multi-part items as INFO to confirm they're part-credited, not a hard fail.

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

### LAW E8 — Coaching builds up; it never marks down
Coaching (the Part‑2 top‑up, and any dedicated coaching session) exists to **teach, not to
test**. In coaching mode the coach names what's right, gives **one** next step, and offers a
**retry** — a `partly` means "good, add this, go again," never a lost mark. Coaching produces
**no pass/fail number that competes with the Part‑1 exam mark**; it reports *progress* ("did
the shaky bits improve?"). Only Part‑1 graded practice yields an exam‑equivalent score.
- *Why:* the demoralising scores came from treating *learning* like *testing*. Separating them
  keeps the practice honest and the coaching kind.
- *Enforced:* page runs Part‑2/coaching in "coach" behaviour (feedback + retry), records
  progress not a competing score; read‑out reports the Part‑1 mark and Part‑2 progress separately.

### LAW E9 — Track what's been asked; never repeat blindly
Every question carries a stable **bank `id`**; every sitting is recorded (`revision_runs`). A
coverage **ledger** (derived from the bank + runs) tells the planner what's been asked, how
long ago, and his record on it, so a new set favours **unseen** and **weak** items and avoids
recent repeats. We can always see coverage of the bank — what we have and haven't asked.
- *Why:* "do we know what questions we have and haven't asked?" — without this, sets repeat or leave gaps.
- *Enforced:* `tools/build_revision.py` selects from the ledger; `validate_revision.py` flags a
  set that repeats an item asked within the last N days.

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
      "sources": ["revision/sources/roshan/Year9_Yearly_Exam_Study_Pack.md §1",
                  "revision/sources/roshan/Roshan_Y9_Revision_Extract.md §SCIENCE"],
      "bank": [ { "id":"SCI-consmass-01", "topic":"Conservation of mass (open/closed)",
                  "src":"...", "ask":"...", "model":"..." }, ... ],
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

## 5A. Source materials — the durable home (`revision/sources/<student>/`)

**The school materials must live in the repo, not in session upload scratch** (which is
ephemeral — a future session or the loader trigger will not have the original uploads).

- `revision/sources/roshan/` holds the committed source of truth: the distilled markdown
  (`Roshan_Y9_Revision_Extract.md`, `Year9_Yearly_Exam_Study_Pack.md`) — exact content, per-
  subject formats, teacher model answers, sample-exam questions and answer keys.
- Original PDFs (study guides, sample papers, the Earnest booklet) are referenced by name in a
  `MANIFEST.md`; store the PDFs themselves too if repo size allows, else keep the markdown
  extraction as the authority.
- LAW E1 (cite your source) and the blueprint's `src` fields point **here**, so provenance
  survives across sessions.

---

## 6. The marking system

- Grader: Supabase edge function `coach`, model **`claude-sonnet-5-5`** (one-line `MODEL`
  const), `effort: low`, `max_tokens: 1024`. Prompt grades substance, ignores
  wording/spelling/order, tie-breaks generous. Returns `{verdict, good, improve}`.
  *(Sonnet over Haiku chosen for marking quality — judging a reworded extended answer is a
  real reasoning task; cost is ~a few cents a month at this volume.)*
- **No self-marking in graded practice.** Written answers are AI-marked; the old "I actually
  got it" self-assessment buttons are gone from Part 1 — a student passing himself is not a
  measurement. (Self-judgement is fine in coaching, which isn't scored.)
- Page scoring: `got_it`=1, `partly`=0.5, `not_yet`=0; MC auto-marked by position; a short
  answer whose `keys` match is an instant full mark (rescue only, never a false pass on
  multi-point questions — those omit `keys`).
- **Grader health:** the function must not silently fall back. If the Anthropic call fails it
  returns `fallback:true`; a health check (§7) alarms if live grading is returning fallback.
  *Why:* the grader ran on a dead API key for days, silently self-marking everything "fine."

Full detail in `revision/MARKING.md`.

---

## 6A. Coaching & the two-phase flow

The exam system always runs as **two phases** (LAW E8):

| Phase | When | What happens | Score |
|---|---|---|---|
| **Part 1 — graded practice** | the exam-sim sitting | each answer marked, substance-based, **partial credit** (E5) | an **honest exam-equivalent mark** — this is the measurement |
| **Part 2 — coached top-up** | after a break, built from Part-1 gaps | re-teach the tricky bits (`teach` cards) → easy-win practice; warm *"what you got right / one thing to add / **try again**"* | **progress, not a competing grade** — "did the shaky bits improve?" |

There are **three** session kinds (don't confuse them):
1. **Graded exam-sim** (Part 1) — no teach cards, AI-marked, honest score.
2. **Coached top-up** (Part 2) — teach cards + easy wins on the Part-1 gaps; progress, not a score.
3. **Dedicated learn-first session** — on demand for a new/weak topic (like the Maths /
   English-decon rounds): "what you need to know" teach cards → gentle practice, multi-round,
   **ungraded**. This is a coaching mode, not an exam sim.

- Part 2 is **auto-offered** after every graded practice; he can take it or leave it.
- **Part 1 must be completed before Part 2 is offered.** A fresh day must route to the
  practice intro, never straight into the top-up. *(Why: a 'ready' reteach once made the page
  skip Part 1 entirely — the learn/practice never ran.)*
- The coach's *behaviour* differs by mode: in a graded sim it **marks** (verdict → score); in
  coaching/learn it **teaches** (encourages, one next step, retry, re-teach). Same engine, two
  jobs — never confuse them (LAW E8).

---

## 6B. The bank & the ledger — coverage (LAW E9)

Mirrors the daily game's menu + ledger:

- **Bank** (in the blueprint) = the universe of askable items, each with a stable `id` + `src`.
- **Runs** (`revision_runs`, Supabase) = every sitting, every answer, verdict and score.
- **Ledger** = coverage/mastery, **derived** from bank ∪ runs (one source of truth, no hand-
  kept file to drift): per item — times asked, last asked, right/partly/wrong history.
- **The planner** (`tools/build_revision.py`) uses the ledger to pick **unseen** and **weak**
  items, avoid recent repeats, and keep each subject's format (E2). Coverage is reportable:
  "asked 34 / 120 bank items; Science Skills 2/18 — thin."
- **Subject mix:** a session covers the subjects being examined, weighted by the exam's own
  marks — **not** an even split, and **not** collapsing into only his weakest subject (per
  Rich). Within each subject the planner favours weak/unseen items.

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
- `revision/sources/roshan/` — the committed school materials (§5A) + `MANIFEST.md`.
- `revision/roshan.json` — the blueprint (bank + per-subject format).
- `revision/MARKING.md` — the marking spec.
- `revision/pages/roshan.html` — the quiz page (source of the Netlify drop).
- `revision/coach/index.ts` — the grader edge function.
- `tools/validate_revision.py` — the gate (E1–E4, E9 repeat check).
- `tools/build_revision.py` — the planner: reads blueprint + ledger, composes a set.
- `RUNBOOK.md` gets an "Exam revision" section: how to redeploy the page (Netlify drop) and
  the function (Supabase), and how to pause/rewire the triggers.

Changes land as commits on the dev branch, reviewable — not blind drag-and-drop.

---

## 9. Scheduled tasks (triggers)

- **Overnight loader** (`trig_01QoA4u…`): currently **paused**. To be rewired so its prompt is
  "read `EXAM-REVISION.md` + the blueprint, follow the LAWS, run `validate_revision.py`,
  then write" — not free-form "invent questions." It stays paused until the blueprint +
  validator exist.
- **Evening read-out** (`trig_012D6eP…`): a parent-friendly read-out for Rich (read in the
  app). Reports the honest Part-1 mark (E6) **plus**: how each subject is tracking across
  sittings (improving / holding / weak, from the ledger E9), the **specific topics** he's
  getting wrong, a **short plain-English explainer** for any topic he keeps missing, and —
  if he did the top-up — whether the shaky bits improved (E8 progress, not a second score).
  If he didn't sit it, a brief friendly nudge. May also carry the grader health check (§6).

---

## 10. Standing notes

- Exams were **postponed** (Roshan's bike accident / surgery); the formats above are the
  school's yearly-exam formats and still apply for the deferred sitting.
- Harrison is **parked** (stopped using it); his blueprint/page are out of scope until he returns.
- Everything here is Year 9 / Roshan. A second student = a second blueprint, same LAWS.
- **All of Roshan's examined subjects already have a documented format in his sources** and
  the blueprint should ultimately cover them all — each with its OWN format (E2):
  English (Earnest short-answer + Lord of the Flies essay), Core Maths (calculation paper),
  Science, History, Geography, PDHPE (MC + short + extended), Commerce (gapfill + short),
  Food Tech (structured responses). We start with **Science, History, Geography**.
- **Study aids** (printable cram sheets, e.g. the Earnest / Lord of the Flies ones) are a valid
  optional output, generated from `revision/sources/` — same source-of-truth rule (E1).

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
10. Learning treated like testing (coaching scored pass/fail). → E8
11. School materials lived only in ephemeral upload scratch. → §5A
12. No record of what's been asked, so sets could repeat or leave gaps. → E9 / ledger
13. A 'ready' top-up once skipped Part 1 entirely (the learn/practice never ran). → §6A
14. Self-marking ("I actually got it") let a student pass himself — no real measurement. → §6
