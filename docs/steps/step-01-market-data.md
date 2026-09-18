# Step 1: Market data

**Goal:** A reliable, automatically updated dataset for the Nifty 500: company list, 3 years of
daily prices, all NSE index values, and detected splits/bonuses, with checks that prove it is correct.

**Status:** Built, loaded and checked locally. Waiting for the first scheduled run on GitHub Actions.

## Decisions made in this step

See [decisions.md](../decisions.md) D9, D11–D15. In short:

- Universe: **Nifty 500** (changed from "all NSE + liquid BSE" to keep the first version small).
- **3 years** of daily prices. **Supabase Free** plan.
- Prices from **NSE bhavcopy** files; BSE only supplies BSE codes.
- Prices stored **raw**; splits/bonuses detected and stored separately.
- Jobs run on **GitHub Actions at 19:00 and 22:00 IST**, Monday–Friday.

## What I checked before building

| Question | Finding |
|---|---|
| Can NSE/BSE files be downloaded? | Yes, with a browser-like User-Agent and Referer |
| How far back does the new NSE format go? | January 2024. Older days use the legacy format (both handled) |
| Is index history available? | Yes, daily `ind_close_all` file for every NSE index, back to 2023 |
| Universe size across NSE + BSE | 5,307 companies (3,019 NSE, 4,687 BSE, 2,399 on both) |
| Storage for Nifty 500 × 3 years | About 375,000 rows, roughly 45 MB |

## What was built

### Database (`supabase/migrations/20260917120000_market_data.sql`)

New tables: `universe_members`, `price_files`, `daily_prices`, `index_prices`, `price_adjustments`.
All readable by logged-in users, written only by jobs. Details: [database.md](../database.md).

### Python jobs

| File | What it does |
|---|---|
| `jobs/migrate.py` | Applies new migration files; records them like the Supabase CLI |
| `jobs/sources/nse.py` | NSE URLs + readers for bhavcopy (both formats), index closes, Nifty 500 list; price validation |
| `jobs/sources/bse.py` | Reads BSE codes (by ISIN) from the BSE bhavcopy |
| `jobs/download.py` | Downloads with browser headers, 0.4 s pause between requests, retries |
| `jobs/sources/nse.py` (actions) | NSE corporate actions API address and reader |
| `jobs/dates.py` | Today in IST, every day in a range, "3 years ago" |
| `jobs/runs.py` | Saves every job run (status, rows, message, errors) to `job_runs` |
| `jobs/adjustments.py` | Reads NSE's action wording ("Bonus 1:1") into a price factor |
| `jobs/sync_universe.py` | Job: Nifty 500 list → `companies` + `universe_members` |
| `jobs/load_prices.py` | Job: NSE files → `daily_prices`, `index_prices`, `price_files` |
| `jobs/load_corporate_actions.py` | Job: NSE corporate actions → `price_adjustments` |
| `jobs/check_data.py` | Job: data quality report; fails on serious problems |

How `load_prices` decides what to download:

1. Every day from 3 years ago to today that has no row in `price_files` yet — weekends
   included, because NSE holds occasional Saturday/Sunday sessions.
2. For each day: try the new-format file, then the legacy file.
3. Match rows to companies by **ISIN**, or by **symbol** if the ISIN changed.
4. Reject rows with impossible values (close outside low–high, price ≤ 0, …).
5. Save prices and the file record in one transaction per day.
6. No file that day → recorded as `no_file` (weekend or holiday), but only once the day is 3+ days old.
7. A company that joined the index in the last 7 days with no prices → its history is back-filled.

### Automation (`.github/workflows/daily-data.yml`)

Weekdays 19:00 and 22:00 IST, or by hand:
sync universe → load prices → load corporate actions → check data.

### Website

Home page now shows: universe size, date range of prices, latest trading day, latest Nifty 500
close, and the last 8 job runs.

### Tests (44 in total, 38 new)

- `tests/test_sources.py`: both bhavcopy formats, ETF/bond rows ignored, blank fields, bad-row
  validation, index file with `-` values, Nifty 500 list, BSE codes (and BSE's HTML error page).
- `tests/test_adjustments.py`: every bonus/split/consolidation wording → factor; dividends, rights,
  buybacks and preference-share bonuses ignored; two actions on one day multiply; the multiplier
  applies only before the ex-date; bad JSON survives; date chunks cover the range.
- `tests/test_dates_and_matching.py`: IST date change, weekends included, leap day,
  ISIN-vs-symbol matching, rejected rows.
- `tests/test_reconnect.py`: retry after a dropped connection, and giving up after 3 tries.

## How it was checked

### Final state of the data (`jobs.check_data`)

```
Universe NIFTY500: 500 companies
Equity files: 744 trading days loaded (2023-09-18 to 2026-09-17), 352 non-trading days
Price rows: 351,651 for 500 companies
Rows rejected while loading (bad values): 0
Members without a price on 2026-09-17: 0
Most missing days (after first price): FORCEMOT 76
Benchmark 'Nifty 500': 744 days, latest 2026-09-17
Indices stored: 172
Splits/bonuses/consolidations: 75
Actions checked against prices: 75 of 75 match
Database size: 87 MB (Supabase Free limit: 500 MB)
Result: OK
```

### Spot checks against reality

| Check | Result |
|---|---|
| RELIANCE close, 18 Sep 2023 | ₹2,436.45 (matches NSE) |
| Nifty 50 close, 18 Sep 2023 | 20,133.30 |
| RELIANCE 1:1 bonus, 28 Oct 2024 | factor 0.5, prices moved x0.5024 |
| BSE codes | Whirlpool 500238, ITI 523610; only BSE Ltd and CDSL have none (NSE-only listings) |
| Holidays | 14 Sep 2026 and 19 Sep 2023 (Ganesh Chaturthi) recorded as non-trading |
| Weekend sessions | 6 found and loaded (Muhurat 2023, three 2024 Saturdays, Budget days 2025 and 2026) |
| 44 Python tests, lint, web lint + build | all pass |

### Three real problems found and fixed

1. **A dropped database connection stopped the whole load.** `load_prices` now reconnects and
   retries the day (up to 3 times). The corporate actions job no longer holds a connection open
   while downloading.
2. **Weekend trading sessions were skipped.** NSE traded on 6 weekend days in 3 years
   (Budget days, Diwali Muhurat). The loader now checks every calendar day.
3. **Splits were guessed from prices, wrongly.** See D14 in [decisions.md](../decisions.md):
   NSE does not adjust `prev_close` on the ex-date, so the old rule produced 777 fake splits and
   found none of the real ones. Splits now come from NSE's official corporate actions list, and
   every one is checked against the price move on its ex-date.

### Known limitations

- **FORCEMOT has 76 missing days** (26 Oct 2023 – 13 Feb 2024). Real: the share does not appear in
  NSE's own files for that period. Calculations must handle gaps rather than assume daily continuity.
- **Membership is current, not historical.** Backtests (Step 12) must allow for survivorship bias.
- **CGCL 5 Mar 2024**: factor 0.25 vs price move 0.30 — inside the 25% tolerance; the share simply
  rose sharply that day.

## Done when

- [x] 3 years of daily prices for the Nifty 500, with source and load time recorded
- [x] Index values for benchmarks and sectors
- [x] Splits/bonuses loaded and all cross-checked against prices
- [x] Data quality report passes
- [x] Home page shows the data status
- [ ] Scheduled GitHub run works (confirms NSE allows downloads from GitHub's servers)
