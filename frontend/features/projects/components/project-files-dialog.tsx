"use client";

import * as React from "react";
import { FilePlus2, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileCard } from "@/components/shared/file-card";
import { uploadAttachment } from "@/features/attachments/api/attachment-api";
import { projectFilesService } from "@/features/projects/api/project-files-api";
import type { ProjectFile } from "@/features/projects/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

const MAX_FILE_SIZE = 100 * 1024 * 1024;

interface ProjectFilesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  projectName: string;
  onFilesChange?: (files: ProjectFile[]) => void;
}

function toCardFile(file: ProjectFile) {
  return {
    name: file.fileName,
    size: file.fileSize ?? null,
    content_type: file.fileContentType ?? null,
  };
}

export function ProjectFilesDialog({
  open,
  onOpenChange,
  projectId,
  projectName,
  onFilesChange,
}: ProjectFilesDialogProps) {
  const { t } = useT("translation");
  const inputRef = React.useRef<HTMLInputElement>(null);
  const [files, setFiles] = React.useState<ProjectFile[]>([]);
  const [isLoading, setIsLoading] = React.useState(false);
  const [isUploading, setIsUploading] = React.useState(false);
  const [removingFileId, setRemovingFileId] = React.useState<number | null>(
    null,
  );

  const syncFiles = React.useCallback(
    (nextFiles: ProjectFile[]) => {
      setFiles(nextFiles);
      onFilesChange?.(nextFiles);
    },
    [onFilesChange],
  );

  const refreshFiles = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const nextFiles = await projectFilesService.list(projectId, {
        revalidate: 0,
      });
      syncFiles(nextFiles);
    } catch (error) {
      console.error("[ProjectFilesDialog] Failed to load project files", error);
      toast.error(t("project.detail.files.toasts.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [projectId, syncFiles, t]);

  React.useEffect(() => {
    if (!open) return;
    void refreshFiles();
  }, [open, refreshFiles]);

  const handlePickFiles = React.useCallback(() => {
    inputRef.current?.click();
  }, []);

  const handleAddFiles = React.useCallback(
    async (selectedFiles: File[]) => {
      if (selectedFiles.length === 0 || isUploading) return;

      setIsUploading(true);
      try {
        const existingNames = new Set(
          files.map((file) => file.fileName.trim().toLowerCase()),
        );

        for (const file of selectedFiles) {
          const normalizedName = file.name.trim().toLowerCase();
          if (existingNames.has(normalizedName)) {
            toast.error(
              t("hero.toasts.duplicateFileName", { name: file.name }),
            );
            continue;
          }

          if (file.size > MAX_FILE_SIZE) {
            toast.error(t("hero.toasts.fileTooLarge"));
            continue;
          }

          try {
            const uploaded = await uploadAttachment(file);
            await projectFilesService.add(projectId, {
              file_name: uploaded.name,
              file_source: uploaded.source,
              file_size: uploaded.size ?? null,
              file_content_type: uploaded.content_type ?? null,
            });
            existingNames.add(normalizedName);
            toast.success(
              t("project.detail.files.toasts.added", { name: file.name }),
            );
          } catch (error) {
            console.error("[ProjectFilesDialog] Failed to add file", error);
            toast.error(t("project.detail.files.toasts.addFailed"));
          }
        }

        await refreshFiles();
      } finally {
        setIsUploading(false);
      }
    },
    [files, isUploading, projectId, refreshFiles, t],
  );

  const handleFileInputChange = React.useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const selected = Array.from(event.target.files ?? []);
      event.target.value = "";
      await handleAddFiles(selected);
    },
    [handleAddFiles],
  );

  const handleRemoveFile = React.useCallback(
    async (file: ProjectFile) => {
      if (removingFileId != null) return;
      setRemovingFileId(file.id);
      try {
        await projectFilesService.remove(projectId, file.id);
        toast.success(
          t("project.detail.files.toasts.removed", { name: file.fileName }),
        );
        await refreshFiles();
      } catch (error) {
        console.error("[ProjectFilesDialog] Failed to remove file", error);
        toast.error(t("project.detail.files.toasts.removeFailed"));
      } finally {
        setRemovingFileId(null);
      }
    },
    [projectId, refreshFiles, removingFileId, t],
  );

  const countLabel = t("project.detail.files.count", {
    count: files.length,
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85dvh] w-[min(100%-2rem,52rem)] flex-col gap-0 overflow-hidden p-0 sm:max-w-none">
        <div className="border-b border-border/60 bg-gradient-to-b from-muted/35 to-background px-6 py-5">
          <DialogHeader className="space-y-2 text-left">
            <div className="flex flex-wrap items-center gap-2">
              <DialogTitle className="text-lg font-semibold text-foreground">
                {t("project.detail.files.title")}
              </DialogTitle>
              <Badge
                variant="outline"
                className="rounded-full border-border/70 bg-background/70 px-2.5 py-0.5 text-xs text-muted-foreground"
              >
                {countLabel}
              </Badge>
            </div>
            <DialogDescription className="max-w-2xl text-sm leading-6 text-muted-foreground">
              {t("project.detail.files.description", { name: projectName })}
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-4 px-6 py-5">
          <div
            className={cn(
              "rounded-2xl border border-dashed border-border/70 bg-muted/20 p-4 transition-colors",
              isLoading && "opacity-80",
            )}
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  {t("project.detail.files.uploadTitle")}
                </p>
                <p className="text-sm leading-6 text-muted-foreground">
                  {t("project.detail.files.uploadDescription")}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  ref={inputRef}
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileInputChange}
                />
                <Button
                  type="button"
                  onClick={handlePickFiles}
                  disabled={isUploading || isLoading}
                >
                  {isUploading ? (
                    <Loader2 className="size-4 animate-spin" />
                  ) : (
                    <FilePlus2 className="size-4" />
                  )}
                  <span>{t("project.detail.files.uploadButton")}</span>
                </Button>
              </div>
            </div>
          </div>

          <div className="min-h-0 flex-1">
            {isLoading ? (
              <div className="flex h-full items-center justify-center rounded-2xl border border-border/60 bg-muted/20 px-4 py-10 text-sm text-muted-foreground">
                {t("project.detail.files.loading")}
              </div>
            ) : files.length === 0 ? (
              <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-border/70 bg-muted/10 px-4 py-10 text-center">
                <div className="max-w-sm space-y-2">
                  <p className="text-sm font-medium text-foreground">
                    {t("project.detail.files.emptyTitle")}
                  </p>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {t("project.detail.files.emptyDescription")}
                  </p>
                </div>
              </div>
            ) : (
              <ScrollArea className="h-full pr-2">
                <div className="grid gap-3 pb-1">
                  {files.map((file) => (
                    <FileCard
                      key={file.id}
                      file={toCardFile(file)}
                      onRemove={() => void handleRemoveFile(file)}
                      showRemove={removingFileId !== file.id}
                      unknownSizeLabel={t("project.detail.files.unknownSize")}
                      className="w-full bg-background"
                    />
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
