"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { FieldLabel, Input } from "@/components/ui/Field";

export function SignInForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const magic = (e: React.FormEvent) => {
    e.preventDefault();
    if (!valid) { setError("Enter a work email address, for example name@operator.at."); return; }
    setError(null);
    setSent(true);
  };

  return (
    <div className="max-w-[380px] w-full flex flex-col gap-5">
      <h2 className="m-0 t-h2 text-ink-hi">Sign in</h2>
      {sent ? (
        <div role="status" className="flex flex-col gap-3 p-4 bg-sheet-well border-l-[3px] border-accent">
          <span className="t-micro text-ink-low">Magic link sent</span>
          <p className="m-0 t-body-sm text-ink-mid pretty">Check <strong className="text-ink-hi font-semibold">{email}</strong>. The link signs you in on this device and expires in 15 minutes.</p>
          <Button variant="secondary" onClick={() => router.push("/app")}>Continue to the demo workspace</Button>
        </div>
      ) : (
        <form onSubmit={magic} noValidate className="flex flex-col gap-5">
          <FieldLabel label="Work email">
            <Input
              type="email" autoComplete="email" placeholder="name@operator.at" value={email}
              onChange={(e) => setEmail(e.target.value)} className="min-h-12 px-3.5"
              aria-invalid={!!error} aria-describedby={error ? "email-error" : undefined}
              style={error ? { borderColor: "var(--sail-6)" } : undefined}
            />
            {error && <span id="email-error" className="t-cap text-ink-mid"><span className="text-sail-6" aria-hidden>□ </span>{error}</span>}
          </FieldLabel>
          <Button type="submit" size="lg">Send magic link</Button>
        </form>
      )}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-px bg-hairline" /><span className="t-micro-10 text-ink-low">or</span><div className="flex-1 h-px bg-hairline" />
      </div>
      <form onSubmit={(e) => { e.preventDefault(); router.push("/app"); }} className="flex flex-col gap-5">
        <FieldLabel label="Password">
          <Input type="password" autoComplete="current-password" className="min-h-12 px-3.5" />
        </FieldLabel>
        <Button type="submit" variant="secondary" size="lg">Sign in</Button>
      </form>
      <p className="m-0 t-body-sm text-ink-mid">No account yet? <Link href="/signin">Create one</Link>. The category checker needs no account at all.</p>
    </div>
  );
}
