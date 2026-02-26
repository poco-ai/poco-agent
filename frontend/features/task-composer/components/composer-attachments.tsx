"use client";

import * as React from "react";
import { FileCard } from "@/components/shared/file-card";
import { RepoCard } from "@/components/shared/repo-card";
import type { InputFile } from "@/features/chat/types/api/session";

interface ComposerAttachmentsProps {
  repoUrl: string;
  gitBranch: string;
  attachments: InputFile[];
  onOpenRepoDialog: () => void;
  onRemoveRepo: () => void;
  onRemoveAttachment: (index: number) => void;
}

/**
 * Displays the list of attached files and repo card above the composer textarea.
 */
export function ComposerAttachments({
  repoUrl,
  gitBranch,
  attachments,
  onOpenRepoDialog,
  onRemoveRepo,
  onRemoveAttachment,
}: ComposerAttachmentsProps) {
  const hasRepo = repoUrl.trim().length > 0;
  const hasAttachments = attachments.length > 0;

  if (!hasRepo && !hasAttachments) return null;

  return (
    <div className="flex flex-wrap gap-3 px-4 pt-4">
      {hasRepo && (
        <RepoCard
          url={repoUrl.trim()}
          branch={gitBranch.trim() || null}
          onOpen={onOpenRepoDialog}
          onRemove={onRemoveRepo}
          className="w-48 bg-background"
        />
      )}
      {attachments.map((file, i) => (
        <FileCard
          key={i}
          file={file}
          onRemove={() => onRemoveAttachment(i)}
          className="w-48 bg-background"
        />
      ))}
    </div>
  );
}
