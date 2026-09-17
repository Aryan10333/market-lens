// Supabase client for server code: Server Components, Server Actions, Route Handlers.
// Create a new client for every request; never share one between requests.
import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { supabaseEnv } from "./env";

export async function createClient() {
  // Read cookies first: it marks the page as per-request, so it is never rendered at build time.
  const cookieStore = await cookies();
  const { url, key } = supabaseEnv();

  return createServerClient(url, key, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options),
          );
        } catch {
          // Server Components cannot set cookies. That is fine here because
          // proxy.ts refreshes the session cookies on every request.
        }
      },
    },
  });
}
