"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { Verdict } from "@/components/verdict/Verdict";

function FromQuery() {
  const id = useSearchParams().get("id") ?? "";
  return <Verdict id={id} />;
}

export function VerdictRoute({ id }: { id: string }) {
  if (id !== "view") return <Verdict id={id} />;
  return <Suspense><FromQuery /></Suspense>;
}
