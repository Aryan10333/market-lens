# Step 2: Technical features

**Goal:** Turn raw prices into the numbers the scanner and Stage analysis need — moving averages,
volume ratios, 52-week levels, relative strength and consolidation ranges — calculated the same way
every time, and testable on their own.

**Status:** Done locally. Runs as part of the daily workflow.

## What was built

### The calculations (`jobs/features.py`)

Plain functions over a table of prices, with no database involved, so every rule can be tested
against a made-up price series.

| Function | What it does |
|---|---|
| `adjust_for_splits` | Multiplies prices before an ex-date by the split/bonus factor (and divides volume), so a 1:1 bonus no longer looks like a 50% crash |
| `weekly_bars` | Groups daily bars into weekly ones (Monday–Sunday), keeping the number of trading days in each week |
| `build_features` | Every feature for one company (see the list below) |
| `rank_within_universe` | Ranks one day's values across all companies, 0–100 |

Features per company per day:

- **Returns** over 1, 5, 21, 63 and 252 trading days
- **Moving averages** 20/50/100/200 days, plus the **30-week average** and its 10-week slope
- **Volume**: 20-day average, today's ratio to it, and average traded value (liquidity)
- **52-week high and low**, and the distance from each
- **Volatility** (21 days, yearly scale)
- **Consolidation range**: 120-day high/low **ending yesterday**, its width, and how many days in a
  row the close stayed inside it. Ending yesterday matters: a breakout must be judged against a
  range that today's move did not create.
- **Relative strength** vs the Nifty 500: the ratio, its 3-month and 1-year change, and a 0–100
  rank against the rest of the universe on that day

Long windows stay empty until enough history exists (`sma_200` needs 200 trading days), so no
value is ever calculated from a partial window.

Every row is stamped `features_v1` (`FEATURE_VERSION`). Change that when a rule changes, so old
and new results can be told apart — the spec requires reproducibility: same data + same version =
same result.

### Storage (`supabase/migrations/20260918060000_features.sql`)

`weekly_prices` and `daily_features`, both split-adjusted, readable by logged-in users, written
only by jobs. Columns are described in [database.md](../database.md).

### The job (`jobs/build_features.py`)

Reads prices + corporate actions + the Nifty 500, adjusts, calculates, writes. By default it only
writes days newer than what is stored (the maths still runs over the full history, because a
200-day average needs 200 days behind it). `--rebuild` rewrites everything after a rule change.

### Automation

Added to `daily-data.yml`: sync universe → load prices → load corporate actions →
**calculate features** → check data.

### Checks (`jobs.check_data`)

Now also reports feature rows, weekly bars, and how many companies have each long-window value on
the latest day. It fails if features are missing or lag behind the prices.

## How it was checked

### 15 new tests (59 in total)

`tests/test_features.py` checks each rule against a series where the answer is known by hand:
split adjustment (single and repeated), volume growing after a bonus, weekly grouping including
short holiday weeks, returns, a hand-calculated 20-day average, averages staying empty until
enough history, volume ratio, 52-week levels and distances, the consolidation range excluding
today, `days_in_range` dropping to 0 on a breakout, the 30-week average and its slope, relative
strength against a flat benchmark, the version stamp, empty input, and ranking.

### Against the real data

| Check | Result |
|---|---|
| Build over 3 years | 351,651 feature rows + 74,229 weekly bars for 500 companies, in 8 minutes |
| RELIANCE across its 1:1 bonus | raw ₹2,655.70 → adjusted ₹1,327.85 (exactly half), continuous with ₹1,334.35 next day |
| 20-day average across that bonus | smooth: 1,382 → 1,373 (no false crash) |
| Coverage on the latest day | 500 companies; 498 have a 200-day average, 485 have 52-week levels (the rest are recent listings) |
| Value ranges | RS rank 0.2–100, volume ratio 0.01–19.2, distance below 52-week high 0–82% |
| Weekly bars | The week of 14 Sep 2026 shows 3 trading days — correct, 14 Sep was a holiday |
| Database size | 190 MB of the 500 MB free limit |

## Known limitations

- **Sector-relative strength is not included yet.** It needs a mapping from each company's sector
  to an NSE sector index; that arrives in Step 3 with the sector-trend scanner.
- **Ranks use today's universe.** Members that left the index are not ranked historically
  (survivorship bias, same as Step 1).
- **Storage**: features roughly doubled the database (87 MB → 190 MB). Widening the universe later
  will need the Supabase Pro plan.

## Done when

- [x] Weekly bars and all daily features calculated for the whole history
- [x] Split-adjusted prices verified across a real bonus
- [x] Every rule covered by a test with a hand-checked answer
- [x] Values versioned (`features_v1`) and rebuildable
- [x] Feature checks added to the data quality report
- [x] Included in the daily workflow
