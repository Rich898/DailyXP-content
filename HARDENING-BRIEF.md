# HARDENING-BRIEF.md — dispatch-chain tripwires + scrub composer resilience

Bootstrap doc for a fresh session. Written 26 Aug 2026, the evening the dispatch
token died silently and nothing noticed for 3.5 hours. Read fully before touching
anything.

## How to work with Rich (non-negotiable)
- Plain English before technical detail.
- One small action at a time; confirm before the next step. Give exact URLs.
- Honest pushback over agreement.
- Shadow-first, t1-gated, promote only on explicit approval — same law as the
  Canvas sweep and Scrub It rollouts.
- Never edit the live send path during evening send windows (Sydney ~17:30–22:15).

## What happened on 26 Aug 2026 (the lesson)
The GitHub token in the Supabase Vault (`github_dispatch_pat`) went invalid.
From 14:00 Sydney every dispatch returned **401 Bad credentials**: no quiz
build, no 16:00 kid-nudge. Nothing alerted. Three separate "green tick lies"
let it stay silent:

1. **The dispatcher stamps before it listens.** `public.xp_dispatch()`
   (pg_cron, every minute) writes its "fired" row to `xp_dispatch_log` BEFORE
   GitHub answers. `net.http_post` is async and nothing ever reads the reply.
   The `status` column exists and has always been null. The 401s were sitting
   in `net._http_response` all along.
2. **The watchdog rides the token it guards.** Watchdog runs are dispatched
   through the same `github_dispatch_pat`, so a dead token kills the guard
   and the guarded together.
3. **The pipeline goes green with a seat down.** On the evening re-run, t1
   compose-failed and the workflow still concluded success (by design — the
   other seats' publishes must commit — but the failure surfaced nowhere).

Recovery that evening: new fine-grained PAT (Actions read/write on
DailyXP-content ONLY) pasted into the Vault by Rich; manual re-dispatch of
daily-quiz, then kid-nudge, via `net.http_post` using the Vault secret
server-side (a token never passes through chat); watchdog-early (17:35)
self-healed y8's nudge the minute it had a working token — the retry ladder
works.

## System map (dispatch chain only)
- pg_cron job `xp-dispatcher` → `public.xp_dispatch()` every minute → reads
  `public.xp_schedule` (Sydney-local times/days) → dedupes via
  `public.xp_dispatch_log` (job + local_date) → `net.http_post` to
  `POST api.github.com/repos/Rich898/DailyXP-content/actions/workflows/{workflow}/dispatches`,
  auth from Vault secret `github_dispatch_pat`.
- 204 = GitHub accepted. Replies land async in `net._http_response`
  (short retention — read soon or lose them).
- **Two credentials, two homes** (missing this map caused the outage):
  `github_dispatch_pat` (Supabase Vault; fires workflows; Actions-RW on the
  content repo only) and `DAILYXP_TOKEN` (GitHub Actions repo secret inside
  DailyXP-content; used BY workflows for checkouts of both repos). Any
  rotation or revocation must account for both. Secrets are only ever
  entered by Rich, directly into the GitHub/Supabase dashboards.

## Work items (in order; each one shadow-first, one at a time)
1. **Dispatcher manners.** Record GitHub's real answer into
   `xp_dispatch_log.status`. Async follow-up sweep (the post is queued):
   match `net._http_response` rows to recent stamps; non-2xx, or no reply
   after N minutes, = failure.
2. **Tripwire 1 — Supabase-side.** A checker on its own pg_cron timer reads
   the recorded outcomes; any failure → SMS Rich via Mobile Message. Needs
   the Mobile Message API key added to the Vault (Rich's hands, dashboard
   only). Ship in shadow (log-only) first; promote after a clean
   observation window. Blind spot: dies if Supabase dies.
3. **Tripwire 2 — GitHub-side.** A small workflow on GitHub's OWN
   `schedule:` cron — no dispatch token anywhere in its path — runs each
   evening and asks "did today's expected runs happen?" (GITHUB_TOKEN with
   `actions: read` on the repo). Missing runs → SMS Rich via the Mobile
   Message creds the workflows already hold. Blind spot: GitHub fully down —
   which Tripwire 1 sees as timeouts. The two cover each other; that
   complementarity is the design.
4. **No silent seat failures.** The pipeline already prints a per-seat
   summary (published / compose-failed). Surface compose-failed into the
   watchdog or an alert instead of letting the run stay quietly green.
5. **Scrub composer resilience** (the t1 compose-fail of 26 Aug, night two
   of live scrub blocks). Two blockers, retries exhausted: (a) scrub-specific
   answer-length tell — correct tile the sole longest, winnable by erasing
   the short ones unread; (b) a repeat-prompt collision (t1 carries the
   deepest seen-history in the system, so it meets repeat pressure first —
   long-lived beta seats will too). Containment behaved correctly:
   yesterday's set stayed live, the nudge guard refused to text a promise
   not kept. Fixes to explore: retry budget / targeted recompose for scrub
   blocks; feed the seat's seen-prompt history to the composer as a negative
   list rather than catching repeats only at review.
6. **Housekeeping.** Deliberately revoke the dead token (checking the
   two-homes map first); confirm a calendar reminder exists ahead of the new
   token's expiry.

## Evidence from the day
- Build re-fire: run 32942735799 (green; t1 compose-failed inside it).
- Kid-nudge re-fire: run 32943608808 (green; y8 no-op — watchdog had already
  healed it; y9 skipped by design, icon channel; t1 suppressed on stale set).
- The query that found the outage: join `xp_dispatch_log` to
  `net._http_response` on a fired_at time window — today's stamps showed
  14:00 → 401, 16:00 → 401, 17:35 → 204 (first fire on the new token).
