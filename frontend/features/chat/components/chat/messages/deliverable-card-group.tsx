"use client";

import * as React from "react";

import { Download, Eye, History, Workflow } from "lucide-react";

import { Button } from "@/components/ui/button";
import { downloadFileFromUrl } from "@/features/chat/components/execution/file-panel/file-sidebar";
import type { DeliverableVersionResponse } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";

export interface AssistantDeliverableCardData {
  deliverableId: string;
  logicalName: string;
  kind: string;
  versions: DeliverableVersionResponse[];
  fileUrlByVersionId?: Record<string, string | null>;
}

interface DeliverableCardGroupProps {
  cards: AssistantDeliverableCardData[];
  onOpenPreview?: (deliverableId: string, versionId: string) => void;
  onOpenProcess?: (deliverableId: string, versionId: string) => void;
}

function getLatestVersion(
  versions: DeliverableVersionResponse[],
): DeliverableVersionResponse | null {
  if (versions.length === 0) return null;
  return [...versions].sort((a, b) => b.version_no - a.version_no)[0] ?? null;
}

function getPreviousVersion(
  versions: DeliverableVersionResponse[],
): DeliverableVersionResponse | null {
  if (versions.length < 2) return null;
  return [...versions].sort((a, b) => b.version_no - a.version_no)[1] ?? null;
}

export function DeliverableCardGroup({
  cards,
  onOpenPreview,
  onOpenProcess,
}: DeliverableCardGroupProps) {
  const { t } = useT("translation");

  if (cards.length === 0) return null;

  return (
    <div className="mt-4 grid gap-3">
      {cards.map((card) => {
        const latestVersion = getLatestVersion(card.versions);
        const previousVersion = getPreviousVersion(card.versions);
        if (!latestVersion) return null;

        const latestFileUrl =
          card.fileUrlByVersionId?.[latestVersion.id] ?? null;

        return (
          <div
            key={`${card.deliverableId}-${latestVersion.id}`}
            className="rounded-xl border border-border bg-card px-4 py-3"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-foreground">
                  {card.logicalName}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  {latestVersion.file_name ?? latestVersion.file_path}
                </div>
              </div>
              <div className="shrink-0 rounded-full border border-border/70 px-2 py-0.5 text-[11px] text-muted-foreground">
                v{latestVersion.version_no}
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  onOpenPreview?.(card.deliverableId, latestVersion.id)
                }
              >
                <Eye className="mr-1 size-4" />
                {t("artifacts.viewer.openInNewWindow")}
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={!latestFileUrl}
                onClick={() => {
                  if (!latestFileUrl) return;
                  void downloadFileFromUrl(
                    latestFileUrl,
                    latestVersion.file_name ??
                      latestVersion.file_path.split("/").pop() ??
                      card.logicalName,
                  );
                }}
              >
                <Download className="mr-1 size-4" />
                {t("artifacts.viewer.downloadOriginal")}
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  onOpenProcess?.(card.deliverableId, latestVersion.id)
                }
              >
                <Workflow className="mr-1 size-4" />
                {t("computer.title")}
              </Button>
              {previousVersion ? (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() =>
                    onOpenPreview?.(card.deliverableId, previousVersion.id)
                  }
                >
                  <History className="mr-1 size-4" />v
                  {previousVersion.version_no}
                </Button>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
