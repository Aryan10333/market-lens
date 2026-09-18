import { ThemeToggle } from "@/components/theme";
import { login, signup } from "./actions";

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const params = await searchParams;
  const error = typeof params.error === "string" ? params.error : null;
  const message = typeof params.message === "string" ? params.message : null;

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <div className="flex justify-end p-4">
        <ThemeToggle />
      </div>

      <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-4 pb-16">
        <div className="text-center">
          <span
            aria-hidden
            className="mx-auto grid size-11 place-items-center rounded-xl bg-brand text-lg font-bold text-on-brand"
          >
            M
          </span>
          <h1 className="mt-3 text-2xl font-semibold">Market Lens</h1>
          <p className="mt-1 text-sm text-muted">
            Scanner and stock research for NSE and BSE, built on the TechnoFunda method.
          </p>
        </div>

        {error && (
          <p className="rounded-lg border border-negative/40 bg-negative-soft px-3 py-2 text-sm text-negative">
            {error}
          </p>
        )}
        {message && (
          <p className="rounded-lg border border-positive/40 bg-positive-soft px-3 py-2 text-sm text-positive">
            {message}
          </p>
        )}

        <form className="flex flex-col gap-3 rounded-xl border border-line bg-surface p-5 shadow-[var(--shadow)]">
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium">Email</span>
            <input
              name="email"
              type="email"
              required
              autoComplete="email"
              placeholder="you@example.com"
              className="rounded-lg border border-line bg-surface-2 px-3 py-2 placeholder:text-faint"
            />
          </label>
          <label className="flex flex-col gap-1.5 text-sm">
            <span className="font-medium">Password</span>
            <input
              name="password"
              type="password"
              required
              minLength={8}
              autoComplete="current-password"
              placeholder="At least 8 characters"
              className="rounded-lg border border-line bg-surface-2 px-3 py-2 placeholder:text-faint"
            />
          </label>

          <button
            formAction={login}
            className="mt-1 rounded-lg bg-brand px-3 py-2 font-medium text-on-brand transition-opacity hover:opacity-90"
          >
            Log in
          </button>
          <button
            formAction={signup}
            className="rounded-lg border border-line px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-2 hover:text-text"
          >
            Create an account
          </button>
        </form>

        <p className="text-center text-xs text-faint">
          New accounts need an email confirmation before the first login.
        </p>
      </main>
    </div>
  );
}
