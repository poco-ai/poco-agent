"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useT } from "@/lib/i18n/client";

import { TeamIssueDetailContent } from "./team-issue-detail-content";

interface TeamIssueDetailDialogProps {
  issueId: string | null;
  onClose: () => void;
  onDeleted: (issueId: string) => void;
  onUpdated: (issue: import("@/features/issues/model/types").WorkspaceIssue) => void;
}

export function TeamIssueDetailDialog({
  issueId,
  onClose,
  onDeleted,
  onUpdated,
}: TeamIssueDetailDialogProps) {
  const { t } = useT("translation");

  return (
    <Dialog open={Boolean(issueId)} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="h-[calc(100vh-1rem)] max-w-[calc(100vw-1rem)] gap-0 overflow-hidden rounded-[28px] p-0 sm:h-[calc(100vh-4rem)] sm:max-w-4xl"
        ariaTitle={t("issues.detailTitle")}
      >
        <DialogHeader className="sr-only">
          <DialogTitle>{t("issues.detailTitle")}</DialogTitle>
          <DialogDescription>{t("issues.detailPlaceholder")}</DialogDescription>
        </DialogHeader>
        {issueId ? (
          <TeamIssueDetailContent
            issueId={issueId}
            onDeleted={onDeleted}
            onUpdated={onUpdated}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
