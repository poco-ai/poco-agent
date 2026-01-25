import { uploadAttachment } from "@/features/attachments/services/attachment-service";
import type { InputFile } from "@/features/chat/types/api/session";
import { Loader2, ArrowUp, Mic, Plus, FileText, Figma } from "lucide-react";
import { toast } from "sonner";
import * as React from "react";
import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { FileCard } from "@/components/shared/file-card";
import { playFileUploadSound } from "@/lib/utils/sound";

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

export interface TaskSendOptions {
  attachments?: InputFile[];
}

export function TaskComposer({
  textareaRef,
  value,
  onChange,
  onSend,
  isSubmitting,
  onFocus,
  onBlur,
}: {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  value: string;
  onChange: (value: string) => void;
  onSend: (options?: TaskSendOptions) => void | Promise<void>;
  isSubmitting?: boolean;
  onFocus?: () => void;
  onBlur?: () => void;
}) {
  const { t } = useT("translation");
  const isComposing = React.useRef(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = React.useState(false);
  const [attachments, setAttachments] = React.useState<InputFile[]>([]);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_FILE_SIZE) {
      toast.error(t("hero.toasts.fileTooLarge"));
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    try {
      setIsUploading(true);
      const uploadedFile = await uploadAttachment(file);
      const newAttachments = [...attachments, uploadedFile];
      setAttachments(newAttachments);
      toast.success(t("hero.toasts.uploadSuccess"));
      playFileUploadSound();
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error(t("hero.toasts.uploadFailed"));
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const removeAttachment = (index: number) => {
    const newAttachments = attachments.filter((_, i) => i !== index);
    setAttachments(newAttachments);
  };

  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const file = Array.from(items)
      .find((item) => item.kind === "file")
      ?.getAsFile();

    if (!file) return;

    if (file.size > MAX_FILE_SIZE) {
      toast.error(t("hero.toasts.fileTooLarge"));
      return;
    }

    try {
      setIsUploading(true);
      const uploadedFile = await uploadAttachment(file);
      const newAttachments = [...attachments, uploadedFile];
      setAttachments(newAttachments);
      toast.success(t("hero.toasts.uploadSuccess"));
      playFileUploadSound();
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error(t("hero.toasts.uploadFailed"));
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = React.useCallback(() => {
    if (isSubmitting || isUploading) return;
    if (!value.trim() && attachments.length === 0) return;

    onSend({ attachments });
    setAttachments([]);
  }, [attachments, isSubmitting, isUploading, onSend, value]);

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        onChange={handleFileSelect}
      />

      {/* Attachments Display */}
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-3 px-4 pt-4">
          {attachments.map((file, i) => (
            <FileCard
              key={i}
              file={file}
              onRemove={() => removeAttachment(i)}
              className="w-48 bg-background border-dashed"
            />
          ))}
        </div>
      )}

      {/* 输入区域 */}
      <div className="px-4 pb-3 pt-4">
        <Textarea
          ref={textareaRef}
          value={value}
          disabled={isSubmitting || isUploading}
          onChange={(e) => onChange(e.target.value)}
          onCompositionStart={() => (isComposing.current = true)}
          onCompositionEnd={() => {
            requestAnimationFrame(() => {
              isComposing.current = false;
            });
          }}
          onPaste={handlePaste}
          onFocus={onFocus}
          onBlur={onBlur}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              if (e.shiftKey) {
                // Allow default behavior (newline)
                return;
              }
              if (
                e.nativeEvent.isComposing ||
                isComposing.current ||
                e.keyCode === 229
              ) {
                return;
              }
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder={t("hero.placeholder")}
          className="min-h-[60px] max-h-[40vh] w-full resize-none border-0 bg-transparent dark:bg-transparent p-0 text-base shadow-none placeholder:text-muted-foreground/50 focus-visible:ring-0 disabled:opacity-50"
          rows={2}
        />
      </div>

      {/* 底部工具栏 */}
      <div className="flex items-center justify-between px-3 pb-3">
        {/* 左侧操作按钮 */}
        <div className="flex items-center gap-1">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={isSubmitting || isUploading}
                className="size-9 rounded-xl hover:bg-accent"
                title={t("hero.attachFile")}
              >
                {isUploading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Plus className="size-4" />
                )}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-48">
              <DropdownMenuItem
                onClick={() => fileInputRef.current?.click()}
                className="cursor-pointer"
              >
                <FileText className="mr-2 size-4" />
                <span>{t("hero.importLocal", "从本地文件导入")}</span>
              </DropdownMenuItem>
              <DropdownMenuItem
                disabled
                className="opacity-50 cursor-not-allowed"
              >
                <Figma className="mr-2 size-4" />
                <span>{t("hero.importFigma", "从 Figma 导入 (即将推出)")}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* 右侧操作按钮 */}
        <div className="flex items-center gap-1">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            disabled={isSubmitting}
            className="size-9 rounded-xl hover:bg-accent"
            title={t("hero.voiceInput")}
          >
            <Mic className="size-4" />
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={
              (!value.trim() && attachments.length === 0) ||
              isSubmitting ||
              isUploading
            }
            size="icon"
            className="size-9 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground"
            title={t("hero.send")}
          >
            <ArrowUp className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
