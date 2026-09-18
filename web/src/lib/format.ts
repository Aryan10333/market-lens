// Small helpers for showing Indian market numbers.

export function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 2 })}`;
}

export function percent(fraction: number | null | undefined, digits = 1): string {
  if (fraction === null || fraction === undefined) return "—";
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function times(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}×`;
}

/** Rupees in crore, the unit Indian market data is usually quoted in. */
export function crore(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `₹${(value / 10_000_000).toLocaleString("en-IN", { maximumFractionDigits: 1 })} cr`;
}

export function dayMonth(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00`).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
