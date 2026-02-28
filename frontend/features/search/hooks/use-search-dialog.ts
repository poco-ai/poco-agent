"use client";

import * as React from "react";

/**
 * Hook for managing global search dialog state and keyboard shortcuts
 * Supports Ctrl+K
 */
export function useSearchDialog() {
  const [isOpen, setIsOpen] = React.useState(false);
  const isMac = React.useMemo(() => {
    if (typeof navigator === "undefined") return false;
    return /Mac|iPhone|iPad|iPod/.test(navigator.platform);
  }, []);
  const searchKey = isMac ? "⌘K" : "Ctrl+K";

  // Keyboard shortcut listener
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      const isShortcut = (isMac ? e.metaKey : e.ctrlKey) && key === "k";
      if (isShortcut) {
        e.preventDefault();
        e.stopPropagation();
        setIsOpen((prev) => !prev);
      }
    };

    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, [isMac]);

  return {
    isSearchOpen: isOpen,
    setIsSearchOpen: setIsOpen,
    searchKey,
  };
}
