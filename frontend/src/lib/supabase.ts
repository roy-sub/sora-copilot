"use client";

/**
 * Supabase browser client.
 *
 * Auth lives in the browser; the access token travels to the backend as a Bearer header
 * (build spec §10). The client is created lazily so an unconfigured build still renders
 * — the sign-in screen explains what is missing instead of throwing on import.
 */

import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { authConfigured, env } from "@/lib/env";

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (!authConfigured) return null;
  client ??= createClient(env.supabaseUrl, env.supabaseAnonKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  });
  return client;
}

/** The current access token, or null when signed out. */
export async function accessToken(): Promise<string | null> {
  const sb = getSupabase();
  if (!sb) return null;
  const { data } = await sb.auth.getSession();
  return data.session?.access_token ?? null;
}
