"use client";

import * as React from "react";
import {
  AlignLeft,
  FolderTree,
  Loader2,
  PencilLine,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { getFilesAction } from "@/features/chat/actions/query-actions";
import { FileSidebar } from "@/features/chat/components/execution/file-panel/file-sidebar";
import { DocumentViewer } from "@/features/chat/components/execution/file-panel/document-viewer";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import type { FileNode, PendingSkillCreation } from "@/features/chat/types";

function normalizePath(value: string): string {
  return value.replace(/\\/g, "/").replace(/^\/+/, "");
}

function filterTreeByPrefix(nodes: FileNode[], prefix: string): FileNode[] {
  const normalizedPrefix = normalizePath(prefix);
  const prefixWithSlash = normalizedPrefix ? `${normalizedPrefix}/` : "";

  const visit = (node: FileNode): FileNode | null => {
    const nodePath = normalizePath(node.path);
    const matches =
      nodePath === normalizedPrefix || nodePath.startsWith(prefixWithSlash);

    if (node.type === "file") {
      return matches ? node : null;
    }

    const children = (node.children ?? [])
      .map((child) => visit(child))
      .filter((child): child is FileNode => child !== null);

    if (!matches && children.length === 0) {
      return null;
    }

    return {
      ...node,
      children,
    };
  };

  return nodes
    .map((node) => visit(node))
    .filter((node): node is FileNode => node !== null);
}

function flattenFiles(nodes: FileNode[]): FileNode[] {
  const result: FileNode[] = [];
  const visit = (items: FileNode[]) => {
    for (const item of items) {
      if (item.type === "file") {
        result.push(item);
        continue;
      }
      if (item.children?.length) {
        visit(item.children);
      }
    }
  };
  visit(nodes);
  return result;
}

interface SkillCreationReviewCardProps {
  creation: PendingSkillCreation;
  isSubmitting?: boolean;
  className?: string;
  onConfirm: (payload: {
    resolved_name?: string | null;
    description?: string | null;
    overwrite?: boolean;
  }) => Promise<unknown>;
  onCancel: () => Promise<unknown>;
}

export function SkillCreationReviewCard({
  creation,
  isSubmitting = false,
  className,
  onConfirm,
  onCancel,
}: SkillCreationReviewCardProps) {
  const { t } = useT("translation");
  const [resolvedName, setResolvedName] = React.useState(
    creation.resolved_name || creation.detected_name,
  );
  const [overwrite, setOverwrite] = React.useState(false);
  const [description, setDescription] = React.useState(
    creation.description || "",
  );
  const [files, setFiles] = React.useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = React.useState<FileNode>();
  const [isLoadingFiles, setIsLoadingFiles] = React.useState(false);
  const [isPreviewVisible, setIsPreviewVisible] = React.useState(false);
  const [conflict, setConflict] = React.useState(false);

  React.useEffect(() => {
    setResolvedName(creation.resolved_name || creation.detected_name);
    setDescription(creation.description || "");
    setOverwrite(false);
    setIsPreviewVisible(false);
  }, [
    creation.description,
    creation.detected_name,
    creation.id,
    creation.resolved_name,
  ]);

  React.useEffect(() => {
    let cancelled = false;

    const loadFiles = async () => {
      if (!creation.session_id) {
        setFiles([]);
        setSelectedFile(undefined);
        setIsPreviewVisible(false);
        return;
      }
      try {
        setIsLoadingFiles(true);
        const workspaceFiles = await getFilesAction({
          sessionId: creation.session_id,
        });
        if (cancelled) return;
        const filtered = filterTreeByPrefix(
          workspaceFiles,
          creation.skill_relative_path,
        );
        const flatFiles = flattenFiles(filtered);
        setFiles(filtered);
        setSelectedFile(flatFiles[0]);
        setIsPreviewVisible(false);
      } catch (error) {
        console.error("[SkillCreationReviewCard] Failed to load files", error);
        if (!cancelled) {
          setFiles([]);
          setSelectedFile(undefined);
          setIsPreviewVisible(false);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingFiles(false);
        }
      }
    };

    void loadFiles();
    return () => {
      cancelled = true;
    };
  }, [creation.session_id, creation.skill_relative_path]);

  React.useEffect(() => {
    let cancelled = false;
    const loadConflict = async () => {
      try {
        const skills = await skillsService.listSkills({ revalidate: 0 });
        if (cancelled) return;
        const normalized = resolvedName.trim().toLowerCase();
        setConflict(
          Boolean(
            normalized &&
            skills.some(
              (skill) => skill.name.trim().toLowerCase() === normalized,
            ),
          ),
        );
      } catch {
        if (!cancelled) {
          setConflict(false);
        }
      }
    };

    void loadConflict();
    return () => {
      cancelled = true;
    };
  }, [resolvedName]);

  React.useEffect(() => {
    if (!isPreviewVisible) {
      return;
    }

    const handleClosePreview = () => {
      setIsPreviewVisible(false);
    };

    window.addEventListener("close-document-viewer", handleClosePreview);
    return () => {
      window.removeEventListener("close-document-viewer", handleClosePreview);
    };
  }, [isPreviewVisible]);

  const handleConfirm = async () => {
    try {
      await onConfirm({
        resolved_name: resolvedName.trim() || undefined,
        description: description.trim(),
        overwrite,
      });
      toast.success(t("chat.skillCreationReview.createSuccess"));
    } catch (error) {
      console.error("[SkillCreationReviewCard] Failed to confirm skill", error);
      toast.error(t("chat.skillCreationReview.createFailed"));
    }
  };

  const handleCancel = async () => {
    try {
      await onCancel();
      toast.success(t("chat.skillCreationReview.cancelSuccess"));
    } catch (error) {
      console.error("[SkillCreationReviewCard] Failed to cancel skill", error);
      toast.error(t("chat.skillCreationReview.cancelFailed"));
    }
  };

  return (
    <div
      className={cn(
        "flex flex-col overflow-visible rounded-lg border border-border bg-card/70 p-4 shadow-sm md:h-[60vh] md:max-h-[80vh] md:overflow-hidden",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <div className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Sparkles className="size-4" />
            </div>
            <div>
              <div className="text-sm font-medium text-foreground">
                {t("chat.skillCreationReview.title")}
              </div>
              <div className="text-xs text-muted-foreground">
                {t("chat.skillCreationReview.subtitle")}
              </div>
            </div>
          </div>
        </div>
        {isSubmitting ? (
          <Loader2 className="size-4 animate-spin text-muted-foreground" />
        ) : null}
      </div>

      <div className="mt-4 grid gap-4 md:min-h-0 md:flex-1 md:grid-cols-[minmax(200px,0.6fr)_minmax(0,1.5fr)] md:overflow-hidden">
        <div className="min-h-[220px] overflow-hidden rounded-lg border border-border/60 bg-background md:min-h-0">
          {isLoadingFiles ? (
            <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 size-4 animate-spin" />
              {t("chat.skillCreationReview.loadingFiles")}
            </div>
          ) : files.length === 0 ? (
            <div className="flex h-full min-h-[320px] items-center justify-center px-4 text-center text-sm text-muted-foreground">
              {t("chat.skillCreationReview.emptyFiles")}
            </div>
          ) : (
            <FileSidebar
              files={files}
              onFileSelect={(file) => {
                setSelectedFile(file);
                setIsPreviewVisible(true);
              }}
              selectedFile={selectedFile}
              embedded
            />
          )}
        </div>

        <div
          className={cn(
            "min-h-[320px] overflow-hidden rounded-lg bg-background md:min-h-0",
            isPreviewVisible && selectedFile
              ? "bg-transparent"
              : "border border-border/60",
          )}
        >
          {isPreviewVisible && selectedFile ? (
            <div className="h-[60vh] min-h-[360px] overflow-hidden md:h-full md:min-h-0">
              <DocumentViewer file={selectedFile} />
            </div>
          ) : (
            <div className="space-y-4 p-4 md:min-h-0 md:overflow-y-auto">
              <div className="space-y-2">
                <Label
                  htmlFor={`skill-creation-name-${creation.id}`}
                  className="flex items-center gap-2"
                >
                  <PencilLine className="size-4 text-muted-foreground" />
                  {t("chat.skillCreationReview.nameLabel")}
                </Label>
                <Input
                  id={`skill-creation-name-${creation.id}`}
                  value={resolvedName}
                  disabled={isSubmitting}
                  onChange={(event) => setResolvedName(event.target.value)}
                  placeholder={creation.detected_name}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <AlignLeft className="size-4" />
                  {t("chat.skillCreationReview.descriptionLabel")}
                </div>
                <Textarea
                  value={description}
                  disabled={isSubmitting}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder={t("chat.skillCreationReview.emptyDescription")}
                  className="min-h-28 resize-y"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  <FolderTree className="size-4" />
                  {t("chat.skillCreationReview.pathLabel")}
                </div>
                <code className="block rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
                  {creation.skill_relative_path}
                </code>
              </div>

              {conflict ? (
                <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
                  <div className="flex items-start gap-2">
                    <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                    <div className="space-y-2">
                      <div>{t("chat.skillCreationReview.conflictWarning")}</div>
                      <div className="flex items-center gap-2">
                        <Checkbox
                          id={`skill-creation-overwrite-${creation.id}`}
                          checked={overwrite}
                          disabled={isSubmitting}
                          onCheckedChange={(checked) =>
                            setOverwrite(checked === true)
                          }
                        />
                        <Label
                          htmlFor={`skill-creation-overwrite-${creation.id}`}
                          className="text-sm font-normal"
                        >
                          {t("chat.skillCreationReview.overwriteLabel")}
                        </Label>
                      </div>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      </div>

      {creation.error ? (
        <div
          className={cn(
            "mt-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive",
          )}
        >
          {creation.error}
        </div>
      ) : null}

      <div className="mt-4 flex items-center justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          disabled={isSubmitting}
          onClick={handleCancel}
        >
          {t("chat.skillCreationReview.cancel")}
        </Button>
        <Button
          type="button"
          disabled={isSubmitting || (conflict && !overwrite)}
          onClick={handleConfirm}
        >
          {conflict
            ? t("chat.skillCreationReview.confirmOverwrite")
            : t("chat.skillCreationReview.confirm")}
        </Button>
      </div>
    </div>
  );
}
