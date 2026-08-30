# PARENT-PORTAL-BRIEF.md — build the parent portal, properly

Bootstrap doc for a fresh session. Written 30 Aug 2026. Read `WORKING-MODEL.md`
first and follow it, then `PARENT-COMMS-V2.md` (the strategy of record for the
comms) and `REPORTING.md` (ratified doctrine). This brief supersedes the
single-page portal direction taken on 29–30 Aug — see "What went wrong" below.

**First message to Rich: confirm this brief still reflects what he wants, then
build it this morning to an EXCELLENT standard.** This is the paying-parent
surface; design quality is the point, not an afterthought.

---

## The goal

A real **Parent Portal** — the parent's product home — not a report page. It has
two jobs:

1. **The parent report, as THREE distinct, well-designed pages** (a three-pronged
   approach, aligned with Rich). NOT one long scroll. Each is its own page/view
   with its own layout, reached by clear navigation:
   - **The Week Ahead** (Monday, forward) — per subject, what school is covering
     this week and what his sets will do about it; one assessment date. The
     forward half of the weekly loop.
   - **This Week** (Friday, backward) — what actually happened: the subject
     spine (what school set → what his sets worked → where each topic stands,
     position + depth → the one misconception detail → next week). The
     fluency-illusion catch is narrated here.
   - **The Running Picture** (Friday, cumulative) — the term-to-date wrap that
     folds this week in: where each subject stands overall, the
     confidently-shallow cross (solid recall × shallow depth), term trends
     (switch on at 4+ weeks), the archive of past weeks.

2. **Room to become the account surface** — this is where a parent will manage
   their account: per-touchpoint on/off, opt-out, contact details, (later)
   the magic-link login at family #2. Design the shell so this has an obvious
   home, even if v1 only stubs it.

Messages become pointers; the portal is the product. The Monday and Friday SMS
are thin **pointers** into the relevant page (the Monday pointer carries no
sweep-derived claim, so it is NOT gated — see `monday_brief.py`).

---

## The standard (this is the brief's real content)

The 29–30 Aug attempt failed because it stacked everything into one scrolling
`portal_page.py` with no navigation and no design thought. Do not repeat that.

- **Three pages, each designed for its job** — a landing/overview with clear
  navigation into the three, or a tabbed shell; each page laid out on its own
  terms (the Week Ahead is a light forward glance; This Week is the deep read;
  The Running Picture is the map). Think about hierarchy, rhythm, what a parent
  sees first on each.
- **Build on the design language we already have** — the product's dark design
  system (the quiz shell `shell/template_v3.html`, `report_page.py`'s `#0B1220`
  radial ground + flare/reef/kelp accents, `kid_wrap.py`'s player-card
  treatment). The portal should feel like the same product, done to the same
  or higher polish. Reuse `report_page.py`'s CSS tokens; don't reinvent the
  palette.
- **Self-contained, private, stamped** — same model as every hosted page: zero
  fetch, `noindex`, build stamp (`report_page.build_stamp()`) so
  `netlify_deploy.verify()` can assert the live render. Unguessable slug +
  bookmark until family #2; then the same pages move behind the Supabase
  magic-link door (the account surface makes this natural).
- **Responsive, mobile-first** — parents open this on a phone.
- **Shadow-first, t1-gated, previewed** — new formats go through the dry-run
  preview window before any live send/publish (WORKING-MODEL). Ship t1 first.

---

## What is already BUILT and GOOD — reuse it (do not rewrite the facts)

The deterministic FACTS/content engines are sound and tested (green on Python
3.11). The presentation is what needs redoing. Keep these:

- **`monday_brief.py`** — the Week Ahead engine. `week_ahead()` (per-subject
  forward facts from the targets: what's covered, new-vs-last-week flagged, a
  forward intent clause, one assessment date; fail-soft continuation form),
  `pointer_sms()` (the thin Monday SMS), and `validate()` (the Monday law:
  forward-only, no verdict/standing/result words, no digits except an
  assessment date, with topic/subject/date masking so real content can't
  false-trip). Tested.
- **`report_stories.subject_blocks()` + `fluency_catch()`** — the This Week
  subject spine facts (per-subject blocks assembled from ledger topics + the
  week's traces + ranked stories + targets; the held-promotion safeguard).
  Tested in `test_friday_report.py`.
- **`report_page.py` subject-spine render** (W3) — the per-`_subject_block`
  renderer and the dark CSS tokens. The *Friday report page itself* is good and
  ratification-pending; decide whether This Week reuses it wholesale or renders
  its blocks inside the portal shell.
- **`portal_page.py` facts helpers** — `subject_cards()` (position + depth,
  weakest-first, frozen excluded), `_confidently_shallow()`, `term_trends()`
  (the 4-week gate), `_cumulative()`. **Reuse these functions; REPLACE the
  single-page `render()`/section layout** with the three-page design.

## What to REDO

- `portal_page.py`'s single-scroll `render()` and its stacked sections — replace
  with a portal shell + three designed pages (or a clean tabbed layout). This is
  the core of the new work.
- Decide the page/navigation architecture (separate HTML pages under the portal
  slug, e.g. `/p/<slug>/` overview + `/p/<slug>/ahead|week|picture`, vs a single
  shell with client-side tab switching — still zero-fetch/self-contained).

## Content decisions still OPEN (lock these with Rich early)

1. Exact section/page names and navigation labels.
2. The confidently-shallow sentence wording (the single most important line —
   "strong recall; hasn't yet shown he can explain it; his next written question
   targets that").
3. Whether the standalone Friday report page (W3) survives as the This Week page
   / the dated archive snapshot, or is folded into the portal shell.
4. Whether the Friday SMS also becomes a pointer (like Monday) or keeps the
   tier-1-report-in-text doctrine + link.
5. What the account surface holds in v1 (stub vs real: per-touchpoint on/off,
   opt-out, contact).
6. The parent-surface name — "The Full Picture" is the working phrase
   (PARENT-COMMS-V2 §8); the two-name decision is deferred to the commercial
   gate, but the vocabulary can be adopted now.

## Wiring (AFTER the design + content are locked — do not wire first)

New `p` slug kind in private `report_slugs.json`; a runner
(`portal_run.py`, mirror `friday_report_run.py`) that builds + publishes the
portal and sends the pointer SMS; a Monday-seed + Friday republish
(`xp_schedule` pg_cron slots); dated archive paths `/r/<slug>/<week>/` (needs
the "Friday overwrites in place" fix first, V2 §5). Rich promotes shadow → live.

---

## What went wrong (29–30 Aug) — so it isn't repeated

- Aligned with Rich that the parent report is three time-phased components
  (Week Ahead / This Week / Running Picture) and that the portal is the product,
  SMS are pointers. **That alignment stands.**
- BUILT the facts engines (good) but rendered everything as ONE long-scroll
  portal page with no navigation and no design thought. Rich (rightly)
  rejected it: "just a long scroll, no real thought or design." The three
  components must be three DESIGNED pages, and the portal is a broader
  account/product surface, not a single report.
- Course-corrected to this brief. The facts layers are kept; the presentation
  is rebuilt to an excellent standard.

## Boot (for the fresh session)

```
Fetch https://raw.githubusercontent.com/Rich898/DailyXP-content/main/WORKING-MODEL.md
and follow it. Then fetch PARENT-PORTAL-BRIEF.md and build the parent portal —
three designed pages, excellent standard, reusing the built facts engines.
```

Branch: keep developing on `claude/dailyxp-parent-comms-gjjo2e` (the built facts
engines — `monday_brief.py`, `subject_blocks`, the portal facts helpers — are
already there). The single-page `portal_page.render()` is the thing to replace.

---

## BUILT 30 Aug 2026 — the rebuild, and the decisions it took

*(Session record: built on `claude/parent-portal-build-0vae4u`, which carries
this branch's engines forward. Rich ratifies by merging.)*

**What shipped (shadow, not wired):** `portal_page.py` rebuilt around
`render_pages()` — FOUR real pages under one slug, replacing the single-scroll
`render()`:

| Path | Page | Refreshes |
|---|---|---|
| `/p/<slug>/` | **Home** — the front door: radar strip, three doorway cards with live one-line teasers, the account surface (v1 stub), the kid's player-card link | each publish |
| `/p/<slug>/ahead/` | **The week ahead** — ONE DATE card + per-subject forward rows (unit, intent clause, NEW chips, per-teacher hedge) | Monday evening |
| `/p/<slug>/week/` | **This week** — the verdict word as hero, excused-aware activity strip, fluency-illusion narration, the subject spine (drawn by `report_page._subject_block`, so Friday's two surfaces share one shape) | Friday evening |
| `/p/<slug>/picture/` | **The running picture** — per-subject landed tally with bars, every topic's position + depth (confidently-shallow cross inline), term trends (4-week gate), the archive, the legend | Friday evening |

All facts helpers kept byte-identical (`subject_cards`, `_confidently_shallow`,
`term_trends`, `_cumulative`); `build_portal()` gained optional `week_verdict` /
`activity` / `touchpoints`. `test_portal_page.py`: 79 assertions green on 3.11,
including the course-correction itself (each component renders on ITS page and
never stacks back into one scroll). `tools/portal_preview.py` renders the whole
portal with invented sample data ("Sam"; codes-only law respected) into
`preview/portal/` — committed, walkable off a checkout.

**Design decisions taken (defaults, Rich can overrule any):**

1. **Real pages, not client-side tabs.** Each page gets its own layout and hero;
   the Monday/Friday SMS pointers deep-link cleanly; every page is small and
   individually stamp-verified by the existing one-page-per-path deploy
   machinery (publish slug `abc/ahead` → `/p/abc/ahead/`). Navigation is a
   fixed bottom app bar (thumb reach) + doorway cards on home.
2. **Names** (open decision 1): on-page titles "The week ahead" / "This week" /
   "The running picture"; nav labels Home · Week ahead · This week · Picture.
   The portal masthead adopts the working vocabulary: **XP DAILY · THE FULL
   PICTURE** (open decision 6 — vocabulary only, no rename).
3. **One accent per time-frame:** ahead = reef (forward horizon), week = flare
   (the live week), picture = kelp (what has grown) — carried through each
   page's hero, chips, and active nav state. Everything else is report_page's
   ratified dark system untouched.
4. **The confidently-shallow sentence** (open decision 2) kept as built:
   "Strong recall — he can pick this confidently, but hasn't yet shown he can
   explain it. His next written question targets exactly that."
5. **The Friday report page survives** (open decision 3) as the dated archive
   snapshot and long form; the portal's This Week page is the live deep read
   and links it ("The full Friday report →"). Nothing is rendered twice from
   two code paths — the spine blocks are drawn by the same renderer.
6. **Account surface v1** (open decision 5): an honest stub — the four
   touchpoints with cadence, all ON, plus the documented change/opt-out path
   ("a text to Rich"). Per-touchpoint config (C6) and magic-link sign-in land
   in this exact space later; the shell doesn't change.
7. **Friday SMS doctrine** (open decision 4): untouched — still Rich's call.

**Freshness contract on every page** (to ratify with V2 §11.3): top bar shows
"updated {date}"; each page names its own cadence; the footer states the
weekly-read-on-purpose line. Build stamp meta + visible footer stamp on all four
pages, inside `verify()`'s 4KB window.

**Not done here (deliberately, per this brief):** no wiring — no `p` slug kind,
no runner, no schedule slots, no dated `/r/<slug>/<week>/` paths. That work
starts only after Rich eyeballs the preview and locks the design.

### Feedback rounds (Rich, page by page)

**Round 1 — 30 Aug, THE WEEK AHEAD** (home deferred to later): headlines are
ALWAYS white, all pages (accent stays in eyebrow/chips/nav; includes the
verdict word on This Week); subheader drops "a plan, not a verdict"; **ONE DATE
→ UPCOMING DATES** — a list of every dated thing (tests, study-guide releases,
due dates; `build_portal(upcoming=[...])`, nearest first, single radar as
fallback); subject rows restructured as **SUBJECT / TOPIC / FOCUS** (topic =
the unit, never fabricated; focus = the forward clause) with the copy
vocabulary fixed at exactly two verbs — **"continues" / "moves into" / or
both** (`monday_brief._intent`; "starts" removed). New-topic chips dropped —
"moves into" now carries that information in the sentence.
