import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { logout } from "./login/actions";

// Home page (logged-in users only; proxy.ts redirects everyone else to /login).
// Shows the state of the market data loaded by the Python jobs.
export default async function Home() {
  const supabase = await createClient();

  const [claims, members, firstFile, lastFile, benchmark, features, runs] =
    await Promise.all([
      supabase.auth.getClaims(),
      supabase
        .from("universe_members")
        .select("*", { count: "exact", head: true })
        .eq("universe", "NIFTY500")
        .is("removed_on", null),
      supabase
        .from("price_files")
        .select("trade_date")
        .eq("kind", "equity")
        .eq("status", "loaded")
        .order("trade_date", { ascending: true })
        .limit(1)
        .maybeSingle(),
      supabase
        .from("price_files")
        .select("trade_date, rows_saved, loaded_at")
        .eq("kind", "equity")
        .eq("status", "loaded")
        .order("trade_date", { ascending: false })
        .limit(1)
        .maybeSingle(),
      supabase
        .from("index_prices")
        .select("trade_date, close")
        .eq("index_name", "Nifty 500")
        .order("trade_date", { ascending: false })
        .limit(1)
        .maybeSingle(),
      supabase
        .from("daily_features")
        .select("trade_date, feature_version")
        .order("trade_date", { ascending: false })
        .limit(1)
        .maybeSingle(),
      supabase
        .from("job_runs")
        .select("id, job_name, status, started_at, message")
        .order("started_at", { ascending: false })
        .limit(8),
    ]);

  const email = String(claims.data?.claims.email ?? "unknown");
  const loadError = [
    members,
    firstFile,
    lastFile,
    benchmark,
    features,
    runs,
  ].find((r) => r.error)?.error;

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-10">
      <header className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Market Lens</h1>
        <div className="flex items-center gap-3">
          <Link
            href="/scanner"
            className="rounded border px-3 py-1.5 text-sm hover:bg-neutral-50"
          >
            Scanner
          </Link>
          <form action={logout}>
            <button className="rounded border px-3 py-1.5 text-sm">
              Log out
            </button>
          </form>
        </div>
      </header>

      <p className="text-sm text-neutral-500">Logged in as {email}</p>

      {loadError && (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">
          Could not read market data: {loadError.message}
        </p>
      )}

      <section className="rounded border p-4">
        <h2 className="mb-3 font-medium">Market data</h2>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-neutral-500">Universe</dt>
            <dd>Nifty 500 · {members.count ?? 0} companies</dd>
          </div>
          <div>
            <dt className="text-neutral-500">Prices loaded</dt>
            <dd>
              {firstFile.data && lastFile.data
                ? `${firstFile.data.trade_date} to ${lastFile.data.trade_date}`
                : "none yet"}
            </dd>
          </div>
          <div>
            <dt className="text-neutral-500">Latest trading day</dt>
            <dd>
              {lastFile.data
                ? `${lastFile.data.trade_date} · ${lastFile.data.rows_saved} companies`
                : "none yet"}
            </dd>
          </div>
          <div>
            <dt className="text-neutral-500">Calculations</dt>
            <dd>
              {features.data
                ? `up to ${features.data.trade_date} · ${features.data.feature_version}`
                : "none yet"}
            </dd>
          </div>
          <div>
            <dt className="text-neutral-500">Nifty 500 close</dt>
            <dd>
              {benchmark.data
                ? `${Number(benchmark.data.close).toLocaleString("en-IN")} on ${benchmark.data.trade_date}`
                : "none yet"}
            </dd>
          </div>
        </dl>
      </section>

      <section className="rounded border p-4">
        <h2 className="mb-3 font-medium">Recent job runs</h2>
        {runs.data && runs.data.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-neutral-500">
                <tr>
                  <th className="py-1 pr-3 font-normal">Job</th>
                  <th className="py-1 pr-3 font-normal">Status</th>
                  <th className="py-1 pr-3 font-normal">Started (IST)</th>
                  <th className="py-1 font-normal">Summary</th>
                </tr>
              </thead>
              <tbody>
                {runs.data.map((r) => (
                  <tr key={r.id} className="border-t align-top">
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {r.job_name}
                    </td>
                    <td
                      className={`py-1.5 pr-3 ${
                        r.status === "failed"
                          ? "text-red-700"
                          : r.status === "running"
                            ? "text-amber-700"
                            : ""
                      }`}
                    >
                      {r.status}
                    </td>
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {new Date(r.started_at).toLocaleString("en-IN", {
                        timeZone: "Asia/Kolkata",
                      })}
                    </td>
                    <td className="py-1.5 text-neutral-600">{r.message}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-neutral-500">No job runs yet.</p>
        )}
      </section>
    </main>
  );
}
