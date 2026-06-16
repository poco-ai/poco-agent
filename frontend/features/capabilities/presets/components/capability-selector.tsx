"use client";

import * as React from "react";
import { Check, CheckCheck, X } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { PresetCapabilityItem } from "@/features/capabilities/presets/lib/preset-types";
import type { SourceInfo } from "@/features/capabilities/types/source";
import { formatSourceLabel } from "@/features/capabilities/utils/source";
import { useT } from "@/lib/i18n/client";
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

interface CapabilityGroup {
  key: string;
  title: string;
  source: SourceInfo | null;
  items: PresetCapabilityItem[];
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
  const { t } = useT("translation");
  const [query, setQuery] = React.useState("");
  const selectedIdSet = React.useMemo(
    () => new Set(selectedIds),
    [selectedIds],
  );

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

  const groups = React.useMemo<CapabilityGroup[]>(() => {
    if (!filteredItems.some((item) => item.source)) {
      return [
        {
          key: "all",
          title,
          source: null,
          items: filteredItems,
        },
      ];
    }

    const nextGroups = new Map<string, CapabilityGroup>();

    for (const item of filteredItems) {
      const sourceKind = item.source?.kind ?? "unknown";
      const sourceLabel = formatSourceLabel(item.source, t);
      const sourceRepo = item.source?.repo?.trim();
      const groupTitle =
        sourceKind === "github"
          ? sourceRepo
            ? sourceRepo
            : sourceLabel
          : sourceLabel;
      const key = [
        sourceKind,
        item.source?.repo?.trim().toLowerCase() ?? "",
        item.source?.url?.trim().toLowerCase() ?? "",
        item.source?.ref?.trim().toLowerCase() ?? "",
        item.source?.filename?.trim().toLowerCase() ?? "",
        item.source?.market?.trim().toLowerCase() ?? "",
        sourceLabel.trim().toLowerCase(),
      ].join("|");

      const existingGroup = nextGroups.get(key);
      if (existingGroup) {
        existingGroup.items.push(item);
        continue;
      }

      nextGroups.set(key, {
        key,
        title: groupTitle,
        source: item.source ?? null,
        items: [item],
      });
    }

    return Array.from(nextGroups.values())
      .map((group) => ({
        ...group,
        items: [...group.items].sort((left, right) =>
          left.name.localeCompare(right.name),
        ),
      }))
      .sort((left, right) => left.title.localeCompare(right.title));
  }, [filteredItems, t, title]);

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

  const setGroupSelected = React.useCallback(
    (groupItems: PresetCapabilityItem[], selected: boolean) => {
      const groupIdSet = new Set(groupItems.map((item) => item.id));
      if (selected) {
        onChange(Array.from(new Set([...selectedIds, ...groupIdSet])));
        return;
      }
      onChange(selectedIds.filter((id) => !groupIdSet.has(id)));
    },
    [onChange, selectedIds],
  );

  const renderItem = (item: PresetCapabilityItem) => {
    const isSelected = selectedIdSet.has(item.id);
    return (
      <button
        key={item.id}
        type="button"
        onClick={() => toggle(item.id)}
        className={cn(
          "flex min-w-0 w-full items-start gap-3 overflow-hidden rounded-xl border px-3 py-3 text-left transition-colors",
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
        <div className="min-w-0 flex-1 overflow-hidden">
          <div className="flex min-w-0 items-center gap-2 overflow-hidden">
            <div className="min-w-0 truncate text-sm font-medium text-foreground">
              {item.name}
            </div>
            {item.scope ? (
              <Badge variant="outline" className="shrink-0 text-[10px]">
                {item.scope}
              </Badge>
            ) : null}
          </div>
          {item.description ? (
            <div className="mt-1 max-w-full overflow-hidden text-xs text-muted-foreground line-clamp-3 break-all">
              {item.description}
            </div>
          ) : null}
        </div>
      </button>
    );
  };

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
          groups.map((group) => {
            const selectedCount = group.items.filter((item) =>
              selectedIdSet.has(item.id),
            ).length;
            const allSelected = selectedCount === group.items.length;
            const groupActionLabel = allSelected
              ? t("library.presetsPage.selectors.clearGroup")
              : t("library.presetsPage.selectors.selectGroup");
            const showGroupHeader = groups.length > 1 || group.source;

            return (
              <div key={group.key} className="space-y-2">
                {showGroupHeader ? (
                  <div className="flex min-w-0 items-center justify-between gap-3 px-1 pt-1">
                    <div className="min-w-0">
                      <div className="truncate text-xs font-medium text-foreground">
                        {group.title}
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        {selectedCount}/{group.items.length}
                      </div>
                    </div>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="size-7 shrink-0 rounded-md text-muted-foreground hover:text-foreground"
                          onClick={() =>
                            setGroupSelected(group.items, !allSelected)
                          }
                          aria-label={groupActionLabel}
                          title={groupActionLabel}
                        >
                          {allSelected ? (
                            <X className="size-3.5" />
                          ) : (
                            <CheckCheck className="size-3.5" />
                          )}
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent side="left">
                        {groupActionLabel}
                      </TooltipContent>
                    </Tooltip>
                  </div>
                ) : null}
                <div className="space-y-2">{group.items.map(renderItem)}</div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
