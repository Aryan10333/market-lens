// Small building blocks shared by every page, so the app looks like one thing.

import type { ReactNode } from "react";

export function Card({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-xl border border-line bg-surface shadow-[var(--shadow)] ${className}`}
    >
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          {title && <h2 className="text-sm font-semibold tracking-wide">{title}</h2>}
          {action}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

/** One headline number with a label, and optional supporting line. */
export function Stat({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: "default" | "positive" | "negative" | "muted";
}) {
  const toneClass = {
    default: "text-text",
    positive: "text-positive",
    negative: "text-negative",
    muted: "text-muted",
  }[tone];
  return (
    <div className="rounded-lg border border-line bg-surface-2/60 px-3 py-2.5">
      <div className="text-xs text-faint">{label}</div>
      <div className={`tabular mt-0.5 text-lg font-semibold ${toneClass}`}>{value}</div>
      {hint && <div className="mt-0.5 text-xs text-faint">{hint}</div>}
    </div>
  );
}

export function Badge({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: "neutral" | "positive" | "negative" | "warning" | "brand";
  className?: string;
}) {
  const tones = {
    neutral: "bg-surface-2 text-muted",
    positive: "bg-positive-soft text-positive",
    negative: "bg-negative-soft text-negative",
    warning: "bg-warning-soft text-warning",
    brand: "bg-brand-soft text-brand",
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

/** A coloured dot + label, used for scanner names. */
export function ScannerTag({ colour, children }: { colour: string; children: ReactNode }) {
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium"
      style={{ background: `var(--${colour}-soft)`, color: `var(--${colour})` }}
    >
      <span
        aria-hidden
        className="size-1.5 rounded-full"
        style={{ background: `var(--${colour})` }}
      />
      {children}
    </span>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line-strong px-6 py-10 text-center">
      <p className="font-medium">{title}</p>
      {children && <p className="mx-auto mt-1 max-w-md text-sm text-muted">{children}</p>}
    </div>
  );
}

export function StatusDot({ status }: { status: string }) {
  const colour =
    status === "success"
      ? "bg-positive"
      : status === "failed"
        ? "bg-negative"
        : status === "running"
          ? "bg-warning"
          : "bg-faint";
  return <span aria-hidden className={`inline-block size-2 rounded-full ${colour}`} />;
}
