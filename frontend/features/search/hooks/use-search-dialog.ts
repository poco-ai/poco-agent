"use client";

import * as React from "react";

/**
 * Hook for managing global search dialog state and keyboard shortcuts
 * Supports Ctrl+K
 */
export function useSearchDialog() {
  const [isOpen, setIsOpen] = React.useState(false);
  const searchKey = "Ctrl+K";

  // Keyboard shortcut listener
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "k") {
        e.preventDefault();
        e.stopPropagation();
        setIsOpen((prev) => !prev);
      }
    };

    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, []);

  return {
    isSearchOpen: isOpen,
    setIsSearchOpen: setIsOpen,
    searchKey,
  };
}
