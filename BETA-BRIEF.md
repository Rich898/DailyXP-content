# XP Daily — Beta Build Brief (fresh-chat bootstrap)

**Last updated: 25 Aug 2026.** If weeks have passed, trust the repo over
this file: check `git log`, `SYSTEM-MAP.md`, `ROADMAP.md` for drift.

## How to use this file
You are a fresh Claude instance. Rich has pasted a command pointing you
here so you can pick up the XP Daily beta build mid-stride. Read this
whole file, then ask Rich one question: **which workstream today?**

## Who you're working with
Rich — founder, not an engineer, works by voice dictation (expect typos,
never comment on them). Ex-AAA game development; thinks in loops, seasons
and XP economies. Wants: **plain English before technical detail, one
small action at a time with confirmation before the next, honest pushback
over agreement.** He is the decision-maker on everything.

## What XP Daily is
A nightly adaptive quiz + parent-communications platform. A weekly sweep
of each kid's school Canvas produces a targets file (what's live in class,
what's assessed when); a 2pm build turns targets + per-kid ledger into
that night's quiz; kids play via coded link; results land in Supabase;
parents get scheduled reports. Full architecture, data map, trigger map
and the 12 testable laws live in **SYSTEM-MAP.md — read it before
touching anything pipeline-shaped.**

Non-negotiable laws (subset): LLMs never hold state — code decides,
language dresses. Publishes are atomic behind a validator, with live
VERIFY. New content risk goes to seat t1 (Rich's test seat) first. The
**carry-forward law**: a sweep is always an UPDATE of the previous
targets file — topics transition (upcoming→live→prior_term), they never
leave by omission; removal only ever explicit; enforced by a code guard
and a validator hard-fail. The **two-repo privacy law**: the public
content repo carries no personal data — kids are seat codes (y8, y9, t1),
per-kid data lives only in the private repo. This brief obeys that law;
so must you.

## The beta (the point of everything below)
Ten families, same school, free. Canary household first — one forgiving
parent, kid in the same year as an existing seat — then the other nine.
Three-week shape: (1) targeting + QA skill, (2) beta kit + auth +
onboarding, (3) canary, then nine. Consciously deferred: other-LMS
support (Google Classroom / Microsoft) — the adapter law plus a written
TARGETS-FORMAT.md contract is the planned seam; do not build it yet.

## Scope board (as of 25 Aug 2026)

**DONE**
- SYSTEM-MAP.md v1.1 committed — source of truth, QA-skill input; 5
  [VERIFY] items remain listed inside it.
- Automated Canvas sweep, stages 1–3: per-seat fetch via student API
  tokens (six surfaces), LLM summarise into targets format with the
  carry-forward merge + changelog, deterministic validator (carry-forward
  hard-fail, date sanity), diff scoreboard vs the manual sweep. Replay
  test scored **93%** against Rich's real manual sweep. Runs shadow-only
  (writes a folder the live pipeline cannot read) on a **Monday 07:07
  Sydney timer** + manual button. Failures are loud: red run, email,
  self-committed logs.

**IN FLIGHT — sweep trust ladder**
- Mon 31 Aug: machine runs before school, Rich does his LAST full manual
  sweep, final side-by-side. If machine matches-or-beats: Rich flips to
  ~5-min review of the machine's changelog (editor, not author).
- Promotion = a separate later change: output destination moves from
  shadow/ to targets/ behind the validator. Never rush this.

**TO BUILD (rough order)**
1. **Schedule-pass** for the sweep: term assessment dates live in an
   assessment-schedule PDF on the year-group noticeboard course — a
   surface the fetcher doesn't pull (files) on a course the summariser
   excludes. Pull the PDF, extract subject/task/date triples (one LLM
   call per seat), attach dates in code. This closes the sweep's known
   date gaps.
2. **QA skill**: end-to-end pipeline test runnable after any change.
   Input = SYSTEM-MAP.md; same session should close its 5 [VERIFY] items.
   Sequence before onboarding anyone.
3. **Two-door auth**: kid door = coded link (zero friction, unchanged);
   parent door = Supabase Auth email magic link; reports move from
   public-unguessable Netlify to a private bucket behind the session
   gate.
4. **Beta kit** (ROADMAP.md has the ratified spec): per-year-level
   Netlify deploys with ?kid= codes, pseudonymous k-codes, consent block,
   deletion/export script, ledger seeding from intake.
5. **new_household.py**: one-command onboarding of a kid+parent combo
   (ONBOARDING.md is the ~20-min human runbook it automates). Includes
   the per-household Canvas student-token pattern (per-seat Actions
   secrets).
6. **Consent/privacy pack** — two lawyer questions outstanding: kid
   teach-back text crossing borders to the Anthropic API (APP 8), and
   how beta households' Canvas credentials are handled.

**DECISIONS PENDING (Rich's, do not assume)**
- Deal card ("set the week": Friday report proposes a parent+kid weekly
  deal — reward for 5 nights, forgiveness buffer, effort floor, streak
  escalation; system is scorekeeper only). Mocked, not wired. In or out
  of beta?
- Kid weekly wrap: which door does it ride? Standing recommendation: the
  kid door.

## Operating rules for you
- Read SYSTEM-MAP.md before pipeline work. Respect every law above.
- Never write targets/ directly; never bypass the validator; shadow
  stays shadow until Rich explicitly promotes.
- Credentials (repo PAT, API keys) are provided by Rich in-session only.
  Never expect them in a file. If he pastes the wrong kind of key, say
  so and advise rotation.
- Verify live over trusting docs: after any push that matters, run it
  and check the result. Silent no-ops are the enemy — assert your edits
  landed.
- One small action, confirm, next. When you disagree, say so plainly.
