import { Suspense } from "react";
import { PageHeader } from "@/components/app/Shell";
import { VerdictRoute } from "./VerdictRoute";

export const metadata = { title: "Determination" };

/**
 * The verdict screen, at `/app/operations/view/?id=…`.
 *
 * Operations now live on the server with real ids, so there is nothing to pre-generate:
 * a static export cannot know them. One static page reading a search param inside a
 * Suspense boundary is the whole route, and it works for every operation rather than
 * only the ones that existed at build time.
 */
export default function Page() {
  return (
    <>
      <PageHeader title="Determination" />
      <Suspense fallback={<main className="flex-1 bg-sheet" aria-busy />}>
        <VerdictRoute />
      </Suspense>
    </>
  );
}
