import { SessionSharePageClient } from "@/features/chat/components/share/session-share-page-client";

export default async function SharePage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  return <SessionSharePageClient token={token} />;
}
