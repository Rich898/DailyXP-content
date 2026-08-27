# WORKING-MODEL.md — how Rich and Claude work, on every surface

Ratified 26 Aug 2026. Every session, on any surface, reads this first, then the task brief. No session reinvents these rules. Amendments happen only by Rich's explicit ratification, and are committed here.

## The four laws

1. **Secrets law.** Credential values travel one way only: Rich's fingers → the destination dashboard (GitHub, Supabase, Mobile Message). Never through chat or any session, in any direction, for any reason — urgency included. Sessions may USE secrets already stored (Supabase Vault server-side, GitHub Actions secrets inside workflows) but never see, receive, or echo one.

2. **Surfaces law.** Four surfaces, four jobs:
   - Chat (claude.ai): brains and levers — diagnose, read logs, query the database, fire workflows.
   - Claude Code on the web (claude.ai/code): hands — creates, edits, and commits repo files in a cloud VM. Nothing installs or lands on Rich's machine. Access is via the Claude GitHub App; grants are per-repo and least-privilege (DailyXP-content first; DailyXP-private only when a task truly needs it). Changes arrive as a branch/PR for Rich's review — the one-step law, enforced by machinery.
   - The system's own workflows: the automated hands — nightly builds, sends, and state commits.
   - Rich's browser: exactly two things — entering secrets, and owner-only clicks (app installs, PR approvals, dashboard settings). If a session is walking Rich through multi-step browser work that isn't one of those two, the session is doing it wrong: stop and reroute.

3. **Boot law.** First action of every session: `Fetch https://raw.githubusercontent.com/Rich898/DailyXP-content/main/WORKING-MODEL.md and follow it.` Then fetch the task brief Rich names (HARDENING-BRIEF.md, BETA-BRIEF.md, etc.). Where this file and a session's instincts disagree, this file wins until Rich amends it.

4. **One-step law.** One small action at a time; confirm before the next. Plain English before technical detail. Honest pushback over agreement.

## Standing operating notes

- Rich is the decision-maker and not an engineer; he works by voice dictation — expect typos, give exact URLs and exact button names.
- Shadow-first, t1-gated: new behaviour ships dark, proves itself, and is promoted only on Rich's explicit approval.
- Never modify the live send path during Sydney evening send windows (roughly 17:30–22:15 weekdays).
- Two credentials, two homes: `github_dispatch_pat` (Supabase Vault — fires workflows via the GitHub API) and `DAILYXP_TOKEN` (GitHub Actions repo secret — used inside workflows for checkouts). Any rotation or revocation maps both BEFORE acting.
- Repos: DailyXP-content (public — code, workflows, briefs, this file) and DailyXP-private (ledger / state / targets / history).
