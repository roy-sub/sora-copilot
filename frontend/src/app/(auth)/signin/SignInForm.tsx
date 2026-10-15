"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { FieldLabel, Input } from "@/components/ui/Field";
import { useAuth } from "@/lib/auth";

type Mode = "signin" | "signup";

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Where to land after signing in.
 *
 * Only an in-app path is honoured. A `next` that names a host, or a protocol-relative
 * `//host`, is discarded: an open redirect on a sign-in form is how a credential page
 * ends up pointing somewhere else.
 */
function nextPath(raw: string | null): string {
  if (!raw || !raw.startsWith("/app/") || raw.startsWith("//")) return "/app/";
  return raw;
}

/**
 * Read it after mount rather than through `useSearchParams`.
 *
 * Under static export a component that reads the query string has to sit behind a
 * Suspense boundary, and the boundary's fallback is what the server renders — so the
 * server HTML and the first client render differ, which React reports as a hydration
 * mismatch and recovers from by re-rendering the subtree. Reading it in an effect makes
 * the two identical by construction, and the destination is only needed once a form has
 * been submitted.
 */
function useNextPath(): string {
  const [path, setPath] = useState("/app/");
  useEffect(() => {
    setPath(nextPath(new URLSearchParams(window.location.search).get("next")));
  }, []);
  return path;
}

function FieldError({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <span id={id} className="t-cap text-ink-mid">
      <span className="text-sail-6" aria-hidden>
        □{" "}
      </span>
      {children}
    </span>
  );
}

export function SignInForm() {
  const router = useRouter();
  const destination = useNextPath();
  const { ready, session, configured, sendMagicLink, signInWithPassword, signUpWithPassword } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<Mode>("signin");
  const [sent, setSent] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState<"magic" | "password" | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Already signed in — including the moment a magic link completes in this tab.
  useEffect(() => {
    if (ready && session) router.replace(destination);
  }, [ready, session, router, destination]);

  const magic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!EMAIL.test(email)) {
      setError("Enter a work email address, for example name@operator.at.");
      return;
    }
    setError(null);
    setBusy("magic");
    try {
      await sendMagicLink(email);
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The link could not be sent.");
    } finally {
      setBusy(null);
    }
  };

  const withPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!EMAIL.test(email)) {
      setError("Enter a work email address first.");
      return;
    }
    if (password.length < 8) {
      setError("Use at least 8 characters for the password.");
      return;
    }
    setError(null);
    setBusy("password");
    try {
      if (mode === "signup") {
        const { needsConfirmation } = await signUpWithPassword(email, password);
        if (needsConfirmation) {
          setConfirm(true);
          return;
        }
      } else {
        await signInWithPassword(email, password);
      }
      router.replace(destination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(null);
    }
  };

  if (!configured) {
    return (
      <div className="max-w-[380px] w-full flex flex-col gap-5">
        <h2 className="m-0 t-h2 text-ink-hi">Sign in</h2>
        <div role="status" className="flex flex-col gap-3 p-4 bg-sheet-well border-l-[3px] border-sail-3">
          <span className="t-micro text-sail-3">Not configured</span>
          <p className="m-0 t-body-sm text-ink-mid pretty">
            This build has no authentication keys, so there is nothing to sign in to yet.
            Set <code className="t-data-sm text-ink-hi">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
            <code className="t-data-sm text-ink-hi">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> — see{" "}
            <code className="t-data-sm text-ink-hi">.env.example</code>.
          </p>
        </div>
        <p className="m-0 t-body-sm text-ink-mid">
          The <Link href="/checker/">category checker</Link> needs no account at all.
        </p>
      </div>
    );
  }

  if (confirm) {
    return (
      <div className="max-w-[380px] w-full flex flex-col gap-5">
        <h2 className="m-0 t-h2 text-ink-hi">Confirm your email</h2>
        <div role="status" className="flex flex-col gap-3 p-4 bg-sheet-well border-l-[3px] border-accent">
          <span className="t-micro text-ink-low">Account created</span>
          <p className="m-0 t-body-sm text-ink-mid pretty">
            Open the confirmation link sent to{" "}
            <strong className="text-ink-hi font-semibold">{email}</strong>. It signs you in and
            creates your organisation.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-[380px] w-full flex flex-col gap-5">
      <h2 className="m-0 t-h2 text-ink-hi">{mode === "signup" ? "Create an account" : "Sign in"}</h2>

      {sent ? (
        <div role="status" className="flex flex-col gap-3 p-4 bg-sheet-well border-l-[3px] border-accent">
          <span className="t-micro text-ink-low">Magic link sent</span>
          <p className="m-0 t-body-sm text-ink-mid pretty">
            Check <strong className="text-ink-hi font-semibold">{email}</strong>. The link signs
            you in on this device and expires in 15 minutes.
          </p>
          <Button variant="ghost" onClick={() => setSent(false)}>
            Use a different address
          </Button>
        </div>
      ) : (
        <form onSubmit={magic} noValidate className="flex flex-col gap-5">
          <FieldLabel label="Work email">
            <Input
              type="email"
              autoComplete="email"
              placeholder="name@operator.at"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="min-h-12 px-3.5"
              aria-invalid={Boolean(error)}
              aria-describedby={error ? "signin-error" : undefined}
              style={error ? { borderColor: "var(--sail-6)" } : undefined}
            />
            {error && <FieldError id="signin-error">{error}</FieldError>}
          </FieldLabel>
          <Button type="submit" size="lg" disabled={busy !== null}>
            {busy === "magic" ? "Sending" : "Send magic link"}
          </Button>
        </form>
      )}

      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-hairline" />
        <span className="t-micro-10 text-ink-low">or</span>
        <div className="flex-1 h-px bg-hairline" />
      </div>

      <form onSubmit={withPassword} noValidate className="flex flex-col gap-5">
        <FieldLabel label="Password">
          <Input
            type="password"
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="min-h-12 px-3.5"
          />
        </FieldLabel>
        <Button type="submit" variant="secondary" size="lg" disabled={busy !== null}>
          {busy === "password" ? "Working" : mode === "signup" ? "Create account" : "Sign in"}
        </Button>
      </form>

      <p className="m-0 t-body-sm text-ink-mid">
        {mode === "signup" ? "Already have an account? " : "No account yet? "}
        <button
          type="button"
          className="underline bg-transparent border-0 p-0 text-ink-hi"
          onClick={() => {
            setMode(mode === "signup" ? "signin" : "signup");
            setError(null);
          }}
        >
          {mode === "signup" ? "Sign in" : "Create one"}
        </button>
        . The <Link href="/checker/">category checker</Link> needs no account at all.
      </p>
    </div>
  );
}
