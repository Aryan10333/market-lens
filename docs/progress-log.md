# Progress log

Newest entries at the top. One entry per working session.

---

## 2026-09-17: First Vercel deploy failed

- Error: build crashed with "Missing NEXT_PUBLIC_SUPABASE_URL or NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY".
- Cause 1: the two variables were not available to the Vercel build.
- Cause 2 (code): `web/src/lib/supabase/server.ts` checked the keys before reading cookies, so Next.js tried to
  render the home page at build time. Fixed by reading cookies first. Build now passes even without keys.
- Added a troubleshooting note to setup.md section G.
- After adding the variables in Vercel and redeploying: the app works on Vercel (login page loads for the owner).
- Note: deployment-specific URLs (`market-lens-<hash>-...vercel.app`) are behind Vercel Authentication, so
  other users must use the production domain (Vercel → Project → Settings → Domains).
- Production URL: https://market-lens-tau-five.vercel.app. Checked: `/api/health` = ok (HTTP 200),
  `/` redirects to `/login`, `/login` loads.

---

## 2026-09-17: Step 0 tested against real Supabase

- Committed Step 0 (`e8c99e3`).
- Fixed `DATABASE_URL`: switched from the Direct connection host (IPv6-only, unreachable) to the Session pooler.
- Passed: Python health check, `/api/health` = ok, RLS on all tables, policies + sign-up trigger present,
  logged-out users cannot read or write data, wrong-password login rejected.
- Browser sign-up, email confirmation and login work; 2 users confirmed, both with profiles.
- Remaining: push to GitHub (CI) and deploy on Vercel.

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
