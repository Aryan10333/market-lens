# Progress log

Newest entries at the top. One entry per working session.

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
