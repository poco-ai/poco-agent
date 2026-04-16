import { WorkspaceProvider } from "@/features/workspaces";
import { TeamLibraryShell } from "@/features/workspaces/ui/team-library-shell";

export default function TeamLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <WorkspaceProvider>
      <TeamLibraryShell>{children}</TeamLibraryShell>
    </WorkspaceProvider>
  );
}
