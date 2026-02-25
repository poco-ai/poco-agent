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

  const isDuplicate = React.useCallback(
    (fileName: string) => {
      const normalized = fileName.trim().toLowerCase();
      return attachments.some(
        (item) => (item.name || "").trim().toLowerCase() === normalized,
      );
    },
    [attachments],
  );

  const uploadFile = React.useCallback(
    async (file: File) => {
      if (isDuplicate(file.name)) {
        toast.error(t("hero.toasts.duplicateFileName", { name: file.name }));
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        toast.error(t("hero.toasts.fileTooLarge"));
        return;
      }

      try {
        setIsUploading(true);
        const uploaded = await uploadAttachment(file);
        setAttachments((prev) => [...prev, uploaded]);
        toast.success(t("hero.toasts.uploadSuccess"));
        playUploadSound();
      } catch (error) {
        console.error("[useFileUpload] Upload failed:", error);
        toast.error(t("hero.toasts.uploadFailed"));
      } finally {
        setIsUploading(false);
      }
    },
    [isDuplicate, t],
  );

  const handleFileSelect = React.useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const input = e.currentTarget;
      const file = e.target.files?.[0];
      if (!file) return;
      try {
        await uploadFile(file);
      } finally {
        input.value = "";
      }
    },
    [uploadFile],
  );

  const handlePaste = React.useCallback(
    async (e: React.ClipboardEvent) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      const file = Array.from(items)
        .find((item) => item.kind === "file")
        ?.getAsFile();

      if (!file) return;
      await uploadFile(file);
    },
    [uploadFile],
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
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
  };
}
