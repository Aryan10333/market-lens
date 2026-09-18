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
  applied with `.venv\Scripts\python -m jobs.migrate`.
- **Why:** Plain SQL is easy to read. The folder is a complete history of how the database was built.
  `jobs.migrate` records applied files in the same table the Supabase CLI uses, so
  `npx supabase db push` also still works.
  Never change the database by hand in the dashboard without also adding a migration file.

## D9. Price data source: NSE bhavcopy

- **Chosen:** Official NSE daily "bhavcopy" files (end-of-day prices for every listed share),
  plus NSE's daily index closing file for all indices.
- **Formats:** NSE changed the file format in January 2024. The loader reads both:
  new "UDiFF" files first, older "legacy" files as fallback.
- **BSE:** used only to fill in each company's BSE code (matched by ISIN). Every Nifty 500 company
  trades on NSE, so NSE prices are enough for now.
- **Why:** Official, free, complete, and the same data the TechnoFunda method builds its screens from.

## D10. Fundamentals source (to be decided in Step 6)

- **Status:** Open. There is no clean free API for Indian company financials. Options: CSV export
  upload, a paid data API, or parsing exchange filings.

## D11. Universe: Nifty 500 (for now)

- **Chosen:** The 500 companies in NSE's Nifty 500 index, refreshed from NSE's list every run.
- **Why:** Small enough to build and check each step quickly, and fits the Supabase Free plan.
  Covers large, mid and many small caps. Can be widened later (e.g. all liquid NSE + BSE stocks).
- **Membership history:** `universe_members` records when a company joins or leaves the index.
- **Known limitation:** history before today uses *today's* member list. Backtests (Step 12) must
  account for this "survivorship bias".

## D12. Price history: 3 years

- **Chosen:** Load 3 years of daily prices the first time (setting `PRICE_HISTORY_YEARS`).
- **Why:** Enough for the 30-week moving average, 52-week high/low, multi-year consolidation
  ranges and first backtests. About 45 MB of storage.

## D13. Supabase plan: Free (for now)

- **Chosen:** Supabase Free (500 MB database).
- **Effect:** Keep the universe and history compact. `check_data` prints the database size each run.
  Upgrade to Pro when storage gets close to the limit.

## D14. Raw prices + official corporate actions

- **Chosen:** Store prices exactly as published. Take splits, bonuses and consolidations from
  **NSE's official corporate actions list**, and store the exact factor in `price_adjustments`.
- **Why:** Stored numbers always match the exchange file (easy to verify). Calculations (Step 2)
  multiply older prices by the factor, so a split does not look like a crash.
- **First attempt, and why it failed:** the original plan was to spot splits in the prices,
  assuming NSE publishes an adjusted "previous close" on the ex-date. It does not: on RELIANCE's
  bonus ex-date the share opened at 1337 while `prev_close` still said 2655.70. That rule produced
  777 fake "splits" and missed every real one.
- **Factors:** bonus a:b → b/(a+b) (1:1 = 0.5); split Rs X → Rs Y → Y/X (10 → 1 = 0.1);
  consolidation → above 1. Two actions on the same day multiply.
- **Ignored:** dividends, rights issues, buybacks, demergers, and bonus issues of preference
  shares (NCRPS) — none of them multiply the equity share count.
- **Self-check:** each action is stored with the price move actually seen on its ex-date, and
  `check_data` warns when the two disagree by more than 25%.

## D15. Daily schedule

- **Chosen:** GitHub Actions runs the data jobs at 19:00 and 22:00 IST, Monday to Friday.
- **Why:** NSE publishes files in the evening. The second run catches late files.
  Runs are incremental, so a repeat run costs almost nothing.

## D16. Scanner thresholds live in a versioned config file

- **Chosen:** `config/scanners.json` holds every threshold and a version (`scanner_v2`). The first
  run of a version copies the whole file into `rule_versions`; later runs refuse to start if the
  file changed without the version changing.
- **Why:** The spec requires that a signal can always be traced to the exact rules that produced
  it, and that the same data plus the same version gives the same result.
- **Effect:** Changing a threshold or a rule means bumping the version. Old signals keep their old
  version and stay explainable.

## D17. Signals are events, not states

- **Chosen:** A scanner fires on the day something happens, not every day a condition holds.
- **Why:** `sector_trend` as a state produced 24,762 signals in 3 years — more than everything else
  combined — because a leading sector stays leading for weeks. As an event (the day the sector
  takes the lead, or the stock climbs back above its 30-week average) it produces 4,451, and each
  one records which of the two started it.

## D18. Keep an eye on storage

- **Chosen:** `build_features` tidies up after a large rewrite, and `check_data` warns when the
  database passes 400 MB.
- **Why:** Rewriting 351k feature rows left dead rows that pushed the database from 190 MB to
  313 MB without adding any data. Tidying brought it back to 186 MB. On the free 500 MB plan that
  difference matters.
