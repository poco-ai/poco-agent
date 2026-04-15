import { TeamIssueDetailPageClient } from "@/features/issues";

export default async function TeamIssueDetailPage({
  params,
}: {
  params: Promise<{ issueId: string }>;
}) {
  const { issueId } = await params;
  return <TeamIssueDetailPageClient issueId={issueId} />;
}
