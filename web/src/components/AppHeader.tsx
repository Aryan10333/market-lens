import Link from "next/link";
import { logout } from "@/app/login/actions";
import { ThemeToggle } from "./theme";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/scanner", label: "Scanner" },
];

export function AppHeader({ email, current }: { email?: string; current: string }) {
  return (
    <header className="sticky top-0 z-10 border-b border-line bg-surface/85 backdrop-blur">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5">
        <Link href="/" className="flex items-center gap-2">
          <span
            aria-hidden
            className="grid size-7 place-items-center rounded-md bg-brand text-sm font-bold text-on-brand"
          >
            M
          </span>
          <span className="font-semibold">Market Lens</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV.map((item) => {
            const active = item.href === current;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-lg px-2.5 py-1.5 text-sm transition-colors ${
                  active
                    ? "bg-brand-soft font-medium text-brand"
                    : "text-muted hover:bg-surface-2 hover:text-text"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          {email && (
            <span className="hidden text-xs text-faint sm:inline" title={email}>
              {email}
            </span>
          )}
          <form action={logout}>
            <button className="rounded-lg border border-line px-2.5 py-1.5 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-text">
              Log out
            </button>
          </form>
        </div>
      </div>
    </header>
  );
}
