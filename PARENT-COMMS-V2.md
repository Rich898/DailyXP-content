# PARENT-COMMS-V2 — proposal: outstanding parent communication and reporting

**Status: PROPOSAL, not ratified. Written 29 Aug 2026 in response to Rich's brief
("this is the paying audience — insights they can't get anywhere else").**
Where this file conflicts with `REPORTING.md`, `ACHIEVEMENTS.md` or `KID-REPORT.md`,
those files remain law until Rich ratifies the specific amendments listed in §11.

---

## 0. Friday's light-theme reports — what actually happened

The comms strategy below only matters if what we send arrives, on time, looking
right. Friday didn't. Root-causing it changed the plan, so it leads.

**The pipeline did its job.** Friday's send (run 33163906233, dispatched manually
20:35 AEST) ran on `main@aac1a06`, which contains the dark repaint — the rendered
pages were dark, all three deploys reached Netlify "ready", verify passed, 3 SMS
sent. Thursday's supervised `--no-sms` run (33062022680, from the pre-repaint
branch) had deployed **light** pages to the **same three stable URLs** 24 hours
earlier.

**But the site never served Friday's pages — and the cause was OURS, not
Netlify's** *(root cause corrected 29 Aug after a read-only dashboard + live-page
inspection: auto-publishing on, nothing locked, the newest deploy Published).*
Netlify lowercases every URL path, and its files API lists live pages under
lowercase paths; our slugs were mixed-case. So every carry-forward deploy
since the 21 Aug fix listed the OLD page at its lowercase path *and* the new
render at a mixed-case path — one normalised path, two entries, stale wins.
**A page only ever landed when it was NEW to the site.** Thursday's run *added*
y8/y9 (wiped on 21 Aug) as light builds; t1 kept serving its 21 Aug survivor
through every green deploy since. No dark render was ever served, which from
the outside looks exactly like "the repaint never shipped".

**Why the pipeline couldn't see it:** `netlify_deploy.verify()` checks only
HTTP 200 + the string "XPDAILY" in the first 4KB. The stale light page
passes both. A green tick that cannot distinguish the page it just uploaded
from last week's page is the same "green tick lies" class as the 26 Aug
dispatch outage — the fourth instance of that class.

### Fixes (first items of the build order, §10)

1. **Case normalisation (code, DONE):** every deploy path, URL and manifest key
   is lowercased at use; new slugs generate lowercase (`token_hex`). A
   redeploy now REPLACES its live page. Recovery button added: dispatch the
   Friday workflow with `redeploy=true` to re-render + re-deploy an
   already-sent week (no SMS, no cursor/snapshot writes).
2. **Build stamp (code):** every family-facing page embeds
   `<meta name="xpdaily-build" content="{GITHUB_SHA} {utc-time}">` plus a tiny
   footer stamp. "Which version am I looking at" is never a mystery again.
3. **Verify that can't lie (code):** `verify()` must require the *build stamp of
   the render it just uploaded* in the fetched page — not a brand string. A
   deploy that doesn't actually publish becomes a loud failure at send time,
   and per existing law the SMS still goes out, without the link, rather than
   linking a wrong page.
4. **Watchdog rung:** after each scheduled publish, the watchdog asserts the
   live page's stamp. Publish-layer failures page the operator instead of
   waiting for a parent to notice.
5. **Scheduling reliability:** GitHub **skipped all three Friday-evening crons**
   on 28 Aug; the send happened only because Rich manually dispatched. Migrate
   `friday-report.yml` and `wed-checkin.yml` triggers to Supabase `xp_schedule`
   (pg_cron) slots — same as daily-quiz — with GitHub crons demoted to
   cursor-guarded backup. This also fixes the 4 Oct DST drift (every GitHub UTC
   cron goes an hour late when AEDT starts) **before** it hits live parent sends.
6. **Process line for RUNBOOK.md:** a supervised `--no-sms` run **deploys to the
   live per-kid URLs**. Never run one from a branch that predates a pending
   visual change; use `--dry-run` for inspection unless the deploy itself is
   under test.

---

## 1. The frame: three questions, three surfaces, one loop

Rich's brief decomposes into the three questions a paying parent actually has:

| Question | Surface | Status today |
|---|---|---|
| What is he working on **right now**, and what's coming? | **Portal — This Week panel** (+ Monday SMS) | new |
| How did **this week** go — against what school set? | **Friday report page** (redesigned, §3) | live, wrong shape |
| How is he doing **overall, by subject**? | **Portal — subject cards, term view, archive** | designed, zero code |
| Is tonight done? | Daily soundbyte SMS | live, unchanged |

**The strategic shift: messages become pointers; the portal becomes the
product.** Today the product a parent experiences is a stream of texts — easy to
ignore, easy to churn from. An always-current page they can open any time is
what makes the accumulated ledger *visible*, and the accumulating history is the
real switching cost: cancelling means the map of *this kid's* misconceptions,
calibration and depth stops growing. Nobody else — school, tutor, or app — can
rebuild it.

**And the week gets a narrative arc:** Monday plants ("here's what school posted;
here's what his sets will do about it"), Wednesday tends (unchanged, one ask),
**Friday harvests against Monday's plan** — the report answers the exact
questions Monday raised. A parent who read Monday's text reads Friday's report
as the resolution of a story they're already inside. That loop — plan → practice
→ evidenced outcome, per subject, weekly — is the thing no other product can do,
because no other product holds both the school's live syllabus *and* nightly
evidence of understanding.

---

## 2. The weekly rhythm (proposed final form)

| When | Parent gets | Job | Status |
|---|---|---|---|
| **Mon evening** | **Week Ahead** SMS + portal This-Week refresh | Orient: what school posted, what the quiz will do, any assessment on radar | NEW — gated, §4 |
| Mon–Fri on completion | Soundbyte | Reassure | unchanged |
| **Wed evening** | Merged check-in | Activate + set expectations | unchanged **+** digit-free assessment-radar clause |
| **Fri evening** | Report SMS + **redesigned page** | Judge the week against Monday's plan, with fixes attached | redesigned, §3 |
| Any time | **Portal** | The full picture: now / this week / overall by subject / archive | build, §5 |

Hard cap: **three scheduled parent sends per week** (Mon, Wed, Fri). The pull
surface (portal) is the pressure valve that lets push volume *fall* over time.
The soundbyte stays completion-triggered (silence remains the only "not done"
signal). The Wednesday check-in is ratified-final and already the light touch
Rich asked for — it does not get rebuilt.

**The household reality check (unsolved in v1, must be solved here):** every
touchpoint is per-kid, and the only live household has two kids — those parents
already receive ~12 texts/week; per-kid Monday makes 14. Amendment: **one
household, one message** for scheduled sends — the Monday and Friday SMS for a
multi-kid household are single consolidated texts (validator law: never a
verdict-vs-verdict juxtaposition; each kid gets their own sentence, no
comparative language — the no-sibling-comparison law extends to prose), and the
portal gets a household landing page linking each kid's picture without
comparing them.

---

## 3. The Friday report, redesigned — subjects as the spine (Rich's ask)

Today's page is organised by insight type (WHAT CHANGED / WHAT HAPPENED / BY
SUBJECT accuracy row / NEXT WEEK). Rich's ask is the right reorganisation:
**subject-first**, and each subject block closes the loop Monday opened.

### Page structure v2

1. **Hero** — unchanged law (standing + trajectory fused, week-word engine).
2. **The week in one strip** — days done · topics practised · events cleared
   (activity row, with the denominator fix below).
3. **SUBJECT BLOCKS — the new spine.** One block per subject, e.g.:

   > **HISTORY — The Crusades** *(what his class is on, from the school sweep)*
   > This week his sets worked: causes of the First Crusade · key figures ·
   > primary-source reading *(bullets = the topics actually scheduled in his
   > published sets this week — never intent, always the plan files)*
   >
   > | Topic | Where he is | Depth |
   > |---|---|---|
   > | Causes of the First Crusade | ● Nearly there | Can connect it — *moved up this week* |
   > | Key figures | ◐ Building | Knows it |
   > | Primary sources | ○ Getting started | — new this week |
   >
   > **The detail worth knowing:** on Tuesday he was sure the People's Crusade
   > was the First Crusade's main force — it wasn't, and the why matters: it set
   > out earlier and separately. His sets re-ask it calmly this coming week.
   > **Next week:** primary sources steps up; causes eases to maintenance.

   Per block: what school set (sweep) → what the sets did (plan files) → where
   each topic stands (red→amber→green band + depth rung where evidenced) →
   at most one misconception-level detail (from the archived set's own `why`)
   → next week's plan for that subject. Gaps always arrive with their fix
   (no-anxiety law unchanged).
4. **Cross-cutting cards, demoted below the subjects:** the win ·
   IN HIS OWN WORDS (integrity-gated quote) · SAY ONE THING / DO ONE THING ·
   WHAT'S COMING (assessment radar) · WEEK ON WEEK (aggregate only) · SPEED
   (only when moved).
5. **Footer:** cumulative strip ("Maths 4 of 6 topics landed · Science 3 of 5 —
   full picture →" linking the portal) · kid-wrap link · build stamp · legend.

### Laws that make the redesign honest

- **Position weekly, trends monthly** stays. A subject block shows where topics
  *stand* any week; per-subject *trend* language waits for the monthly window
  (2–6 questions/subject/week flips on noise and would burn trust).
- **Depth rungs render only where evidenced** (ceiling law): an MCQ-only topic
  caps at "can list it" and the page never implies more; missing depth shows as
  "—", not as a judgement.
- **Bullets come from published sets, not intent.** The "this week his sets
  worked" list derives from `plans/<seat>/` + published quiz JSON. The page can
  never claim practice the planner didn't schedule.
- **Fix the activity denominator (real bug, found this review):**
  `week_activity` computes `possible = 5` flat and never reads the completion
  record — a pipeline HOLD or a sick day currently yields "3/5 — quiet week:
  nudge the habit", which violates *our gaps are never reported as the kid's*
  and the absence doctrine. Subtract NOT-PUBLISHED/ABSENT days (from
  `schedule.json`) from the denominator; suppress the "quiet" verdict when the
  shortfall is the pipeline's.
- **Narrate the fluency-illusion catch when it fires.** "He got the
  multiple-choice right but couldn't yet explain it, so we held the promotion"
  is happening silently in code (TB✗ outranks a correct MCQ). One sentence
  turns an invisible safeguard into the visible rigour a paying parent is
  buying. Cheap, distinctive, ship it.

Most of this is **rendering, not new computation**: `friday_report.build_card`
already computes standing per topic, movement, radar, snapshot-by-subject —
`snapshot()` and `standing_detail` are in the fact card today and never drawn.

---

## 4. Monday: "here's the week" — the genuinely new touchpoint, shipped gated

The best idea in the brief, and the most dangerous if rushed: its failure mode
is *confidently telling a paying parent something false about their child's
school week*, on a manual sweep that fails silently (wrong Chrome account,
per-teacher pages missed) and that ratified law says Monday must never depend
on.

The timing is on our side: the automated sweep's final side-by-side is **Mon 31
Aug** (machine 07:07 vs Rich's last manual sweep). The Monday touchpoint is what
finally gives the sweep a paying consumer — but it ships **behind the sweep
promotion gate**, not before.

**Sequenced shape:**

- **Step 1 (now, no SMS): the portal This-Week panel.** Republished Monday
  evening from the sweep diff ("NEW OR CHANGED", never the whole carry-forward
  file) + assessment radar + one line on what the sets will do. A stale panel
  on a page a parent *chooses* to open is forgivable; a stale push isn't.
- **Step 2 (after two consecutive clean automated-sweep Mondays): the Monday
  SMS**, t1 first, then household-consolidated to all seats.

**The Monday law (to ratify):**

- **Forward-looking only. Zero performance content.** Validator denylist:
  no verdict words, no standing words (solid, building, behind, "at the door",
  "close to locking in", "been biting him"), no digits except an assessment
  date. Topic names, dates, and plan intent are the only legal fact classes.
  Monday never judges — gaps stay where they arrive dressed as help (Wed) or
  position (Fri).
- **Fail-soft:** if the newest targets file isn't this Monday's, send the
  honest continuation form ("this week his quizzes keep working the current
  topics — X in Maths, Y in Science — while we sync with what school posts").
  Never silent (scheduled-touchpoint law), never invented.
- **Assessment claims are hedged as practice-coverage**, never outcome
  prediction ("his sets are steering toward it" — computed from the plan files,
  and only while the latest sweep still asserts the date; a moved date gets a
  quiet correction line, and after the test the check-in *asks* how it went
  rather than asserting readiness was enough).
- **Per-teacher subjects carry a confidence flag** in the targets format:
  shared-module subjects are claimable; per-teacher subjects (y8 English, y9
  Science/English) are hedged or omitted for any seat whose teacher page isn't
  verified — at beta, another family's teacher may differ.
- **Reveal order: the kid sees his week first.** The board/week lands in the
  kid's 4pm quiz surface before the parent's evening text mentions it — the
  parent joins the kid's story, never fronts it.
- **Collision rule:** Monday evening already carries an on-completion
  soundbyte; apply the Wednesday-merge precedent (if the run is in before the
  Monday send, one merged text; both cursors advance).
- Delivery: pg_cron slot, own cursor, watchdog rung, wed_checkin architecture
  (deterministic fact card → dresser → validator → deterministic fallback).
- FROZEN seat → quiet variant; term-break → suppressed by the calendar (§6).

**Example (t1 pilot, household form):**

> XP Daily — the week ahead. School this week: Maths moves into solving
> equations with brackets, Science starts how body systems work together,
> English continues persuasive writing. One date: a Science topic test
> Thursday 10 Sep — his nightly sets are already steering practice toward it.
> The full picture, any time: {portal link}

---

## 5. The portal — "always available" done honestly

One more page kind on the existing reports site (`/p/<slug>/`), rendered by a
new `portal_page.py` from data the Friday job already holds. **No login yet**:
unguessable-slug + bookmark is the ratified privacy posture until family #2,
at which point the same renderer moves behind the Supabase magic-link door
(already specced, first use of the collected parent email). "Login at any
point" for the current three families is a bookmark that never breaks — same
feature, less friction.

**Cheapest win in this entire document:** the `/r/` URLs are *already*
permanent and bookmark-stable. One text per family — "bookmark this — {name}'s
page is always there" — delivers 80% of "always available" this week, for zero
build.

Structure (top to bottom = the three questions):
1. **NOW strip** — per subject: current class focus + assessment radar.
2. **THIS WEEK panel** — sweep diff + what the sets are doing (Monday's
   content, §4 step 1).
3. **SUBJECT CARDS** — per-topic rows with both axes side by side. This is
   where the founding insight finally renders: **state=solid × depth=lists →
   "strong recall; hasn't yet shown he can explain it — his next written
   question targets this."** Confidently-shallow, on a page, per topic.
4. **TERM TRENDS** — fills in as snapshots accumulate (weekly state+depth
   snapshots have been banking since go-live; trends switch on at 4+ weeks,
   and we say so rather than faking them).
5. **ARCHIVE** — past Friday reports. Requires dated report paths
   (`/r/<slug>/2026-09-04/` with `/r/<slug>/` → latest); today each Friday
   overwrites in place, so the ratified archive is currently impossible.
6. **Footer** — legend (the verdict ladder's ratified home), reading notes,
   "questions? text Rich", build stamp.

**Portal laws (to ratify):**
- **Freshness contract:** judgment-shaped facts recompute **Friday only**; the
  This-Week panel refreshes Monday; a visible "updated {date}" stamp on the
  page; watchdog asserts the live stamp after each republish. No same-night
  results, ever — an always-on surface must not become a Tuesday-8pm
  interrogation feed; the batched-judgment spine survives.
- **Dignity/aging rule:** repaired topics and resolved confident-wrongs
  collapse into "fixed it" history framed as wins; teach-back quotes rotate
  rather than accumulate. (And the quote archive waits for the outstanding
  APP 8 privacy advice on teach-back text.)
- **Deletion promise extends to hosted surfaces:** the deletion script must
  enumerate and remove every page for a family (reports, dated archive, wrap,
  portal, slugs) with manifest read-back verification — the carry-forward
  manifest currently keeps everything live forever and has no removal path.

---

## 6. Calendar, holidays, exams — the cliff nobody scheduled

NSW spring break is ~25 Sep–12 Oct — four weeks out — and **no term calendar
exists**: the current Wednesday cutoff would text "tonight's run isn't in yet"
into the holidays, and Friday would verdict a beach week "Quiet".

- Ship a shared `calendar.json` (term dates, per-seat exam blocks) that gates
  **every** scheduled send and the quiz pipeline's expectations.
- **End-of-term wrap** (new, one per term): the cumulative-by-subject
  reflection — where he started, what landed, what he can now explain, what
  carries into next term. This is the literal "cumulative status by subject"
  deliverable and the strongest renewal artifact the product can produce.
- **EXAM-MODE doctrine** (file is referenced in SYSTEM-MAP but doesn't exist):
  exam weeks flip sets to revision posture, Monday frames the week as
  revision, and an exam-week Friday suspends the week-word verdict.
- DST: covered by the pg_cron migration (§0.5) — before 4 Oct.

---

## 7. XP, achievements, and what the kid chases

**The parent side of Rich's worry is already solved doctrine** — points are
demoted on every parent surface, there is no points target ("a target on
points rewards choosing easier questions"), XP-by-day is a kid-wrap metric.
The residue is real but different: **the meaning layer is invisible.** Badges
kids earn have no weekly surface (the kid wrap is built, tested, and never
deployed — `kid_wrap_url=None`), the portal doesn't exist, and depth only just
went live. XP looks like the point of the product because it's the only thing
rendered.

**Re-anchor, don't rip out.** XP keeps its honest job — the showing-up meter,
rank fuel, tone-band input ("+1,840 XP banked", not "1,840 of 2,450"). The
meaning layer goes above it:

**The weekly board — "up for grabs this week"** (Rich's idea, made concrete):
- **Permanent trophies** (the existing 12-badge v1 set) stay as-is.
- **Weekly contracts**, declared Monday, resolved Friday, keyed
  `Contract|{iso_week}|{name}` — deterministic reads of the ledger, no AI,
  max five slots:
  - **ON THE BOARD** — canonical runs 4 of 5 school days (4, not 5: one sick
    Tuesday must not kill the week's goal by Wednesday; Perfect Week remains
    the 5/5 trophy on top).
  - **CLEAN HANDS WEEK** — Clean Run condition (zero lucky guesses, zero
    confident-wrongs) on 3+ nights. This is the accuracy badge done the only
    doctrine-safe way — calibration, not a raw %. **A raw-accuracy badge is
    refused**: a fixed % target reproduces the exact failure the points-target
    ban encodes (rewards safe guessing, dreads hard sets).
  - **IN YOUR OWN WORDS** — a teach-back graded solid (integrity-clean);
    gold flavour at `connects`. Puts the crown-jewel instrument into the chase.
  - **LOCK IT: {topic}** / **BOUNCE BACK: {topic}** — 0–2 named offers picked
    deterministically from the ledger (nearest-to-solid; REPAIR exit) —
    `kid_wrap.badge_hints` already prototypes exactly this. Offers only ever
    name non-solid topics (no farming mastered ground). An untaken offer
    rolls forward, never "failed".
- Board rides the published quiz JSON (no new fetches); resolves in the
  nightly achievements pass; renders on the quiz start/end screens and the
  Friday wrap.

**Parents and the board — the narrow amendment to "kid-facing only":**
parents may hear **offers forward and stories backward, never scores**.
Monday: "on his board this week: locking in Fractions, and a comeback on
Angles — ask him which he's going for" (a plan, not a result; and it satisfies
the transparency law byte-for-byte, because it's the same board the kid sees
first). Friday: at most one taken contract, narrated as the win. **Never
tallies** — "2 of 3 taken" is a grade and hands over interrogation ammunition;
completion rates and badge counts stay banned on parent surfaces.

**The deal card** (pending decision in BETA-BRIEF): the weekly board
supersedes it. One weekly-target system, not two half-built ones — the deal
card's family-agreement layer can return later as an opt-in on top of the
board if wanted.

**Kid-consent gate:** t1 can't test kid-affect (t1's kid is Rich). Harrison's
and Roshan's reaction at the weekly sit-down is an explicit ratification gate
before parent-visible offers roll to y8/y9.

---

## 8. The name

**Keep "XP Daily" through beta.** The brand is load-bearing (domain portfolio
bought, xpdaily.com.au canonical, ACMA "XP Daily" sender registration in the
entity plan, three families onboarded on the vocabulary) and there is zero
parent evidence against it — the unease is really about the invisible meaning
layer, which §7 fixes for free. The kid-facing name *should* be game-coded:
fun is the distribution strategy.

**End-state recommendation: two-name architecture at the commercial gate.**
The kid surface stays XP Daily (the game he opens); the parent surface gets
its own descriptive sub-brand — working name **"The Full Picture"** (the
report's own phrase) — so the parent-facing product stops leading with XP
without a rename. Decide with real parent-interview signal at the
family-#2/commercial gate, not before. Adopt the good vocabulary now for free:
the board can speak "claims" (Battleground's language) without any rebrand.

---

## 9. Guarantees: sent on time, at quality — the SLOs

What "guaranteed" means, concretely, for every scheduled parent send:

1. **Trigger:** pg_cron (Sydney-local, DST-proof) primary; GitHub cron as
   cursor-guarded backup. No scheduled parent send depends on GitHub's
   best-effort queue again (it skipped all three crons this Friday).
2. **Delivery:** cursor advances only on provider acceptance (already law for
   Friday); implement the Mobile Message **delivery webhook** so acceptance
   becomes confirmed delivery — the current fail-open blind spot.
3. **Content:** deterministic fact card → validator → deterministic fallback
   on every touchpoint (wed_checkin pattern everywhere); **operator preview
   window** for any new/changed format — the `--dry-run` preview HTML goes to
   Rich the day before, for the first two weeks of that format only
   (ROADMAP's "human-reviewed initially" promise, currently lapsed, reinstated
   with an explicit retirement).
4. **Rendering:** build stamp on every page; verify() asserts the stamp of the
   render it just uploaded; watchdog rung asserts the live page after every
   scheduled publish. (§0 — the fix for this week's failure, generalised.)
5. **Routing:** delete the legacy `MOBILE_MESSAGE_TO_PARENTS` fallback for
   `parents:<code>` targets — today a mistyped per-family secret would
   silently text a new family's report to *Rich's* family. Fail loud instead.
   Sequenced before any new family.
6. **Config & consent:** per-family, per-touchpoint on/off as real private-repo
   config consulted by every send (promised in REPORTING.md, implemented
   nowhere — currently the only "off" is deleting a secret, which kills
   Friday too). Opt-out path documented in the welcome + portal footer, and
   provider opt-out webhooks ingested — the Spam Act obligations bite exactly
   when parents start paying.
7. **Measurement (currently zero):** delivery-receipt rate · Friday link-tap +
   portal-visit counts (privacy-safe server-side analytics) · opt-out count ·
   kid completion-rate and nudge-to-play latency (the motivation metric) · a
   fortnightly 3-question parent pulse. Go/no-go thresholds gate the
   10-family rollout. We are currently flying the entire comms layer blind.

---

## 10. Build order

**Week 1 — ship what exists, fix what lied:**
1. Netlify publish fix (owner, dashboard) + build stamp + stamp-verify +
   watchdog rung. Re-verify all three live pages dark.
2. Kid wrap: wire it (import + deploy + real `kid_wrap_url`), fix its stale
   cabinet (drop Boss Slayer; add Full Claim, Personal Best), apply the dark
   repaint. This is a **transparency-law compliance fix**, not a feature —
   parents have received Friday detail for weeks that the kid's mirror surface
   never showed.
3. Friday page: activity-denominator fix; cumulative-by-subject strip
   (already computed, never rendered); fluency-illusion sentence; portal-link
   footer slot.
4. "Bookmark this" text to each family (the zero-build always-available win).
5. pg_cron slots for wed/fri sends; `calendar.json` gating every scheduled
   send.
6. Mon 31 Aug sweep side-by-side happens regardless — its promotion is the
   gate for §4 step 2.

**Week 2 — the new surfaces, t1-first:**
7. Subject-spine Friday report (§3) behind the operator preview window; t1
   first, then all seats.
8. Portal v1 (`/p/<slug>/`): NOW strip + This-Week panel + subject cards +
   archive links + legend. Monday-evening + Friday republish. Dated report
   paths begin.
9. Weekly board, kid-facing, t1 only; sit-down reaction gate before y8/y9.
10. notify.py fallback deletion + per-family config + delivery webhook.

**Week 3+ (gated):** Monday SMS (t1 → household-consolidated all-seats, after
two clean automated-sweep Mondays) · Wednesday radar clause (digit-free date
phrasing, amendment ratified) · end-of-term wrap build before 25 Sep ·
EXAM-MODE.md before the first y9 exam block.

**Refused, with reasons:** a rename now (§8) · parent-visible badge tallies
(§7) · a raw-accuracy badge (§7) · a Monday SMS before the sweep promotion
gate (§4) · same-night results on the portal (§5) · a second weekly channel
(email duplicates SMS content; email's designed first use is magic-link auth;
a monthly term digest can come later if parents ask) · lightening Wednesday
(already light, ratified final) · custom auth of any kind (magic link at
family #2, nothing homegrown).

---

## 11. What needs Rich's ratification (the actual decisions)

1. **Friday subject-spine redesign** (§3) — supersedes the current section
   order of the ratified Friday page.
2. **Monday touchpoint + Monday law** (§4) — new touchpoint; amends the
   canonical rhythm table; requires REPORTING.md amendment.
3. **Portal build + portal laws** (§5) — freshness contract, aging rule,
   dated archives.
4. **Household consolidation** (§2) — one scheduled text per household.
5. **Achievements amendment** (§7) — weekly contracts; parents hear offers
   forward / stories backward, never counts; deal card superseded.
6. **Name** (§8) — keep XP Daily; two-name decision deferred to commercial
   gate.
7. **The guarantees package** (§9) — including the preview window and the
   metrics, which change what Rich sees each week.
8. Kill-list confirmations (§10 "Refused").

Each lands as its own REPORTING.md / ACHIEVEMENTS.md amendment with explicit
supersession scope, per the working model. Until then, current law stands.
