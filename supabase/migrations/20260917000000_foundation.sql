-- Step 0: Foundation tables.
--   profiles  : one row per logged-in user (linked to Supabase Auth)
--   companies : master list of NSE/BSE listed companies
--   job_runs  : log of every Python job run (data loads, calculations)
--
-- Security model (Row Level Security):
--   * Users can read and edit only their own profile.
--   * Any logged-in user can read companies and job_runs.
--   * Only the Python jobs write companies/job_runs. They connect as the database
--     owner, which bypasses RLS. The web app cannot write these tables.

-- ---------------------------------------------------------------------------
-- Helper: keep "updated_at" current on every update
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------------------------
-- profiles
-- ---------------------------------------------------------------------------
create table public.profiles (
  id           uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  created_at   timestamptz not null default now(),
  updated_at   timestamptz not null default now()
);

create trigger profiles_set_updated_at
  before update on public.profiles
  for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;

create policy "Users can read own profile"
  on public.profiles for select to authenticated
  using ((select auth.uid()) = id);

create policy "Users can update own profile"
  on public.profiles for update to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- Create a profile automatically when someone signs up.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, display_name)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)));
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- companies
-- One row per company. A company listed on both exchanges has both
-- nse_symbol and bse_code filled. ISIN is the shared identity across exchanges.
-- ---------------------------------------------------------------------------
create table public.companies (
  id          bigint generated always as identity primary key,
  isin        text not null unique check (isin ~ '^IN[A-Z0-9]{10}$'),
  name        text not null,
  nse_symbol  text unique,
  bse_code    text unique,
  sector      text,
  industry    text,
  is_active   boolean not null default true,
  source      text not null,                        -- where this row came from, e.g. 'nse_equity_list'
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint companies_has_listing check (nse_symbol is not null or bse_code is not null)
);

create index companies_name_idx on public.companies (lower(name));

create trigger companies_set_updated_at
  before update on public.companies
  for each row execute function public.set_updated_at();

alter table public.companies enable row level security;

create policy "Logged-in users can read companies"
  on public.companies for select to authenticated
  using (true);

-- ---------------------------------------------------------------------------
-- job_runs
-- ---------------------------------------------------------------------------
create table public.job_runs (
  id            bigint generated always as identity primary key,
  job_name      text not null,
  status        text not null default 'running' check (status in ('running', 'success', 'failed')),
  started_at    timestamptz not null default now(),
  finished_at   timestamptz,
  rows_written  integer,
  message       text
);

create index job_runs_job_started_idx on public.job_runs (job_name, started_at desc);

alter table public.job_runs enable row level security;

create policy "Logged-in users can read job runs"
  on public.job_runs for select to authenticated
  using (true);

-- ---------------------------------------------------------------------------
-- health(): lets the public /api/health endpoint confirm the database answers,
-- without exposing any table data.
-- ---------------------------------------------------------------------------
create or replace function public.health()
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
  select jsonb_build_object('database', 'ok', 'time', now());
$$;

revoke all on function public.health() from public;
grant execute on function public.health() to anon, authenticated;
