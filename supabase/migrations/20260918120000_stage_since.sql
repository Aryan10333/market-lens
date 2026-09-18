-- Stage rows kept the full evidence for every single day, which made the table larger
-- than the prices it came from (193 MB for 260k rows).
--
-- The evidence only really belongs to the day the stage changed - that is when the
-- decision was made. So it is now stored on change days only, and every row carries the
-- date its stage started, so a page can say "Stage 2 since 24 Oct 2025" in one query.

truncate table public.daily_stages;  -- rebuilt from scratch by jobs.classify_stages

alter table public.daily_stages
  alter column evidence drop not null,
  add column stage_since date not null;

comment on column public.daily_stages.evidence is
  'The checks behind the decision. Filled on the day the stage changed; empty on later days.';
