// How the four stages are shown. The rules themselves live in jobs/stages.py;
// this only describes them for the reader.

export type StageEvidence = {
  price_vs_30w?: string;
  "30w_trend"?: string;
  pct_from_high_52w?: number | null;
  pct_above_low_52w?: number | null;
  rs_rank_63d?: number | null;
  days_in_range?: number | null;
  why?: string;
  today_alone_suggests?: number;
  confirm_days?: number;
};

export const STAGES: Record<number, { name: string; meaning: string; colour: string }> = {
  1: {
    name: "Stage 1 · Basing",
    meaning: "Sideways after a fall, long-term average flat. Watch, do not buy.",
    colour: "scan-sector",
  },
  2: {
    name: "Stage 2 · Advancing",
    meaning: "Above a rising 30-week average with structure intact. The buy zone.",
    colour: "scan-breakout",
  },
  3: {
    name: "Stage 3 · Topping",
    meaning: "The advance has stalled and the average is flattening. Risk shifts to defence.",
    colour: "scan-surge",
  },
  4: {
    name: "Stage 4 · Declining",
    meaning: "Below a falling 30-week average, lower highs and lows. No reason to hold.",
    colour: "scan-volume",
  },
};

export function stageInfo(stage: number | null | undefined) {
  return stage && STAGES[stage]
    ? STAGES[stage]
    : { name: "Stage unknown", meaning: "Not enough history for a 30-week average yet.", colour: "scan-high" };
}
