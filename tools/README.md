# tools/ — scheduler limbs (assisted-manual mode)

## results_reader.py — limb #1: the morning read

Replaces the by-hand reading of the results Sheet. Stateless, no network, no
secrets: it parses a *saved dump* of the Sheet and prints the morning summary.

**Morning-go workflow (in-chat):**
1. Claude reads the results Sheet via the Drive connector (`read_file_content`,
   fileId held in the private handoff doc — never in this repo).
2. Save the connector output verbatim to a local file (e.g. `work/sheet_dump.md`).
3. `python3 tools/results_reader.py work/sheet_dump.md --since <last-ledger-date>`
4. Apply the emitted ledger implications to the private mastery ledgers by hand
   (the reader deliberately does not write ledgers — see BUILD-results-reader.md).

Accepts either the connector's markdown-table dump or a CSV export with columns
`received_at, student, quiz_date, day, attempt, score, payload_json`.

**What it encodes (doctrine, see BUILD brief + CONTENT-MODEL + ABSENCE):**
- Dedupe by (student, ts); retry-taps post exact duplicates.
- SYSTEM TEST rows ignored.
- Canonical run per set = lowest attempt then earliest ts; a lone attempt>1 is
  canonical-with-caveat (contamination possible).
- Timing invariant check (active ≤ elapsed); phase sums printed.
- Kid-relative speed flags per phase (fast ≤50% / slow ≥180% / trivial ≤35% of
  the student's own median, min 4 samples) — printed alongside the shell's
  fixed-cutoff flags; raw seconds always shown so a human can overrule.
- Four-way wrongness: confident-wrong ≠ guessing-wrong ≠ slow-wrong ≠
  fast-wrong → four different ledger responses.
- Correct-but-trivially-fast on a known weakness = UNTESTED, not mastered.
- Lucky guesses never promote. Fresh-skips are benched intel, never misses.
- Absence is neutral: a student with no runs in the window gets a calm note,
  not an alarm.
- Cross-run signals: repeat confident-wrong in a subject, and subject misses
  across ≥2 runs (ledger-as-drift-detector escalation).

`--json out.json` writes normalised runs + per-student phase medians for the
next limb (question composer).

**Not in scope (by design):** composing questions (limb #2), cron/API
autonomy (limb #3), writing ledger files.

Repo law reminder: no results data, no names, no secrets in this repo — the
reader takes names from the payload at runtime and nothing here hardcodes them.
