import { ScheduledTaskDetailPageClient } from "@/features/scheduled-tasks";

export default async function ScheduledTaskDetailPage({
  params,
}: {
  params: Promise<{ lng: string; taskId: string }>;
}) {
  const { taskId } = await params;
  return <ScheduledTaskDetailPageClient taskId={taskId} />;
}
