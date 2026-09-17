// GET /api/health
// Public check that the web app is running and can reach the database.
// Returns 200 when everything is fine, 503 when the database cannot be reached.
import { createClient } from "@supabase/supabase-js";
import { connection } from "next/server";
import { supabaseEnv } from "@/lib/supabase/env";

export async function GET() {
  await connection(); // always run at request time, never a cached build-time result
  const checkedAt = new Date().toISOString();

  try {
    const { url, key } = supabaseEnv();
    const supabase = createClient(url, key, { auth: { persistSession: false } });
    const { data, error } = await supabase.rpc("health");
    if (error) throw new Error(error.message);

    return Response.json({ status: "ok", app: "ok", database: data?.database ?? "ok", checkedAt });
  } catch (err) {
    const message = err instanceof Error ? err.message : "unknown error";
    return Response.json(
      { status: "error", app: "ok", database: "error", message, checkedAt },
      { status: 503 },
    );
  }
}
