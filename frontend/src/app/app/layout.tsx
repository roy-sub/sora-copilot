import { AppShell } from "@/components/app/Shell";
import { AuthGate } from "@/components/app/AuthGate";
import { WorkspaceProvider } from "@/lib/workspace";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <AppShell>
        <AuthGate>{children}</AuthGate>
      </AppShell>
    </WorkspaceProvider>
  );
}
