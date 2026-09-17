# Market Lens

A research app for Indian stocks (NSE + BSE) based on the TechnoFunda method:
a **scanner** finds candidate stocks from price and volume, and a **stock analysis** page explains
each one (stage, fundamentals, four cylinders, MACHINE, RoCE × growth), with AI-written reports.

Hosted on **Vercel**, data in **Supabase**, AI by **OpenAI**.

## Folders

| Folder | What is inside |
|---|---|
| `web/` | The website (Next.js). Pages, login, API routes. Deployed to Vercel. |
| `jobs/` | Python scripts that load market data and do calculations. Run by GitHub Actions. |
| `tests/` | Tests for the Python code. |
| `supabase/` | Database changes (`migrations/*.sql`) and Supabase CLI config. |
| `docs/` | All documentation. Start with `docs/README.md`. |
| `.github/workflows/` | Automatic checks (CI) and, later, scheduled data jobs. |

## Quick start

See [docs/setup.md](docs/setup.md).
