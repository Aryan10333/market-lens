# Database

All tables live in the `public` schema of the Supabase Postgres database.
Tables are created by the SQL files in `supabase/migrations/`.

Who can do what:

- **Logged-in users** use the website. Row Level Security (RLS) decides which rows they can read or change.
- **Python jobs** connect with the database password (`DATABASE_URL`). They can write shared data.

---

## profiles

One row per user. Created automatically when someone signs up.

| Column | Type | Meaning |
|---|---|---|
| id | uuid | Same as the user's id in Supabase Auth |
| display_name | text | Name shown in the app (defaults to the part of the email before `@`) |
| created_at | timestamptz | When the row was created |
| updated_at | timestamptz | When the row was last changed |

Access: each user can read and update **only their own** row.

---

## companies

Master list of listed companies. Filled by the Python jobs from Step 1.

| Column | Type | Meaning |
|---|---|---|
| id | bigint | Internal number |
| isin | text | ISIN, e.g. `INE002A01018`. Unique. Links NSE and BSE listings. |
| name | text | Company name |
| nse_symbol | text | NSE symbol, e.g. `RELIANCE` (empty if not on NSE) |
| bse_code | text | BSE scrip code, e.g. `500325` (empty if not on BSE) |
| sector | text | Sector |
| industry | text | Industry |
| is_active | boolean | `false` once delisted |
| source | text | Where the data came from |
| created_at / updated_at | timestamptz | Row timestamps |

Rules: ISIN must look like `IN` + 10 letters/digits. At least one of `nse_symbol` or `bse_code` must be filled.

Access: all logged-in users can read. Only jobs can write.

---

## job_runs

A log of every Python job run, so you can see when data was last updated and whether it worked.

| Column | Type | Meaning |
|---|---|---|
| id | bigint | Internal number |
| job_name | text | e.g. `load_prices` |
| status | text | `running`, `success` or `failed` |
| started_at | timestamptz | Start time |
| finished_at | timestamptz | End time |
| rows_written | integer | How many rows the job saved |
| message | text | Summary or error message |

Access: all logged-in users can read. Only jobs can write.

---

## universe_members

Which companies are in the tracked universe, and when. Filled by `jobs.sync_universe`.

| Column | Type | Meaning |
|---|---|---|
| universe | text | Universe name, currently `NIFTY500` |
| company_id | bigint | The company (`companies.id`) |
| added_on | date | First day seen in the index list |
| removed_on | date | Day it was no longer in the list (empty = still a member) |

A company that leaves and re-joins gets a new row. Access: logged-in users read; jobs write.

---

## price_files

One row per exchange file processed. Shows where data came from and when it was loaded.

| Column | Type | Meaning |
|---|---|---|
| exchange | text | `NSE` |
| kind | text | `equity` (share prices) or `index` (index values) |
| trade_date | date | Trading day the file is for |
| status | text | `loaded`, or `no_file` (no file published: market holiday) |
| file_format | text | `udiff` (from 2024) or `legacy` (older), for equity files |
| source_url | text | Exact download address |
| rows_in_file | integer | Rows in the file |
| rows_saved | integer | Rows saved (universe companies only for equity) |
| rows_rejected | integer | Rows skipped because of impossible values |
| loaded_at | timestamptz | When it was loaded |

Access: logged-in users read; jobs write.

---

## daily_prices

End-of-day share prices, **exactly as published by NSE** (not adjusted for splits/bonuses).

| Column | Type | Meaning |
|---|---|---|
| company_id | bigint | The company |
| trade_date | date | Trading day |
| series | text | `EQ` normal; `BE`/`BZ` trade-for-trade (restricted) |
| open, high, low, close | numeric(12,2) | Prices in ₹ |
| prev_close | numeric(12,2) | Previous close as published (adjusted by NSE on split/bonus days) |
| volume | bigint | Shares traded |
| traded_value | numeric(18,2) | Value traded in ₹ |
| num_trades | integer | Number of trades |

Rules: one row per company per day; prices above 0; low ≤ high. Rows where close or open is
outside low–high are rejected by the loader. Access: logged-in users read; jobs write.

---

## index_prices

End-of-day values of all NSE indices (Nifty 50, Nifty 500, sector indices like Nifty IT, etc.).

| Column | Type | Meaning |
|---|---|---|
| index_name | text | Name as NSE publishes it, e.g. `Nifty 500` |
| trade_date | date | Trading day |
| open, high, low | numeric(12,2) | May be empty for some indices |
| close | numeric(12,2) | Closing value |

Access: logged-in users read; jobs write.

---

## price_adjustments

Splits, bonuses and consolidations from NSE's corporate actions list, loaded by
`jobs.load_corporate_actions` (rebuilt every run).

| Column | Type | Meaning |
|---|---|---|
| company_id | bigint | The company |
| ex_date | date | First trading day at the new share count |
| factor | numeric(14,8) | Multiply prices **before** ex_date by this. 1:1 bonus = 0.5, 10→1 split = 0.1 |
| action_type | text | `bonus`, `split`, `consolidation`, or `multiple` (two on the same day) |
| description | text | NSE's own wording, e.g. "Bonus 1:1" |
| observed_ratio | numeric(14,8) | Price move actually seen on the ex-date (close ÷ previous close), for checking |
| source | text | Where it came from (`nse_corporate_actions`) |
| detected_at | timestamptz | When loaded |

Access: logged-in users read; jobs write.

---

## supabase_migrations.schema_migrations

Which migration files have been applied (used by `jobs.migrate` and the Supabase CLI).

---

## Functions

| Function | Purpose |
|---|---|
| `health()` | Returns `{"database": "ok", "time": ...}`. Used by `GET /api/health`. Reveals no data. |
| `set_updated_at()` | Trigger that keeps `updated_at` current. |
| `handle_new_user()` | Trigger that creates a `profiles` row on sign-up. |
