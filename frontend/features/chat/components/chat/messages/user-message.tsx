"use client";

import * as React from "react";
import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Copy,
  Check,
  Pencil,
  Sparkles,
} from "lucide-react";
import { FileCard } from "@/components/shared/file-card";
import { RepoCard } from "@/components/shared/repo-card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type {
  AgentTriggerContext,
  ChatFileReference,
  ChatSkillReference,
  MessageBlock,
  InputFile,
} from "@/features/chat/types";
import { getFileIcon } from "@/lib/utils/file/get-file-icon";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

const MAX_LINES = 5;

export function UserMessage({
  messageId,
  content,
  triggerContext,
  fileReferences,
  skillReferences,
  attachments,
  repoUrl,
  gitBranch,
  onEdit,
}: {
  messageId: string;
  content: string | MessageBlock[];
  triggerContext?: AgentTriggerContext;
  fileReferences?: ChatFileReference[];
  skillReferences?: ChatSkillReference[];
  attachments?: InputFile[];
  repoUrl?: string | null;
  gitBranch?: string | null;
  onEdit?: (args: { messageId: string; content: string }) => Promise<void>;
}) {
  const { t } = useT("translation");
  const [isExpanded, setIsExpanded] = React.useState(false);
  const [shouldCollapse, setShouldCollapse] = React.useState(false);
  const [isCopied, setIsCopied] = React.useState(false);
  const [isTriggerContextOpen, setIsTriggerContextOpen] = React.useState(false);
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
  const triggerContextRows = React.useMemo(
    () => buildTriggerContextRows(triggerContext, t),
    [triggerContext, t],
  );
  const triggerSource = formatTriggerSource(triggerContext);

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
              {triggerContext ? (
                <div className="w-full min-w-0 max-w-full overflow-hidden rounded-lg border border-border bg-background/80 text-sm shadow-sm">
                  <button
                    type="button"
                    className="flex w-full min-w-0 items-center gap-2 px-3 py-2 text-left text-muted-foreground transition-colors hover:text-foreground"
                    onClick={() =>
                      setIsTriggerContextOpen((current) => !current)
                    }
                    aria-expanded={isTriggerContextOpen}
                  >
                    {isTriggerContextOpen ? (
                      <ChevronDown className="size-4 shrink-0" />
                    ) : (
                      <ChevronRight className="size-4 shrink-0" />
                    )}
                    <span className="min-w-0 flex-1 truncate font-medium text-foreground">
                      {t("chat.triggerContextTitle")}
                    </span>
                    <span className="hidden min-w-0 truncate sm:inline">
                      {[
                        triggerContext.trigger_type,
                        triggerSource,
                        triggerContext.channel_id,
                        triggerContext.trigger_message_id,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </span>
                  </button>
                  {isTriggerContextOpen ? (
                    <dl className="grid gap-2 border-t border-border px-3 py-2 text-xs sm:grid-cols-[max-content_minmax(0,1fr)]">
                      {triggerContextRows.map((row) => (
                        <React.Fragment key={row.label}>
                          <dt className="text-muted-foreground">{row.label}</dt>
                          <dd className="min-w-0 break-words font-mono text-foreground">
                            {row.value}
                          </dd>
                        </React.Fragment>
                      ))}
                    </dl>
                  ) : null}
                </div>
              ) : null}
              <div className="w-fit min-w-0 max-w-full overflow-hidden rounded-lg bg-muted px-4 py-2 text-foreground">
                <p
                  ref={observerRef}
                  className={`text-base whitespace-pre-wrap break-words break-all [overflow-wrap:anywhere] ${
                    shouldCollapse && !isExpanded ? "line-clamp-5" : ""
                  }`}
                >
                  {renderReferenceText(
                    textContent,
                    fileReferences ?? [],
                    skillReferences ?? [],
                  )}
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

function formatFileReferenceDisplay(reference: ChatFileReference): string {
  const displayName = reference.displayName?.trim();
  if (displayName) return displayName;
  if (reference.kind === "workspace_file") {
    return reference.path.split("/").filter(Boolean).pop() || reference.path;
  }
  return reference.metadata?.path || reference.source;
}

function formatFileReferenceTitle(reference: ChatFileReference): string {
  const displayName = formatFileReferenceDisplay(reference);
  if (reference.kind === "workspace_file") {
    return reference.path || displayName;
  }
  return reference.metadata?.path || reference.source || displayName;
}

function formatFileReferenceIconName(reference: ChatFileReference): string {
  if (reference.kind === "workspace_file") {
    return reference.path || reference.displayName;
  }
  return reference.metadata?.path || reference.displayName || reference.source;
}

type PositionedReference =
  | { kind: "file"; reference: ChatFileReference; start: number }
  | { kind: "skill"; reference: ChatSkillReference; start: number };

function resolveReferenceStart(
  text: string,
  reference: { insertedText: string; range?: { start: number; end: number } },
): number {
  return reference.range &&
    text.slice(reference.range.start, reference.range.end) ===
      reference.insertedText
    ? reference.range.start
    : text.indexOf(reference.insertedText);
}

function renderReferenceText(
  text: string,
  fileReferences: ChatFileReference[],
  skillReferences: ChatSkillReference[],
): React.ReactNode[] | string {
  if (fileReferences.length === 0 && skillReferences.length === 0) return text;

  const filePositions: PositionedReference[] = fileReferences
    .map((reference) => {
      return {
        kind: "file" as const,
        reference,
        start: resolveReferenceStart(text, reference),
      };
    })
    .filter((item) => item.start >= 0);
  const skillPositions: PositionedReference[] = skillReferences
    .map((reference) => {
      return {
        kind: "skill" as const,
        reference,
        start: resolveReferenceStart(text, reference),
      };
    })
    .filter((item) => item.start >= 0);

  const positioned = [...filePositions, ...skillPositions].sort(
    (left, right) => left.start - right.start,
  );

  if (positioned.length === 0) return text;

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (const item of positioned) {
    if (item.start < cursor) continue;
    if (item.start > cursor) {
      nodes.push(
        <React.Fragment key={`text-${cursor}`}>
          {text.slice(cursor, item.start)}
        </React.Fragment>,
      );
    }

    if (item.kind === "skill") {
      const reference = item.reference;
      nodes.push(
        <span
          key={`${reference.id}-${item.start}`}
          title={reference.metadata?.description ?? reference.displayName}
          className="inline-flex max-w-full cursor-text select-text items-center rounded-md border border-primary/30 bg-primary/10 px-1.5 py-0.5 text-sm font-semibold text-foreground align-baseline"
        >
          <Sparkles className="mr-1 size-3.5 shrink-0" aria-hidden="true" />
          {reference.displayName.replace(/^[/$]/, "")}
        </span>,
      );
      cursor = item.start + reference.insertedText.length;
      continue;
    }

    const reference = item.reference;
    const displayName = formatFileReferenceDisplay(reference);
    const Icon = getFileIcon(formatFileReferenceIconName(reference));
    nodes.push(
      <span
        key={`${reference.id}-${item.start}`}
        title={formatFileReferenceTitle(reference)}
        className="inline-flex max-w-full cursor-text select-text items-center rounded-md border border-amber-900/30 bg-amber-900/10 px-1.5 py-0.5 text-sm font-semibold text-foreground align-baseline"
      >
        <Icon className="mr-1 size-3.5 shrink-0" aria-hidden="true" />
        {displayName.replace(/^#/, "")}
      </span>,
    );
    cursor = item.start + reference.insertedText.length;
  }

  if (cursor < text.length) {
    nodes.push(
      <React.Fragment key={`text-${cursor}`}>
        {text.slice(cursor)}
      </React.Fragment>,
    );
  }
  return nodes;
}

function formatTriggerSource(triggerContext?: AgentTriggerContext): string {
  const actor = triggerContext?.source_actor;
  if (!actor) return "";
  const displayName = actor.display_name?.trim();
  const identity = actor.user_id?.trim() || actor.agent_identity_id?.trim();
  if (displayName && identity) return `${displayName} (${identity})`;
  return displayName || identity || actor.actor_type || "";
}

function joinIds(values?: string[]): string {
  const normalized = values?.map((value) => value.trim()).filter(Boolean) ?? [];
  return normalized.length > 0 ? normalized.join(", ") : "-";
}

function buildTriggerContextRows(
  triggerContext: AgentTriggerContext | undefined,
  t: (key: string) => string,
): Array<{ label: string; value: string }> {
  if (!triggerContext) return [];
  return [
    {
      label: t("chat.triggerContextFields.source"),
      value: formatTriggerSource(triggerContext) || "-",
    },
    {
      label: t("chat.triggerContextFields.triggerType"),
      value: triggerContext.trigger_type || "-",
    },
    {
      label: t("chat.triggerContextFields.server"),
      value: triggerContext.server_id || "-",
    },
    {
      label: t("chat.triggerContextFields.channel"),
      value: triggerContext.channel_id || "-",
    },
    {
      label: t("chat.triggerContextFields.message"),
      value: triggerContext.trigger_message_id || "-",
    },
    {
      label: t("chat.triggerContextFields.thread"),
      value: triggerContext.thread_root_message_id || "-",
    },
    {
      label: t("chat.triggerContextFields.agent"),
      value: triggerContext.target_agent_identity_id || "-",
    },
    {
      label: t("chat.triggerContextFields.handle"),
      value: triggerContext.target_agent_handle || "-",
    },
    {
      label: t("chat.triggerContextFields.messages"),
      value: joinIds(triggerContext.references?.message_ids),
    },
    {
      label: t("chat.triggerContextFields.artifacts"),
      value: joinIds(triggerContext.references?.artifact_ids),
    },
    {
      label: t("chat.triggerContextFields.tasks"),
      value: joinIds(triggerContext.references?.task_ids),
    },
    {
      label: t("chat.triggerContextFields.handoff"),
      value: triggerContext.handoff?.dedupe_key || "-",
    },
  ];
}
