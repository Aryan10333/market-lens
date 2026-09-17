# Step 0: Foundation

**Goal:** An empty but working app skeleton: website with login, database tables, Python jobs
setup, automatic checks, and health checks. No market data yet.

**Status:** Code done and tested locally. Waiting for Supabase / GitHub / Vercel accounts to be
connected (see "What you need to do").

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

Not yet checked (needs your Supabase project): migration applied, real sign-up/login,
health check passing against the real database.

## What you need to do

Follow [setup.md](../setup.md) sections **D → G**:

1. Create the Supabase project, fill in `.env` and `web\.env.local`.
2. Run `npx supabase db push` to create the tables.
3. Run `.venv\Scripts\python -m jobs.health_check` and open `http://localhost:3000`, then sign up.
4. Push to a private GitHub repo; add `DATABASE_URL` secret.
5. Import into Vercel with Root Directory `web`.

## Done when

- [ ] `jobs.health_check` prints "Health check passed"
- [ ] `/api/health` returns `"status":"ok"` locally and on Vercel
- [ ] Two different users can sign up and log in separately
- [ ] CI is green on GitHub
