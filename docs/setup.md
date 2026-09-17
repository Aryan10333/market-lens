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
4. Create the tables (runs `supabase/migrations/*.sql` on your project):

   ```powershell
   npx supabase login
   npx supabase link --project-ref YOUR_PROJECT_REF
   npx supabase db push
   ```

   The project ref is the part of the URL before `.supabase.co`.
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

## Everyday commands

| What | Command |
|---|---|
| Run Python tests | `.venv\Scripts\python -m pytest` |
| Check Python style | `.venv\Scripts\python -m ruff check .` |
| Auto-format Python | `.venv\Scripts\python -m ruff format .` |
| Check DB connection | `.venv\Scripts\python -m jobs.health_check` |
| Start website locally | `cd web` then `npm run dev` |
| Check website code | `cd web` then `npm run lint` and `npm run build` |
| Create a new DB migration | `npx supabase migration new short_name` |
| Apply migrations | `npx supabase db push` |
