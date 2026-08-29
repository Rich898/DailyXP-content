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
land with each build, not before. Next session's workstream:
**KID-WRAP-BRIEF.md** (B2). B1 is approved and mapped, executes after or
alongside it.

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
| B1 | **Friday/Wednesday sends move to pg_cron** (Supabase `xp_schedule` rows; GitHub crons demoted to cursor-guarded backup). GitHub *skipped all three* Friday crons on 28 Aug — the send only happened because Rich pressed the button. Also fixes the 4 Oct DST hour-shift before it hits parent sends. **APPROVED 29 Aug ("lets do B1"); no Supabase changes made yet.** Mapped and ready: rows follow the `(job, workflow, local_time, days int[])` convention, ISO dow, one row per slot with distinct job names — wed-checkin Wed 18:25 + 20:25 `{3}`; friday-report Fri 20:35/21:05/21:45 `{5}` + Sat 07:30 `{6}`; verify end-to-end with a temporary test row (cursor makes a same-week dispatch a safe no-op), then delete it. | Claude | 🟠 approved |
| B2 | **Kid wrap chain** — **BRIEFED: `KID-WRAP-BRIEF.md` is the bootstrap for a fresh session.** Dark repaint + cabinet reconcile (drop Boss Slayer; add Full Claim, Personal Best) + build stamp + wire deploy in `friday_report_run` (today `kid_wrap_url=None` at line 215 — kids' earned badges have NO weekly surface; transparency-law breach in practice). Ships to all seats via `redeploy=true` after merge, no waiting for Friday. | Claude | 🟠 next session |
| B3 | **Watchdog rung for pages:** after each scheduled publish, watchdog asserts the live page's build stamp — publish-layer failures alert instead of waiting for a parent to notice. | Claude | 🟠 (after A10) |
| B4 | **Slug rotation:** the current report slugs leaked into public Actions logs (pre-A4 runs), so they're burned. Rotate in private `report_slugs.json` (new slugs auto-generate lowercase `token_hex`, permanently immune to A11's collision) + redeploy + re-send links. Sequence BEFORE any "bookmark this" text. | Claude (needs private repo access) | 🟠 |
| B5 | **"Bookmark this" text to each family** — delivers "always available" for zero build. Only after B4. | Claude drafts, **Rich approves copy** | ⏳ B4 |
| B6 | **Sweep trust test Mon 31 Aug** (machine 07:07 vs Rich's last manual sweep). Its promotion is the gate for everything Monday-shaped. | **Rich** | 🔴 Monday |

## C. Before term break (25 Sep) and DST (4 Oct)

| # | Action | Owner | Status |
|---|---|---|---|
| C1 | **`calendar.json`** (term dates, per-seat exam blocks) gating EVERY scheduled send + the quiz pipeline — otherwise Wednesday texts "tonight's run isn't in yet" into the school holidays and Friday verdicts a beach week "Quiet". | Claude | 🟠 |
| C2 | **End-of-term wrap** — the cumulative-by-subject term reflection (the strongest renewal artifact; PARENT-COMMS-V2 §6). Build before 25 Sep. | Claude, **Rich ratifies format** | 📋 |
| C3 | **EXAM-MODE.md** — referenced in SYSTEM-MAP, doesn't exist. Sets planner + comms posture for exam weeks (revision framing, no week-word verdict on an exam Friday). | Claude drafts | 🟠 |
| C4 | **Subject-spine Friday report** (V2 §3): per-subject blocks — what school set → what his sets worked → where each topic stands → misconception detail → next week. Ships through the A5 preview window, t1 first. | Claude, **Rich ratifies** | 📋 |
| C5 | **Portal v1** (`/p/<slug>/`): NOW strip · This-Week panel (Monday's content as pull, not push) · subject cards (the solid×lists "confidently shallow" cross finally renders) · dated report archive · legend. Freshness law: judgment recomputes Friday only; visible "updated" stamp. | Claude, **Rich ratifies** | 📋 |
| C6 | **Delivery webhook** (Mobile Message) so "accepted" becomes "delivered"; plus per-family per-touchpoint on/off config as real private state (today the only off-switch is deleting a secret). | Claude | 🟠 |
| C7 | **Metrics or we're flying blind:** delivery-receipt rate, link-tap/portal visits (privacy-safe), opt-out count, kid completion + nudge-to-play latency; fortnightly 3-question parent pulse. Thresholds gate the 10-family beta. | Claude proposes, **Rich sets thresholds** | 📋 |

## D. Gated / beta-entry

| # | Action | Owner | Status |
|---|---|---|---|
| D1 | **Monday Week-Ahead SMS** — after TWO consecutive clean automated-sweep Mondays (B6 promotion). Monday law per V2 §4: forward-looking only, validator denylist of state words, fail-soft continuation copy, kid-sees-it-first, household-consolidated, merge rule with the Monday soundbyte. | Claude, **Rich ratifies law** | ⏳ B6 ×2 |
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
