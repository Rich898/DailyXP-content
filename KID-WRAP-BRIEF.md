# KID-WRAP-BRIEF.md — ship the kid's weekly wrap (badges finally get a surface)

Bootstrap doc for a fresh session. Written 29 Aug 2026, at the end of the
parent-comms review weekend. Read `WORKING-MODEL.md` first and follow it; then
this file is the workstream. `KID-REPORT.md` is the ratified spec for the page
itself — this brief is the build order and the current state of the code.

## How to work with Rich (non-negotiable, same as every brief)
- Plain English before technical detail. One small action, confirm, next.
- Honest pushback over agreement. He is the decision-maker; he is not an engineer.
- Shadow-first, t1-gated; promote only on his explicit approval.
- Never edit the live send path during Sydney evening send windows (~17:30–22:15 weekdays).

## Context (what just happened, 28–29 Aug)
The Friday parent reports served stale/light pages under a green pipeline.
Root cause found and fixed on main: Netlify lowercases paths, our mixed-case
slugs made every carry-forward deploy carry the old page AND the new render as
two entries for one normalised path — the stale one won, so pages only landed
when NEW to the site (`RUNBOOK.md` Gotcha #11). Alongside it, merged via PR
#16: build stamps on every report page + a verify that demands the exact
render back from the live URL; PII (names, per-kid URLs) stripped from public
Actions logs; a `redeploy=true` recovery input on the Friday workflow; the
`PARENT-COMMS-V2.md` proposal; and `ACTIONS.md` — the tracked iron-out list.
Rich has read the proposal (as the "Full Picture" page) and is **aligned on
decisions 1–8**; formal doctrine amendments land with each build.

## The problem this session solves
**Kids earn badges that nothing shows them.** The badge engine
(`tools/achievements.py`) runs nightly and writes `achievements_earned.json` —
but the kid's weekly wrap page (`tools/kid_wrap.py`, built and script-tested
via `tools/test_kid_wrap.py`) has NEVER been deployed:
`tools/friday_report_run.py:213` computes `wrap_url` and line 215 passes
`kid_wrap_url=None`; `kid_wrap` is never imported. This is also a
**transparency-law breach in practice** (`KID-REPORT.md` §2: nothing on the
parent report is hidden from the kid — yet parents have received Friday detail
for weeks while the kid's mirror surface never existed). Fixing it is a
compliance item, not a feature, and it is the prerequisite for the weekly
"up for grabs" board (proposal decision 5).

## Work items, in order

1. **Dark repaint `kid_wrap.py`.** It is still on the light theme:
   `:root{--paper:#F7F8F4;--ink:#101B2D;…}` at kid_wrap.py:402 and
   `theme-color #F7F8F4` at :971. Apply the same colours-only treatment commit
   `728ab0d` gave `report_page.py` (shell design system: #0B1220 radial
   ground, light ink, flare/reef/kelp accents, card #101F35). The kid page
   should feel like the game shell, because it is one (`KID-REPORT.md` §8).

2. **Reconcile the cabinet.** `CABINET` at kid_wrap.py:138-140 lists 10 badges
   including retired **"Boss Slayer"**; the live v1 set (`ACHIEVEMENTS.md`,
   changelog 20 Aug) is 12: drop Boss Slayer, add **Full Claim** and
   **Personal Best** (with icons + one-line "how it's earned" strings, matching
   the existing dict shapes at :146 and :158). Verify names against
   `tools/achievements.py` — the engine, not the doc, is the runtime truth.

3. **Build stamp.** Add the `xpdaily-build` meta + footer stamp exactly as
   `report_page.py` now does (`report_page.build_stamp()` is importable — reuse
   it, don't copy it). Must sit early in `<head>`, inside verify's 4KB window.

4. **Wire the deploy.** In `friday_report_run.py`: import `kid_wrap`, render
   the wrap, `deploy.publish(slugs[code]["wrap"], html, kind="w")` BEFORE the
   parent report deploys, and pass the real `kid_wrap_url` into
   `rpage.render(...)` **only if the wrap verified live** (the parent page must
   never link a 404). Wrap slugs already exist per kid in the private
   `work/report_slugs.json` (`{code: {report, wrap}}`); `netlify_deploy` now
   lowercases all paths/URLs at use — do not fight that. Public log lines:
   codes only, never names, never URLs (the A4 law; see the masked prints
   already in the file and match them). Dry-run: write
   `preview_wrap_<code>.html` next to the report previews and widen the
   workflow's dry-run artifact glob from `preview_report_*` to `preview_*`.

5. **Tests + verification, in this order:** (a) all touched suites green on
   Python 3.11 (`test_kid_wrap.py`, `test_friday_report.py`,
   `test_netlify_deploy.py` — note two suites were recently fixed for
   3.11-only syntax; keep them 3.11-clean); (b) `dry_run=true` dispatch →
   inspect the preview artifact (dark theme, cabinet correct, stamp present);
   (c) merge on Rich's word; (d) `redeploy=true` dispatch — with the wrap
   wired it re-renders AND deploys wraps + reports for the already-sent week,
   no SMS, no state writes — then confirm the wrap URLs are live, dark, and
   stamped. That sequence ships the wrap to all three seats without waiting
   for Friday.

## Laws that bind this build (do not relitigate)
- `KID-REPORT.md` in full: player card not report card; the transparency law;
  the integrity exception (a quarantined teach-back is NEVER surfaced to the
  kid, in any form); praise the move never the player; depth rungs attach to
  topics, never to him; no comparison of any kind.
- Week 1 / thin-data: under-claim, start-line framing, never an empty shame page.
- Slugs lowercase at use (Gotcha #11); `--no-sms` deploys to LIVE URLs, use
  `--dry-run` for inspection (Gotcha #10); public logs are PII-free.
- The wrap rides the SAME facts as the parent report (`friday_report.build_card`
  + stories) — never a second facts layer (`KID-REPORT.md` §8).

## One question to put to Rich during the build
The wrap is deployed and linked from the parent report's footer ("player
card"). Does the KID also get his own Friday text with the wrap link this
week (REPORTING.md's kid-side Friday), or does that wait for the weekly-board
build (decision 5)? One clear recommendation, then his call.

## Out of scope here (tracked in ACTIONS.md)
B1 (pg_cron for Wed/Fri sends — approved, mapped, ready to execute), slug
rotation (B4), the board itself (D2), portal (C5), Monday touchpoint (D1).
