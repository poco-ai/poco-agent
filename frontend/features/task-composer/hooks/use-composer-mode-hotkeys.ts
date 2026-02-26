"use client";

import * as React from "react";

import type { ComposerMode } from "@/features/task-composer/types";
import { getNextComposerMode } from "@/features/task-composer/lib/mode-utils";

interface UseComposerModeHotkeysOptions {
  textareaRef: React.RefObject<HTMLTextAreaElement | null>;
  setMode: React.Dispatch<React.SetStateAction<ComposerMode>>;
  enabled?: boolean;
}

/**
 * Adds Shift+Tab support for cycling through composer modes while the main textarea is focused.
 * Keeps behavior scoped so we do not interfere with keyboard navigation elsewhere in the app.
 */
export function useComposerModeHotkeys({
  textareaRef,
  setMode,
  enabled = true,
}: UseComposerModeHotkeysOptions) {
  React.useEffect(() => {
    if (!enabled) return;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!event.shiftKey || event.key !== "Tab") return;
      const textarea = textareaRef.current;
      if (!textarea) return;
      if (document.activeElement !== textarea) return;
      event.preventDefault();
      event.stopPropagation();
      setMode((prev) => getNextComposerMode(prev));
    };

    window.addEventListener("keydown", handleKeyDown, true);
    return () => {
      window.removeEventListener("keydown", handleKeyDown, true);
    };
  }, [enabled, setMode, textareaRef]);
}
