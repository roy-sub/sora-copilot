import type { Metadata } from "next";
import { SignInForm } from "./SignInForm";
import { STAMP, Wordmark } from "@/components/Brand";

export const metadata: Metadata = { title: "Sign in" };

export default function SignIn() {
  return (
    <div className="grid gap-sheet min-h-screen grid-cols-[repeat(auto-fit,minmax(min(320px,100%),1fr))]">
      <div className="bg-sheet p-6 md:p-12 flex flex-col justify-between gap-10">
        <Wordmark />
        <div className="max-w-[40ch]">
          <h1 className="m-0 mb-4 font-display font-light text-[36px] leading-[1.08] tracking-[-.03em] text-ink-hi pretty">From mission to dossier in minutes.</h1>
          <p className="m-0 t-body leading-[1.6] text-ink-mid pretty">Every line cites its rule. Determinations are stamped with the rulebase version that produced them, so a result you defend today is the same result in six months.</p>
        </div>
        <span className="t-data-sm text-ink-low">{STAMP} · EU Frankfurt</span>
      </div>
      <div className="bg-sheet-raised p-6 md:p-12 flex flex-col justify-center gap-6">
        <SignInForm />
      </div>
    </div>
  );
}
