# Decisions

Each decision: what we chose, and why. Newest decisions go at the bottom.

## D1. Markets: NSE and BSE stocks

- **Chosen:** Indian equities listed on NSE and/or BSE.
- **Why:** This is the market the TechnoFunda method is built for.
- **How:** One row per company in `companies`. The **ISIN** (for example `INE002A01018`) links the
  NSE symbol and the BSE code of the same company, so a stock listed on both is not counted twice.

## D2. Time horizon: weekly and monthly, no intraday

- **Chosen:** End-of-day (daily) prices only. Weekly and monthly bars are built from the daily bars.
- **Why:** Holding periods are weeks to months. Stage analysis uses the 30-week moving average,
  which needs weekly bars, not minute data.
- **Effect:** Data loads once per trading day after the market closes (evening IST).
  No live prices, no real-time feeds. This keeps it cheap and simple.

## D3. Website: Next.js on Vercel

- **Chosen:** Next.js (TypeScript) in `web/`, hosted on Vercel.
- **Why:** Vercel hosts Next.js natively. Next.js route handlers replace the separate FastAPI
  server suggested in the spec, so there is one less service to run.

## D4. Database and logins: Supabase

- **Chosen:** Supabase Postgres + Supabase Auth.
- **Why:** Postgres is what the spec asks for. Auth gives multi-user login out of the box.
- **Multi-user:** Each user has their own login. Shared data (companies, prices, signals) is readable
  by all logged-in users. Personal data (watchlist, notes, MACHINE assessments) is private to each
  user. This is enforced inside the database with **Row Level Security (RLS)**.

## D5. Calculations: Python jobs run by GitHub Actions

- **Chosen:** Python scripts in `jobs/`, run on a schedule by GitHub Actions, writing to Supabase.
- **Why:**
  - Python + pandas is the best fit for price/indicator maths and the later backtesting step.
  - Vercel functions have short time limits and size limits; processing thousands of stocks does
    not fit there.
  - GitHub Actions is free for this amount of work and has a built-in scheduler.
- **Rule:** The website only *reads* the results. Jobs *write* them.

## D6. AI: OpenAI

- **Chosen:** OpenAI API, called from the server side of the web app (key never sent to the browser).
- **How:** All AI calls go through one small wrapper module, so switching provider later only changes
  one file.
- **Rule (from the spec):** AI only writes from numbers the app has already calculated and stored.
  Every AI report is saved together with the data it was given, so it can be checked later.

## D7. Local Python environment

- **Chosen:** A virtual environment in `.venv/` at the project root. Packages listed in
  `requirements.txt` (needed to run) and `requirements-dev.txt` (tests and style checks).
- **Why:** Keeps project packages separate from the system Python. Plain text requirement files are
  the simplest format to read.

## D8. Database changes as SQL files

- **Chosen:** Every change to the database is a numbered `.sql` file in `supabase/migrations/`,
  applied with the Supabase CLI (`npx supabase db push`).
- **Why:** Plain SQL is easy to read. The folder is a complete history of how the database was built.
  Never change the database by hand in the dashboard without also adding a migration file.

## D9. Price data source (to be finalised in Step 1)

- **Plan:** Official daily "bhavcopy" files from NSE and BSE for the daily update, plus a one-time
  historical backfill. Splits and bonuses must be handled so the history is not broken.
- **Status:** Will be tested and confirmed in Step 1.

## D10. Fundamentals source (to be decided in Step 6)

- **Status:** Open. There is no clean free API for Indian company financials. Options: CSV export
  upload, a paid data API, or parsing exchange filings.
