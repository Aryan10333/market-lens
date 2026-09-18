-- Step 1: Market data tables.
--   universe_members  : which companies are in the tracked universe (Nifty 500), and since when
--   price_files       : one row per downloaded exchange file (source + load time)
--   daily_prices      : end-of-day prices per company, exactly as published (not adjusted)
--   index_prices      : end-of-day values of NSE indices (benchmarks, sectors)
--   price_adjustments : splits/bonuses detected from the data, used later to adjust old prices
--
-- All tables: logged-in users can read, only the Python jobs write.

-- ---------------------------------------------------------------------------
-- universe_members
-- A company can leave and re-join an index, so each stay is its own row.
-- removed_on is empty while the company is still a member.
-- ---------------------------------------------------------------------------
create table public.universe_members (
  universe    text   not null,                          -- e.g. 'NIFTY500'
  company_id  bigint not null references public.companies (id),
  added_on    date   not null,
  removed_on  date,
  primary key (universe, company_id, added_on),
  constraint universe_members_dates check (removed_on is null or removed_on >= added_on)
);

-- At most one open membership per company per universe.
create unique index universe_members_one_open
  on public.universe_members (universe, company_id)
  where removed_on is null;

-- ---------------------------------------------------------------------------
-- price_files
-- ---------------------------------------------------------------------------
create table public.price_files (
  exchange       text        not null,                  -- 'NSE'
  kind           text        not null check (kind in ('equity', 'index')),
  trade_date     date        not null,
  status         text        not null check (status in ('loaded', 'no_file')),  -- no_file = holiday
  file_format    text,                                  -- 'udiff' or 'legacy' for equity files
  source_url     text,
  rows_in_file   integer,
  rows_saved     integer,
  rows_rejected  integer,
  loaded_at      timestamptz not null default now(),
  primary key (exchange, kind, trade_date)
);

-- ---------------------------------------------------------------------------
-- daily_prices
-- Raw prices from the NSE bhavcopy. Split/bonus adjustment happens in calculations,
-- using price_adjustments, so the stored numbers always match the exchange file.
-- ---------------------------------------------------------------------------
create table public.daily_prices (
  company_id    bigint        not null references public.companies (id),
  trade_date    date          not null,
  series        text          not null,                 -- EQ, BE, BZ
  open          numeric(12,2) not null,
  high          numeric(12,2) not null,
  low           numeric(12,2) not null,
  close         numeric(12,2) not null,
  prev_close    numeric(12,2),                          -- as published; changes on split/bonus days
  volume        bigint        not null,                 -- shares traded
  traded_value  numeric(18,2) not null,                 -- rupees
  num_trades    integer,
  primary key (company_id, trade_date),
  constraint daily_prices_positive check (open > 0 and high > 0 and low > 0 and close > 0),
  constraint daily_prices_range check (low <= high),
  constraint daily_prices_volume check (volume >= 0 and traded_value >= 0)
);

create index daily_prices_date_idx on public.daily_prices (trade_date);

-- ---------------------------------------------------------------------------
-- index_prices
-- ---------------------------------------------------------------------------
create table public.index_prices (
  index_name  text          not null,                   -- e.g. 'Nifty 500', 'Nifty IT'
  trade_date  date          not null,
  open        numeric(12,2),
  high        numeric(12,2),
  low         numeric(12,2),
  close       numeric(12,2) not null,
  primary key (index_name, trade_date)
);

create index index_prices_date_idx on public.index_prices (trade_date);

-- ---------------------------------------------------------------------------
-- price_adjustments
-- On a split/bonus day NSE publishes prev_close already adjusted.
-- factor = published prev_close / actual close of the previous trading day.
-- Example: 1:1 bonus -> factor 0.5. Prices before ex_date are multiplied by factor.
-- ---------------------------------------------------------------------------
create table public.price_adjustments (
  company_id           bigint        not null references public.companies (id),
  ex_date              date          not null,
  factor               numeric(14,8) not null check (factor > 0),
  prev_close_published numeric(12,2) not null,
  close_before         numeric(12,2) not null,
  detected_at          timestamptz   not null default now(),
  primary key (company_id, ex_date)
);

-- ---------------------------------------------------------------------------
-- Row Level Security: read for logged-in users, no writes from the web app.
-- ---------------------------------------------------------------------------
alter table public.universe_members  enable row level security;
alter table public.price_files       enable row level security;
alter table public.daily_prices      enable row level security;
alter table public.index_prices      enable row level security;
alter table public.price_adjustments enable row level security;

create policy "Logged-in users can read universe members"
  on public.universe_members for select to authenticated using (true);
create policy "Logged-in users can read price files"
  on public.price_files for select to authenticated using (true);
create policy "Logged-in users can read daily prices"
  on public.daily_prices for select to authenticated using (true);
create policy "Logged-in users can read index prices"
  on public.index_prices for select to authenticated using (true);
create policy "Logged-in users can read price adjustments"
  on public.price_adjustments for select to authenticated using (true);
