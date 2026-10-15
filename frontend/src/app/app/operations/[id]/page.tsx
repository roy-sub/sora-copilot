import { OPERATIONS } from "@/data/fixtures";
import { VerdictRoute } from "./VerdictRoute";

// "view" serves operations created on this device: /app/operations/view/?id=…
export const generateStaticParams = () => [...OPERATIONS.map((o) => ({ id: o.id })), { id: "view" }];
export const dynamicParams = false;

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <VerdictRoute id={id} />;
}
