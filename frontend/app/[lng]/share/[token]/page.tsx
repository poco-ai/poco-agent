import { AppShell } from "@/components/shell/app-shell";
import { getServerAuthState } from "@/features/auth/lib/server-session";
import { SessionSharePageClient } from "@/features/chat/components/share/session-share-page-client";

export default async function SharePage({
  params,
}: {
  params: Promise<{ lng: string; token: string }>;
}) {
  const { lng, token } = await params;
  const authState = await getServerAuthState();
  const content = (
    <SessionSharePageClient token={token} authStatus={authState.status} />
  );

  if (authState.status === "authenticated") {
    return <AppShell lng={lng}>{content}</AppShell>;
  }

  return content;
}
