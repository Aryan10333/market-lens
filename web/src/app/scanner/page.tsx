import Link from "next/link";
import { AppHeader } from "@/components/AppHeader";
import { Card, EmptyState, ScannerTag } from "@/components/ui";
import { dayMonth } from "@/lib/format";
import {
  headline,
  scannerColour,
  scannerInfo,
  SCANNER_ORDER,
  type Evidence,
} from "@/lib/scanners";
import { createClient } from "@/lib/supabase/server";

type SignalRow = {
  id: number;
  trade_date: string;
  scanner: string;
  rule_version: string;
  evidence: Evidence;
  companies: { nse_symbol: string | null; name: string; sector: string | null } | null;
};

// Scanner results for one trading day. Every row can explain why it triggered.
export default async function ScannerPage({ searchParams }: PageProps<"/scanner">) {
  const params = await searchParams;
  const chosenScanner = typeof params.scanner === "string" ? params.scanner : null;
  const chosenDate = typeof params.date === "string" ? params.date : null;

  const supabase = await createClient();
  const claims = await supabase.auth.getClaims();

  const latest = await supabase
    .from("signals")
    .select("trade_date")
    .order("trade_date", { ascending: false })
    .limit(1)
    .maybeSingle();
  const day = chosenDate ?? latest.data?.trade_date ?? null;

  const dayResult = day
    ? await supabase
        .from("signals")
        .select(
          "id, trade_date, scanner, rule_version, evidence, companies(nse_symbol, name, sector)",
        )
        .eq("trade_date", day)
        .limit(1000)
    : null;

  const all = (dayResult?.data as SignalRow[] | null) ?? [];
  const counts = new Map<string, number>();
  for (const s of all) counts.set(s.scanner, (counts.get(s.scanner) ?? 0) + 1);

  const signals = chosenScanner ? all.filter((s) => s.scanner === chosenScanner) : all;
  const error = latest.error?.message ?? dayResult?.error?.message ?? null;

  const linkFor = (scanner: string | null) => {
    const search = new URLSearchParams();
    if (scanner) search.set("scanner", scanner);
    if (chosenDate) search.set("date", chosenDate);
    return `/scanner${search.size ? `?${search}` : ""}`;
  };

  return (
    <>
      <AppHeader email={String(claims.data?.claims.email ?? "")} current="/scanner" />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 px-4 py-6">
        <div>
          <h1 className="text-xl font-semibold">Scanner</h1>
          <p className="text-sm text-muted">
            {day
              ? `${all.length} signal${all.length === 1 ? "" : "s"} on ${dayMonth(day)}`
              : "No signals yet"}
          </p>
        </div>

        {error && (
          <p className="rounded-xl border border-negative/40 bg-negative-soft px-4 py-3 text-sm text-negative">
            {error}
          </p>
        )}

        {/* Filter by screen. Counts are for the whole day, not the current filter. */}
        <nav className="flex flex-wrap gap-2">
          <Link
            href={linkFor(null)}
            aria-current={!chosenScanner ? "page" : undefined}
            className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
              !chosenScanner
                ? "border-brand bg-brand text-on-brand"
                : "border-line text-muted hover:bg-surface-2"
            }`}
          >
            All {all.length}
          </Link>
          {SCANNER_ORDER.map((key) => {
            const active = chosenScanner === key;
            const colour = scannerColour(key);
            return (
              <Link
                key={key}
                href={linkFor(key)}
                aria-current={active ? "page" : undefined}
                className="rounded-full border px-3 py-1.5 text-sm transition-colors"
                style={
                  active
                    ? {
                        borderColor: `var(--${colour})`,
                        background: `var(--${colour}-soft)`,
                        color: `var(--${colour})`,
                      }
                    : { borderColor: "var(--border)" }
                }
              >
                <span className="inline-flex items-center gap-1.5">
                  <span
                    aria-hidden
                    className="size-1.5 rounded-full"
                    style={{ background: `var(--${colour})` }}
                  />
                  {scannerInfo(key).name}
                  <span className="tabular text-faint">{counts.get(key) ?? 0}</span>
                </span>
              </Link>
            );
          })}
        </nav>

        {signals.length === 0 ? (
          <EmptyState title="Nothing triggered here">
            These screens are deliberately narrow, so quiet days are normal. Try another screen, or
            a different date.
          </EmptyState>
        ) : (
          <ul className="grid gap-3 md:grid-cols-2">
            {signals.map((s) => {
              const info = scannerInfo(s.scanner);
              const colour = scannerColour(s.scanner);
              const company = s.companies;
              return (
                <li key={s.id}>
                  <Card className="h-full">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="flex items-baseline gap-2">
                          <span className="font-semibold">{company?.nse_symbol ?? "—"}</span>
                          <span className="truncate text-sm text-muted">{company?.name}</span>
                        </div>
                        {company?.sector && (
                          <p className="mt-0.5 text-xs text-faint">{company.sector}</p>
                        )}
                      </div>
                      <ScannerTag colour={colour}>{info.name}</ScannerTag>
                    </div>

                    <p className="mt-3 border-l-2 pl-3 text-sm" style={{ borderColor: `var(--${colour})` }}>
                      {headline(s.scanner, s.evidence)}
                    </p>

                    <details className="group mt-3">
                      <summary className="cursor-pointer list-none text-sm text-brand hover:underline">
                        Why it triggered
                        <span aria-hidden className="ml-1 inline-block group-open:rotate-90">
                          ›
                        </span>
                      </summary>
                      <p className="mt-2 text-sm text-muted">{info.what}</p>
                      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                        {info.explain(s.evidence).map((item) => (
                          <div key={item.label}>
                            <dt className="text-xs text-faint">{item.label}</dt>
                            <dd className="tabular">{item.value}</dd>
                          </div>
                        ))}
                      </dl>
                      <p className="mt-3 text-xs text-faint">
                        Rule <span className="font-mono">{s.rule_version}</span> ·{" "}
                        {dayMonth(s.trade_date)}
                      </p>
                    </details>
                  </Card>
                </li>
              );
            })}
          </ul>
        )}
      </main>
    </>
  );
}
