// How each scanner is described in the app, and how its evidence is shown.
// The wording comes from the TechnoFunda methodology: these are the price-volume
// screens that start the funnel.

import { crore, money, percent, times } from "./format";

export type Evidence = Record<string, string | number | null>;

export type ScannerInfo = {
  name: string;
  what: string;
  /** Turns stored evidence into "why it triggered", in plain words. */
  explain: (e: Evidence) => { label: string; value: string }[];
};

const n = (e: Evidence, key: string): number | null => {
  const value = e[key];
  return typeof value === "number" ? value : null;
};

export const SCANNERS: Record<string, ScannerInfo> = {
  consolidation_breakout: {
    name: "Consolidation breakout",
    what: "Price left a long sideways range on heavy volume",
    explain: (e) => [
      { label: "Broke above", value: money(n(e, "breakout_level")) },
      { label: "Close", value: money(n(e, "close")) },
      { label: "Above level by", value: percent(n(e, "above_level_pct")) },
      { label: "Days in range", value: `${n(e, "days_in_range") ?? "—"}` },
      { label: "Range width", value: percent(n(e, "range_width")) },
      { label: "Volume", value: `${times(n(e, "volume_ratio_20"))} the 20-day average` },
    ],
  },
  new_high_breakout: {
    name: "New high breakout",
    what: "Price reached a 52-week high while the long-term trend is rising",
    explain: (e) => [
      { label: "Close", value: money(n(e, "close")) },
      { label: "52-week high", value: money(n(e, "high_52w")) },
      { label: "Below the high", value: percent(n(e, "pct_from_high_52w"), 2) },
      { label: "Volume", value: `${times(n(e, "volume_ratio_20"))} the 20-day average` },
      { label: "30-week average", value: money(n(e, "wma_30w")) },
      { label: "30-week trend", value: `${percent(n(e, "wma_30w_slope"))} over 10 weeks` },
    ],
  },
  volume_expansion: {
    name: "Volume expansion",
    what: "Volume far above its own average, with price not falling",
    explain: (e) => [
      { label: "Close", value: money(n(e, "close")) },
      { label: "Volume", value: `${times(n(e, "volume_ratio_20"))} the 20-day average` },
      {
        label: "20-day average volume",
        value: (n(e, "volume_avg_20") ?? 0).toLocaleString("en-IN", { maximumFractionDigits: 0 }),
      },
      { label: "Day's move", value: percent(n(e, "return_1d")) },
      { label: "Below 52-week high", value: percent(n(e, "pct_from_high_52w")) },
    ],
  },
  price_volume_surge: {
    name: "Price + volume surge",
    what: "An unusual price move on unusual volume — the methodology's first-level screen",
    explain: (e) => [
      { label: "Close", value: money(n(e, "close")) },
      { label: "Day's move", value: percent(n(e, "return_1d")) },
      { label: "Volume", value: `${times(n(e, "volume_ratio_20"))} the 20-day average` },
      { label: "Below 52-week high", value: percent(n(e, "pct_from_high_52w")) },
    ],
  },
  sector_trend: {
    name: "Sector trend",
    what: "A rising stock inside a sector that is beating the market",
    explain: (e) => [
      { label: "Close", value: money(n(e, "close")) },
      { label: "Sector index", value: `${e.sector_index ?? "—"}` },
      { label: "Sector, 1 month", value: percent(n(e, "sector_return_21d")) },
      { label: "Sector vs market", value: percent(n(e, "sector_relative_21d")) },
      { label: "Sector rank", value: `${(n(e, "sector_rank") ?? 0).toFixed(0)} / 100` },
      { label: "Stock strength rank", value: `${(n(e, "rs_rank_63d") ?? 0).toFixed(0)} / 100` },
    ],
  },
};

/** Accent colour token for each scanner (defined in globals.css). */
const COLOURS: Record<string, string> = {
  price_volume_surge: "scan-surge",
  volume_expansion: "scan-volume",
  consolidation_breakout: "scan-breakout",
  new_high_breakout: "scan-high",
  sector_trend: "scan-sector",
};

export function scannerColour(key: string): string {
  return COLOURS[key] ?? "scan-high";
}

/** The order the methodology applies them: price-volume first, then structure. */
export const SCANNER_ORDER = [
  "price_volume_surge",
  "volume_expansion",
  "consolidation_breakout",
  "new_high_breakout",
  "sector_trend",
];

export function scannerInfo(key: string): ScannerInfo {
  return (
    SCANNERS[key] ?? {
      name: key,
      what: "",
      explain: (e) =>
        Object.entries(e)
          .filter(([k]) => k !== "symbol")
          .map(([k, v]) => ({ label: k, value: String(v) })),
    }
  );
}

/** A short one-line summary for the results table. */
export function headline(key: string, e: Evidence): string {
  switch (key) {
    case "consolidation_breakout":
      return `Broke ${money(n(e, "breakout_level"))} after ${n(e, "days_in_range")} days in range, ${times(n(e, "volume_ratio_20"))} volume`;
    case "new_high_breakout":
      return `At its 52-week high of ${money(n(e, "high_52w"))}, ${times(n(e, "volume_ratio_20"))} volume`;
    case "volume_expansion":
      return `${times(n(e, "volume_ratio_20"))} its average volume, price ${percent(n(e, "return_1d"))}`;
    case "price_volume_surge":
      return `Up ${percent(n(e, "return_1d"))} on ${times(n(e, "volume_ratio_20"))} volume`;
    case "sector_trend":
      return `${e.sector_index ?? "Sector"} beating the market by ${percent(n(e, "sector_relative_21d"))}`;
    default:
      return "";
  }
}

export { crore };
