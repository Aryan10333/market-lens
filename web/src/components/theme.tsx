"use client";

import { useSyncExternalStore } from "react";

type Choice = "light" | "dark" | "system";

/** Runs before the page is painted, so the correct theme is already applied.
 *  Kept as a string because it must run as an ordinary script, not React code. */
export const themeScript = `(function(){try{
  var c = localStorage.getItem('theme');
  var dark = c === 'dark' || (c !== 'light' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark', dark);
}catch(e){}})();`;

// The choice lives outside React (localStorage + the OS setting), so the component
// subscribes to it rather than keeping its own copy.
const listeners = new Set<() => void>();

function readChoice(): Choice {
  try {
    const stored = localStorage.getItem("theme");
    return stored === "light" || stored === "dark" ? stored : "system";
  } catch {
    return "system";
  }
}

function applyChoice(choice: Choice) {
  const dark =
    choice === "dark" ||
    (choice === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
}

function setChoice(choice: Choice) {
  try {
    if (choice === "system") localStorage.removeItem("theme");
    else localStorage.setItem("theme", choice);
  } catch {
    // Private browsing can block storage; the theme then lasts for this page only.
  }
  applyChoice(choice);
  listeners.forEach((notify) => notify());
}

function subscribe(notify: () => void) {
  listeners.add(notify);
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const onSystemChange = () => {
    if (readChoice() === "system") applyChoice("system"); // follow the device
    notify();
  };
  media.addEventListener("change", onSystemChange);
  window.addEventListener("storage", notify); // keep other tabs in step
  return () => {
    listeners.delete(notify);
    media.removeEventListener("change", onSystemChange);
    window.removeEventListener("storage", notify);
  };
}

const OPTIONS: { value: Choice; label: string; icon: string }[] = [
  { value: "light", label: "Light", icon: "☀" },
  { value: "dark", label: "Dark", icon: "☾" },
  { value: "system", label: "System", icon: "⌘" },
];

export function ThemeToggle() {
  const choice = useSyncExternalStore(subscribe, readChoice, () => "system" as Choice);

  return (
    <div
      role="group"
      aria-label="Colour theme"
      className="flex rounded-lg border border-line bg-surface p-0.5"
    >
      {OPTIONS.map((option) => {
        const active = choice === option.value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={active}
            title={option.label}
            onClick={() => setChoice(option.value)}
            className={`rounded-md px-2 py-1 text-xs transition-colors ${
              active ? "bg-brand-soft text-brand" : "text-faint hover:bg-surface-2 hover:text-muted"
            }`}
          >
            <span aria-hidden>{option.icon}</span>
            <span className="sr-only">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
