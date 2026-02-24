import { AppShell } from "@/components/shell/app-shell";

export default async function ShellLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lng: string }>;
}) {
  const { lng } = await params;
  return <AppShell lng={lng}>{children}</AppShell>;
}
