-- Step 2: calculated values (features) for each company and day.
--
--   weekly_prices  : weekly bars built from daily prices (needed for the 30-week average)
--   daily_features : moving averages, volume ratios, 52-week levels, relative strength,
--                    consolidation range - everything the scanner and Stage analysis read
--
-- Prices in these tables are SPLIT-ADJUSTED, so they can be compared across time.
-- Raw prices stay in daily_prices. Every row records which version of the calculations
-- produced it, so a rule change can be re-run and compared.

create table public.weekly_prices (
  company_id  bigint        not null references public.companies (id),
  week_start  date          not null,                -- Monday of that week
  week_end    date          not null,                -- last trading day in that week
  open        numeric(14,4) not null,
  high        numeric(14,4) not null,
  low         numeric(14,4) not null,
  close       numeric(14,4) not null,
  volume      bigint        not null,
  trading_days smallint     not null,
  primary key (company_id, week_start)
);

create index weekly_prices_week_idx on public.weekly_prices (week_start);

create table public.daily_features (
  company_id       bigint        not null references public.companies (id),
  trade_date       date          not null,
  feature_version  text          not null,

  close_adj        numeric(14,4) not null,           -- split-adjusted close

  -- returns over the last N trading days, as fractions (0.05 = +5%)
  return_1d        numeric(12,6),
  return_5d        numeric(12,6),
  return_21d       numeric(12,6),
  return_63d       numeric(12,6),
  return_252d      numeric(12,6),

  -- daily moving averages of the adjusted close
  sma_20           numeric(14,4),
  sma_50           numeric(14,4),
  sma_100          numeric(14,4),
  sma_200          numeric(14,4),

  -- weekly long-term trend (Stage analysis uses the 30-week average)
  wma_30w          numeric(14,4),
  wma_30w_slope    numeric(12,6),                    -- change over the last 10 weeks, as a fraction

  -- volume and liquidity
  volume_avg_20    bigint,
  volume_ratio_20  numeric(12,4),                    -- today's volume / 20-day average
  value_avg_20     numeric(18,2),                    -- average traded value in rupees

  -- 52-week levels
  high_52w         numeric(14,4),
  low_52w          numeric(14,4),
  pct_from_high_52w numeric(12,6),                   -- 0.032 = 3.2% below the high
  pct_above_low_52w numeric(12,6),

  volatility_21d   numeric(12,6),                    -- yearly volatility from 21 daily returns

  -- consolidation range over the last 120 trading days
  range_high_120   numeric(14,4),
  range_low_120    numeric(14,4),
  range_width_120  numeric(12,6),                    -- (high - low) / low
  days_in_range    smallint,                         -- how long price has stayed inside it

  -- strength against the benchmark index
  rs_ratio         numeric(18,8),                    -- adjusted close / benchmark close
  rs_change_63d    numeric(12,6),
  rs_change_252d   numeric(12,6),
  rs_rank_63d      numeric(6,2),                     -- 0-100 rank against the rest of the universe

  calculated_at    timestamptz   not null default now(),
  primary key (company_id, trade_date)
);

create index daily_features_date_idx on public.daily_features (trade_date);

alter table public.weekly_prices  enable row level security;
alter table public.daily_features enable row level security;

create policy "Logged-in users can read weekly prices"
  on public.weekly_prices for select to authenticated using (true);
create policy "Logged-in users can read daily features"
  on public.daily_features for select to authenticated using (true);
