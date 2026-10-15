import { Suspense } from "react";
import { PageHeader } from "@/components/app/Shell";
import { DossiersRoute } from "./DossiersRoute";

export const metadata = { title: "Dossiers" };

export default function Page() {
  return (
    <>
      <PageHeader title="Dossiers" />
      <Suspense fallback={<main className="flex-1 bg-sheet" aria-busy />}>
        <DossiersRoute />
      </Suspense>
    </>
  );
}
