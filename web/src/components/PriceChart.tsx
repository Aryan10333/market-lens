"use client";

import {
  CandlestickSeries,
  createChart,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type Time,
} from "lightweight-charts";
import { useEffect, useRef, useState } from "react";

export type Bar = {
  time: string; // YYYY-MM-DD
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type Overlay = { time: string; value: number | null };

/** Reads the current theme colours from CSS, so the chart matches the page. */
function colours() {
  const style = getComputedStyle(document.documentElement);
  const get = (name: string) => style.getPropertyValue(name).trim();
  return {
    text: get("--text-muted"),
    grid: get("--border"),
    up: get("--positive"),
    down: get("--negative"),
    average: get("--brand"),
    volume: get("--border-strong"),
  };
}

export function PriceChart({
  daily,
  weekly,
  averageDaily,
  averageWeekly,
  averageLabel = "30-week average",
}: {
  daily: Bar[];
  weekly: Bar[];
  averageDaily: Overlay[];
  averageWeekly: Overlay[];
  averageLabel?: string;
}) {
  const [view, setView] = useState<"daily" | "weekly">("daily");
  const holder = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const element = holder.current;
    if (!element) return;

    const bars = view === "daily" ? daily : weekly;
    const overlay = view === "daily" ? averageDaily : averageWeekly;
    const c = colours();

    const chart = createChart(element, {
      height: 360,
      layout: {
        background: { color: "transparent" },
        textColor: c.text,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: c.grid },
        horzLines: { color: c.grid },
      },
      rightPriceScale: { borderColor: c.grid, scaleMargins: { top: 0.08, bottom: 0.28 } },
      timeScale: { borderColor: c.grid, rightOffset: 4 },
      crosshair: { mode: 1 },
    });
    chartRef.current = chart;

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: c.up,
      downColor: c.down,
      borderUpColor: c.up,
      borderDownColor: c.down,
      wickUpColor: c.up,
      wickDownColor: c.down,
    });
    candles.setData(
      bars.map((b) => ({
        time: b.time as Time,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      })),
    );

    const average = chart.addSeries(LineSeries, {
      color: c.average,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      title: averageLabel,
    });
    average.setData(
      overlay
        .filter((p) => p.value !== null)
        .map((p) => ({ time: p.time as Time, value: p.value as number })),
    );

    const volume = chart.addSeries(HistogramSeries, {
      color: c.volume,
      priceScaleId: "volume",
      priceFormat: { type: "volume" },
      lastValueVisible: false,
    });
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    volume.setData(
      bars.map((b) => ({
        time: b.time as Time,
        value: b.volume,
        color: b.close >= b.open ? `${c.up}66` : `${c.down}66`,
      })),
    );

    chart.timeScale().fitContent();

    const onResize = () => chart.applyOptions({ width: element.clientWidth });
    onResize();
    window.addEventListener("resize", onResize);

    // Redraw with new colours when the theme changes.
    const themeWatcher = new MutationObserver(() => {
      const next = colours();
      chart.applyOptions({
        layout: { textColor: next.text },
        grid: { vertLines: { color: next.grid }, horzLines: { color: next.grid } },
        rightPriceScale: { borderColor: next.grid },
        timeScale: { borderColor: next.grid },
      });
      candles.applyOptions({
        upColor: next.up,
        downColor: next.down,
        borderUpColor: next.up,
        borderDownColor: next.down,
        wickUpColor: next.up,
        wickDownColor: next.down,
      });
      average.applyOptions({ color: next.average });
    });
    themeWatcher.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["class"],
    });

    return () => {
      window.removeEventListener("resize", onResize);
      themeWatcher.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [view, daily, weekly, averageDaily, averageWeekly, averageLabel]);

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex rounded-lg border border-line p-0.5">
          {(["daily", "weekly"] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={view === option}
              onClick={() => setView(option)}
              className={`rounded-md px-2.5 py-1 text-xs capitalize transition-colors ${
                view === option
                  ? "bg-brand-soft text-brand"
                  : "text-faint hover:bg-surface-2 hover:text-muted"
              }`}
            >
              {option}
            </button>
          ))}
        </div>
        <p className="text-xs text-faint">
          Split-adjusted prices · blue line: {averageLabel}
        </p>
      </div>
      <div ref={holder} className="w-full" />
    </div>
  );
}
