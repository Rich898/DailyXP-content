# BUILD BRIEF — Results Reader / Ledger-Updater (scheduler limb #1)

*Start a FRESH chat with this file + both mastery ledgers + the GitHub token. This is the first piece of the XP Daily scheduler, built to run MANUALLY in-chat now (no API key, no cron, no GitHub Actions yet). It replaces the slow, error-prone by-hand reading of the results Sheet each morning.*

## What we're building
A script (Python, runs in the chat's bash env) that:
1. **Reads the results Sheet** via the Google Drive connector — fileId `1m0ZBUBaI82TJZRG6mMug_UgGiEWJDP9FadN9-0xjDIo`, tab `results`, parse the `payload_json` column.
2. **Dedupes** rows by (student, date, ts) — retry-taps create exact duplicates (already observed: Harrison's Mon run posted twice, 21s apart, identical ts).
3. **Extracts every signal** per run: score/max, speed & steady right/of, per-question records (picked, ok, timeUsed, confidence), flags (skips, confidentWrong, slowWrong, fastWrong, luckyGuess), timing (active/elapsed/idle, phases, perQuestion), teach-back text + chars. Trust payload `ts` (UTC) over the sheet's local timestamp column.
4. **Flags repeat runs** (attempt > 1 = not the honest run; first run of the day is canonical).
5. **Emits a clean per-student state summary** the morning "go" can act on: what's new since last read, per-topic signal, what each flag implies for ledger state (shaky/developing/solid/REPAIR, confident-wrong handling, fast-wrong = rush not gap, etc. — see the ledger docs).

## What it is NOT (yet)
- Not the question composer (that's limb #2 — decide API-written vs template vs in-chat then).
- Not autonomous — no cron, no Actions, no API key. Runs when Rich says "go", in-chat.
- Doesn't WRITE the ledger files automatically at first — it emits the update; human/Claude applies it. (Can automate ledger-file writes later.)

## Design rules (from the project doctrine — all in the repo)
- Ledger states + flag semantics: see the two mastery ledgers' "how to read" sections + CONTENT-MODEL.md.
- Confident-wrong ≠ guessing-wrong ≠ slow-wrong ≠ fast-wrong → four different scheduler responses. Fast-but-wrong is relative to the kid's OWN pace, not a fixed cutoff.
- "Correct but trivially fast on a supposed weakness" = treat as untested, not mastered.
- Absence is neutral (ABSENCE.md) — a missing day is not a failure; untested topics simply stay due.
- Never repeat a question across runs; the reader should surface what's been tested to help enforce that.

## Test it against real data
The Sheet currently holds real runs: Roshan MON (R2.1, attempt 1, honest — 1807), Harrison MON (H2.1, attempt 2 + its duplicate — 2178), plus a Roshan SYSTEM TEST row to be ignored (tag SYSTEM TEST). Build the reader, run it against this live data, show it correctly deduping the Harrison pair, ignoring the test row, and emitting sensible per-boy summaries.

## Infra facts the fresh chat needs
- Repo: `Rich898/DailyXP-content` (public). Operating manual lives there: RUNBOOK, CONTENT-MODEL, REPORTING, SEASONS, ABSENCE, ROADMAP, SHELL-3.1-SPEC, plus /shell.
- Results Sheet fileId: `1m0ZBUBaI82TJZRG6mMug_UgGiEWJDP9FadN9-0xjDIo` (read via Google Drive:read_file_content).
- GitHub token (Contents R/W, this repo only) — Rich pastes at chat start.
- Container resets between chats; pull anything needed from the repo.
- Next limbs after this: question-composer (limb #2), then GitHub Actions cron + Anthropic API key for autonomy (limb #3). Assisted-first, autonomous once proven.
