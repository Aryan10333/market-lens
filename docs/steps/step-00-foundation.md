# Step 0: Foundation

**Goal:** An empty but working app skeleton: website with login, database tables, Python jobs
setup, automatic checks, and health checks. No market data yet.

**Status:** Working locally with the real Supabase project. Remaining: GitHub push (CI) and Vercel deploy.

## What was built

### 1. Tools

- Installed **Node.js 24 LTS** (needed for the website).
- Created the Python virtual environment `.venv\` (Python 3.12) and installed packages.

### 2. Python jobs (`jobs/`)

| File | What it does |
|---|---|
| `config.py` | Reads settings (`APP_ENV`, `LOG_LEVEL`, `DATABASE_URL`, `OPENAI_API_KEY`) from `.env`. Stops with a clear message if a value is invalid or missing. |
| `log.py` | Makes every log line a JSON object (time, level, message, extra fields). Easy to search. |
| `db.py` | Opens a connection to Supabase Postgres. |
| `health_check.py` | Connects to the database and checks the Step 0 tables exist. |

Tests in `tests/test_config.py` (6 tests): default settings, cleaning of values, invalid values
rejected, missing-setting message, JSON log format.

### 3. Database (`supabase/migrations/20260917000000_foundation.sql`)

- `profiles`: one per user, created automatically on sign-up; private to that user.
- `companies`: NSE + BSE company master, keyed by ISIN; readable by logged-in users.
- `job_runs`: log of job runs; readable by logged-in users.
- `health()` function for the health endpoint.

Details: [database.md](../database.md).

### 4. Website (`web/`)

Created with `create-next-app` (Next.js 16, TypeScript, Tailwind CSS), plus Supabase packages.

| File | What it does |
|---|---|
| `src/lib/supabase/env.ts` | Reads the Supabase URL and publishable key |
| `src/lib/supabase/client.ts` | Supabase client for browser code |
| `src/lib/supabase/server.ts` | Supabase client for server code (acts as the logged-in user) |
| `src/lib/supabase/proxy.ts` + `src/proxy.ts` | Before every request: refresh the login session; send logged-out users to `/login` |
| `src/app/login/page.tsx` + `actions.ts` | Log in, sign up, log out (email + password) |
| `src/app/auth/confirm/route.ts` | Handles the link in the sign-up confirmation email |
| `src/app/api/health/route.ts` | `GET /api/health`: 200 if the database answers, 503 if not |
| `src/app/page.tsx` | Home page (logged-in only): shows user email and foundation status |

Public pages (no login needed): `/login`, `/auth/...`, `/api/health`. Everything else needs login.

> Note: In Next.js 16, "Middleware" is renamed to **Proxy** (`proxy.ts`).

### 5. Automatic checks (`.github/workflows/ci.yml`)

On every push / pull request:

- Python: style check (`ruff`), format check, tests (`pytest`).
- Website: lint (`eslint`) and production build.

### 6. Documentation (`docs/`)

`README.md`, `decisions.md`, `architecture.md`, `roadmap.md`, `setup.md`, `database.md`,
`progress-log.md`, and this file.

## How it was checked

| Check | Result |
|---|---|
| Python tests | 6 passed |
| Python style (`ruff check`, `ruff format --check`) | passed |
| `jobs.health_check` without `DATABASE_URL` | exits with clear message "DATABASE_URL is not set" |
| Website lint | passed |
| Website production build | passed; all routes dynamic |
| `GET /api/health` with no real database | HTTP 503, `"database":"error"` (correct) |
| `GET /` while logged out | HTTP 307 redirect to `/login` (correct) |
| `GET /login` | HTTP 200 |

### Checked against the real Supabase project (2026-09-17)

| Check | Result |
|---|---|
| `jobs.health_check` | passed; tables `companies`, `job_runs`, `profiles` found |
| `GET /api/health` | HTTP 200, `"database":"ok"` |
| RLS switched on for all 3 tables | yes |
| Policies and sign-up trigger exist | yes (4 policies, `on_auth_user_created`) |
| Logged-out visitor reads `companies` | 0 rows visible (blocked, correct) |
| Logged-out visitor writes `job_runs` | blocked by RLS (correct) |
| Login with wrong password | rejected (correct) |

Problem found and fixed: `DATABASE_URL` first used the **Direct connection** host
(`db.<ref>.supabase.co`), which is IPv6-only and could not be reached. Use the **Session pooler**
string instead (host ends in `pooler.supabase.com`, user `postgres.<ref>`).

Checked by hand in the browser: sign-up, email confirmation and login work. 2 users signed up and confirmed; each got a `profiles` row automatically.

## What you need to do

Supabase setup, local checks and sign-up are done. Remaining, from [setup.md](../setup.md):

1. **F:** Push to GitHub (`origin` = `github.com/Aryan10333/market-lens`); add the `DATABASE_URL` secret.
2. **G:** Import into Vercel with Root Directory `web`; add the two `NEXT_PUBLIC_SUPABASE_*` variables;
   add the Vercel URL to Supabase Site URL and Redirect URLs.

## Done when

- [x] `jobs.health_check` prints "Health check passed"
- [x] `/api/health` returns `"status":"ok"` locally
- [ ] `/api/health` returns `"status":"ok"` on Vercel
- [x] Two different users can sign up and log in separately
- [ ] CI is green on GitHub
