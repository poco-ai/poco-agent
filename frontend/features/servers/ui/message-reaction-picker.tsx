"use client";

import * as React from "react";

import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

const DEFAULT_REACTIONS = ["👍", "✅", "👀", "❤️", "🎉", "🚀"];

export function MessageReactionPicker({
  open,
  onOpenChange,
  onSelect,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (emoji: string) => void;
}) {
  const { t } = useT("translation");
  const panelRef = React.useRef<HTMLDivElement | null>(null);

  React.useEffect(() => {
    if (!open) {
      return undefined;
    }
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (target instanceof Node && panelRef.current?.contains(target)) {
        return;
      }
      onOpenChange(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onOpenChange(false);
      }
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onOpenChange, open]);

  if (!open) {
    return null;
  }

  return (
    <div
      ref={panelRef}
      className="absolute right-0 top-full z-40 mt-2 grid w-max grid-cols-[repeat(6,2rem)] gap-1 rounded-md border border-secondary bg-background p-2 shadow-[var(--shadow-lg)]"
      role="menu"
      aria-label={t("conversationView.reactions.pickerLabel")}
    >
      {DEFAULT_REACTIONS.map((emoji) => (
        <button
          key={emoji}
          type="button"
          onClick={() => {
            onSelect(emoji);
            onOpenChange(false);
          }}
          aria-label={t("conversationView.reactions.addEmoji", { emoji })}
          title={t("conversationView.reactions.addEmoji", { emoji })}
          className={cn(
            "flex size-8 items-center justify-center rounded-md text-base transition-colors",
            "hover:bg-secondary focus-visible:bg-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          )}
          role="menuitem"
        >
          {emoji}
        </button>
      ))}
    </div>
  );
}
