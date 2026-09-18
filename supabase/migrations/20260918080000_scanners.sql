-- Step 3: scanners.
--
--   sector_features : how each sector index is doing against the benchmark
--   rule_versions   : the exact thresholds a scanner used, kept forever
--   signals         : one row per stock that triggered a scanner on a day, with the
--                     actual numbers that made it trigger
--
-- Every signal points at the rule version that produced it, so any result can be
-- explained and reproduced later.

create table public.sector_features (
  sector             text          not null,          -- as NSE labels it, e.g. 'Information Technology'
  trade_date         date          not null,
  index_name         text          not null,          -- the NSE index used, e.g. 'Nifty IT'
  close              numeric(14,4) not null,
  return_21d         numeric(12,6),
  return_63d         numeric(12,6),
  relative_21d       numeric(12,6),                   -- sector return minus benchmark return
  relative_63d       numeric(12,6),
  rank_relative_21d  numeric(6,2),                    -- 0-100 against the other sectors that day
  feature_version    text          not null,
  primary key (sector, trade_date)
);

create index sector_features_date_idx on public.sector_features (trade_date);

create table public.rule_versions (
  version     text        primary key,                -- e.g. 'scanner_v1'
  kind        text        not null,                   -- 'scanner'
  config      jsonb       not null,                   -- every threshold, exactly as used
  created_at  timestamptz not null default now()
);

create table public.signals (
  id            bigint generated always as identity primary key,
  company_id    bigint      not null references public.companies (id),
  trade_date    date        not null,
  scanner       text        not null,                 -- e.g. 'consolidation_breakout'
  rule_version  text        not null references public.rule_versions (version),
  evidence      jsonb       not null,                 -- the numbers behind the trigger
  created_at    timestamptz not null default now(),
  unique (company_id, trade_date, scanner, rule_version)
);

create index signals_recent_idx on public.signals (trade_date desc, scanner);

alter table public.sector_features enable row level security;
alter table public.rule_versions   enable row level security;
alter table public.signals         enable row level security;

create policy "Logged-in users can read sector features"
  on public.sector_features for select to authenticated using (true);
create policy "Logged-in users can read rule versions"
  on public.rule_versions for select to authenticated using (true);
create policy "Logged-in users can read signals"
  on public.signals for select to authenticated using (true);
