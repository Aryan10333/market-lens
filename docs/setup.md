# Setup

Commands are for **PowerShell on Windows**, run from the project folder `market-lens\`
unless a step says otherwise.

## A. Tools on your PC (one time)

| Tool | Check | Status |
|---|---|---|
| Python 3.12 | `python --version` | installed |
| Node.js 24 LTS | `node --version` | installed (open a **new** terminal if `node` is not found) |
| Git | `git --version` | installed |

## B. Python virtual environment (one time)

Already created in `.venv\`. To re-create it from scratch:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
```

To use it, either:

- run commands with the venv's Python directly: `.venv\Scripts\python -m pytest`, or
- activate it: `.venv\Scripts\Activate.ps1` (then just `python`, `pytest`, `ruff`).
  If PowerShell blocks this, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## C. Website packages (one time)

```powershell
cd web
npm install
```

## D. Create the Supabase project (one time)

1. Sign in at https://supabase.com → **New project**.
   - Region: **Mumbai (ap-south-1)**, closest to Indian users.
   - Save the **database password** somewhere safe.
2. Copy these values:
   - **Project URL** and **Publishable key**: Project Settings → API Keys.
   - **Session pooler connection string**: click **Connect** → "Session pooler". Put your password into it.
3. Create the settings files:
   - Copy `web\.env.example` to `web\.env.local` and fill in URL + publishable key.
   - Copy `.env.example` to `.env` and fill in `DATABASE_URL`.
4. Create the tables (runs every `supabase/migrations/*.sql` file not applied yet):

   ```powershell
   .venv\Scripts\python -m jobs.migrate
   ```
5. Login settings: Authentication → URL Configuration:
   - **Site URL:** `http://localhost:3000` (change to the Vercel URL after deploying).
   - **Redirect URLs:** add `http://localhost:3000/auth/confirm`.
6. (Recommended) Authentication → Email Templates → "Confirm signup": change the link to

   ```
   {{ .SiteURL }}/auth/confirm?token_hash={{ .TokenHash }}&type=email
   ```

   so confirmation links work even if opened in a different browser.

> Note: Supabase's built-in email sender allows only a few emails per hour. Before inviting many
> users, set up your own SMTP (Authentication → Emails → SMTP settings).

## E. Check that everything connects

```powershell
# Python jobs -> database
.venv\Scripts\python -m jobs.health_check
```

Expected: a line containing `"Health check passed"`.

```powershell
# Website
cd web
npm run dev
```

Then:

- Open http://localhost:3000/api/health → should show `"status":"ok"`.
- Open http://localhost:3000 → redirects to login → **Sign up** → confirm email → log in →
  home page shows "Foundation status".

## F. Put the code on GitHub (one time)

1. Create an empty **private** repository on GitHub.
2. Commit and push this folder to it.
3. Repository → Settings → Secrets and variables → Actions → add secret `DATABASE_URL`
   (used by the scheduled data jobs from Step 1).

CI (`.github/workflows/ci.yml`) then runs automatically on every push.

## G. Deploy the website to Vercel (one time)

1. Sign in at https://vercel.com → **Add New → Project** → import the GitHub repository.
2. **Root Directory:** `web`.
3. **Environment Variables:** add `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
4. Deploy. Open `https://YOUR-APP.vercel.app/api/health`.
5. Back in Supabase → Authentication → URL Configuration:
   - Site URL: `https://YOUR-APP.vercel.app`
   - Add redirect URL: `https://YOUR-APP.vercel.app/auth/confirm`

Every push to `main` now deploys automatically.

**Which URL to use:** each deploy gets its own URL like `market-lens-abc123-yourteam.vercel.app`. Those are
protected by *Vercel Authentication* (only your Vercel account can open them). Give users, and put into
Supabase, the **production domain** shown in Vercel → Project → Settings → **Domains**
(for example `market-lens-yourteam.vercel.app`, or your own domain).

**If the build fails with "Missing NEXT_PUBLIC_SUPABASE_URL ...":** the variables are not visible to the build.
In Vercel → Project → Settings → Environment Variables, check:

- names are spelled exactly `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`,
- values have no quotes and no spaces,
- **Production** and **Preview** are both ticked.

Then Deployments → latest → **Redeploy**. Variables added after a build only apply to the next build.

## H. Daily market data (one time)

1. Make sure the GitHub secret `DATABASE_URL` is set (section F).
2. GitHub → **Actions** → **Daily market data** → **Run workflow** to test it once.
3. After that it runs by itself every weekday at 19:00 and 22:00 IST.
4. If a run fails, open it: the **Check data quality** step prints a report.

To load data from your own PC instead:

```powershell
.venv\Scripts\python -m jobs.sync_universe       # 1. company list
.venv\Scripts\python -m jobs.load_prices         # 2. prices (first run ~40 min for 3 years)
.venv\Scripts\python -m jobs.load_corporate_actions  # 3. splits/bonuses
.venv\Scripts\python -m jobs.build_features      # 4. calculations (averages, 52w, RS...)
.venv\Scripts\python -m jobs.run_scanners        # 5. scanners
.venv\Scripts\python -m jobs.check_data          # 6. report
```

## Everyday commands

| What | Command |
|---|---|
| Run Python tests | `.venv\Scripts\python -m pytest` |
| Check Python style | `.venv\Scripts\python -m ruff check .` |
| Auto-format Python | `.venv\Scripts\python -m ruff format .` |
| Check DB connection | `.venv\Scripts\python -m jobs.health_check` |
| Start website locally | `cd web` then `npm run dev` |
| Check website code | `cd web` then `npm run lint` and `npm run build` |
| Create a new DB migration | add `supabase\migrations\YYYYMMDDHHMMSS_short_name.sql` |
| See applied / pending migrations | `.venv\Scripts\python -m jobs.migrate --list` |
| Apply migrations | `.venv\Scripts\python -m jobs.migrate` |
| Update company list | `.venv\Scripts\python -m jobs.sync_universe` |
| Load new prices | `.venv\Scripts\python -m jobs.load_prices` |
| Re-load a date range | `.venv\Scripts\python -m jobs.load_prices --start 2026-09-01 --end 2026-09-05 --reload` |
| Load splits/bonuses | `.venv\Scripts\python -m jobs.load_corporate_actions` |
| Calculate features | `.venv\Scripts\python -m jobs.build_features` |
| Recalculate everything | `.venv\Scripts\python -m jobs.build_features --rebuild` |
| Run scanners (latest day) | `.venv\Scripts\python -m jobs.run_scanners` |
| Replay scanners over history | `.venv\Scripts\python -m jobs.run_scanners --from 2023-09-18` |
| Data quality report | `.venv\Scripts\python -m jobs.check_data` |
