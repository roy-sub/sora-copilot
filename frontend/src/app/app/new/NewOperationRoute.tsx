"use client";

import { useSearchParams } from "next/navigation";
import { Wizard } from "@/components/wizard/Wizard";

export function NewOperationRoute() {
  const id = useSearchParams().get("id");
  return <Wizard operationId={id} />;
}
