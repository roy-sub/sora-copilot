import { Suspense } from "react";
import { PageHeader } from "@/components/app/Shell";
import { AuthorityRoute } from "./AuthorityRoute";

export const metadata = { title: "Authority" };

/**
 * The administrative half of an application, at `/app/authority/?op=…`.
 *
 * The determination is what SORA Copilot computes. This is what the operator still has
 * to do with it: which authority receives the file, in which order, and what travels
 * with it. It is kept on its own screen rather than bolted onto the verdict because the
 * two are answerable by different people on different days.
 */
export default function Page() {
  return (
    <>
      <PageHeader title="Authority" />
      <Suspense fallback={<main className="flex-1 bg-sheet" aria-busy />}>
        <AuthorityRoute />
      </Suspense>
    </>
  );
}
