# Progress log

Newest entries at the top. One entry per working session.

---

## 2026-09-18: Step 3 Scanner V1

- Five scanners as pure functions (`jobs/scanners.py`) with thresholds in `config/scanners.json`,
  versioned and enforced: the job refuses to run if the file changes without a version bump.
- Sector trends added to the feature build (18 of 20 sectors have an NSE index).
- New tables `sector_features`, `rule_versions`, `signals`; job `jobs/run_scanners.py`.
- Replayed 3 years: 22,076 signals. Sample check: GRAPHITE broke an 80-day range on 12.9x volume.
- **Changed `sector_trend` to fire only on the day it becomes true** - as a state it produced
  24,762 signals (60% of all). Now 4,451. Bumped rules to `scanner_v2` and re-ran.
- **Fixed storage bloat**: rewriting all feature rows left dead rows (190 -> 313 MB). After
  tidying: 186 MB. `build_features` now cleans up automatically; `check_data` warns above 400 MB.
- Scanner page in the web app: filter by scanner, each result shows why it triggered.
- 22 new tests (83 total). Added to the daily workflow.
- Next: Step 4, the stock analysis page with charts and Stage 1-4.

---

## 2026-09-18: Step 2 Technical features

- New `jobs/features.py`: split adjustment, weekly bars, moving averages (incl. 30-week + slope),
  returns, volume ratios, 52-week levels, volatility, consolidation range, relative strength vs
  Nifty 500 and a 0-100 universe rank. All pure functions, stamped `features_v1`.
- New tables `weekly_prices` and `daily_features`; job `jobs/build_features.py` (incremental,
  `--rebuild` after a rule change); added to the daily workflow before `check_data`.
- Built the full history: 351,651 feature rows + 74,229 weekly bars in 8 minutes.
- Verified: RELIANCE's 1:1 bonus adjusts to exactly half with no break in the moving average;
  coverage and value ranges sensible; holiday week shows 3 trading days.
- 15 new tests (59 total). Database now 190 MB of the 500 MB free limit.
- Next: Step 3 scanners.

---

## 2026-09-18: Step 1 finished loading and checking

- Added reconnect-and-retry to `load_prices` (a sleeping laptop had killed the first run).
- Finished the 3-year load: 744 trading days, 351,651 price rows, 500 companies, 172 indices.
- **Found: weekend trading sessions were being skipped.** NSE traded on 6 weekend days in 3 years.
  The loader now checks every calendar day; those 6 sessions are loaded.
- **Found: the split/bonus rule was wrong.** NSE does not publish an adjusted `prev_close` on the
  ex-date (RELIANCE opened at 1337 while prev_close said 2655.70). The old rule produced 777 fake
  splits and no real ones. Replaced `detect_adjustments` with `load_corporate_actions`, which reads
  NSE's official corporate actions list (bonus/split/consolidation, ignoring dividends, rights,
  buybacks and preference-share bonuses). Two actions on the same ex-date now multiply.
- Result: 75 actions over 3 years, all 75 matching the price move on their ex-date.
- Tests: 44 pass. Database size 87 MB of the 500 MB free limit.
- Committed and pushed (`ee0404d`). CI green.
- First "Daily market data" run on GitHub Actions succeeded: NSE downloads work from GitHub's
  servers. It ran at 10:01 IST while the market was open, so no new prices yet - the 19:00 IST
  run picks those up. **Step 1 done.**

---

## 2026-09-17: Step 1 Market data (in progress, paused)

**Decided:** Nifty 500 universe, 3 years of history, Supabase Free, NSE bhavcopy prices,
raw prices + detected splits/bonuses, jobs at 19:00 and 22:00 IST (decisions D9, D11-D15).

**Done:**

- Migration `20260917120000_market_data.sql` applied with the new `jobs.migrate`
  (Step 0 migration marked as already applied).
- Jobs: `sync_universe`, `load_prices`, adjustments, `check_data`, plus NSE/BSE readers.
- `sync_universe` run: 500 companies, 498 with BSE codes (BSE Ltd and CDSL are NSE-only).
- Test loads correct: Sep 2026 (500/day, 14 Sep holiday), Jul 2024 (new format), Sep 2023
  (legacy format, 19 Sep holiday). RELIANCE and Nifty 50 values spot-checked.
- 26 Python tests pass; lint passes. Home page shows data status and job runs.
- Workflow `daily-data.yml` added. Docs updated (decisions, database, architecture, setup, roadmap, step-01).

**Paused:** the full 3-year load stopped after 172 trading days (loaded up to 2024-06-10) when the
database connection dropped (laptop sleeping). Days already loaded are saved; the job is resumable.
Nothing is committed yet.

**Fix to make when resuming:** `load_prices` should survive a dropped connection (reconnect and
retry the day) instead of stopping the whole run.

**To resume:**

1. `.venv\Scripts\python -m jobs.load_prices` (continues from the missing days)
2. load splits/bonuses and check the RELIANCE bonus (Oct 2024) is found
3. `.venv\Scripts\python -m jobs.check_data`
4. Fill in "How it was checked" in `docs/steps/step-01-market-data.md`
5. Commit, push, run "Daily market data" once from GitHub Actions (tests NSE access from GitHub)

---

## 2026-09-17: First Vercel deploy failed

- Error: build crashed with "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY".
- Cause 1: the two variables were not available to the Vercel build.
- Cause 2 (code): `web/src/lib/supabase/server.ts` checked the keys before reading cookies, so Next.js tried to
  render the home page at build time. Fixed by reading cookies first. Build now passes even without keys.
- Added a troubleshooting note to setup.md section G.
- After adding the variables in Vercel and redeploying: the app works on Vercel (login page loads for the owner).
- Note: deployment-specific URLs (`market-lens-<hash>-...vercel.app`) are behind Vercel Authentication, so
  other users must use the production domain (Vercel → Project → Settings → Domains).
- Production URL: https://market-lens-tau-five.vercel.app. Checked: `/api/health` = ok (HTTP 200),
  `/` redirects to `/login`, `/login` loads.

---

## 2026-09-17: Step 0 tested against real Supabase

- Committed Step 0 (`e8c99e3`).
- Fixed `DATABASE_URL`: switched from the Direct connection host (IPv6-only, unreachable) to the Session pooler.
- Passed: Python health check, `/api/health` = ok, RLS on all tables, policies + sign-up trigger present,
  logged-out users cannot read or write data, wrong-password login rejected.
- Browser sign-up, email confirmation and login work; 2 users confirmed, both with profiles.
- Remaining: push to GitHub (CI) and deploy on Vercel.

---

## 2026-09-17: Step 0 Foundation (code)

**Decided** (details in [decisions.md](decisions.md)):

- NSE + BSE stocks, linked by ISIN.
- Weekly/monthly horizon → end-of-day data only; weekly/monthly bars built from daily.
- Next.js on Vercel; Supabase for database + multi-user login; Python jobs on GitHub Actions; OpenAI for AI.

**Done:**

- Read both PDFs in `docs/` (method + app specification).
- Installed Node.js 24 LTS. Created Python venv `.venv\` with psycopg, python-dotenv, pytest, ruff.
- Python jobs skeleton: settings, JSON logging, DB connection, health check + 6 tests.
- Database migration: `profiles`, `companies`, `job_runs`, `health()`, with Row Level Security.
- Website: Next.js 16 app with Supabase login (sign up / log in / log out), protected pages,
  `/api/health`.
- CI workflow for Python and website.
- Docs: README, decisions, architecture, roadmap, setup, database, step-00.

**Checked:** Python tests and style pass; website lint and build pass; health endpoint and login
redirect behave correctly without a database.

**Next:** Connect Supabase, GitHub and Vercel accounts (setup.md D–G), then start Step 1 (market data).
