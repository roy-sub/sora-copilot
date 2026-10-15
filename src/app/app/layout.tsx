import { AppShell } from "@/components/app/Shell";
import { WorkspaceProvider } from "@/lib/workspace";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <WorkspaceProvider>
      <AppShell>{children}</AppShell>
    </WorkspaceProvider>
  );
}
