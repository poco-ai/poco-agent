"use client";

import * as React from "react";
import { Check } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import type { PresetCapabilityItem } from "@/features/capabilities/presets/lib/preset-types";
import { cn } from "@/lib/utils";

interface CapabilitySelectorProps {
  title: string;
  description: string;
  items: PresetCapabilityItem[];
  selectedIds: number[];
  onChange: (ids: number[]) => void;
  searchPlaceholder: string;
  emptyLabel: string;
}

export function CapabilitySelector({
  title,
  description,
  items,
  selectedIds,
  onChange,
  searchPlaceholder,
  emptyLabel,
}: CapabilitySelectorProps) {
  const [query, setQuery] = React.useState("");
  const selectedIdSet = React.useMemo(() => new Set(selectedIds), [selectedIds]);

  const filteredItems = React.useMemo(() => {
    if (!query.trim()) return items;
    const normalizedQuery = query.trim().toLowerCase();
    return items.filter((item) => {
      return (
        item.name.toLowerCase().includes(normalizedQuery) ||
        (item.description || "").toLowerCase().includes(normalizedQuery) ||
        (item.scope || "").toLowerCase().includes(normalizedQuery)
      );
    });
  }, [items, query]);

  const toggle = React.useCallback(
    (id: number) => {
      if (selectedIdSet.has(id)) {
        onChange(selectedIds.filter((itemId) => itemId !== id));
        return;
      }
      onChange([...selectedIds, id]);
    },
    [onChange, selectedIdSet, selectedIds],
  );

  return (
    <div className="space-y-3 rounded-2xl border border-border/60 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <h4 className="text-sm font-medium text-foreground">{title}</h4>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <Badge variant="secondary">{selectedIds.length}</Badge>
      </div>

      <Input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={searchPlaceholder}
      />

      <div className="max-h-56 space-y-2 overflow-y-auto pr-1">
        {filteredItems.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/60 px-3 py-5 text-center text-sm text-muted-foreground">
            {emptyLabel}
          </div>
        ) : (
          filteredItems.map((item) => {
            const isSelected = selectedIdSet.has(item.id);
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => toggle(item.id)}
                className={cn(
                  "flex w-full items-start gap-3 rounded-xl border px-3 py-3 text-left transition-colors",
                  isSelected
                    ? "border-foreground/20 bg-accent/60"
                    : "border-border/50 bg-card hover:bg-accent/40",
                )}
              >
                <span
                  className={cn(
                    "mt-0.5 flex size-5 items-center justify-center rounded-md border",
                    isSelected
                      ? "border-foreground/20 bg-foreground text-background"
                      : "border-border text-transparent",
                  )}
                >
                  <Check className="size-3.5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-2">
                    <span className="truncate text-sm font-medium text-foreground">
                      {item.name}
                    </span>
                    {item.scope ? (
                      <Badge variant="outline" className="text-[10px]">
                        {item.scope}
                      </Badge>
                    ) : null}
                  </span>
                  {item.description ? (
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {item.description}
                    </span>
                  ) : null}
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
