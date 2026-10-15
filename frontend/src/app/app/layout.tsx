import { AppShell } from "@/components/app/Shell";
import { AuthGate } from "@/components/app/AuthGate";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppShell>
      <AuthGate>{children}</AuthGate>
    </AppShell>
  );
}
