import {
  useState,
  useCallback,
  useRef,
  useEffect,
  useImperativeHandle,
  forwardRef,
} from "react";
import { SendHorizontal, Plus, Loader2, Pause } from "lucide-react";
import { uploadAttachment } from "@/features/attachments/services/attachment-service";
import type { InputFile } from "@/features/chat/types";
import { toast } from "sonner";
import { FileCard } from "@/components/shared/file-card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n/client";
import { playFileUploadSound } from "@/lib/utils/sound";
import { useSlashCommandAutocomplete } from "@/features/chat/hooks/use-slash-command-autocomplete";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (content: string, attachments?: InputFile[]) => void;
  onCancel?: () => void;
  canCancel?: boolean;
  isCancelling?: boolean;
  disabled?: boolean;
}

export interface ChatInputRef {
  setValueAndFocus: (value: string) => void;
}

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

/**
 * Chat input component with send button
 */
export const ChatInput = forwardRef<ChatInputRef, ChatInputProps>(
  (
    {
      onSend,
      onCancel,
      canCancel = false,
      isCancelling = false,
      disabled = false,
    },
    ref,
  ) => {
    const { t } = useT("translation");
    const [value, setValue] = useState("");
    const [attachments, setAttachments] = useState<InputFile[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Expose methods to parent component
    useImperativeHandle(ref, () => ({
      setValueAndFocus: (newValue: string) => {
        setValue(newValue);
        // Focus textarea, set cursor to end, and adjust height
        setTimeout(() => {
          if (textareaRef.current) {
            textareaRef.current.focus();
            textareaRef.current.setSelectionRange(
              newValue.length,
              newValue.length,
            );
            // Auto-resize textarea for new content
            textareaRef.current.style.height = "auto";
            textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
          }
        }, 0);
      },
    }));

    // Track whether user is composing with IME (Input Method Editor)
    const isComposingRef = useRef(false);

    const slashAutocomplete = useSlashCommandAutocomplete({
      value,
      onChange: setValue,
      textareaRef,
    });

    const handleSend = useCallback(() => {
      if (!value.trim() && attachments.length === 0) return;

      const content = value;
      const currentAttachments = [...attachments];
      setValue(""); // Clear immediately
      setAttachments([]);
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
      onSend(content, currentAttachments);
    }, [value, attachments, onSend]);

    // Reset textarea height when value becomes empty
    useEffect(() => {
      if (!value && textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }, [value]);

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (slashAutocomplete.handleKeyDown(e)) return;
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
      [value, attachments, handleSend, slashAutocomplete],
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

      const normalizedName = file.name.trim().toLowerCase();
      if (
        attachments.some(
          (item) => (item.name || "").trim().toLowerCase() === normalizedName,
        )
      ) {
        toast.error(
          t("hero.toasts.duplicateFileName", {
            name: file.name,
          }),
        );
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        toast.error(t("hero.toasts.fileTooLarge", { size: "100MB" }));
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      try {
        setIsUploading(true);
        const uploadedFile = await uploadAttachment(file);
        setAttachments((prev) => [...prev, uploadedFile]);
        toast.success(t("hero.toasts.uploadSuccess"));
        playFileUploadSound(); // Play sound on successful upload
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
      setAttachments((prev) => prev.filter((_, i) => i !== index));
    };

    const hasDraft = value.trim().length > 0 || attachments.length > 0;
    const showCancel = Boolean(onCancel) && canCancel && !hasDraft;

    return (
      <div className="shrink-0 min-w-0 px-4 pb-4 pt-2">
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          onChange={handleFileSelect}
        />
        {attachments.length > 0 && (
          <div className="mb-2 flex min-w-0 flex-wrap gap-2 px-3">
            {attachments.map((file, i) => (
              <FileCard
                key={i}
                file={file}
                onRemove={() => removeAttachment(i)}
                className="w-full max-w-48 bg-background"
              />
            ))}
          </div>
        )}
        <div className="relative flex w-full min-w-0 items-center gap-2 rounded-lg border border-border bg-card px-3 py-2">
          {slashAutocomplete.isOpen ? (
            <div className="absolute bottom-full left-0 z-50 mb-2 w-full overflow-hidden rounded-lg border border-border bg-popover shadow-md">
              <div className="max-h-64 overflow-auto py-1">
                {slashAutocomplete.suggestions.map((item, idx) => {
                  const selected = idx === slashAutocomplete.activeIndex;
                  return (
                    <button
                      key={item.command}
                      type="button"
                      onMouseEnter={() => slashAutocomplete.setActiveIndex(idx)}
                      onMouseDown={(e) => {
                        // Prevent textarea from losing focus.
                        e.preventDefault();
                        slashAutocomplete.applySelection(idx);
                      }}
                      className={cn(
                        "w-full px-3 py-2 text-left text-sm",
                        selected
                          ? "bg-accent text-accent-foreground"
                          : "hover:bg-accent/50",
                      )}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-mono">{item.command}</span>
                        {item.argument_hint ? (
                          <span className="text-xs text-muted-foreground font-mono truncate">
                            {item.argument_hint}
                          </span>
                        ) : null}
                      </div>
                      {item.description ? (
                        <div className="text-xs text-muted-foreground truncate">
                          {item.description}
                        </div>
                      ) : null}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}

          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                disabled={disabled || isUploading}
                onClick={() => fileInputRef.current?.click()}
                className="flex-shrink-0 flex items-center justify-center size-8 rounded-md hover:bg-accent text-muted-foreground transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                aria-label={t("hero.importLocal")}
              >
                {isUploading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Plus className="size-4" />
                )}
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" sideOffset={8}>
              {t("hero.importLocal")}
            </TooltipContent>
          </Tooltip>

          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onCompositionStart={handleCompositionStart}
            onCompositionEnd={handleCompositionEnd}
            placeholder={t("chat.inputPlaceholder")}
            disabled={disabled}
            rows={1}
            className="flex-1 min-w-0 bg-transparent text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 resize-none overflow-y-auto py-1 scrollbar-hide"
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
          {showCancel ? (
            <button
              type="button"
              onClick={onCancel}
              disabled={isCancelling}
              className="flex-shrink-0 flex items-center justify-center size-8 rounded-md bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors disabled:cursor-not-allowed disabled:opacity-60"
              aria-label={t("chatInput.cancelTask")}
              title={t("chatInput.cancelTask")}
            >
              {isCancelling ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Pause className="size-4" />
              )}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSend}
              disabled={!hasDraft || disabled}
              className="flex-shrink-0 flex items-center justify-center size-8 rounded-md bg-foreground text-background hover:bg-foreground/90 disabled:bg-muted disabled:text-muted-foreground transition-colors disabled:cursor-not-allowed disabled:opacity-50"
              aria-label={t("hero.send")}
              title={t("hero.send")}
            >
              <SendHorizontal className="size-4" />
            </button>
          )}
        </div>
      </div>
    );
  },
);
ChatInput.displayName = "ChatInput";
