"use client";

import {
  Clock3,
  Container,
  FolderKanban,
  FolderRoot,
  MemoryStick,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PersistentRuntimeBadge } from "@/components/shared/persistent-runtime-badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getAgentRuntimeStatus } from "@/features/servers/lib/agent-runtime-status";
import type { ServerAgentItem } from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";

function formatDateTime(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function ServerAgentDetailDialog({
  open,
  onOpenChange,
  agent,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent: ServerAgentItem | null;
}) {
  const { t } = useT("translation");
  if (!agent) {
    return null;
  }
  const runtimeStatus = getAgentRuntimeStatus(agent);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{agent.displayName}</DialogTitle>
          <DialogDescription>
            @{agent.handle} ·{" "}
            {t("servers.agents.preset", { id: agent.presetId })}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <section className="space-y-4 rounded-3xl border border-border/70 bg-card p-5">
            <div className="space-y-1.5">
              <p className="text-sm font-semibold text-foreground">
                {t("servers.agents.profileTitle")}
              </p>
              <p className="text-sm text-muted-foreground">
                {agent.description || t("servers.agents.emptyDescription")}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary">{agent.lifecycleState}</Badge>
              <Badge variant="outline">{agent.visibility}</Badge>
              <PersistentRuntimeBadge
                status={runtimeStatus}
                label={t(runtimeStatus.labelKey)}
                pinnedLabel={t("runtime.labels.pinned")}
              />
              <Badge variant="outline">
                {t("servers.agents.preset", { id: agent.presetId })}
              </Badge>
            </div>

            <div className="grid gap-3">
              <div className="rounded-2xl border border-border/60 bg-background/80 p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Container className="size-3.5" />
                  <span>{t("servers.agents.runtimeStatus")}</span>
                </div>
                <p className="mt-2 text-sm font-semibold text-foreground">
                  {t(runtimeStatus.labelKey)}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {runtimeStatus.rawRuntimeStatus ??
                    t("servers.agents.unknown")}
                </p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-background/80 p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Clock3 className="size-3.5" />
                  <span>{t("servers.agents.lastSynced")}</span>
                </div>
                <p className="mt-2 text-sm text-foreground">
                  {formatDateTime(agent.persistentState?.lastSyncedAt) ??
                    t("servers.agents.emptyValue")}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => toast.info(t("servers.agents.tempRuntimeHint"))}
              >
                <Sparkles className="size-4" />
                {t("servers.agents.tempRuntime")}
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => toast.info(t("servers.agents.promoteHint"))}
              >
                <FolderKanban className="size-4" />
                {t("servers.agents.promote")}
              </Button>
            </div>
          </section>

          <section className="space-y-4 rounded-3xl border border-border/70 bg-card p-5">
            <div className="space-y-1.5">
              <p className="text-sm font-semibold text-foreground">
                {t("servers.agents.stateSummaryTitle")}
              </p>
              <p className="text-sm text-muted-foreground">
                {t("servers.agents.stateSummaryDescription")}
              </p>
            </div>

            <div className="space-y-3 text-sm">
              <div className="rounded-2xl border border-border/60 bg-background/80 p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <FolderRoot className="size-3.5" />
                  <span>{t("servers.agents.stateRoot")}</span>
                </div>
                <p className="mt-2 break-all text-foreground">
                  {agent.persistentState?.stateRootPath ??
                    t("servers.agents.emptyValue")}
                </p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-background/80 p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <MemoryStick className="size-3.5" />
                  <span>{t("servers.agents.memoryFile")}</span>
                </div>
                <p className="mt-2 break-all text-foreground">
                  {agent.persistentState?.memoryPath ??
                    t("servers.agents.emptyValue")}
                </p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-background/80 p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <FolderKanban className="size-3.5" />
                  <span>{t("servers.agents.activeTask")}</span>
                </div>
                <p className="mt-2 break-all text-foreground">
                  {agent.persistentState?.activeTaskId ??
                    t("servers.agents.emptyValue")}
                </p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-background/80 p-4">
                <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Container className="size-3.5" />
                  <span>{t("servers.agents.activeSession")}</span>
                </div>
                <p className="mt-2 break-all text-foreground">
                  {agent.persistentState?.activeSessionId ??
                    t("servers.agents.emptyValue")}
                </p>
              </div>
            </div>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}
