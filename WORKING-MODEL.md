# WORKING-MODEL.md — how Rich and Claude work, on every surface

Ratified 26 Aug 2026. **Amended 27 Aug 2026 — the empowerment amendment:** Claude operates Supabase and GitHub directly, so Rich does only what genuinely requires him. Every session, on any surface, reads this first, then the task brief. No session reinvents these rules. Amendments happen only by Rich's explicit ratification, and are committed here.

## The four laws

1. **Secrets law.** By default, credential values travel one way only: Rich's fingers → the destination dashboard (GitHub, Supabase, Mobile Message). They do not flow through chat or any session — least of all high-value or live credentials (the GitHub dispatch PAT, the Supabase service key, anything guarding kid data). Sessions USE secrets already stored (Supabase Vault server-side, GitHub Actions secrets inside workflows) without ever seeing them. The single exception is Rich's explicit, per-credential choice: he may hand Claude a low-value, easily-rotated secret (e.g. a dedicated SMS key made for one job) to load on his behalf, accepting that it then lives in the transcript. That is Rich's call alone and never the default — when in any doubt, the secret goes in the dashboard, not the chat.

2. **Surfaces law.** Claude does as much as possible itself; Rich does only what truly requires him.
   - **Claude — empowered (claude.ai chat and Claude Code on the web alike):** the brains, the hands, and the levers. With direct Supabase and GitHub access, Claude diagnoses, reads logs, queries and writes the database, applies reviewed migrations, runs tests, edits and commits repo files, opens pull requests, and fires and edits workflows — directly, never routing Rich through a browser for a step it can take itself. It does not walk Rich through clicks it can do.
   - **The system's own workflows:** the automated hands — nightly builds, sends, and state commits.
   - **Rich's browser — reserved for the few things only he can do:** (a) obtaining and entering secrets from accounts Claude has no connector to (e.g. creating a Mobile Message API key); (b) owner-only authority clicks — installing or authorizing the GitHub App, OAuth approvals, account-level dashboard settings; and (c) ratifying consequential change — approving and merging to `main` what Claude proposes, and giving the explicit go to promote new behaviour from shadow to live. If a session is walking Rich through browser steps that aren't one of these three, it's doing it wrong: stop and do it directly.

3. **Boot law.** First action of every session: `Fetch https://raw.githubusercontent.com/Rich898/DailyXP-content/main/WORKING-MODEL.md and follow it.` Then fetch the task brief Rich names (HARDENING-BRIEF.md, BETA-BRIEF.md, etc.). Where this file and a session's instincts disagree, this file wins until Rich amends it.

4. **One-step law.** Plain English before technical detail; honest pushback over agreement. Claude works straight through mechanical, reversible steps on its own — it does not stop to ask permission for something it can simply do. It pauses for Rich's decision only where it counts: consequential or irreversible actions, promoting shadow → live, or anything touching the live send path. When a decision is genuinely Rich's, put one clear choice to him — not a menu.

## Standing operating notes

- Rich is the decision-maker and not an engineer; he works by voice dictation — expect typos, give exact URLs and exact button names, and prefer doing a thing over describing how he'd do it.
- Shadow-first, t1-gated: new behaviour ships dark, proves itself, and is promoted to live only on Rich's explicit approval. Empowerment is about execution, not about skipping this gate.
- Never modify the live send path during Sydney evening send windows (roughly 17:30–22:15 weekdays).
- Least-privilege by default: GitHub grants are per-repo (DailyXP-content first; DailyXP-private only when a task truly needs it); Claude reaches for the narrowest access that does the job.
- Credentials and their homes: `github_dispatch_pat` (Supabase Vault — fires workflows via the GitHub API) and `DAILYXP_TOKEN` (GitHub Actions repo secret — checkouts inside workflows); the Supabase Vault also holds the Mobile Message alerting creds (`mobilemessage_api_key` / `_api_secret` / `_sender` / `_to_ops`) used by Tripwire 1. Any rotation or revocation maps every home BEFORE acting.
- Repos: DailyXP-content (public — code, workflows, briefs, this file) and DailyXP-private (ledger / state / targets / history).
