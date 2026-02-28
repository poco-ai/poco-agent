"use client";

import * as React from "react";
import { ChevronDown, ChevronUp, Copy, Check, Pencil } from "lucide-react";
import { FileCard } from "@/components/shared/file-card";
import { RepoCard } from "@/components/shared/repo-card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { MessageBlock, InputFile } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

const MAX_LINES = 5;

export function UserMessage({
  messageId,
  content,
  attachments,
  repoUrl,
  gitBranch,
  onEdit,
}: {
  messageId: string;
  content: string | MessageBlock[];
  attachments?: InputFile[];
  repoUrl?: string | null;
  gitBranch?: string | null;
  onEdit?: (args: { messageId: string; content: string }) => Promise<void>;
}) {
  const { t } = useT("translation");
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [shouldCollapse, setShouldCollapse] = React.useState(false);
  const [isCopied, setIsCopied] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);
  const [isSubmittingEdit, setIsSubmittingEdit] = React.useState(false);
  const [draftContent, setDraftContent] = React.useState("");
  const observerRef = React.useRef<HTMLParagraphElement>(null);
  const editTextareaRef = React.useRef<HTMLTextAreaElement>(null);

  // Parse content if it's an array of blocks
  const parseContent = (content: string | MessageBlock[]): string => {
    if (typeof content === "string") {
      return content;
    }

    // Filter out ToolResultBlock and only keep TextBlock
    const textBlocks = content.filter(
      (block): block is { _type: "TextBlock"; text: string } =>
        block._type === "TextBlock",
    );

    // Join all text blocks with newlines
    return textBlocks.map((block) => block.text).join("\n\n");
  };

  const textContent = parseContent(content);
  const trimmedRepoUrl = (repoUrl || "").trim();
  const trimmedGitBranch = (gitBranch || "").trim();
  const hasRepo = trimmedRepoUrl.length > 0;
  const hasAttachments = Boolean(attachments && attachments.length > 0);

  // Copy handler
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(textContent);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy message", err);
    }
  };

  // Edit handler
  const handleEdit = () => {
    setDraftContent(textContent);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    if (isSubmittingEdit) return;
    setIsEditing(false);
    setDraftContent(textContent);
  };

  const handleSubmitEdit = async () => {
    if (!onEdit || isSubmittingEdit) return;
    const nextContent = draftContent.trim();
    if (!nextContent) return;
    setIsSubmittingEdit(true);
    try {
      await onEdit({ messageId, content: nextContent });
      setIsEditing(false);
    } finally {
      setIsSubmittingEdit(false);
    }
  };

  // Check if content overflows using ResizeObserver
  React.useEffect(() => {
    const element = observerRef.current;
    if (!element) return;

    const checkOverflow = () => {
      // Compare scrollHeight with client height to detect overflow
      const lineHeight = parseFloat(getComputedStyle(element).lineHeight);
      const thresholdHeight = lineHeight * MAX_LINES;
      setShouldCollapse(element.scrollHeight > thresholdHeight + 1); // +1 for rounding
    };

    // Initial check
    checkOverflow();

    // Observe size changes
    const observer = new ResizeObserver(checkOverflow);
    observer.observe(element);

    return () => observer.disconnect();
  }, [textContent]);

  React.useEffect(() => {
    if (!isEditing) return;
    const rafId = window.requestAnimationFrame(() => {
      const textarea = editTextareaRef.current;
      if (!textarea) return;
      textarea.focus();
      const length = textarea.value.length;
      textarea.setSelectionRange(length, length);
    });
    return () => window.cancelAnimationFrame(rafId);
  }, [isEditing]);

  return (
    <div className="flex w-full min-w-0 flex-col items-end gap-2">
      {(hasRepo || hasAttachments) && (
        <div className="flex w-full min-w-0 max-w-[85%] flex-wrap justify-end gap-2">
          {hasRepo ? (
            <RepoCard
              url={trimmedRepoUrl}
              branch={trimmedGitBranch || null}
              className="w-full max-w-48"
              showRemove={false}
              onOpen={() => {
                const raw = trimmedRepoUrl;
                const openUrl = /^https?:\/\//i.test(raw)
                  ? raw
                  : `https://${raw}`;
                try {
                  window.open(openUrl, "_blank", "noopener,noreferrer");
                } catch (error) {
                  console.warn("[UserMessage] Failed to open repo url", error);
                }
              }}
            />
          ) : null}
          {attachments?.map((file, i) => (
            <FileCard
              key={i}
              file={file}
              className="w-full max-w-48"
              showRemove={false}
            />
          ))}
        </div>
      )}
      {(textContent || isEditing) && (
        <div
          className={cn(
            "group flex min-w-0 flex-col items-end gap-2",
            isEditing ? "w-[85%] min-w-[50%]" : "max-w-[85%]",
          )}
        >
          {isEditing ? (
            <div className="w-full min-w-0 max-w-full overflow-hidden rounded-lg border border-border bg-muted/60 px-3 py-3">
              <Textarea
                ref={editTextareaRef}
                value={draftContent}
                onChange={(event) => setDraftContent(event.target.value)}
                disabled={isSubmittingEdit}
                className="min-h-8 max-h-60 resize-none overflow-y-auto border-0 bg-transparent shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
              />
              <div className="mt-2 flex items-center justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCancelEdit}
                  disabled={isSubmittingEdit}
                >
                  {t("common.cancel")}
                </Button>
                <Button
                  size="sm"
                  onClick={handleSubmitEdit}
                  disabled={!draftContent.trim() || isSubmittingEdit}
                >
                  {t("hero.send")}
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div className="w-fit min-w-0 max-w-full overflow-hidden rounded-lg bg-muted px-4 py-2 text-foreground">
                <p
                  ref={observerRef}
                  className={`text-base whitespace-pre-wrap break-words break-all [overflow-wrap:anywhere] ${
                    shouldCollapse && !isExpanded ? "line-clamp-5" : ""
                  }`}
                >
                  {textContent}
                </p>
              </div>
              <div className="flex items-center justify-between w-full gap-1 opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
                {shouldCollapse && (
                  <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  >
                    {isExpanded ? (
                      <>
                        <ChevronUp className="h-4 w-4" />
                        {t("chat.collapse")}
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-4 w-4" />
                        {t("chat.expand")}
                      </>
                    )}
                  </button>
                )}
                <div className="flex items-center gap-1 ml-auto">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-foreground"
                    onClick={onCopy}
                    title={t("chat.copyMessage")}
                  >
                    {isCopied ? (
                      <Check className="size-3.5" />
                    ) : (
                      <Copy className="size-3.5" />
                    )}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-foreground"
                    onClick={handleEdit}
                    title={t("chat.editMessage")}
                  >
                    <Pencil className="size-3.5" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
