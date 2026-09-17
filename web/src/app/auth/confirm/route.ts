// GET /auth/confirm
// The link in the sign-up confirmation email points here. It verifies the
// one-time token, logs the user in, and sends them to the home page.
import type { EmailOtpType } from "@supabase/supabase-js";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const tokenHash = searchParams.get("token_hash");
  const type = searchParams.get("type") as EmailOtpType | null;
  const code = searchParams.get("code");
  const supabase = await createClient();

  // Link style 1 (recommended email template): ?token_hash=...&type=email
  if (tokenHash && type) {
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    if (!error) redirect("/");
  }

  // Link style 2 (default email template): ?code=... — works only in the same browser used to sign up.
  if (code) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) redirect("/");
  }

  redirect("/login?error=Confirmation%20link%20is%20invalid%20or%20expired");
}
