"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";

import {
  slashCommandsService,
  SLASH_COMMAND_SUGGESTIONS_INVALIDATED_EVENT,
} from "@/features/capabilities/slash-commands/services/slash-commands-service";
import type { SlashCommandSuggestion as BackendSlashCommandSuggestion } from "@/features/capabilities/slash-commands/types";

export type SlashCommandSuggestionSource = "builtin" | "custom" | "skill";

export interface SlashCommandSuggestion {
  command: string;
  name: string;
  description?: string | null;
  argument_hint?: string | null;
  source: SlashCommandSuggestionSource;
}

type TokenInfo = {
  token: string;
  start: number;
  end: number;
  hasArgs: boolean;
};

function extractToken(value: string): TokenInfo | null {
  const leading = value.match(/^\s*/)?.[0].length ?? 0;
  if (value.slice(leading, leading + 1) !== "/") return null;

  let end = leading;
  while (end < value.length && !/\s/.test(value[end] || "")) {
    end += 1;
  }
  const token = value.slice(leading, end);
  if (!token.startsWith("/")) return null;

  const hasArgs = end < value.length && /\s/.test(value[end] || "");
  return { token, start: leading, end, hasArgs };
}

type UseSlashCommandAutocompleteParams = {
  value: string;
  onChange: (next: string) => void;
  textareaRef?: RefObject<HTMLTextAreaElement | null>;
};

export function useSlashCommandAutocomplete({
  value,
  onChange,
  textareaRef,
}: UseSlashCommandAutocompleteParams) {
  const [dynamicSuggestions, setDynamicSuggestions] = useState<
    BackendSlashCommandSuggestion[]
  >([]);
  const isMountedRef = useRef(true);
  const [dismissedToken, setDismissedToken] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const loadSuggestions = useCallback(async (forceFresh = false) => {
    try {
      const list = await slashCommandsService.listSuggestions({
        revalidate: 0,
        cacheBust: forceFresh ? Date.now() : undefined,
      });
      if (!isMountedRef.current) return;
      setDynamicSuggestions(list);
    } catch (error) {
      // Autocomplete should be best-effort and never break chat input showing/sending.
      console.warn("[SlashCommands] autocomplete list failed:", error);
    }
  }, []);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadSuggestions(true);
    }, 0);
    return () => {
      window.clearTimeout(timer);
    };
  }, [loadSuggestions]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const handleSuggestionsInvalidated = () => {
      void loadSuggestions(true);
    };

    window.addEventListener(
      SLASH_COMMAND_SUGGESTIONS_INVALIDATED_EVENT,
      handleSuggestionsInvalidated,
    );
    return () => {
      window.removeEventListener(
        SLASH_COMMAND_SUGGESTIONS_INVALIDATED_EVENT,
        handleSuggestionsInvalidated,
      );
    };
  }, [loadSuggestions]);

  const tokenInfo = useMemo(() => extractToken(value), [value]);

  const suggestions: SlashCommandSuggestion[] = useMemo(() => {
    const mappedDynamic: SlashCommandSuggestion[] = dynamicSuggestions.map(
      (item) => ({
        command: `/${item.name}`,
        name: item.name,
        description: item.description,
        argument_hint: item.argument_hint,
        source: item.source,
      }),
    );

    const merged = [...mappedDynamic];
    const unique = new Map<string, SlashCommandSuggestion>();
    for (const item of merged) {
      unique.set(item.command, item);
    }
    return Array.from(unique.values()).sort((a, b) =>
      a.command.localeCompare(b.command),
    );
  }, [dynamicSuggestions]);

  const filtered = useMemo(() => {
    if (!tokenInfo) return [];
    if (tokenInfo.hasArgs) return [];
    const prefix = tokenInfo.token.toLowerCase();
    return suggestions.filter((s) =>
      s.command.toLowerCase().startsWith(prefix),
    );
  }, [suggestions, tokenInfo]);

  const normalizedActiveIndex = useMemo(() => {
    if (filtered.length <= 0) return 0;
    return (
      ((activeIndex % filtered.length) + filtered.length) % filtered.length
    );
  }, [activeIndex, filtered.length]);

  const isExactSingleMatch = useMemo(() => {
    if (!tokenInfo) return false;
    const trimmed = value.trim();
    return filtered.length === 1 && filtered[0]?.command === trimmed;
  }, [filtered, tokenInfo, value]);

  const isOpen = Boolean(
    tokenInfo &&
    !tokenInfo.hasArgs &&
    tokenInfo.token.length >= 1 &&
    filtered.length > 0 &&
    dismissedToken !== tokenInfo.token &&
    !isExactSingleMatch,
  );

  const applySelection = useCallback(
    (index: number) => {
      if (!tokenInfo) return;
      const item = filtered[index];
      if (!item) return;

      const before = value.slice(0, tokenInfo.start);
      const after = value.slice(tokenInfo.end);
      const insertSpace = tokenInfo.end === value.length ? " " : "";
      const next = `${before}${item.command}${insertSpace}${after}`;
      onChange(next);
      setDismissedToken(item.command);

      if (textareaRef?.current) {
        const cursorPos = (before + item.command + insertSpace).length;
        requestAnimationFrame(() => {
          textareaRef.current?.focus();
          textareaRef.current?.setSelectionRange(cursorPos, cursorPos);
        });
      }
    },
    [filtered, onChange, textareaRef, tokenInfo, value],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>): boolean => {
      if (!isOpen) return false;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % filtered.length);
        return true;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex(
          (prev) => (prev - 1 + filtered.length) % filtered.length,
        );
        return true;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        if (tokenInfo) setDismissedToken(tokenInfo.token);
        return true;
      }
      if (e.key === "Tab") {
        e.preventDefault();
        applySelection(normalizedActiveIndex);
        return true;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        // Only autocomplete on Enter when the current token isn't already an exact match.
        const trimmed = value.trim();
        const isExact = filtered.some((s) => s.command === trimmed);
        if (!isExact) {
          e.preventDefault();
          applySelection(normalizedActiveIndex);
          return true;
        }
      }

      return false;
    },
    [applySelection, filtered, isOpen, normalizedActiveIndex, tokenInfo, value],
  );

  return {
    isOpen,
    tokenInfo,
    suggestions: filtered,
    activeIndex: normalizedActiveIndex,
    setActiveIndex,
    applySelection,
    handleKeyDown,
    dismiss: () => {
      if (tokenInfo) setDismissedToken(tokenInfo.token);
    },
  };
}
