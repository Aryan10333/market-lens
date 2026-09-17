import { createClient } from "@/lib/supabase/server";
import { logout } from "./login/actions";

// Home page (logged-in users only; proxy.ts redirects everyone else to /login).
// For now it shows who is logged in and whether the database tables are reachable.
export default async function Home() {
  const supabase = await createClient();
  const { data: claims } = await supabase.auth.getClaims();
  const { count, error } = await supabase
    .from("companies")
    .select("*", { count: "exact", head: true });

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-10">
      <header className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold">Market Lens</h1>
        <form action={logout}>
          <button className="rounded border px-3 py-1.5 text-sm">Log out</button>
        </form>
      </header>

      <p className="text-sm text-neutral-500">Logged in as {String(claims?.claims.email ?? "unknown")}</p>

      <section className="rounded border p-4">
        <h2 className="mb-2 font-medium">Foundation status</h2>
        <ul className="space-y-1 text-sm">
          <li>Web app: running</li>
          <li>Login: working</li>
          <li>
            Companies table:{" "}
            {error ? `error — ${error.message}` : `${count ?? 0} companies loaded (data arrives in Step 1)`}
          </li>
        </ul>
      </section>
    </main>
  );
}
