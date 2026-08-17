-- XP Daily — runs_raw idempotency (Shell v3.1)
-- ---------------------------------------------------------------------------
-- Problem: runs_raw had no dedupe, so a re-sent run (e.g. the offline outbox
-- flushing after the webhook already succeeded) could insert a duplicate row.
--
-- Fix: the shell now stamps every submission with a stable per-run id
-- (payload->>'runId') that is generated ONCE and reused on every retry. This
-- PARTIAL unique index dedupes on that id. It is partial (WHERE runId IS NOT
-- NULL) so it ignores older rows that predate runId entirely — it therefore
-- can't fail on the existing seed duplicates, and needs no manual cleanup.
--
-- Safe to run more than once (IF NOT EXISTS). Paste into the Supabase SQL editor.

CREATE UNIQUE INDEX IF NOT EXISTS runs_raw_runid_uniq
    ON runs_raw ((payload->>'runId'))
    WHERE payload->>'runId' IS NOT NULL;

-- After this, a duplicate insert (same runId) is rejected by Postgres. The
-- shell's Supabase write is fire-and-forget, so that rejection is silently
-- ignored and no duplicate row is created. When Supabase becomes the primary
-- sink (after the Google Sheets retirement), the shell should additionally
-- treat that rejection (HTTP 409) as a successful, already-recorded submit.
