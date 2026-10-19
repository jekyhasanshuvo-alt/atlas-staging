import { AppShell } from "@/components/layout/app-shell";
import { WorkspaceGuard } from "@/components/auth/student-provider";
export default function StudentLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AppShell>
      <WorkspaceGuard>{children}</WorkspaceGuard>
    </AppShell>
  );
}
