import { useRef, useState, useEffect } from "react";
import { ArrowUp, Plus, SlidersHorizontal, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n/client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AVAILABLE_CONNECTORS,
  type ConnectorType,
} from "@/features/home/model/connectors";
import { toast } from "sonner";
import { uploadAttachment } from "@/features/attachments/services/attachment-service";
import type { InputFile } from "@/features/chat/types";
import { FileCard } from "@/components/shared/file-card";
import { playFileUploadSound } from "@/lib/utils/sound";
import { useSlashCommandAutocomplete } from "@/features/chat/hooks/use-slash-command-autocomplete";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (attachments?: InputFile[]) => void;
  disabled?: boolean;
  hasMessages?: boolean;
}

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB

export function ChatInput({
  value,
  onChange,
  onSend,
  disabled,
  hasMessages = false,
}: ChatInputProps) {
  const { t } = useT("translation");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isComposing = useRef(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [attachments, setAttachments] = useState<InputFile[]>([]);
  const slashAutocomplete = useSlashCommandAutocomplete({
    value,
    onChange,
    textareaRef,
  });

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashAutocomplete.handleKeyDown(e)) return;
    if (e.key === "Enter" && !e.shiftKey) {
      if (
        e.nativeEvent.isComposing ||
        isComposing.current ||
        e.keyCode === 229
      ) {
        return;
      }
      e.preventDefault();
      if (
        (value.trim() || attachments.length > 0) &&
        !disabled &&
        !isUploading
      ) {
        onSend(attachments);
        setAttachments([]);
      }
    }
  };

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
      toast.error(t("hero.toasts.fileTooLarge"));
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

  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const file = Array.from(items)
      .find((item) => item.kind === "file")
      ?.getAsFile();

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
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      toast.error(t("hero.toasts.fileTooLarge"));
      return;
    }

    try {
      setIsUploading(true);
      const uploadedFile = await uploadAttachment(file);
      setAttachments((prev) => [...prev, uploadedFile]);
      toast.success(t("hero.toasts.uploadSuccess"));
      playFileUploadSound();
    } catch (error) {
      console.error("Upload failed:", error);
      toast.error(t("hero.toasts.uploadFailed"));
    } finally {
      setIsUploading(false);
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="border-t border-border p-4">
      <div className="max-w-4xl mx-auto">
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          onChange={handleFileSelect}
        />
        <div className="rounded-2xl border border-border bg-card shadow-sm">
          {/* Attachments */}
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 px-4 pt-4">
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

          {/* Input area */}
          <div className="relative px-4 pb-3 pt-4">
            {slashAutocomplete.isOpen ? (
              <div className="absolute bottom-full left-0 z-50 mb-2 w-full overflow-hidden rounded-lg border border-border bg-popover shadow-md">
                <div className="max-h-64 overflow-auto py-1">
                  {slashAutocomplete.suggestions.map((item, idx) => {
                    const selected = idx === slashAutocomplete.activeIndex;
                    return (
                      <button
                        key={item.command}
                        type="button"
                        onMouseEnter={() =>
                          slashAutocomplete.setActiveIndex(idx)
                        }
                        onMouseDown={(ev) => {
                          ev.preventDefault();
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
            <Textarea
              ref={textareaRef}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              onPaste={handlePaste}
              onCompositionStart={() => (isComposing.current = true)}
              onCompositionEnd={() => {
                requestAnimationFrame(() => {
                  isComposing.current = false;
                });
              }}
              placeholder={hasMessages ? "" : t("hero.placeholder")}
              disabled={disabled}
              className="min-h-[60px] max-h-[40vh] w-full resize-none border-0 p-0 text-base shadow-none placeholder:text-muted-foreground/50 focus-visible:ring-0"
              rows={1}
            />
          </div>

          {/* Bottom toolbar */}
          <div className="flex items-center justify-between px-3 pb-3">
            {/* Left side buttons */}
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-9 rounded-xl hover:bg-accent"
                title={t("hero.attachFile")}
                disabled={disabled || isUploading}
                onClick={() => fileInputRef.current?.click()}
              >
                {isUploading ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <Plus className="size-4" />
                )}
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-9 rounded-xl hover:bg-accent"
                    title={t("hero.tools")}
                    disabled={disabled}
                  >
                    <SlidersHorizontal className="size-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="start"
                  className="w-56 max-h-64 overflow-y-auto"
                >
                  {(() => {
                    const order: Record<ConnectorType, number> = {
                      mcp: 0,
                      skill: 1,
                      app: 2,
                      api: 3,
                    };
                    const sortedConnectors = [...AVAILABLE_CONNECTORS].sort(
                      (a, b) => (order[a.type] ?? 99) - (order[b.type] ?? 99),
                    );

                    return sortedConnectors.map((connector) => (
                      <DropdownMenuItem
                        key={connector.id}
                        disabled
                        className="opacity-50 cursor-not-allowed"
                      >
                        <div className="flex items-center justify-between w-full">
                          <div className="flex items-center gap-2">
                            <connector.icon className="size-4" />
                            <span>{connector.title}</span>
                          </div>
                          {/* TODO: Implement connection logic */}
                          <span className="text-xs font-medium">连接</span>
                        </div>
                      </DropdownMenuItem>
                    ));
                  })()}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Right side buttons */}
            <div className="flex items-center gap-1">
              <Button
                onClick={() => {
                  onSend(attachments);
                  setAttachments([]);
                }}
                disabled={
                  (!value.trim() && attachments.length === 0) ||
                  disabled ||
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
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Enter {t("hints.send")}，Shift + Enter {t("hints.newLine")}
        </p>
      </div>
    </div>
  );
}
