# Architecture

## The big picture

```
  NSE / BSE daily files                                    OpenAI
          |                                                  ^
          v                                                  |
  +------------------+      writes      +-----------+  reads  +------------------+
  | Python jobs      | ---------------> | Supabase  | <------ | Website (Next.js)|
  | (GitHub Actions, |                  | Postgres  |         | on Vercel        |
  |  once a day)     |                  | + Auth    |         |                  |
  +------------------+                  +-----------+         +------------------+
                                                                      ^
                                                                      |
                                                                    Users
                                                              (each with a login)
```

## Who does what

| Part | Job | Where it runs |
|---|---|---|
| **Python jobs** (`jobs/`) | Download prices, calculate indicators, run scanners, save results | GitHub Actions (scheduled) or your PC |
| **Supabase** | Stores all data. Handles sign-up and login. Protects private data with RLS. | Supabase cloud |
| **Website** (`web/`) | Shows scanners, charts, analysis. Saves users' notes. Calls OpenAI for reports. | Vercel |

## How market data flows (Step 1)

```
 NSE Nifty 500 list ──> sync_universe ──> companies, universe_members
 BSE bhavcopy ────────┘                    (BSE codes by ISIN)

 NSE equity bhavcopy ─> load_prices ────> daily_prices   (+ price_files: source, time)
 NSE index closes ────┘                   index_prices

 NSE corporate actions -> load_corporate_actions -> price_adjustments

 all tables ──────────> check_data ──────> report (fails the workflow on serious problems)
```

Runs every weekday at 19:00 and 22:00 IST in GitHub Actions (`daily-data.yml`).

## How a user request flows

1. A user opens a page in the browser.
2. `web/src/proxy.ts` runs first: it refreshes the login session and sends logged-out users to `/login`.
3. The page (server side) reads from Supabase **as that user**, so RLS decides what they can see.
4. The HTML is sent back to the browser.

## Keys and secrets

| Key | Used by | Secret? |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Website | No (public) |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Website | No (public; RLS limits it) |
| `DATABASE_URL` (contains DB password) | Python jobs | **Yes** |
| `OPENAI_API_KEY` | Website server, jobs | **Yes** |

Secret keys live only in `.env` / `.env.local` on your PC, in Vercel's environment settings, and in
GitHub repository secrets. They are never committed to git.

## Folder map

```
market-lens/
  .env.example            settings template for Python jobs
  requirements.txt        Python packages needed to run
  requirements-dev.txt    Python packages for tests and style checks
  ruff.toml               Python style rules
  jobs/                   Python jobs
    config.py             reads settings from .env
    log.py                JSON log lines
    db.py                 database connection
    runs.py               records each job run in job_runs
    dates.py              IST dates, weekdays
    download.py           polite downloads with retries
    sources/nse.py        NSE file addresses and readers (bhavcopy, indices, Nifty 500 list)
    sources/bse.py        BSE bhavcopy reader (BSE codes)
    adjustments.py        split/bonus wording -> price factor
    health_check.py       checks the DB connection and tables
    migrate.py            applies new supabase/migrations/*.sql files
    sync_universe.py      job: Nifty 500 list -> companies, universe_members
    load_prices.py        job: NSE files -> daily_prices, index_prices, price_files
    load_corporate_actions.py  job: NSE corporate actions -> price_adjustments
    check_data.py         job: data quality report
  tests/                  Python tests (pytest)
  supabase/
    config.toml           Supabase CLI settings
    migrations/           database changes, one .sql file each
  web/                    website
    .env.example          settings template for the website
    src/proxy.ts          runs before each request (login session)
    src/lib/supabase/     Supabase clients (browser, server, proxy)
    src/app/page.tsx      home page
    src/app/login/        login and sign-up page
    src/app/auth/confirm/ email confirmation link handler
    src/app/api/health/   GET /api/health
  .github/workflows/ci.yml          automatic checks
  .github/workflows/daily-data.yml  scheduled data jobs (weekday evenings)
  docs/                   documentation
```
