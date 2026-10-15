/**
 * Public environment, read once and validated.
 *
 * Static export means these are inlined at build time, so a missing value is a build-time
 * fact rather than a runtime surprise. Nothing here is secret: the Supabase anon key is
 * designed to be public and is constrained by row-level security.
 */

export const env = {
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  apiUrl: (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, ""),
  mapStyleUrl: process.env.NEXT_PUBLIC_MAP_STYLE_URL ?? "",
} as const;

/** True when sign-in can actually work. The UI says so plainly rather than failing opaquely. */
export const authConfigured = Boolean(env.supabaseUrl && env.supabaseAnonKey);
