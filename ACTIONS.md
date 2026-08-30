# ACTIONS.md — the iron-out list (parent comms + reliability)

**Opened 29 Aug 2026** after the light-theme Friday send. Rule: nothing on this
list is "noted" — everything is DONE, IN FLIGHT with an owner, or GATED on a
named thing. Insights without an action row don't belong in this file.

Status key: ✅ DONE (on this branch, tests green) · 🔴 RICH — needs Rich's
hands or say-so · 🟠 READY — Claude builds it next session on the go-ahead ·
⏳ GATED — blocked on a named precondition · 📋 DECIDE — a ratification call
(PARENT-COMMS-V2.md §11).

**29 Aug 2026 — alignment recorded:** Rich read the proposal (the "Full
Picture" page) and is aligned on decisions 1–8. Formal doctrine amendments
land with each build, not before. **The execution plan for the whole program
is `PARENT-COMMS-BUILD-BRIEF.md`** — fresh sessions boot from it (work items
W1–W8; each session asks Rich which item today).

**30 Aug 2026 — COURSE CHANGE (parent portal):** Rich aligned that the parent
report is a **three-pronged** approach — Week Ahead (Mon) / This Week (Fri) /
Running Picture (Fri) — living in a real **Parent Portal** (also the future
account-management surface), as **three DESIGNED pages, not one scroll**. The
29–30 Aug single-page `portal_page.render()` was rejected as under-designed.
The deterministic FACTS engines built this session are kept and reused
(`monday_brief.py` — Week Ahead + Monday-law + pointer SMS; `subject_blocks`/
`fluency_catch`; portal facts helpers `subject_cards`/`term_trends`/
`_confidently_shallow`). **Fresh sessions now boot from `PARENT-PORTAL-BRIEF.md`**
to rebuild the presentation to an excellent standard. W1 (scheduler) is live;
W2/W3 remain shadow on the branch and are unaffected.

---

## A. Now (this weekend)

| # | Action | Owner | Status |
|---|---|---|---|
| A1 | ~~Unstick Netlify publishing~~ — **CLOSED, not the cause.** Rich's Claude-browser inspection (29 Aug, read-only): auto-publishing on, nothing locked, newest deploy Published. Real cause → A11. | Rich ✓ | ✅ verified |
| A11 | **Case-collision root cause fixed.** Netlify lowercases paths; our mixed-case slugs meant a carried-forward live page and its own replacement collided in one manifest and the stale one won — pages only landed when NEW to the site (why y8/y9 serve Thursday's *light* builds and t1 serves its 21 Aug page). All paths/URLs/manifest keys now lowercase at use; future slugs generate lowercase; regression tests lock it. RUNBOOK Gotcha #11. | Claude | ✅ this branch |
| A12 | **Stale-page recovery button:** `redeploy=true` input on the Friday workflow — re-renders + re-deploys the already-sent week (no SMS, no cursor/snapshot writes). Fired 29 Aug (run #17): all three pages live, dark, stamp-verified; carried-forward counts finally reconcile. Test SMS with the report link delivered to parents:t1 same day. | Claude | ✅ verified live |
| A2 | **Build stamp on every report page** (`<meta xpdaily-build>` + footer): View Source answers "which build is this". | Claude | ✅ this branch |
| A3 | **Verify that can't lie:** `netlify_deploy.verify()` now demands the exact stamp of the render it just uploaded (with a short CDN-propagation retry). A locked/stale site now fails the run loudly and the SMS goes out link-less instead of linking a wrong page. *This alone would have caught Friday's failure at send time.* | Claude | ✅ this branch |
| A4 | **PII out of public Actions logs:** Friday runner no longer prints kids' first names or per-kid report URLs (this repo is public → its logs are public). Dry-run SMS bodies go to preview files, not logs. | Claude | ✅ this branch |
| A5 | **Dry-run preview artifact:** `friday-report.yml` dry_run dispatch now uploads `preview_report_*` (page + SMS text) as a private artifact — the operator pre-send review window for any new format. | Claude | ✅ this branch |
| A6 | **Misroute landmine defused:** `notify.py` no longer falls back from `parents:<code>` to the shared legacy list — a mistyped per-family secret can never text one family's report to another household. Senders' hard-aborts now actually fire. | Claude | ✅ this branch |
| A7 | **Activity math honest:** a pipeline HOLD or recorded absence no longer counts against the kid — denominator reads the completion record (`schedule.json`, any of its shapes), and a fully-excused shortfall can't produce "Quiet — nudge the habit". *Law served: our gaps are never reported as the kid's.* | Claude | ✅ this branch |
| A8 | **Test suite runs on the pipeline's own Python:** two test files used 3.12-only f-strings and couldn't execute on CI's 3.11 at all. Fixed; all suites green on 3.11. | Claude | ✅ this branch |
| A9 | **RUNBOOK Gotcha #10:** `--no-sms` deploys to LIVE per-kid URLs (how Thursday's light pages went live); inspection is `--dry-run`. | Claude | ✅ this branch |
| A10 | **Merge to main.** Done 29 Aug: PR #16 merged (strategy doc + hardening + case-collision fix), A12 fired, live pages verified dark. | **Rich** ✓ | ✅ |

## B. Before Friday 4 Sep (next send)

| # | Action | Owner | Status |
|---|---|---|---|
| B1 | **Friday/Wednesday sends move to pg_cron** (Supabase `xp_schedule` rows; GitHub crons demoted to cursor-guarded backup). GitHub *skipped all three* Friday crons on 28 Aug — the send only happened because Rich pressed the button. Also fixes the 4 Oct DST hour-shift before it hits parent sends. **DONE 29 Aug (`supabase/005_friday_ladder.sql`, applied live).** Wed check-ins were already on pg_cron (18:25 + 20:25 `{3}`, proven firing); the gap was the Friday ladder — the seed carried only the 20:35 rung. Added the three catch-up rungs `friday-report-2105`/`-2145` Fri `{5}` + `-0730-sat` `{6}` and renamed the target rung `friday-report-2035` to the convention. `xp_schedule` now 14 slots. Verified end-to-end with a temporary `heartbeat.yml` row (side-effect-free — `test-sms.yml`'s default target texts a parent seat, so not used): the live dispatcher selected the fresh row at its slot and pg_net POSTed **HTTP 204** (req 90), then the temp row was deleted. The Friday 20:35 rung itself was already proven live 28 Aug (req 86, 204). SYSTEM-MAP trigger lines + slot inventory updated. | Claude | ✅ this branch |
| B2 | **Kid wrap chain** — work item **W2 in `PARENT-COMMS-BUILD-BRIEF.md`**. **BUILT 29 Aug (tests green 3.11).** Dark repaint (`kid_wrap.py` → shell's #0B1220 radial ground + light ink, colours only, matching `report_page` 728ab0d); cabinet reconciled to `achievements.py`'s 12 live badges (dropped Boss Slayer; added Full Claim + Personal Best; icons + earn-lines; `test_kid_wrap` count 11→12); `report_page.build_stamp()` meta added early in `<head>` (so the wrap's Netlify deploy verifies live); deploy wired in `friday_report_run.py` — renders the wrap from the SAME card/stories/quote + `game_facts`/`coaching`, publishes to `/w/<slug>/` kind `w` BEFORE the report, links `kid_wrap_url` only when the wrap verified live (never a 404), dry-run writes `preview_wrap_<code>.html`, workflow artifact glob widened `preview_report_*`→`preview_*`. Logs codes-only; a wrap failure never blocks the parent report. **Pending: Rich eyeballs the dry-run artifact → merge → `redeploy=true` ships wraps to all seats same day.** Open decision below (kid's own Friday text: now vs with the W7 board). | Claude | ✅ this branch |
| B3 | **Watchdog rung for pages:** after each scheduled publish, watchdog asserts the live page's build stamp — publish-layer failures alert instead of waiting for a parent to notice. | Claude | 🟠 (after A10) |
| B4 | **Slug rotation:** the current report slugs leaked into public Actions logs (pre-A4 runs), so they're burned. Rotate in private `report_slugs.json` (new slugs auto-generate lowercase `token_hex`, permanently immune to A11's collision) + redeploy + re-send links. Sequence BEFORE any "bookmark this" text. | Claude (needs private repo access) | 🟠 |
| B5 | **"Bookmark this" text to each family** — delivers "always available" for zero build. Only after B4. | Claude drafts, **Rich approves copy** | ⏳ B4 |
| B6 | **Sweep trust test Mon 31 Aug** (machine 07:07 vs Rich's last manual sweep). Its promotion is the gate for everything Monday-shaped. | **Rich** | 🔴 Monday |
| B7 | **`kid_nudge.py:159` breaks on Python 3.11** — a `\uXXXX` escape inside an f-string expression part (`{'sent ✓' if ok else …}`) is a `SyntaxError` on 3.11, the same class A8 fixed in two test files but missed here. Live 4pm nudge is UNAFFECTED (kid-nudge.yml runs 3.12), but `test_kid_nudge.py` + `test_planner_events.py` fail on the 3.11 gate every merge passes through. One-line fix ready (hoist the mark to a variable). Held: `kid_nudge` is a live send-path file — Rich's go. Discovered during W2. | Claude (Rich's go — live path) | 🔴 ready, held |

## C. Before term break (25 Sep) and DST (4 Oct)

| # | Action | Owner | Status |
|---|---|---|---|
| C1 | **`calendar.json`** (term dates, per-seat exam blocks) gating EVERY scheduled send + the quiz pipeline — otherwise Wednesday texts "tonight's run isn't in yet" into the school holidays and Friday verdicts a beach week "Quiet". | Claude | 🟠 |
| C2 | **End-of-term wrap** — the cumulative-by-subject term reflection (the strongest renewal artifact; PARENT-COMMS-V2 §6). Build before 25 Sep. | Claude, **Rich ratifies format** | 📋 |
| C3 | **EXAM-MODE.md** — referenced in SYSTEM-MAP, doesn't exist. Sets planner + comms posture for exam weeks (revision framing, no week-word verdict on an exam Friday). | Claude drafts | 🟠 |
| C4 | **Subject-spine Friday report** (V2 §3 / work item **W3**) — **BUILT 29 Aug (tests green 3.11), shadow on branch.** `report_stories.subject_blocks()` assembles per-subject blocks from facts already computed (ledger topics + the week's traces + ranked stories + targets block); `report_page.render()` reorganised subject-first (activity strip → BY SUBJECT spine → demoted cross-cutting cards → cumulative footer strip → portal link), with the fluency-illusion sentence (`report_stories.fluency_catch()`) and per-topic band + depth-where-evidenced (ceiling: unevidenced → "—"). `friday_report_run.build_for` wired to pass it through; legacy story-card render preserved as the no-spine fallback. Sample preview sent. **Pending: Rich eyeballs the real dry-run artifact (t1 first) → ratify → land the REPORTING.md amendment with supersession scope (the section-order supersession, V2 §11.1).** | Claude, **Rich ratifies** | 🟠 built, awaiting ratify |
| C5 | **Portal v1** (`/p/<slug>/` / work item **W4**) — **RENDERER BUILT 29 Aug (tests green 3.11), shadow on branch.** New `tools/portal_page.py`: `build_portal()` assembles from already-computed facts (ledger topics, targets block, radar, targets diff, banked snapshots — no AI); `render()` draws NOW strip · THIS WEEK panel (Monday's content as pull) · BY SUBJECT where-he-stands cards (position + depth side by side, with the solid×lists "confidently shallow" cross finally rendering) · TERM TRENDS (gated at 4+ snapshot weeks, else says so) · ARCHIVE (dated report links) · legend + visible "updated {date}" stamp. Reuses `report_page`'s dark system + band/depth/ceiling helpers. `test_portal_page.py` (24 assertions) green. Sample preview sent. **FOLLOW-UP (deploy wiring, separate chunk): new `p` slug kind in `report_slugs.json`; a Monday-seed + Friday republish that writes the page; dated archive paths `/r/<slug>/<week>/` (needs the "Friday overwrites in place" fix first, V2 §5); wire `portal_url` into the Friday report's cumulative footer.** Then Rich ratifies (V2 §11.3: freshness contract, aging rule, dated archives). **REBUILT 30 Aug per `PARENT-PORTAL-BRIEF.md`** (the single-scroll render was rejected): `portal_page.render_pages()` now draws FOUR designed pages under one slug — home (radar + doorway teasers + account-surface stub + player-card link) `/ahead/` (Monday, forward) `/week/` (Friday: verdict hero + fluency narration + the subject spine via `report_page._subject_block`) `/picture/` (tally bars + position×depth map with the confidently-shallow cross + gated trends + archive + legend) — cross-linked by a fixed bottom app nav, one accent per time-frame (reef/flare/kelp), stamps on every page. Facts helpers unchanged; 79 assertions green 3.11; sample-data preview committed at `preview/portal/` (`tools/portal_preview.py`); cross-linked preview artifacts sent to Rich. Decisions taken + supersessions recorded in the brief's "BUILT 30 Aug" section. | Claude, **Rich ratifies** | 🟠 four-page portal built, shadow; Rich eyeballs preview → wiring |
| C6 | **Delivery webhook** (Mobile Message) so "accepted" becomes "delivered"; plus per-family per-touchpoint on/off config as real private state (today the only off-switch is deleting a secret). | Claude | 🟠 |
| C7 | **Metrics or we're flying blind:** delivery-receipt rate, link-tap/portal visits (privacy-safe), opt-out count, kid completion + nudge-to-play latency; fortnightly 3-question parent pulse. Thresholds gate the 10-family beta. | Claude proposes, **Rich sets thresholds** | 📋 |

## D. Gated / beta-entry

| # | Action | Owner | Status |
|---|---|---|---|
| D1 | **Monday Week-Ahead** — RE-SCOPED 30 Aug (Rich): the parent report is THREE components on the portal — WEEK AHEAD (Mon, forward) · THIS WEEK (Fri, what happened) · RUNNING PICTURE (Fri, cumulative). The week-ahead CONTENT lives on the portal (pull, ungated). The Monday **SMS is a thin POINTER** ("here's what's being covered this week — <link>"): it names subjects + link, carries no sweep-derived claim, so it is NOT gated and can send today. **Built:** `monday_brief.py` (`week_ahead()` forward facts + `pointer_sms()` + the Monday-law `validate()` — forward-only, no verdict/standing words, no digits except an assessment date, topic/subject/date-masked so real content can't false-trip); portal restructured into the three components; `test_portal_page.py` covers all of it (green 3.11). A content-carrying Monday push (topic detail in the text, not just a pointer) still waits for the B6 sweep gate. | Claude, **Rich ratifies law** | 🟠 built (pointer ungated); content-push ⏳ B6 ×2 |
| D2 | **Weekly board ("up for grabs")** — kid-facing contracts (participation 4/5 · clean-hands · teach-back · named Lock-It/Bounce-Back offers), deterministic, riding the published quiz JSON; t1 first; Harrison/Roshan sit-down reaction is the gate for any parent-visible mention. Parents: offers forward, stories backward, never tallies. Supersedes the pending deal card. | Claude, **Rich ratifies ACHIEVEMENTS amendment** | 📋 |
| D3 | **Auth (magic link) + reports behind the session gate** — at family #2, per the ratified trigger. Nothing homegrown. | Claude | ⏳ family #2 |
| D4 | **Deletion script covers hosted surfaces** (reports, archive, wrap, portal, slugs) with manifest read-back verification — before archives hold a term of kid data. | Claude | 🟠 pre-beta |
| D5 | **Opt-out + Spam Act pack:** documented opt-out path in welcome + portal footer; provider opt-out ingestion. Before the first non-family household. | Claude | 🟠 pre-beta |
| D6 | **Name decision** — keep XP Daily through beta; two-name architecture ("The Full Picture" for the parent surface) decided at the commercial gate with real parent signal. | **Rich** | 📋 parked |
| D7 | **Quiz-site name leak:** public roster `play_urls` embed kids' first names in Netlify site names (breaks the codes-only law; the quiz URL IS the kid's identity). Rename sites to code-based, update roster. | Claude + **Rich** (Netlify renames) | 🟠 |
| D8 | **Log audit across all senders** — Friday runner fixed (A4); sweep the remaining tools' prints for name/URL leakage as they're touched. | Claude | 🟠 rolling |

---

**Standing rule this file exists to enforce (add to WORKING-MODEL on
ratification):** a family-facing change is DONE only when it is (1) on `main`,
(2) live-verified by its build stamp, and (3) has a row here moved to ✅ — not
when a chat message says it's a good idea.
