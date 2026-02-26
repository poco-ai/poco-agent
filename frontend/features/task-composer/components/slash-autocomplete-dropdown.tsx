"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SlashSuggestion {
  command: string;
  description?: string | null;
  argument_hint?: string | null;
}

interface SlashAutocompleteDropdownProps {
  isOpen: boolean;
  suggestions: SlashSuggestion[];
  activeIndex: number;
  onHover: (index: number) => void;
  onSelect: (index: number) => void;
}

/**
 * Floating dropdown for slash-command autocomplete suggestions.
 */
export function SlashAutocompleteDropdown({
  isOpen,
  suggestions,
  activeIndex,
  onHover,
  onSelect,
}: SlashAutocompleteDropdownProps) {
  if (!isOpen) return null;

  return (
    <div className="absolute bottom-full left-0 z-50 mb-2 w-full overflow-hidden rounded-lg border border-border bg-popover shadow-md">
      <div className="max-h-64 overflow-auto py-1">
        {suggestions.map((item, idx) => {
          const selected = idx === activeIndex;
          return (
            <button
              key={item.command}
              type="button"
              onMouseEnter={() => onHover(idx)}
              onMouseDown={(ev) => {
                ev.preventDefault();
                onSelect(idx);
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
  );
}
