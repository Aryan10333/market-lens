import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { dayMonth } from "@/lib/format";
import { headline, scannerInfo, type Evidence } from "@/lib/scanners";

type SignalRow = {
  id: number;
  trade_date: string;
  scanner: string;
  rule_version: string;
  evidence: Evidence;
  companies: { nse_symbol: string | null; name: string; sector: string | null } | null;
};

// Scanner results for one trading day. Every row shows why it triggered.
export default async function ScannerPage({ searchParams }: PageProps<"/scanner">) {
  const params = await searchParams;
  const chosenScanner = typeof params.scanner === "string" ? params.scanner : null;
  const chosenDate = typeof params.date === "string" ? params.date : null;

  const supabase = await createClient();

  const latest = await supabase
    .from("signals")
    .select("trade_date")
    .order("trade_date", { ascending: false })
    .limit(1)
    .maybeSingle();
  const day = chosenDate ?? latest.data?.trade_date ?? null;

  let signals: SignalRow[] = [];
  let error: string | null = latest.error?.message ?? null;

  if (day) {
    let query = supabase
      .from("signals")
      .select("id, trade_date, scanner, rule_version, evidence, companies(nse_symbol, name, sector)")
      .eq("trade_date", day)
      .order("scanner")
      .limit(500);
    if (chosenScanner) query = query.eq("scanner", chosenScanner);
    const result = await query;
    signals = (result.data as SignalRow[] | null) ?? [];
    error = error ?? result.error?.message ?? null;
  }

  const counts = new Map<string, number>();
  for (const s of signals) counts.set(s.scanner, (counts.get(s.scanner) ?? 0) + 1);

  const tab = (key: string | null, label: string) => {
    const search = new URLSearchParams();
    if (key) search.set("scanner", key);
    if (chosenDate) search.set("date", chosenDate);
    const active = chosenScanner === key;
    return (
      <Link
        key={key ?? "all"}
        href={`/scanner${search.size ? `?${search}` : ""}`}
        className={`rounded border px-3 py-1.5 text-sm ${
          active ? "border-neutral-900 bg-neutral-900 text-white" : "hover:bg-neutral-50"
        }`}
      >
        {label}
      </Link>
    );
  };

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-5 px-4 py-8">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Scanner</h1>
          <p className="text-sm text-neutral-500">
            {day ? `Signals for ${dayMonth(day)}` : "No signals yet"}
          </p>
        </div>
        <Link href="/" className="text-sm underline">
          Home
        </Link>
      </header>

      {error && (
        <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</p>
      )}

      <nav className="flex flex-wrap gap-2">
        {tab(null, `All (${signals.length})`)}
        {Object.keys(scannerTabs).map((key) =>
          tab(key, `${scannerInfo(key).name}${chosenScanner ? "" : ` (${counts.get(key) ?? 0})`}`),
        )}
      </nav>

      {signals.length === 0 ? (
        <p className="rounded border p-4 text-sm text-neutral-600">
          Nothing triggered here. That is a normal result: these screens are meant to be narrow.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {signals.map((s) => {
            const info = scannerInfo(s.scanner);
            const company = s.companies;
            return (
              <li key={s.id} className="rounded border p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <div>
                    <span className="font-medium">{company?.nse_symbol ?? "—"}</span>
                    <span className="ml-2 text-sm text-neutral-600">{company?.name}</span>
                  </div>
                  <span className="rounded bg-neutral-100 px-2 py-0.5 text-xs">{info.name}</span>
                </div>

                <p className="mt-1 text-sm text-neutral-700">{headline(s.scanner, s.evidence)}</p>

                <details className="mt-2">
                  <summary className="cursor-pointer text-sm text-neutral-500">
                    Why it triggered
                  </summary>
                  <p className="mt-2 text-sm text-neutral-600">{info.what}</p>
                  <dl className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
                    {info.explain(s.evidence).map((item) => (
                      <div key={item.label}>
                        <dt className="text-neutral-500">{item.label}</dt>
                        <dd>{item.value}</dd>
                      </div>
                    ))}
                  </dl>
                  <p className="mt-2 text-xs text-neutral-400">
                    {company?.sector ? `${company.sector} · ` : ""}rule {s.rule_version}
                  </p>
                </details>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}

// Listed in the order the methodology applies them: price-volume first, then structure.
const scannerTabs = {
  price_volume_surge: true,
  volume_expansion: true,
  consolidation_breakout: true,
  new_high_breakout: true,
  sector_trend: true,
};
