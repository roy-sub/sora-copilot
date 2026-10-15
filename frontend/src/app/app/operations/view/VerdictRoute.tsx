"use client";

import { useSearchParams } from "next/navigation";
import { ButtonLink } from "@/components/ui/Button";
import { Verdict } from "@/components/verdict/Verdict";

export function VerdictRoute() {
  const id = useSearchParams().get("id");
  if (!id) {
    return (
      <main className="flex-1 bg-sheet p-6 flex flex-col gap-4 items-start">
        <h2 className="m-0 t-h2 text-ink-hi">No operation selected</h2>
        <p className="m-0 t-body-sm text-ink-mid max-w-[52ch] pretty">
          Open a determination from the operations list.
        </p>
        <ButtonLink href="/app/">Go to operations</ButtonLink>
      </main>
    );
  }
  return <Verdict operationId={id} />;
}
