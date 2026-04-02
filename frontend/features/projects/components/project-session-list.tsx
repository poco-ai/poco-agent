"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowUpRight, Clock3, MessageSquareText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { TASK_STATUS_META } from "@/features/projects/constants/task-status";
import type { TaskHistoryItem } from "@/features/projects/types";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface ProjectSessionListProps {
  tasks: TaskHistoryItem[];
}

function formatTimestamp(timestamp: string, locale: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function ProjectSessionList({ tasks }: ProjectSessionListProps) {
  const { t } = useT("translation");
  const router = useRouter();
  const params = useParams();
  const lng = useLanguage() || "en";
  const activeTaskId =
    typeof params?.id === "string" ? (params.id as string) : undefined;

  const orderedTasks = React.useMemo(
    () =>
      [...tasks].sort(
        (left, right) =>
          new Date(right.timestamp).getTime() -
          new Date(left.timestamp).getTime(),
      ),
    [tasks],
  );

  if (orderedTasks.length === 0) {
    return (
      <section className="rounded-3xl border border-dashed border-border/70 bg-background px-6 py-8 text-center shadow-sm">
        <div className="mx-auto flex size-12 items-center justify-center rounded-2xl bg-muted/50 text-muted-foreground">
          <MessageSquareText className="size-6" />
        </div>
        <h2 className="mt-4 text-base font-semibold text-foreground">
          {t("project.detail.sessionList.emptyTitle")}
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          {t("project.detail.sessionList.emptyDescription")}
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-3xl border border-border/60 bg-background px-5 py-5 shadow-sm sm:px-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">
            {t("project.detail.sessionList.title")}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("project.detail.sessionList.subtitle", {
              count: orderedTasks.length,
            })}
          </p>
        </div>
      </div>

      <div className="grid gap-3">
        {orderedTasks.map((task) => {
          const statusMeta = TASK_STATUS_META[task.status];
          const timestampLabel =
            formatTimestamp(task.timestamp, lng) ||
            t("project.detail.unknownUpdatedAt");
          const isActive = task.id === activeTaskId;

          return (
            <button
              key={task.id}
              type="button"
              onClick={() =>
                router.push(
                  lng ? `/${lng}/chat/${task.id}` : `/chat/${task.id}`,
                )
              }
              className={cn(
                "group flex w-full items-start justify-between gap-4 rounded-2xl border px-4 py-4 text-left transition-colors",
                isActive
                  ? "border-primary/40 bg-primary/5"
                  : "border-border/60 bg-muted/20 hover:bg-muted/35",
              )}
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "size-2 shrink-0 rounded-full",
                      statusMeta.dotClassName,
                    )}
                    aria-hidden="true"
                  />
                  <p className="truncate text-sm font-medium text-foreground">
                    {task.title || t("chat.newChat")}
                  </p>
                  {task.hasPendingUserInput ? (
                    <Badge className="h-5 rounded-full px-2 text-[10px] font-semibold">
                      {t("sidebar.askTag")}
                    </Badge>
                  ) : null}
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                  <span>{t(statusMeta.labelKey)}</span>
                  <span className="flex items-center gap-1">
                    <Clock3 className="size-3.5" />
                    {timestampLabel}
                  </span>
                </div>
              </div>

              <span
                className="flex size-8 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors group-hover:text-foreground"
                aria-hidden="true"
              >
                <ArrowUpRight className="size-4" />
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
