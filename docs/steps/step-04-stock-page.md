# Step 4: Stock analysis page

**Goal:** Open any company and see what is happening to it: price and volume, which Stage it is in
and why, the numbers behind that, and every scanner signal it has produced.

**Status:** Done locally, running in the daily workflow.

## Stage analysis (`jobs/stages.py`, `config/stages.json`)

| Stage | What it means | How it is decided |
|---|---|---|
| **1 Basing** | Sideways after a fall. Watch, do not buy. | Flat 30-week average, price in a range near its lows |
| **2 Advancing** | The buy zone. | Above a **rising** 30-week average, within 25% of the 52-week high, not among the weakest stocks |
| **3 Topping** | The advance has stalled. | Above an average that has flattened, or price slipping below an average that is still rising |
| **4 Declining** | No reason to hold. | Below a **falling** 30-week average |

Two rules matter more than the thresholds:

- **Price above a moving average is not Stage 2.** The methodology is explicit about this, and the
  test suite checks it three ways: a flat average, a price far from its high, and a weak stock all
  fail to qualify.
- **A stage change must hold for 5 trading days.** Without this, a share wobbling around its
  average changed stage every few days. RELIANCE flipped between Stage 1 and 3 six times in eight
  months; now it changes about six times in three years. Across the universe: ~12 changes per
  company over three years.

Every decision stores its evidence — where price sits against the 30-week average, the average's
trend, distance from the 52-week high and low, strength rank, days in range — and a sentence
saying why.

## The page (`/stocks/<symbol>`)

- **Header**: symbol, name, sector, NSE symbol, BSE code, ISIN.
- **Four stat tiles**: close with the day's move, 52-week range, strength rank against the market,
  and liquidity.
- **Chart**: daily and weekly candles (split-adjusted) with the 30-week average and volume bars.
  Colours come from the page theme, so it follows light and dark mode.
- **Stage card**: the stage, since when, why, and the evidence behind it.
- **Technical numbers**: 50- and 200-day averages, 1-month and 1-year moves, volatility, average
  volume, and the 120-day range.
- **Signal history**: every scanner signal for that company, most recent first.

Scanner results now link straight to this page.

## Problems found and fixed

### 1. The database nearly filled up (492 MB of 500 MB)

Two causes:

- Rebuilding features left the old rows behind (~50% of both big tables were dead rows).
- `daily_stages` stored the full evidence for **every day**, making it 193 MB for 260k rows —
  larger than the prices it came from.

Fixed by storing evidence **only on the day the stage changed** (which is when the decision was
actually made) plus a `stage_since` date on every row, and by compacting the tables properly.
Result: **224 MB**, with the stage table down from 193 MB to about 12 MB.

### 2. A big write failed if the connection dropped

The feature job wrote all 351k rows in one transaction; a dropped connection lost the lot. Writes
now go in batches of 10,000, each retried on a new connection if needed. The reconnect helper moved
to `jobs/db.py` and is shared by the price, feature and stage jobs.

### 3. Recent listings were wrongly marked "declining"

A share with no 52-week high yet (listed within the year) fell through to Stage 4 even when its
30-week average was rising. Now, price below a **rising** average is Stage 3 — a share can only be
declining once the long trend itself turns down. GROWW and ICICIAMC moved from Stage 4 to Stage 3;
genuinely falling shares (VEDL, RPOWER) stayed at Stage 4.

## How it was checked

### 16 new tests (100 in total)

`tests/test_stages.py`: each stage at its boundary, the three ways "above an average" fails to be
Stage 2, below-a-rising-average is Stage 3 (including a stock with no 52-week high), stage changes
need five days, a one-day wobble changes nothing, flip-flopping never confirms, and every decision
carries a readable reason. `tests/test_features.py` checks the adjusted open/high/low kept for
candles.

### Against the real data

| Check | Result |
|---|---|
| Stages classified | 259,675 company-days; 92k days had too little history (under 40 weeks) |
| Spread on 17 Sep 2026 | basing 70, advancing 152, topping 147, declining 131 |
| Stage changes | 5,928 in three years, about 12 per company |
| Stage 2 examples | WELCORP, PAYTM, ATHERENERG — all above a rising average, near highs, strength rank 99–100 |
| Stage 4 examples | VEDL (23% below a falling average), RPOWER — correct |
| Database | 224 MB of 500 MB after the clean-up |

## Known limitations

- **No fundamental data yet**, so the page is technical only. Financials arrive in Step 6.
- **Charts show about 18 months** of daily bars to keep the page quick; the full history is stored.
- **Stage history is not charted yet** — the page shows the current stage and since when.
- A share can sit at "Stage unknown" for its first 40 weeks, because the 30-week average needs
  30 weeks of data plus 10 more to have a slope.

## Done when

- [x] Stage 1–4 decided by transparent, versioned rules with stored evidence
- [x] "Above an average is not Stage 2" enforced and tested
- [x] Stage changes confirmed over several days, so they mean something
- [x] Daily and weekly candle charts with the 30-week average and volume
- [x] Signal history per company
- [x] Scanner results link to the page
- [x] Runs in the daily workflow
