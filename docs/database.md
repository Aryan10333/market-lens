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

## Functions

| Function | Purpose |
|---|---|
| `health()` | Returns `{"database": "ok", "time": ...}`. Used by `GET /api/health`. Reveals no data. |
| `set_updated_at()` | Trigger that keeps `updated_at` current. |
| `handle_new_user()` | Trigger that creates a `profiles` row on sign-up. |
