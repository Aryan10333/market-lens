# Architecture

## The big picture

```
  NSE / BSE daily files                                    OpenAI
          |                                                  ^
          v                                                  |
  +------------------+      writes      +-----------+  reads  +------------------+
  | Python jobs      | ---------------> | Supabase  | <------ | Website (Next.js)|
  | (GitHub Actions, |                  | Postgres  |         | on Vercel        |
  |  once a day)     |                  | + Auth    |         |                  |
  +------------------+                  +-----------+         +------------------+
                                                                      ^
                                                                      |
                                                                    Users
                                                              (each with a login)
```

## Who does what

| Part | Job | Where it runs |
|---|---|---|
| **Python jobs** (`jobs/`) | Download prices, calculate indicators, run scanners, save results | GitHub Actions (scheduled) or your PC |
| **Supabase** | Stores all data. Handles sign-up and login. Protects private data with RLS. | Supabase cloud |
| **Website** (`web/`) | Shows scanners, charts, analysis. Saves users' notes. Calls OpenAI for reports. | Vercel |

## How a user request flows

1. A user opens a page in the browser.
2. `web/src/proxy.ts` runs first: it refreshes the login session and sends logged-out users to `/login`.
3. The page (server side) reads from Supabase **as that user**, so RLS decides what they can see.
4. The HTML is sent back to the browser.

## Keys and secrets

| Key | Used by | Secret? |
|---|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | Website | No (public) |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Website | No (public; RLS limits it) |
| `DATABASE_URL` (contains DB password) | Python jobs | **Yes** |
| `OPENAI_API_KEY` | Website server, jobs | **Yes** |

Secret keys live only in `.env` / `.env.local` on your PC, in Vercel's environment settings, and in
GitHub repository secrets. They are never committed to git.

## Folder map

```
market-lens/
  .env.example            settings template for Python jobs
  requirements.txt        Python packages needed to run
  requirements-dev.txt    Python packages for tests and style checks
  ruff.toml               Python style rules
  jobs/                   Python jobs
    config.py             reads settings from .env
    log.py                JSON log lines
    db.py                 database connection
    health_check.py       checks the DB connection and tables
  tests/                  Python tests (pytest)
  supabase/
    config.toml           Supabase CLI settings
    migrations/           database changes, one .sql file each
  web/                    website
    .env.example          settings template for the website
    src/proxy.ts          runs before each request (login session)
    src/lib/supabase/     Supabase clients (browser, server, proxy)
    src/app/page.tsx      home page
    src/app/login/        login and sign-up page
    src/app/auth/confirm/ email confirmation link handler
    src/app/api/health/   GET /api/health
  .github/workflows/ci.yml  automatic checks
  docs/                   documentation
```
