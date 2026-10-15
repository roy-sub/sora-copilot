import { Suspense } from "react";
import { PageHeader } from "@/components/app/Shell";
import { NewOperationRoute } from "./NewOperationRoute";

export const metadata = { title: "New operation" };

/**
 * The intake wizard.
 *
 * Static export cannot have a dynamic segment here, so the operation id travels as a
 * search param and is read inside a Suspense boundary — the same pattern the verdict
 * route uses for operations created on this device.
 */
export default function NewOperationPage() {
  return (
    <>
      <PageHeader title="New operation" />
      <Suspense fallback={<main className="flex-1 bg-sheet" aria-busy />}>
        <NewOperationRoute />
      </Suspense>
    </>
  );
}
