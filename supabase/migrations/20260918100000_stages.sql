-- Step 4: Stage analysis (Weinstein's four stages, as used by the methodology).
--
-- Adjusted open/high/low are added to daily_features so charts can show candles on the
-- same scale as the adjusted close (daily_features already stores close_adj).
--
-- daily_stages holds which stage each company was in on each day, with the evidence
-- behind the decision and the version of the rules that decided it.

alter table public.daily_features
  add column open_adj numeric(14,4),
  add column high_adj numeric(14,4),
  add column low_adj  numeric(14,4);

create table public.daily_stages (
  company_id    bigint      not null references public.companies (id),
  trade_date    date        not null,
  stage         smallint    not null check (stage between 1 and 4),
  rule_version  text        not null references public.rule_versions (version),
  evidence      jsonb       not null,   -- the checks behind the decision
  calculated_at timestamptz not null default now(),
  primary key (company_id, trade_date)
);

create index daily_stages_date_idx on public.daily_stages (trade_date);

comment on table public.daily_stages is
  'Stage 1 basing, 2 advancing, 3 topping, 4 declining - decided from the 30-week average, '
  'price structure and relative strength, never from price being above an average alone.';

alter table public.daily_stages enable row level security;

create policy "Logged-in users can read stages"
  on public.daily_stages for select to authenticated using (true);
