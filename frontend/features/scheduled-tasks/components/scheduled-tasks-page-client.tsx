"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { useAppShell } from "@/components/shell/app-shell-context";
import { CreateScheduledTaskDialog } from "@/features/scheduled-tasks/components/create-scheduled-task-dialog";
import { ScheduledTaskEditDialog } from "@/features/scheduled-tasks/components/scheduled-task-edit-dialog";
import { ScheduledTasksHeader } from "@/features/scheduled-tasks/components/scheduled-tasks-header";
import { ScheduledTasksTable } from "@/features/scheduled-tasks/components/scheduled-tasks-table";
import { useScheduledTasksStore } from "@/features/scheduled-tasks/hooks/use-scheduled-tasks-store";
import type { ScheduledTask } from "@/features/scheduled-tasks/types";

export function ScheduledTasksPageClient() {
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null);
  const store = useScheduledTasksStore();
  const router = useRouter();
  const { lng } = useAppShell();

  const handleToggleEnabled = async (task: ScheduledTask) => {
    await store.updateTask(task.scheduled_task_id, {
      enabled: !task.enabled,
    });
  };

  return (
    <>
      <ScheduledTasksHeader onAddClick={() => setCreateOpen(true)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        <PullToRefresh onRefresh={store.refresh} isLoading={store.isLoading}>
          <div className="flex flex-1 flex-col px-6 py-6 overflow-auto">
            <div className="w-full">
              <ScheduledTasksTable
                tasks={store.tasks}
                savingId={store.savingId}
                onToggleEnabled={handleToggleEnabled}
                onOpen={(task) => {
                  router.push(
                    `/${lng}/capabilities/scheduled-tasks/${task.scheduled_task_id}`,
                  );
                }}
                onEdit={(task) => {
                  setEditingTask(task);
                  setEditOpen(true);
                }}
                onTrigger={async (task) => {
                  const resp = await store.triggerTask(task.scheduled_task_id);
                  if (resp?.session_id) {
                    router.push(`/${lng}/chat/${resp.session_id}`);
                  }
                }}
                onDelete={async (task) => {
                  await store.removeTask(task.scheduled_task_id);
                }}
              />
            </div>
          </div>
        </PullToRefresh>
      </div>

      <CreateScheduledTaskDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreate={async (input) => {
          const created = await store.createTask(input);
          if (created) {
            router.push(
              `/${lng}/capabilities/scheduled-tasks/${created.scheduled_task_id}`,
            );
          }
        }}
        isSaving={store.savingId === "create"}
      />

      <ScheduledTaskEditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        task={editingTask}
        isSaving={
          !!editingTask && store.savingId === editingTask.scheduled_task_id
        }
        onSave={async (payload) => {
          if (!editingTask) return;
          await store.updateTask(editingTask.scheduled_task_id, payload);
          await store.refresh();
        }}
      />
    </>
  );
}
