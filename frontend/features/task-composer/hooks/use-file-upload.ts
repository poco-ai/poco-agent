import * as React from "react";
import { toast } from "sonner";
import { uploadAttachment } from "@/features/attachments/api/attachment-api";
import type { InputFile } from "@/features/chat/types/api/session";
import { playUploadSound } from "@/lib/utils/sound";

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100 MB

interface UseFileUploadOptions {
  /** i18n translation function */
  t: (key: string, opts?: Record<string, unknown>) => string;
}

/**
 * Shared hook for file upload logic used by both TaskComposer and ChatInput.
 *
 * Encapsulates:
 * - File validation (size, duplicate detection)
 * - Upload via attachment service
 * - Attachment list state management
 * - Paste handler for clipboard images
 */
export function useFileUpload({ t }: UseFileUploadOptions) {
  const [isUploading, setIsUploading] = React.useState(false);
  const [attachments, setAttachments] = React.useState<InputFile[]>([]);

  const getAttachmentNameSet = React.useCallback(() => {
    return new Set(
      attachments
        .map((item) => (item.name || "").trim().toLowerCase())
        .filter(Boolean),
    );
  }, [attachments]);

  const uploadFiles = React.useCallback(
    async (files: File[]) => {
      if (files.length === 0) return;

      const existingNames = getAttachmentNameSet();
      setIsUploading(true);

      try {
        for (const file of files) {
          const normalized = file.name.trim().toLowerCase();
          if (existingNames.has(normalized)) {
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
            setAttachments((prev) => [...prev, uploaded]);
            existingNames.add(normalized);
            toast.success(t("hero.toasts.uploadSuccess"));
            playUploadSound();
          } catch (error) {
            console.error("[useFileUpload] Upload failed:", error);
            toast.error(t("hero.toasts.uploadFailed"));
          }
        }
      } finally {
        setIsUploading(false);
      }
    },
    [getAttachmentNameSet, t],
  );

  const uploadFile = React.useCallback(
    async (file: File) => {
      await uploadFiles([file]);
    },
    [uploadFiles],
  );

  const handleFileSelect = React.useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const input = e.currentTarget;
      const files = Array.from(e.target.files ?? []);
      if (files.length === 0) return;
      try {
        await uploadFiles(files);
      } finally {
        input.value = "";
      }
    },
    [uploadFiles],
  );

  const handlePaste = React.useCallback(
    async (e: React.ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      const file = Array.from(items)
        .find((item) => item.kind === "file")
        ?.getAsFile();

      if (!file) return;
      await uploadFiles([file]);
    },
    [uploadFiles],
  );

  const removeAttachment = React.useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearAttachments = React.useCallback(() => {
    setAttachments([]);
  }, []);

  return {
    isUploading,
    attachments,
    uploadFile,
    uploadFiles,
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
  };
}
