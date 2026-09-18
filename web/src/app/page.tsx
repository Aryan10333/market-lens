import Link from "next/link";
import { AppHeader } from "@/components/AppHeader";
import { Badge, Card, EmptyState, ScannerTag, Stat, StatusDot } from "@/components/ui";
import { dayMonth } from "@/lib/format";
import { scannerColour, scannerInfo } from "@/lib/scanners";
import { createClient } from "@/lib/supabase/server";

// Dashboard: the state of the data, and what the scanners found most recently.
export default async function Home() {
  const supabase = await createClient();

  const [claims, members, firstFile, lastFile, benchmark, features, signalDay, runs] =
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
        .select("trade_date, rows_saved")
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
        .limit(2),
      supabase
        .from("daily_features")
        .select("trade_date, feature_version")
        .order("trade_date", { ascending: false })
        .limit(1)
        .maybeSingle(),
      supabase
        .from("signals")
        .select("trade_date")
        .order("trade_date", { ascending: false })
        .limit(1)
        .maybeSingle(),
      supabase
        .from("job_runs")
        .select("id, job_name, status, started_at, message")
        .order("started_at", { ascending: false })
        .limit(6),
    ]);

  const email = String(claims.data?.claims.email ?? "");
  const latestSignalDay = signalDay.data?.trade_date ?? null;

  const recentSignals = latestSignalDay
    ? await supabase
        .from("signals")
        .select("id, scanner")
        .eq("trade_date", latestSignalDay)
        .limit(500)
    : null;

  const perScanner = new Map<string, number>();
  for (const s of recentSignals?.data ?? []) {
    perScanner.set(s.scanner, (perScanner.get(s.scanner) ?? 0) + 1);
  }

  const [latestIndex, previousIndex] = benchmark.data ?? [];
  const indexMove =
    latestIndex && previousIndex
      ? (Number(latestIndex.close) - Number(previousIndex.close)) / Number(previousIndex.close)
      : null;

  const loadError = [members, firstFile, lastFile, benchmark, features, runs].find(
    (r) => r.error,
  )?.error;

  return (
    <>
      <AppHeader email={email} current="/" />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 px-4 py-6">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-xl font-semibold">Dashboard</h1>
            <p className="text-sm text-muted">
              {lastFile.data
                ? `Market data up to ${dayMonth(lastFile.data.trade_date)}`
                : "No market data yet"}
            </p>
          </div>
          {latestSignalDay && (
            <Link
              href="/scanner"
              className="rounded-lg bg-brand px-3 py-1.5 text-sm font-medium text-on-brand"
            >
              Open scanner
            </Link>
          )}
        </div>

        {loadError && (
          <p className="rounded-xl border border-negative/40 bg-negative-soft px-4 py-3 text-sm text-negative">
            Could not read market data: {loadError.message}
          </p>
        )}

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat
            label="Nifty 500"
            value={
              latestIndex
                ? Number(latestIndex.close).toLocaleString("en-IN", { maximumFractionDigits: 2 })
                : "—"
            }
            tone={indexMove === null ? "default" : indexMove >= 0 ? "positive" : "negative"}
            hint={
              indexMove === null
                ? undefined
                : `${indexMove >= 0 ? "▲" : "▼"} ${(Math.abs(indexMove) * 100).toFixed(2)}% on the day`
            }
          />
          <Stat label="Universe" value={members.count ?? 0} hint="Nifty 500 companies tracked" />
          <Stat
            label="Signals"
            value={recentSignals?.data?.length ?? 0}
            hint={latestSignalDay ? `on ${dayMonth(latestSignalDay)}` : "none yet"}
          />
          <Stat
            label="History"
            value={
              firstFile.data && lastFile.data
                ? `${new Date(firstFile.data.trade_date).getFullYear()}–${new Date(
                    lastFile.data.trade_date,
                  ).getFullYear()}`
                : "—"
            }
            hint={features.data ? `calculations ${features.data.feature_version}` : "no features"}
          />
        </div>

        <Card
          title="What the scanners found"
          action={
            <Link href="/scanner" className="text-sm text-brand hover:underline">
              See all →
            </Link>
          }
        >
          {perScanner.size === 0 ? (
            <EmptyState title="Nothing triggered on the last trading day">
              These screens are meant to be narrow. Quiet days are a normal result.
            </EmptyState>
          ) : (
            <div className="flex flex-wrap gap-2">
              {[...perScanner.entries()]
                .sort((a, b) => b[1] - a[1])
                .map(([scanner, count]) => (
                  <Link
                    key={scanner}
                    href={`/scanner?scanner=${scanner}`}
                    className="rounded-xl border border-line px-3 py-2 transition-colors hover:bg-surface-2"
                  >
                    <ScannerTag colour={scannerColour(scanner)}>
                      {scannerInfo(scanner).name}
                    </ScannerTag>
                    <div className="tabular mt-1.5 text-lg font-semibold">{count}</div>
                  </Link>
                ))}
            </div>
          )}
        </Card>

        <Card title="Data jobs">
          {runs.data && runs.data.length > 0 ? (
            <div className="-mx-4 overflow-x-auto px-4">
              <table className="w-full min-w-[34rem] text-left text-sm">
                <thead className="text-xs text-faint">
                  <tr>
                    <th className="pb-2 pr-3 font-medium">Job</th>
                    <th className="pb-2 pr-3 font-medium">Started (IST)</th>
                    <th className="pb-2 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.data.map((r) => (
                    <tr key={r.id} className="border-t border-line align-top">
                      <td className="py-2 pr-3 whitespace-nowrap">
                        <span className="flex items-center gap-2">
                          <StatusDot status={r.status} />
                          <span className="font-mono text-xs">{r.job_name}</span>
                        </span>
                      </td>
                      <td className="tabular py-2 pr-3 whitespace-nowrap text-muted">
                        {new Date(r.started_at).toLocaleString("en-IN", {
                          timeZone: "Asia/Kolkata",
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </td>
                      <td className="py-2 text-muted">
                        {r.status === "failed" ? <Badge tone="negative">failed</Badge> : r.message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState title="No jobs have run yet" />
          )}
        </Card>
      </main>
    </>
  );
}
