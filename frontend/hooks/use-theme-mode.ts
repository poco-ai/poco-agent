"use client";

import * as React from "react";
import { useTheme } from "next-themes";

export type ThemeMode = "light" | "dark";

const resolveThemeMode = (
  theme: string | undefined,
  resolvedTheme: string | undefined,
): ThemeMode => {
  if (theme === "light" || theme === "dark") return theme;
  if (resolvedTheme === "light" || resolvedTheme === "dark")
    return resolvedTheme;
  return "dark";
};

export function useThemeMode() {
  const { theme, resolvedTheme, setTheme } = useTheme();

  const mode = React.useMemo(
    () => resolveThemeMode(theme, resolvedTheme),
    [theme, resolvedTheme],
  );

  const setMode = React.useCallback(
    (nextMode: ThemeMode) => setTheme(nextMode),
    [setTheme],
  );

  return {
    theme,
    resolvedTheme,
    mode,
    setMode,
  };
}
