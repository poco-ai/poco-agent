import { useCallback, useEffect, useState } from "react";
import type { SettingsTabRequest, SettingsTabId } from "@/features/settings";

interface UseSettingsShortcutResult {
  isSettingsOpen: boolean;
  setIsSettingsOpen: React.Dispatch<React.SetStateAction<boolean>>;
  settingsTabRequest: SettingsTabRequest | null;
  openSettings: (tab?: SettingsTabId) => void;
  handleSettingsOpenChange: (nextOpen: boolean) => void;
}

/**
 * Hook to manage settings dialog state and keyboard shortcut (Ctrl+,).
 */
export function useSettingsShortcut(): UseSettingsShortcutResult {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTabRequest, setSettingsTabRequest] =
    useState<SettingsTabRequest | null>(null);

  const openSettings = useCallback((tab?: SettingsTabId) => {
    if (tab) {
      setSettingsTabRequest({ tab, requestId: Date.now() });
    } else {
      setSettingsTabRequest(null);
    }
    setIsSettingsOpen(true);
  }, []);

  const toggleSettingsByHotkey = useCallback(() => {
    setIsSettingsOpen((prev) => {
      const next = !prev;
      if (!next) {
        setSettingsTabRequest(null);
      }
      return next;
    });
  }, []);

  const handleSettingsOpenChange = useCallback((nextOpen: boolean) => {
    setIsSettingsOpen(nextOpen);
    if (!nextOpen) {
      setSettingsTabRequest(null);
    }
  }, []);

  useEffect(() => {
    const handleOpenSettingsShortcut = (event: KeyboardEvent) => {
      if (!event.ctrlKey) return;
      if (!(event.key === "," || event.code === "Comma")) return;
      event.preventDefault();
      event.stopPropagation();
      toggleSettingsByHotkey();
    };

    window.addEventListener("keydown", handleOpenSettingsShortcut, true);
    return () => {
      window.removeEventListener("keydown", handleOpenSettingsShortcut, true);
    };
  }, [toggleSettingsByHotkey]);

  return {
    isSettingsOpen,
    setIsSettingsOpen,
    settingsTabRequest,
    openSettings,
    handleSettingsOpenChange,
  };
}
