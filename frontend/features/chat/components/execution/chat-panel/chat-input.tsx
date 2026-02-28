import {
  useState,
  useCallback,
  useRef,
  useEffect,
  useImperativeHandle,
  forwardRef,
} from "react";
import { ArrowUp, Plus, Loader2, Pause, Mic, MicOff } from "lucide-react";
import SpeechRecognition, {
  useSpeechRecognition,
} from "react-speech-recognition";
import { uploadAttachment } from "@/features/attachments/api/attachment-api";
import type { InputFile } from "@/features/chat/types";
import { toast } from "sonner";
import { FileCard } from "@/components/shared/file-card";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useT } from "@/lib/i18n/client";
import { playUploadSound } from "@/lib/utils/sound";
import { useSlashCommandAutocomplete } from "@/features/chat/hooks/use-slash-command-autocomplete";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (content: string, attachments?: InputFile[]) => void;
  onCancel?: () => void;
  canCancel?: boolean;
  isCancelling?: boolean;
  disabled?: boolean;
  history?: string[];
  className?: string;
}

export interface ChatInputRef {
  setValueAndFocus: (value: string) => void;
  appendValueAndFocus: (value: string) => void;
}

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const MANUAL_EDIT_PAUSE_MS = 1000;

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
      history = [],
      className,
    },
    ref,
  ) => {
    const { t } = useT("translation");
    const [value, setValue] = useState("");
    const [attachments, setAttachments] = useState<InputFile[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const [historyIndex, setHistoryIndex] = useState(-1);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);
    const dictationBaseRef = useRef("");
    const isDictatingRef = useRef(false);
    const isSpeechUpdateRef = useRef(false);
    const manualEditUntilRef = useRef(0);
    const [hasVoiceSupport, setHasVoiceSupport] = useState(false);

    const syncTextareaValue = useCallback((nextValue: string) => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      textarea.focus();
      textarea.setSelectionRange(nextValue.length, nextValue.length);
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
    }, []);

    const applyValue = useCallback(
      (nextValue: string) => {
        setValue(nextValue);
        requestAnimationFrame(() => {
          syncTextareaValue(nextValue);
        });
      },
      [syncTextareaValue],
    );

    const appendValue = useCallback(
      (nextValue: string) => {
        const trimmedValue = nextValue.trim();
        if (!trimmedValue) return;

        const separator = value.trim()
          ? value.endsWith("\n")
            ? "\n"
            : "\n\n"
          : "";
        applyValue(`${value}${separator}${trimmedValue}\n`);
      },
      [applyValue, value],
    );

    // Expose methods to parent component
    useImperativeHandle(ref, () => ({
      setValueAndFocus: (newValue: string) => {
        setHistoryIndex(-1);
        applyValue(newValue);
      },
      appendValueAndFocus: (newValue: string) => {
        setHistoryIndex(-1);
        appendValue(newValue);
      },
    }));

    // Track whether user is composing with IME (Input Method Editor)
    const isComposingRef = useRef(false);

    const slashAutocomplete = useSlashCommandAutocomplete({
      value,
      onChange: setValue,
      textareaRef,
    });

    const {
      interimTranscript,
      finalTranscript,
      listening,
      resetTranscript,
      browserSupportsSpeechRecognition,
    } = useSpeechRecognition();

    useEffect(() => {
      if (browserSupportsSpeechRecognition && !hasVoiceSupport) {
        setHasVoiceSupport(true);
      }
    }, [browserSupportsSpeechRecognition, hasVoiceSupport]);

    // Keep voice transcript synchronized with current input while dictating.
    useEffect(() => {
      if (!isDictatingRef.current) {
        return;
      }

      if (!listening) {
        isDictatingRef.current = false;
        isSpeechUpdateRef.current = false;
        return;
      }

      if (manualEditUntilRef.current > Date.now()) {
        return;
      }

      const liveTranscript = [finalTranscript, interimTranscript]
        .filter(Boolean)
        .join(" ");
      const base = dictationBaseRef.current;
      const separator = base && liveTranscript && !/\s$/.test(base) ? " " : "";
      const nextValue = `${base}${separator}${liveTranscript}`;

      if (nextValue !== value) {
        isSpeechUpdateRef.current = true;
        applyValue(nextValue);
        isSpeechUpdateRef.current = false;
      }
    }, [applyValue, finalTranscript, interimTranscript, listening, value]);

    // Reset speech state after message has been sent and cleared.
    useEffect(() => {
      if (!value && !listening) {
        resetTranscript();
        dictationBaseRef.current = "";
        isDictatingRef.current = false;
        isSpeechUpdateRef.current = false;
      }
    }, [listening, resetTranscript, value]);

    const handleToggleVoiceInput = useCallback(async () => {
      if (!browserSupportsSpeechRecognition) {
        toast.error(t("hero.toasts.voiceInputNotSupported"));
        return;
      }

      try {
        if (listening) {
          await SpeechRecognition.stopListening();
          return;
        }

        dictationBaseRef.current = value;
        isDictatingRef.current = true;
        manualEditUntilRef.current = 0;
        resetTranscript();
        await SpeechRecognition.startListening({ continuous: true });

        requestAnimationFrame(() => {
          const textarea = textareaRef.current;
          if (!textarea) return;
          textarea.focus();
          const end = textarea.value.length;
          textarea.setSelectionRange(end, end);
        });
      } catch (error) {
        console.error("Speech recognition failed:", error);
        toast.error(t("hero.toasts.voiceInputFailed"));
      }
    }, [
      browserSupportsSpeechRecognition,
      listening,
      resetTranscript,
      t,
      value,
    ]);

    const handleSend = useCallback(() => {
      if (!value.trim() && attachments.length === 0) return;

      const content = value;
      const currentAttachments = [...attachments];
      if (listening) {
        void SpeechRecognition.stopListening();
      }
      resetTranscript();
      dictationBaseRef.current = "";
      isDictatingRef.current = false;
      isSpeechUpdateRef.current = false;
      manualEditUntilRef.current = 0;
      setHistoryIndex(-1);
      setValue(""); // Clear immediately
      setAttachments([]);
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
      onSend(content, currentAttachments);
    }, [value, attachments, listening, onSend, resetTranscript]);

    // Reset textarea height when value becomes empty
    useEffect(() => {
      if (!value && textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }, [value]);

    useEffect(() => {
      if (historyIndex !== -1 && historyIndex >= history.length) {
        setHistoryIndex(-1);
      }
    }, [history, historyIndex]);

    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (slashAutocomplete.handleKeyDown(e)) return;
        if (listening && isDictatingRef.current && e.key !== "Enter") {
          manualEditUntilRef.current = Date.now() + MANUAL_EDIT_PAUSE_MS;
        }
        if (
          disabled ||
          isComposingRef.current ||
          e.nativeEvent.isComposing ||
          e.altKey ||
          e.ctrlKey ||
          e.metaKey ||
          e.shiftKey
        ) {
          return;
        }
        if (e.key === "ArrowUp" || e.key === "ArrowDown") {
          if (history.length === 0) return;
          if (e.key === "ArrowUp") {
            e.preventDefault();
            const nextIndex =
              historyIndex === -1
                ? history.length - 1
                : Math.max(0, historyIndex - 1);
            setHistoryIndex(nextIndex);
            applyValue(history[nextIndex] ?? "");
            return;
          }
          if (e.key === "ArrowDown") {
            if (historyIndex === -1) return;
            e.preventDefault();
            const nextIndex =
              historyIndex >= history.length - 1 ? -1 : historyIndex + 1;
            setHistoryIndex(nextIndex);
            applyValue(nextIndex === -1 ? "" : (history[nextIndex] ?? ""));
            return;
          }
        }
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
      [
        value,
        attachments,
        handleSend,
        slashAutocomplete,
        disabled,
        listening,
        historyIndex,
        history,
        applyValue,
      ],
    );

    const handleCompositionStart = useCallback(() => {
      isComposingRef.current = true;
    }, []);

    const handleCompositionEnd = useCallback(() => {
      requestAnimationFrame(() => {
        isComposingRef.current = false;
      });
    }, []);

    const handleInputChange = useCallback(
      (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        const nextValue = e.target.value;
        if (isDictatingRef.current && !isSpeechUpdateRef.current) {
          dictationBaseRef.current = nextValue;
          manualEditUntilRef.current = Date.now() + MANUAL_EDIT_PAUSE_MS;
          if (listening) {
            resetTranscript();
          }
        }

        setValue(nextValue);
        if (historyIndex !== -1) {
          setHistoryIndex(-1);
        }
      },
      [historyIndex, listening, resetTranscript],
    );

    const handleInputFocus = useCallback(() => {
      if (isDictatingRef.current) {
        manualEditUntilRef.current = Date.now() + MANUAL_EDIT_PAUSE_MS;
      }
    }, []);

    const handleInputClick = useCallback(() => {
      if (isDictatingRef.current) {
        manualEditUntilRef.current = Date.now() + MANUAL_EDIT_PAUSE_MS;
      }
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
        playUploadSound();
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
      <div className={cn("shrink-0 min-w-0 px-4 pb-4 pt-2", className)}>
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
                      <span className="font-mono">{item.command}</span>
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
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={handleInputFocus}
            onClick={handleInputClick}
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
              className="flex-shrink-0 flex items-center justify-center size-8 rounded-md bg-muted text-foreground hover:bg-muted/80 transition-colors disabled:cursor-not-allowed disabled:opacity-60"
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
            <>
              {hasVoiceSupport ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      type="button"
                      onClick={() => {
                        void handleToggleVoiceInput();
                      }}
                      disabled={disabled || isUploading}
                      className={cn(
                        "flex-shrink-0 flex items-center justify-center size-8 rounded-md transition-colors disabled:cursor-not-allowed disabled:opacity-50",
                        listening
                          ? "bg-destructive text-destructive-foreground hover:bg-destructive/90 animate-pulse"
                          : "hover:bg-accent text-muted-foreground",
                      )}
                      aria-label={
                        listening
                          ? t("hero.stopVoiceInput")
                          : t("hero.startVoiceInput")
                      }
                    >
                      {listening ? (
                        <MicOff className="size-4" />
                      ) : (
                        <Mic className="size-4" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" sideOffset={8}>
                    {listening
                      ? t("hero.stopVoiceInput")
                      : t("hero.startVoiceInput")}
                  </TooltipContent>
                </Tooltip>
              ) : null}
              <button
                type="button"
                onClick={handleSend}
                disabled={!hasDraft || disabled}
                className="flex-shrink-0 flex items-center justify-center size-8 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                aria-label={t("hero.send")}
                title={t("hero.send")}
              >
                <ArrowUp className="size-4" />
              </button>
            </>
          )}
        </div>
      </div>
    );
  },
);
ChatInput.displayName = "ChatInput";
