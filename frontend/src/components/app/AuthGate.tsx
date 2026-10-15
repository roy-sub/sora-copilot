"use client";

import { useRequireAuth } from "@/lib/auth";

/**
 * Holds the authenticated area until the session lookup settles, then either renders it
 * or lets `useRequireAuth` redirect to sign-in.
 *
 * Static export has no server, so this is the only place the guard can live. It holds a
 * sheet rather than a spinner: the layout does not move when the content arrives, and
 * there is no "checking your session" copy to read and then lose.
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const { ready, signedIn } = useRequireAuth();

  if (!ready || !signedIn) {
    return <main className="flex-1 bg-sheet" aria-busy={!ready} />;
  }
  return <>{children}</>;
}
