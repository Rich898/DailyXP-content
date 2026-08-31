# KID-WEEKLY-FRAMEWORK.md — the kid's weekly reporting framework

**Status: PROPOSAL, not ratified. Written 31 Aug 2026 in response to Rich's
brief** ("does the kid get a version of the week ahead — showing not just
topics but what achievements are available, for showing up, for mastery, by
subject? What do end-of-week and big-picture look like? What does great look
like for the kid putting his 5 minutes in every day?").

Where this file conflicts with `KID-REPORT.md`, `ACHIEVEMENTS.md` or
`REPORTING.md`, those remain law until Rich ratifies the amendments in §13.
Visual mockups (sample data, "Sam") live at `preview/kid/` — board, wrap and
season pages, walkable off a checkout.

---

## 1. The frame: the kid's three questions, one loop

The parent portal answers the parent's three questions with three designed
pages. The kid deserves the same architecture — same ledger, opposite entry
point. His three questions, in his language:

| Question (kid's words) | Surface | When | Status |
|---|---|---|---|
| What's coming, and what can I win? | **THE BOARD** | Monday, by 4pm | NEW |
| How did my week land — what did I claim? | **THE WRAP** | Friday evening | built + live; gains one section |
| What have I actually built? | **THE SEASON** | evergreen, refreshed Friday | NEW |

And the loop that joins them — the kid's mirror of the parent's
plant → tend → harvest:

> **Monday the board goes up** (here's the ground, here's what's up for
> grabs) → **every night's run advances it** (the quiz is where the work
> happens; the nudge stays one line) → **Friday the board settles** (the wrap
> pays out what was claimed and names what rolls on) → **the Season banks
> it** (the long arc that makes 5 minutes a night visible as a career).

The parent loop is weekly and narrated; the kid loop is nightly and played.
Same week, same facts, two languages — exactly the asymmetry KID-REPORT.md §3
already codifies, extended from one Friday page to the whole week.

**Why this matters strategically:** the weekly board is the piece of
PARENT-COMMS-V2 §7 (ratification item D2) that makes the meaning layer
visible — today badges surface only *after* the fact, so XP looks like the
point of the product. A board declared Monday turns achievements from a
receipt into a *chase*, and a kid chasing this board is chasing the pedagogy:
every slot on it is a deterministic read of the ledger.

---

## 2. What great looks like — the week of a kid doing the work

*(The brief's central question, answered as a walkthrough. Sample kid "Sam";
every number below appears in the mockups.)*

**Monday 3:59pm.** The board published with the daily set. The 4pm nudge —
already worded for this, since 31 Aug: *"New week on the board. XPDaily is
up 👊"* — lands with the link. Sam opens THE BOARD and sees, in order:

* **TONIGHT** — he walks in 50 XP short of a rank-up and one night short of a
  Silver streak. Both land *tonight* if he plays. (Monday is the fresh-start
  moment; the board spends its urgency there.)
* **UP FOR GRABS** — five contracts, declared for the week, settling Friday:
  On the Board (4 of 5 nights) · Clean Hands Week (3 clean runs) · In Your
  Own Words (one teach-back graded solid) · **Lock It: Linear equations**
  (Maths — at the door of solid) · **Bounce Back: Angles** (Maths — the
  comeback). Showing up, craft, and mastery *by named subject* — the three
  families Rich asked for, as five specific offers.
* **IN REACH** — the standing trophies closest to falling: Silver streak
  (tonight), **Full Clear: Science** (one topic away), Untouchable: Fractions
  (its third spaced check is due this week).
* **NEW GROUND** — what school brings this week, per subject, same facts as
  his parents' Week Ahead page: Maths moves into solving equations with
  brackets; Science moves into how body systems work together; History moves
  into primary sources. No verdicts — a map, not a report.
* **BOSS RADAR** — the Science topic test, 10 days out, with the honest line:
  his sets are already steering at it.
* **THE SHAPE OF THE WEEK** — four runs and Friday's Battleground.

Total read: under a minute. Then he plays — and Monday night the end screen
confirms the rank-up and the Silver streak the board promised. The board kept
its word within six hours of going up. **That is the trust loop that makes
next Monday's board worth opening.**

**Tuesday–Thursday.** Nothing new to read — deliberately. The nudge stays one
line; the quiz is the surface. (Phase 2 puts a one-line board strip on the
quiz start screen — "Night 3 · Lock It: Linear equations is in tonight's
set" — so the stakes travel with the play, not with more messages.) Wednesday
his teach-back on the Crusades lands the In Your Own Words contract. Thursday
his best-ever night (1,240 XP) takes Personal Best and locks Linear
equations — the contract he could see coming since Monday.

**Friday.** The Battleground: 3 of 4 zones claimed, no penalty on the
fourth. Then the wrap — hero word **STRONG** — and its new section, **THE
BOARD, SETTLED**: four contracts claimed, and Bounce Back: Angles **rolls
on** to Monday's board, same terms, no strike against him. Below it, the
unlocks (Silver Streak, Locked It, Personal Best, Perfect Week — the 5/5
trophy on top of the 4/5 contract), what he beat, his own words quoted back
with the CAN CONNECT IT stamp, what's stalking him next week with a
beat-it line for each, the one move. The last line: *the new board goes up
Monday.*

**Any time.** THE SEASON — his evergreen page: Lieutenant, level 6, the
XP-by-week arc, records (best night, longest chain, Battleground best), the
full cabinet, and **THE MAP** — every subject's topics as territory tiles in
the exact colours his parents' Overall Picture uses. Plus the ladder track:
four topics at *can connect it*, all four earned by explaining — the one
track in the game that can't be grinded.

Twenty-five minutes of play, one minute of reading Monday, three of reading
Friday. Every one of those minutes was either **playing** or **seeing what
the playing built**.

---

## 3. The kid's week, end-to-end (surface map)

| When | Surface | Job | Change |
|---|---|---|---|
| Mon ≤4:00pm | **THE BOARD** `/w/<slug>/board/` | Orient + arm: ground, contracts, offers, radar | **NEW page** |
| Mon–Fri 4:00pm | Nudge SMS | One line + link (Mon's copy already says "board") | unchanged |
| Mon–Fri evening | The quiz | The work itself; end screen pays badges instantly | unchanged (phase 2: board strip) |
| Fri evening | **THE WRAP** `/w/<slug>/` | Celebrate + re-arm; **settles the board** | built; **+1 section** |
| Any time | **THE SEASON** `/w/<slug>/season/` | The big picture in game language | **NEW page** |

Hard rule carried over from the parent side, inverted: **zero new kid
sends.** The kid already gets exactly one text a day; this framework adds
pages behind the links he already taps, never messages. A teenager's channel
discipline is stricter than a parent's, not looser.

The three pages cross-link with a fixed bottom nav (Board · Wrap · Season),
the parent portal's app-bar pattern on the kid's own design system.

---

## 4. THE BOARD — Monday, forward (the kid's week ahead)

**The one-line test:** a mission briefing, not a syllabus. If a section
would sit comfortably in a school newsletter, it's wrong; if it would sit in
a season-opener screen, it's right.

### Sections, in order

1. **TONIGHT** — at most two immediate stakes, picked deterministically:
   a rank-up within one typical night's XP; a streak tier landing tonight;
   otherwise the night count toward On the Board. Monday at 4:01pm this is
   the first thing on his screen, and it is always *tonight-shaped* — the
   board's whole job compressed into "play tonight and something lands".
2. **UP FOR GRABS — the contracts.** Five slots max (V2 §7, D2), declared
   Monday, settled Friday, keyed `Contract|{iso_week}|{name}`:
   * **ON THE BOARD** — canonical runs 4 of 5 school days. (4, not 5 — one
     sick Tuesday must never kill the week's goal by Wednesday. Perfect Week
     remains the 5/5 trophy on top.) *Family: showing up.*
   * **CLEAN HANDS WEEK** — 3+ nights with zero lucky guesses and zero
     confident-wrongs. The only accuracy-shaped offer the doctrine permits —
     calibration, not a raw % (a raw-accuracy target rewards safe guessing
     and dreads hard sets; refused in V2 §10). *Family: craft.*
   * **IN YOUR OWN WORDS** — one teach-back graded solid (integrity-clean);
     gold flavour at `connects`. Puts the crown-jewel instrument into the
     chase. *Family: craft.*
   * **LOCK IT: {topic}** — 0–1 named offer: the topic nearest solid, from
     the ledger (`kid_wrap.badge_hints` already computes exactly this).
     *Family: mastery, named by subject.*
   * **BOUNCE BACK: {topic}** — 0–1 named offer: a REPAIR topic whose exit
     is queued. *Family: mastery, named by subject.*

   Each tile names its family and subject (MATHS · LOCK IT: LINEAR
   EQUATIONS), states its terms in one line, and says "settles Friday".
   Offers only ever name non-solid topics — no farming mastered ground.
3. **IN REACH** — the standing (permanent) trophies nearest to falling, so
   the cabinet is a chase all week, not a Friday receipt: the next streak
   tier with nights-away; **FULL CLEAR: {subject}** with topics-away (the
   per-subject achievement Rich asked about, made visible *before* it's
   earned); an Untouchable spaced check falling due. Cap three, each with a
   progress bar. This is `badge_hints`, promoted from the wrap's cabinet
   footer to a Monday section.
4. **NEW GROUND** — per subject: what school brings this week. Same facts as
   the parents' Week Ahead (`monday_brief.week_ahead()` — the same
   moves-into/continues clauses), dressed as terrain: NEW GROUND chips on
   what's new, "holds" on what continues. Where a contract lives in a
   subject, the row says so — the map and the missions point at each other.
5. **BOSS RADAR** — dated things *he* has to show up for (test, due task),
   as countdowns, with the steer line ("your sets are already steering at
   it"). A kid-dressed subset of the parent's UPCOMING DATES: releases and
   admin dates stay parent-side; the radar carries what demands something of
   him. KID-REPORT.md §9's open question, answered: yes, framed as the boss
   approach — a countdown a player reads as preparation time, not dread.
6. **THE SHAPE OF THE WEEK** — five tiles, Mon–Thu runs, Friday
   ⚔ BATTLEGROUND ("four zones on the week's contested ground — Full Claim
   pays the flag"). The skeleton is a constant; showing it makes Friday an
   event he's counting toward from Monday.
7. **The closing line** — "Everything up there advances one way: play
   tonight." The board never ends with a list; it ends with the move.

### The board's laws (the kid Monday law)

* **Stakes, never judgments.** The board may say where a topic *sits* (the
  wrap already said it on Friday — same fact, still true Monday); it may
  never re-judge last week. No verdict words, no misses, no "you didn't".
  Monday opens a week; it doesn't reopen the old one.
* **Offers, never orders.** Every slot is phrased as up-for-grabs, not
  assigned. The kid picks his pursuit — autonomy is the difference between
  a game and homework with points.
* **Rolls on, never failed.** An untaken contract reappears (if the ledger
  still nominates it) with identical framing. The board has **no memory of
  misses**: it re-derives fresh every Monday from the live ledger and never
  counts attempts ("back on the board", never "third week running").
* **Fresh start, structurally.** Monday's board is computed from where the
  ledger *is*, not from what last week's board *wanted*. A wiped-out week
  produces the same clean board a strong week does — the fresh-start effect
  is the single best re-entry mechanic there is, and guilt is the single
  worst.
* **The reveal order (already ratified, V2 §4):** the kid sees his week
  first. Board live by 4pm; the parent's Monday pointer fires 18:45. Any
  parent-facing mention of the board (phase 3) is the same board he already
  saw — the parent joins his story, never fronts it.
* **No XP bounty on contracts in v1.** XP stays the showing-up meter;
  contracts pay in claims, cabinet progress and the settle screen. A fixed
  small bounty is a one-line change later if the sit-down says the board
  needs more juice — listed as an open dial in §13, not built by default.
  (Rationale: the moment contracts pay XP, the board and the level economy
  couple, and every future tuning of one drags the other.)

---

## 5. The nightly loop — where the board lives Tuesday to Thursday

Nothing new arrives midweek, by design (the no-nagging law is load-bearing
for a teenager). The board lives in the play:

* **Phase 1 (pages only):** the end screen already pays badges the moment
  they're earned — contracts resolve in the same nightly achievements pass,
  so a taken contract surfaces as its badge/claim naturally.
* **Phase 2 (shell v3.x, via the mechanics process):** a one-line board
  strip on the quiz start screen — "Night 3 · ⚑ Lock It: Linear equations is
  in tonight's set" — and settle ticks on the end screen. The board rides
  the published quiz JSON (no new fetches, same privacy model). This is the
  V2 §7 line "renders on the quiz start/end screens", staged so the page
  framework never waits on shell work.

---

## 6. THE WRAP — Friday, backward (one new section, everything else stands)

The wrap is built, live and ratified (KID-REPORT.md). One structural
addition and one line:

* **THE BOARD, SETTLED** — new section between THE RUN and UNLOCKS. One tile
  per contract: **CLAIMED** (kelp, with the specific act and day) or
  **ROLLS ON** (neutral, with the honest state and "back on Monday's board,
  same terms"). Never red, never "failed", never a percentage of contracts
  taken. Placement rationale: the run states the week, the board settles the
  *named* stakes, and only then do UNLOCKS deliver the surprises — declared
  goals first, variable rewards second; that ordering is what makes Monday's
  declarations feel binding rather than decorative.
* **The trail line** — the wrap currently ends looking backward; it gains
  "the new board goes up Monday" (in the footer block), closing the loop the
  same way the parent's Wednesday points at Friday.

Everything else — hero word, THE RUN, UNLOCKS, WHAT YOU BEAT, FINISHING
MOVE, STALKING YOU NEXT WEEK, THE ONE MOVE, the ladder explainer — stands
exactly as ratified and shipped. The wrap's targets section and the next
board are two views of one queue: what stalks him Friday is what the board
offers him Monday (Bounce Back / Lock It draw from the same ledger rows), so
the weekend holds one continuous story: *named Friday, offered Monday,
played nightly, settled next Friday.*

---

## 7. THE SEASON — evergreen, the kid's big picture

The kid's mirror of the parents' Overall Picture — the answer to "what have
I built", readable in ninety seconds, in the game's own vocabulary. The
parent page is a risk map (weakest first, revision priorities); the kid page
is a **holdings map** (what you've taken and held, what's still contested).
Same facts, same colours, opposite emotional entry — that inversion is the
whole design.

### Sections, in order

1. **The identity plate** — rank insignia, rank, level, season XP, progress
   bar to next rank-up. The long arc's face.
2. **THE ARC** — XP by week across the season (the wrap's XP-by-day bars,
   zoomed out). Points-ride-on-difficulty caveat travels with it, as
   everywhere.
3. **RECORDS** — personal bests only, never comparisons: best night,
   longest chain, best Battleground claim, Perfect Weeks this season. The
   only rival on this page is his own history.
4. **THE CABINET** — all twelve badges, earned lit / unearned dim with
   their earn-lines (the trophy room the wrap only footnotes), plus the
   IN REACH hints. A kid who can *read* the whole cabinet can plan a chase.
5. **THE MAP** — per subject, one tile per topic, coloured by its band,
   weakest first, with "{n} zones · {k} contested". **Identical colour
   language and identical facts to the parents' Overall Picture bars** —
   transparency law kept byte-level (his page says "contested", theirs says
   "to watch"; the tiles match 1:1). Full Clear renders here as the
   subject's endgame: "1 zone from FULL CLEAR."
6. **THE LADDER TRACK** — topics counted per depth rung, with the honest
   explainer the wrap already carries: MCQs cap at *can list it*; only
   explaining moves a topic to *can connect it*; *can apply it elsewhere*
   isn't earnable yet — and the page says so ("no way to earn this yet —
   coming"), because an unreachable rung honestly labelled is a horizon,
   and silently unreachable is a lie. The count at `connects` is the page's
   proudest number: the track that can't be grinded.
7. **SEASON ARC / WHAT'S COMING** — weeks left in the season, the finale
   (term end), the next-chapter tease (SEASONS.md retention logic:
   something is always coming).

### Season laws

* **Refreshes Friday, with the wrap** (plus Monday's republish for the nav
  and board link). The batched-judgment spine extends to the kid: mastery
  moves on this page weekly, never same-night — the *quiz* is the live
  surface; the season is the album, not the feed.
* Depth rungs render under the same calibration gate as every other surface
  (`UNDERSTANDING.md` §7 / the existing env switch).
* Accuracy does not appear here at all — it's a weekly line-to-beat on the
  wrap (ratified), not a career statistic. A career accuracy number is a
  grade wearing a costume.

---

## 8. The motivation architecture — why each piece is shaped this way

The framework leans on five well-evidenced mechanisms, each implemented in
its *kind* form and each already consistent with repo doctrine:

1. **Fresh starts** (the fresh-start effect): Monday's board is a clean
   slate by construction (§4). The strongest known re-entry lever for a
   lapsed habit, and the reason the board must never carry debt.
2. **Goal gradient** (effort accelerates near a goal): IN REACH bars,
   "1 night away", "50 XP from Sergeant", front-loaded level curve. The
   board's job is to keep at least one near-goal visible every single week.
3. **Endowed progress**: the streak *walks in* at its Friday value; On the
   Board opens at 1/4 after Monday's run. He starts every week already
   moving.
4. **Loss aversion, used gently**: the streak is the system's one
   loss-shaped mechanic, deliberately softened — school-day semantics,
   absence law, and the 4/5 contract so a single missed night costs a chain
   but never the week. We never add a second loss mechanic; the board is
   all-upside on purpose.
5. **Autonomy + competence + relatedness** (self-determination theory —
   the difference between play and compliance): offers not orders (§4);
   coaching that shows the counter (competence is *seeing how to win*, and
   the wrap's beat-it lines plus the board's "the way in" lines are that);
   the fellow-player voice (relatedness without surveillance).

And the two house rules that make the rewards *honest* rather than merely
effective, restated because they are the levy every new surface must pay:

* **The reward is load-bearing** (ACHIEVEMENTS.md): every chaseable thing on
  the board reads the real ledger — the thing that feels good to unlock IS
  the thing we want done. No cosmetic goals, no volume-farming goals, no
  raw-% goals.
* **Difficulty belongs to the set; the only rival is his own past self.**
  Every surface, every line.

---

## 9. When he's stuck — the support design, scenario by scenario

*"Support them when they are getting stuck" — the brief. Stuck has three
distinct shapes, and each gets a different, specific answer:*

**Didn't show (the Quiet week).** The nudge stays one line — never
escalates, never counts misses. Friday's wrap says what a quiet week is
("the run's still here — it picks back up when you do") with no debt
language; ON THE BOARD simply isn't claimed and *rolls on*. Monday's board
is structurally identical to the one a perfect week produces: TONIGHT still
leads with a live stake, because the ledger always has one. Re-entry costs
nothing and is rewarded immediately — the streak restarts at 1 and Bronze is
2 nights away, which is a *nearer* goal than Gold was.

**Showed up and it got harder (the Slower week).** The hero owns it in the
house voice: "the sets came in harder — that's the game finding your edge,
and the edge is where topics rank up" (desirable difficulties, said so a
14-year-old believes it). Every stalking target carries its trap (what was
picked and why the trap works) and its beat-it coaching line — the counter,
not the commiseration. Next Monday, Bounce Back offers lead the contracts:
the struggling topic becomes the week's featured comeback, with "the way in"
named. Calm Hands and Sure Shot — the craft badges — exist precisely so a
kid recovering a topic has something to *win* during the recovery, before
the topic itself comes good.

**Stuck on one thing (the REPAIR topic).** The system's framing everywhere:
a comeback story in progress, never a deficit. The rotation has it queued
(said on every surface); the misconception is named specifically (the one
thing to fix, not "practise more"); the teach-back is offered as the
finishing move. If it rolls three Mondays running, the board's no-memory law
means he's never told that — the *planner* escalates (repair weighting), the
*language* never does. Machines schedule persistence; humans would nag.

**And the quiet failure mode — coasting** (showing up, clean runs, nothing
deepening): the ladder track answers it. A cabinet full of consistency
badges with `connects` sitting at zero is visible on the Season page, In
Your Own Words is on the board every single week, and the teach-back is the
only path up. The framework never lets "did my five minutes" and "getting
somewhere" drift apart silently — that drift is the fluency illusion, and
catching it is the founding mission.

---

## 10. Transparency and safeguarding — the checks, law by law

* **Nothing on the parent surface is hidden from the kid** (KID-REPORT §2):
  already true for the wrap; the board extends it forward — the NEW GROUND
  facts are the parents' Week Ahead facts, same engine
  (`monday_brief.week_ahead`), and the kid sees them *first* (clocks, §4).
  The per-teacher hedge line stays parent-side only: it's a statement about
  our sweep confidence, not a fact about him (he knows who his teacher is).
* **Nothing on the kid surface becomes ammunition** (ACHIEVEMENTS.md
  kid-facing law + V2 §7 amendment): parents hear **offers forward, stories
  backward, never tallies** — Monday may say "on his board this week:
  locking in Linear equations — ask him which he's going for" (phase 3,
  gated); Friday may narrate at most one taken contract as the win. "4 of 5
  contracts" never crosses the wall; the kid's own pages may tally freely
  (COLLECTED 8/12) because a tally he holds is a collection, and a tally
  held over him is a grade.
* **Integrity exception unchanged and absolute:** quarantined teach-backs
  never surface kid-side in any form, on any of the three pages; the board
  and season consume the same pre-gated objects as the wrap.
* **No comparison, anywhere:** no sibling, no cohort, no "most players".
  RECORDS are self-records. The y8/y9 boards are separate pages with
  separate slugs; nothing cross-links a household's kids.
* **Language laws enforced in code**, not in review: `violations()` runs
  against the full rendered page for all three pages (the wrap's existing
  mechanism, extended), and a page that breaches ships nothing.

---

## 11. Build notes (reuse-first, same discipline as the portal build)

**Facts already computed, reused byte-identical:**
`friday_report.build_card` + `report_stories` (wrap inputs, unchanged) ·
`monday_brief.week_ahead()` (NEW GROUND + radar, the parent engine) ·
`kid_wrap.badge_hints` (IN REACH; today's prototype of the offers) ·
`achievements.py` + `achievements_earned.json` (cabinet, unchanged) ·
`soundbyte.current_school_streak` (one streak definition everywhere) ·
weekly snapshots + `runs.json` (season arc, records, map).

**New, deterministic, no AI:**

* `tools/weekly_board.py` — declare (Monday: derive the five slots from
  ledger + streak + calendar; write `work/boards/<iso_week>.json` to the
  private repo), resolve (nightly, inside the achievements pass — same
  diff-against-ledger shape), settle (Friday: read for the wrap). Contracts
  keyed `Contract|{iso_week}|{name}`. Idempotent, re-runnable, cursor-free
  (the board file is its own record).
* `tools/kid_board.py` — renders THE BOARD from `weekly_board` + the Monday
  facts. Published to `/w/<slug>/board/` (existing `w` slug, existing
  one-page-per-path deploy + stamp-verify machinery).
* `tools/kid_season.py` — renders THE SEASON from game facts + snapshots +
  the badge ledger. Published to `/w/<slug>/season/`.
* `kid_wrap.py` — gains `_board_block()` (THE BOARD, SETTLED) + the trail
  line + the bottom nav. Tests extend `test_kid_wrap`'s pattern: the
  transparency union lock, the language-law lock on full pages, board
  determinism, and the roll-forward invariant (the strings "failed",
  "missed" can never render on a board tile).

**Clocks (all Sydney, all pg_cron per the B1 doctrine):** board renders and
publishes with Monday's 2pm daily-quiz run (it rides the same targets the
planner just consumed — zero extra fetches) and must verify live before the
4pm nudge; the parent portal's Monday 18:45 slot stays untouched — the
reveal order is enforced by clocks, not promises. Wrap + season publish in
the existing Friday run, season re-stamped Monday for the nav.

**Phasing and gates:**

1. **Phase 1 — pages, t1 only.** Board + settle section + season, shadow →
   Rich eyeballs previews → live for t1. **The Harrison/Roshan sit-down
   reaction is the explicit gate** (D2) before y8/y9 get boards.
2. **Phase 2 — the quiz start/end strip**, through the mechanics process
   (isolated preview, approved for fun and quality, then live).
3. **Phase 3 — the parent Monday mention** (offers forward), only after
   phase 1 has survived the sit-down and the Monday SMS content-push gate
   (B6 ×2) is history.

**Calendar dependency:** the board is gated by `calendar.json` (C1) like
every scheduled surface — a holiday Monday publishes no board, and the last
board before term break carries the finale framing instead of contracts.

---

## 12. Deliberately NOT in this framework (the kill list)

* **No leaderboards, no sibling anything, ever** — standing law.
* **No raw-accuracy contract** — refused in V2 §10; Clean Hands is the only
  doctrine-safe accuracy-shaped offer.
* **No XP bounties on contracts in v1** — the open dial, §4.
* **No new kid SMS** — the daily nudge is the whole push channel.
* **No live midweek page updates** — the quiz is the live surface; the
  pages keep the weekly rhythm (same reasoning as the parent freshness
  contract: an always-on surface must not become a nightly interrogation of
  himself).
* **No red/failed states on the board** — CLAIMED and ROLLS ON are the only
  two settle states.
* **No parent-visible tallies or badge counts** — offers forward, stories
  backward (V2 §7).
* **No cosmetics economy yet** — SEASONS.md owns cosmetics later; nothing
  here spends that budget.

---

## 13. What needs Rich's ratification

1. **The three-surface shape + names** — THE BOARD / THE WRAP / THE SEASON
   under `/w/<slug>/`, with the bottom nav. (Names deliberately match the
   vocabulary already live in the nudge copy and the Battleground.)
2. **The five contract slots** — the set, the copy, and 4-of-5 for On the
   Board.
3. **The kid Monday law** (§4: stakes never judgments · offers never orders
   · rolls on never failed · no memory of misses) — lands as a KID-REPORT.md
   amendment alongside the board section.
4. **The wrap change** — THE BOARD, SETTLED placement + the trail line.
5. **THE SEASON v1 scope** (§7) — including accuracy staying off it.
6. **The no-XP-bounty default** — or set the dial now.
7. **Phasing + gates** (§11) — t1 first; the sit-down gates y8/y9; shell
   strip is phase 2; parent mention is phase 3.
8. **Doctrine amendments on build:** ACHIEVEMENTS.md gains the weekly
   contracts (superseding the deal card, per V2 §7); KID-REPORT.md gains
   board + season sections; REPORTING.md's rhythm table gains the kid rows.

Until each is ratified, current law stands. Mockups: `preview/kid/`.
