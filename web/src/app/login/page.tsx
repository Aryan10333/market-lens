import { login, signup } from "./actions";

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const params = await searchParams;
  const error = typeof params.error === "string" ? params.error : null;
  const message = typeof params.message === "string" ? params.message : null;

  return (
    <main className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-4 py-12">
      <div>
        <h1 className="text-2xl font-semibold">Market Lens</h1>
        <p className="text-sm text-neutral-500">Log in or create an account.</p>
      </div>

      {error && <p className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-800">{error}</p>}
      {message && (
        <p className="rounded border border-green-300 bg-green-50 p-3 text-sm text-green-800">{message}</p>
      )}

      <form className="flex flex-col gap-3">
        <label className="flex flex-col gap-1 text-sm">
          Email
          <input name="email" type="email" required autoComplete="email" className="rounded border px-3 py-2" />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Password
          <input
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete="current-password"
            className="rounded border px-3 py-2"
          />
        </label>
        <div className="flex gap-2 pt-2">
          <button formAction={login} className="flex-1 rounded bg-neutral-900 px-3 py-2 text-white">
            Log in
          </button>
          <button formAction={signup} className="flex-1 rounded border px-3 py-2">
            Sign up
          </button>
        </div>
      </form>
    </main>
  );
}
