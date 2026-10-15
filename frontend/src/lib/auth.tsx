"use client";

/**
 * Session state, from Supabase Auth.
 *
 * Email + magic link is the primary path (brief §6); a password form is offered for
 * operators who prefer one. Static export means there is no server callback: the magic
 * link returns to `/app/` and `detectSessionInUrl` completes the exchange in the browser.
 */

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { Session, User } from "@supabase/supabase-js";
import { authConfigured } from "@/lib/env";
import { getSupabase } from "@/lib/supabase";

interface Auth {
  /** False until the initial session lookup has finished — do not redirect before this. */
  ready: boolean;
  session: Session | null;
  user: User | null;
  configured: boolean;
  sendMagicLink: (email: string) => Promise<void>;
  signInWithPassword: (email: string, password: string) => Promise<void>;
  signUpWithPassword: (email: string, password: string) => Promise<{ needsConfirmation: boolean }>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<Auth | null>(null);

/** Supabase error messages are terse; these read like the rest of the product. */
function readable(message: string): string {
  const m = message.toLowerCase();
  if (m.includes("invalid login credentials")) return "That email and password do not match an account.";
  if (m.includes("email not confirmed")) return "Confirm your email address first — check your inbox for the link.";
  if (m.includes("user already registered")) return "That email already has an account. Sign in instead.";
  if (m.includes("rate limit") || m.includes("too many")) return "Too many attempts. Wait a minute and try again.";
  if (m.includes("password should be")) return "Use at least 8 characters for the password.";
  return message;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(!authConfigured);

  useEffect(() => {
    const sb = getSupabase();
    if (!sb) return;
    let active = true;

    sb.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setReady(true);
    });

    const { data: sub } = sb.auth.onAuthStateChange((_event, next) => {
      setSession(next);
      setReady(true);
    });
    return () => {
      active = false;
      sub.subscription.unsubscribe();
    };
  }, []);

  const requireClient = useCallback(() => {
    const sb = getSupabase();
    if (!sb) {
      throw new Error(
        "Sign-in is not configured in this build. NEXT_PUBLIC_SUPABASE_URL and " +
          "NEXT_PUBLIC_SUPABASE_ANON_KEY are not set.",
      );
    }
    return sb;
  }, []);

  const sendMagicLink = useCallback(
    async (email: string) => {
      const { error } = await requireClient().auth.signInWithOtp({
        email,
        options: { emailRedirectTo: `${location.origin}/app/` },
      });
      if (error) throw new Error(readable(error.message));
    },
    [requireClient],
  );

  const signInWithPassword = useCallback(
    async (email: string, password: string) => {
      const { error } = await requireClient().auth.signInWithPassword({ email, password });
      if (error) throw new Error(readable(error.message));
    },
    [requireClient],
  );

  const signUpWithPassword = useCallback(
    async (email: string, password: string) => {
      const { data, error } = await requireClient().auth.signUp({
        email,
        password,
        options: { emailRedirectTo: `${location.origin}/app/` },
      });
      if (error) throw new Error(readable(error.message));
      return { needsConfirmation: !data.session };
    },
    [requireClient],
  );

  const signOut = useCallback(async () => {
    await getSupabase()?.auth.signOut();
    setSession(null);
  }, []);

  const value = useMemo<Auth>(
    () => ({
      ready,
      session,
      user: session?.user ?? null,
      configured: authConfigured,
      sendMagicLink,
      signInWithPassword,
      signUpWithPassword,
      signOut,
    }),
    [ready, session, sendMagicLink, signInWithPassword, signUpWithPassword, signOut],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): Auth {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}

/**
 * Sends a signed-out visitor to /signin once the session lookup has settled.
 *
 * Returns `ready` so a guarded screen can hold its layout rather than flashing. When
 * auth is not configured the guard stands down, so the skeleton stays clickable before
 * a Supabase project exists.
 */
export function useRequireAuth(): { ready: boolean; signedIn: boolean } {
  const { ready, session, configured } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (configured && ready && !session) {
      // Carry the destination so a visitor who followed a pricing link lands on the
      // plan panel rather than on a dashboard they did not ask for.
      const here = window.location.pathname + window.location.search;
      router.replace(`/signin/?next=${encodeURIComponent(here)}`);
    }
  }, [configured, ready, session, router]);

  return { ready, signedIn: !configured || Boolean(session) };
}
