-- 009_revision_coverage.sql
-- Coverage ledger for the exam-revision system (EXAM-REVISION.md LAW E9).
-- Derived from revision_runs: per student + topic id (src) + subject — how often a topic was
-- asked, when last asked, and the average/last score (0 / 0.5 / 1, partial credit per LAW E5).
-- tools/generate_revision.py reads this (revision_coverage) to skip recently-asked topics and
-- prioritise weak ones. Only answers that carry a topic `src` (sessions from day37 on) appear.
create or replace view public.revision_coverage as
select
  r.student,
  a->>'src'                                          as topic_id,
  a->>'s'                                             as subject,
  count(*)                                            as times_asked,
  max(r.received_at)                                  as last_asked,
  round(avg( nullif(a->>'score','')::numeric ), 2)    as avg_score,
  (array_agg( nullif(a->>'score','')::numeric order by r.received_at desc ))[1] as last_score
from public.revision_runs r,
     lateral jsonb_array_elements(r.payload->'answers') a
where a ? 'src' and a->>'src' is not null and a->>'src' <> ''
group by r.student, a->>'src', a->>'s';

grant select on public.revision_coverage to anon, authenticated, service_role;
