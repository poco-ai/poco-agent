import { useState, useCallback, useRef } from "react";
import { SendHorizontal, Plus, Loader2, FileText, Figma } from "lucide-react";
import { uploadAttachment } from "@/features/attachments/services/attachment-service";
import type { InputFile } from "@/features/chat/types";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { FileCard } from "@/components/shared/file-card";
import { useT } from "@/lib/i18n/client";
import { playFileUploadSound } from "@/lib/utils/sound";

interface ChatInputProps {
  onSend: (content: string, attachments?: InputFile[]) => void;
  disabled?: boolean;
}

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

/**
 * Chat input component with send button
 */
export function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const { t } = useT("translation");
  const [value, setValue] = useState("");
  const [attachments, setAttachments] = useState<InputFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Track whether user is composing with IME (Input Method Editor)
  const isComposingRef = useRef(false);

  const handleSend = useCallback(() => {
    if (!value.trim() && attachments.length === 0) return;

    const content = value;
    const currentAttachments = [...attachments];
    setValue(""); // Clear immediately
    setAttachments([]);
    onSend(content, currentAttachments);
  }, [value, attachments, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Only send on Enter if not composing (IME input in progress)
      if (e.key === "Enter") {
        if (e.shiftKey) {
          // Allow default behavior for newline
          return;
        }
        if (
          (value.trim() || attachments.length > 0) &&
          !isComposingRef.current &&
          !e.nativeEvent.isComposing &&
          e.keyCode !== 229
        ) {
          e.preventDefault();
          handleSend();
        }
      }
    },
    [value, attachments, handleSend],
  );

  const handleCompositionStart = useCallback(() => {
    isComposingRef.current = true;
  }, []);

  const handleCompositionEnd = useCallback(() => {
    requestAnimationFrame(() => {
      isComposingRef.current = false;
    });
  }, []);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > MAX_FILE_SIZE) {
      toast.error(`文件过大，最大支持 100MB`);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    try {
      setIsUploading(true);
      const uploadedFile = await uploadAttachment(file);
      setAttachments((prev) => [...prev, uploadedFile]);
      toast.success("文件上传成功");
      playFileUploadSound(); // Play sound on successful upload
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error("文件上传失败");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="shrink-0 px-4 pb-4 pt-2">
      <input
        type="file"
        ref={fileInputRef}
        className="hidden"
        onChange={handleFileSelect}
      />
      {attachments.length > 0 && (
        <div className="flex flex-wrap gap-2 px-3 mb-2">
          {attachments.map((file, i) => (
            <FileCard
              key={i}
              file={file}
              onRemove={() => removeAttachment(i)}
              className="w-48 bg-background"
            />
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              disabled={disabled || isUploading}
              className="flex-shrink-0 flex items-center justify-center size-8 rounded-md hover:bg-muted text-muted-foreground transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isUploading ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Plus className="size-4" />
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuItem
              onClick={() => fileInputRef.current?.click()}
              className="cursor-pointer"
            >
              <FileText className="mr-2 size-4" />
              <span>从本地文件导入</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              disabled
              className="opacity-50 cursor-not-allowed"
            >
              <Figma className="mr-2 size-4" />
              <span>从 Figma 导入 (即将推出)</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onCompositionStart={handleCompositionStart}
          onCompositionEnd={handleCompositionEnd}
          placeholder={t("chat.inputPlaceholder")}
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 resize-none overflow-hidden py-1"
          style={{
            minHeight: "2rem",
            maxHeight: "10rem",
            lineHeight: "1.5rem",
          }}
          onInput={(e) => {
            // Auto-resize textarea
            const target = e.target as HTMLTextAreaElement;
            target.style.height = "auto";
            target.style.height = `${Math.min(target.scrollHeight, 160)}px`;
          }}
        />
        <button
          onClick={handleSend}
          disabled={(!value.trim() && attachments.length === 0) || disabled}
          className="flex-shrink-0 flex items-center justify-center size-8 rounded-md bg-foreground text-background hover:bg-foreground/90 disabled:bg-muted disabled:text-muted-foreground transition-colors disabled:cursor-not-allowed disabled:opacity-50"
        >
          <SendHorizontal className="size-4" />
        </button>
      </div>
    </div>
  );
}
