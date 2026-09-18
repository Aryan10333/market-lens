import Link from "next/link";
import { notFound } from "next/navigation";
import { AppHeader } from "@/components/AppHeader";
import { PriceChart, type Bar, type Overlay } from "@/components/PriceChart";
import { Badge, Card, EmptyState, ScannerTag, Stat } from "@/components/ui";
import { crore, dayMonth, money, percent, times } from "@/lib/format";
import { headline, scannerColour, scannerInfo, type Evidence } from "@/lib/scanners";
import { stageInfo, type StageEvidence } from "@/lib/stages";
import { createClient } from "@/lib/supabase/server";

const CHART_DAYS = 400; // about 18 months of trading days

// The select strings below are long, so the row shapes are written out here.
type FeatureRow = {
  trade_date: string;
  open_adj: number | null;
  high_adj: number | null;
  low_adj: number | null;
  close_adj: number | null;
  volume_avg_20: number | null;
  volume_ratio_20: number | null;
  value_avg_20: number | null;
  wma_30w: number | null;
  wma_30w_slope: number | null;
  sma_50: number | null;
  sma_200: number | null;
  high_52w: number | null;
  low_52w: number | null;
  pct_from_high_52w: number | null;
  pct_above_low_52w: number | null;
  rs_rank_63d: number | null;
  rs_change_63d: number | null;
  return_1d: number | null;
  return_21d: number | null;
  return_252d: number | null;
  volatility_21d: number | null;
  range_high_120: number | null;
  range_low_120: number | null;
  days_in_range: number | null;
};

type WeeklyRow = {
  week_end: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

// One company: price and volume, which Stage it is in and why, the numbers behind
// that, and every scanner signal it has produced.
export default async function StockPage({ params }: PageProps<"/stocks/[symbol]">) {
  const { symbol } = await params;
  const upper = decodeURIComponent(symbol).toUpperCase();
  const supabase = await createClient();

  const claims = await supabase.auth.getClaims();
  const company = await supabase
    .from("companies")
    .select("id, isin, name, nse_symbol, bse_code, sector, industry")
    .eq("nse_symbol", upper)
    .maybeSingle();

  if (!company.data) notFound();
  const companyId = company.data.id;

  const [features, weekly, stage, signals] = await Promise.all([
    supabase
      .from("daily_features")
      .select(
        "trade_date, open_adj, high_adj, low_adj, close_adj, volume_avg_20, volume_ratio_20, " +
          "value_avg_20, wma_30w, wma_30w_slope, sma_50, sma_200, high_52w, low_52w, " +
          "pct_from_high_52w, pct_above_low_52w, rs_rank_63d, rs_change_63d, return_1d, " +
          "return_21d, return_252d, volatility_21d, range_high_120, range_low_120, days_in_range",
      )
      .eq("company_id", companyId)
      .order("trade_date", { ascending: false })
      .limit(CHART_DAYS),
    supabase
      .from("weekly_prices")
      .select("week_end, open, high, low, close, volume")
      .eq("company_id", companyId)
      .order("week_start", { ascending: false })
      .limit(160),
    supabase
      .from("daily_stages")
      .select("trade_date, stage, stage_since, rule_version")
      .eq("company_id", companyId)
      .order("trade_date", { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase
      .from("signals")
      .select("id, trade_date, scanner, rule_version, evidence")
      .eq("company_id", companyId)
      .order("trade_date", { ascending: false })
      .limit(20),
  ]);

  const rows = ((features.data ?? []) as unknown as FeatureRow[]).slice().reverse(); // oldest first
  const latest = rows.at(-1);
  const num = (value: unknown) => (value === null || value === undefined ? null : Number(value));

  const dailyBars: Bar[] = rows
    .filter((r) => r.open_adj !== null)
    .map((r) => ({
      time: r.trade_date,
      open: Number(r.open_adj),
      high: Number(r.high_adj),
      low: Number(r.low_adj),
      close: Number(r.close_adj),
      volume: Number(r.volume_avg_20 ?? 0) * Number(r.volume_ratio_20 ?? 0),
    }));
  const dailyAverage: Overlay[] = rows.map((r) => ({
    time: r.trade_date,
    value: num(r.wma_30w),
  }));

  const weeklyRows = ((weekly.data ?? []) as unknown as WeeklyRow[]).slice().reverse();
  const weeklyBars: Bar[] = weeklyRows.map((w) => ({
    time: w.week_end,
    open: Number(w.open),
    high: Number(w.high),
    low: Number(w.low),
    close: Number(w.close),
    volume: Number(w.volume),
  }));
  // The 30-week average is a weekly value, so it maps straight onto the weekly bars.
  const byDate = new Map(rows.map((r) => [r.trade_date, num(r.wma_30w)]));
  const weeklyAverage: Overlay[] = weeklyRows.map((w) => ({
    time: w.week_end,
    value: byDate.get(w.week_end) ?? null,
  }));

  const stageData = stage.data;
  // The evidence is stored on the day the stage changed: that is when it was decided.
  const stageStart = stageData
    ? await supabase
        .from("daily_stages")
        .select("evidence")
        .eq("company_id", companyId)
        .eq("trade_date", stageData.stage_since)
        .maybeSingle()
    : null;
  const evidence = (stageStart?.data?.evidence ?? {}) as StageEvidence;
  const info = stageInfo(stageData?.stage);
  const dayMove = num(latest?.return_1d);

  return (
    <>
      <AppHeader email={String(claims.data?.claims.email ?? "")} current="/scanner" />
      <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 px-4 py-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-baseline gap-2">
              <h1 className="text-xl font-semibold">{company.data.nse_symbol}</h1>
              <span className="text-muted">{company.data.name}</span>
            </div>
            <p className="mt-1 flex flex-wrap items-center gap-2 text-xs text-faint">
              {company.data.sector && <Badge>{company.data.sector}</Badge>}
              <span>NSE {company.data.nse_symbol}</span>
              {company.data.bse_code && <span>· BSE {company.data.bse_code}</span>}
              <span>· {company.data.isin}</span>
            </p>
          </div>
          <Link href="/scanner" className="text-sm text-brand hover:underline">
            ← Back to scanner
          </Link>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat
            label={latest ? `Close · ${dayMonth(latest.trade_date)}` : "Close"}
            value={money(num(latest?.close_adj))}
            tone={dayMove === null ? "default" : dayMove >= 0 ? "positive" : "negative"}
            hint={dayMove === null ? undefined : `${dayMove >= 0 ? "▲" : "▼"} ${percent(Math.abs(dayMove))} on the day`}
          />
          <Stat
            label="52-week range"
            value={`${money(num(latest?.low_52w))} – ${money(num(latest?.high_52w))}`}
            hint={`${percent(num(latest?.pct_from_high_52w))} below the high`}
          />
          <Stat
            label="Strength vs market"
            value={latest?.rs_rank_63d ? `${Number(latest.rs_rank_63d).toFixed(0)} / 100` : "—"}
            hint={`3-month move vs Nifty 500: ${percent(num(latest?.rs_change_63d))}`}
          />
          <Stat
            label="Liquidity"
            value={crore(num(latest?.value_avg_20))}
            hint={`per day · volume ${times(num(latest?.volume_ratio_20))} average`}
          />
        </div>

        <Card title="Price and volume">
          {dailyBars.length === 0 ? (
            <EmptyState title="No price history yet" />
          ) : (
            <PriceChart
              daily={dailyBars}
              weekly={weeklyBars}
              averageDaily={dailyAverage}
              averageWeekly={weeklyAverage}
            />
          )}
        </Card>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Stage analysis">
            <div className="flex items-center gap-3">
              <ScannerTag colour={info.colour}>{info.name}</ScannerTag>
              {stageData && (
                <span className="text-xs text-faint">
                  since {dayMonth(stageData.stage_since)} · rule{" "}
                  <span className="font-mono">{stageData.rule_version}</span>
                </span>
              )}
            </div>
            <p className="mt-3 text-sm text-muted">{info.meaning}</p>
            {evidence.why && <p className="mt-2 text-sm">{evidence.why}</p>}

            <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              <div>
                <dt className="text-xs text-faint">Price vs 30-week average</dt>
                <dd className="capitalize">
                  {evidence.price_vs_30w ?? "—"}{" "}
                  <span className="tabular text-faint">({money(num(latest?.wma_30w))})</span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-faint">30-week average trend</dt>
                <dd className="capitalize">
                  {evidence["30w_trend"] ?? "—"}{" "}
                  <span className="tabular text-faint">
                    ({percent(num(latest?.wma_30w_slope))} over 10 weeks)
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-xs text-faint">Below its 52-week high</dt>
                <dd className="tabular">{percent(num(latest?.pct_from_high_52w))}</dd>
              </div>
              <div>
                <dt className="text-xs text-faint">Above its 52-week low</dt>
                <dd className="tabular">{percent(num(latest?.pct_above_low_52w))}</dd>
              </div>
              <div>
                <dt className="text-xs text-faint">Days inside its range</dt>
                <dd className="tabular">{latest?.days_in_range ?? "—"}</dd>
              </div>
              <div>
                <dt className="text-xs text-faint">Strength rank</dt>
                <dd className="tabular">
                  {latest?.rs_rank_63d ? `${Number(latest.rs_rank_63d).toFixed(0)} / 100` : "—"}
                </dd>
              </div>
            </dl>
            <p className="mt-4 border-t border-line pt-3 text-xs text-faint">
              Price being above an average is not Stage 2 on its own: the average must be rising,
              and the stock must be near its highs and not among the weakest. A change of stage
              only counts once it holds for {evidence.confirm_days ?? 5} trading days, so a share
              wobbling around its average does not flip stage every week.
            </p>
          </Card>

          <Card title="Technical numbers">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
              {[
                ["50-day average", money(num(latest?.sma_50))],
                ["200-day average", money(num(latest?.sma_200))],
                ["1-month move", percent(num(latest?.return_21d))],
                ["1-year move", percent(num(latest?.return_252d))],
                ["Volatility (yearly)", percent(num(latest?.volatility_21d), 0)],
                ["Average volume (20d)", (num(latest?.volume_avg_20) ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 })],
                ["120-day range high", money(num(latest?.range_high_120))],
                ["120-day range low", money(num(latest?.range_low_120))],
              ].map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs text-faint">{label}</dt>
                  <dd className="tabular">{value}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>

        <Card title="Signal history">
          {(signals.data ?? []).length === 0 ? (
            <EmptyState title="No scanner signals yet">
              This company has not triggered any of the five screens in the stored history.
            </EmptyState>
          ) : (
            <ul className="flex flex-col divide-y divide-line">
              {(signals.data ?? []).map((s) => (
                <li key={s.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 py-2.5">
                  <span className="tabular w-28 text-sm text-muted">{dayMonth(s.trade_date)}</span>
                  <ScannerTag colour={scannerColour(s.scanner)}>
                    {scannerInfo(s.scanner).name}
                  </ScannerTag>
                  <span className="text-sm text-muted">
                    {headline(s.scanner, s.evidence as Evidence)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </main>
    </>
  );
}
