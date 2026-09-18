# Step 3: Scanner V1

**Goal:** The five price-volume screens from the methodology, each reproducible and able to
explain itself, plus a page to look through the results.

**Status:** Done locally, running in the daily workflow.

## The five scanners

Thresholds live in `config/scanners.json`, not in the code, so they can be changed without
touching a rule. Every scanner first requires the stock to be liquid enough to act on
(₹1 crore a day average traded value).

| Scanner | Triggers when | Signals in 3 years |
|---|---|---|
| **Price + volume surge** | Price up 4%+ on 2× normal volume — the methodology's first-level screen | 7,998 |
| **Volume expansion** | Volume 3× its 20-day average with price not falling | 8,585 |
| **Consolidation breakout** | Price leaves a range it stayed inside 60+ days, on 1.5× volume ("bamboo") | 483 |
| **New high breakout** | Within 0.5% of the 52-week high, on above-average volume, 30-week average rising | 559 |
| **Sector trend** | Stock above its 30-week average, in a sector in the top 20% and beating the market | 4,451 |

Two rules follow the methodology deliberately:

- **New high breakout requires a rising 30-week average.** The methodology is explicit that price
  being near a high, or above an average, is not enough on its own.
- **Sector trend only fires on the day it becomes true.** It describes a state that lasts weeks.
  Left as a state it produced 24,762 signals — 60% of everything. Now it fires when the sector
  moves into the lead, or the stock climbs back above its 30-week average, and the signal records
  which of the two it was. That dropped it to 4,451.

## How a result explains itself

Every signal stores the numbers that made it trigger. For example, GRAPHITE on 9 Sep 2026:

```
Broke ₹802.40 after 80 days in range, 12.9× volume
  Close ₹844.70 · above the level by 5.3% · range width 23% · rule scanner_v2
```

The scanner page shows that line, and "Why it triggered" opens the full evidence. Nobody needs to
read the code to understand a signal, which the spec requires.

## Reproducibility

- `config/scanners.json` carries a **version** (`scanner_v2`), stored with every signal.
- The first run of a version saves the whole configuration into `rule_versions`.
- If the file changes without the version changing, **the job refuses to run**: old signals would
  no longer be explained by the stored thresholds.
- Signals can be replayed over any date range, and a replay produces the same result from the same
  data and version.

## What was built

| File | What it does |
|---|---|
| `config/scanners.json` | Every threshold, plus the rule version |
| `jobs/scanners.py` | The five rules as plain functions returning evidence (or nothing) |
| `jobs/sectors.py` | Which NSE index represents each sector (18 of 20; Textiles and Diversified have none) |
| `jobs/features.py` → `build_sector_features` | Sector returns vs the benchmark, ranked 0–100 each day |
| `jobs/run_scanners.py` | Runs the scanners, saves signals, guards the rule version |
| `web/src/app/scanner/page.tsx` | Results for a day, filterable, with "why it triggered" |
| `web/src/lib/scanners.ts` | Plain-word descriptions of each scanner and its evidence |
| Migration `20260918080000_scanners.sql` | `sector_features`, `rule_versions`, `signals` |

## How it was checked

### 22 new tests (83 in total)

`tests/test_scanners.py` covers each rule at its boundary: a breakout needs price above the range,
a long enough range, enough volume, and a range narrow enough to be a consolidation; a new high
needs a rising long-term trend; volume expansion ignores falling prices; a surge needs both price
and volume; sector trend needs a leading sector, a strong stock, and a fresh start. Plus:
thin stocks are skipped by everything, young stocks without history trigger nothing, one day can
trigger several scanners, and the config has thresholds for every scanner.

`tests/test_features.py` adds sector comparisons: a rising sector beats a flat market and ranks
100, a falling one ranks lower.

### Against the real data

| Check | Result |
|---|---|
| 3-year replay | 22,076 signals across the five scanners, in about 2 minutes |
| Consolidation breakouts | e.g. GRAPHITE 9 Sep 2026: 80 days in range, 12.9× volume — the pattern the methodology describes |
| Quiet day (17 Sep 2026) | 31 signals, no breakouts. Verified as correct: the nearest stock to a 52-week high was 0.63% below it, against a 0.5% threshold |
| Page query | Checked against the API; a logged-out visitor correctly sees nothing (RLS) |
| Storage | 186 MB of 500 MB after tidying up |

### A storage problem found and fixed

Rebuilding all 351k feature rows left dead rows behind, pushing the database from 190 MB to
313 MB without adding real data. After tidying up it is 186 MB. `build_features` now cleans up
automatically after a large rewrite, and `check_data` warns above 400 MB.

## Known limitations

- **No custom scanner builder yet.** The spec's "advanced filter builder with AND/OR conditions"
  and saved scanners are a later addition; V1 ships the five preset screens.
- **Clicking a result does not open a stock page yet** — that is Step 4.
- **Thresholds are first guesses.** They are configuration, not findings. Whether these numbers
  pick good candidates is a question for the backtester in Step 12.
- **Two sectors have no index** (Textiles, Diversified), so their stocks never trigger the sector
  scanner. They still appear in the other four.

## Done when

- [x] Five scanners implemented as pure, tested functions
- [x] Thresholds in configuration, versioned, and enforced against drift
- [x] Signals stored with the evidence behind each trigger
- [x] 3 years replayed
- [x] Scanner page showing results and "why it triggered"
- [x] Runs daily in GitHub Actions
