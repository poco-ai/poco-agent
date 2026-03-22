"use client";

import { CheckCircle2, Server, Sparkles, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { CapabilityRecommendation } from "@/features/task-composer/types/capability-recommendation";
import { useT } from "@/lib/i18n/client";

interface CapabilityRecommendationsProps {
  recommendations: CapabilityRecommendation[];
  selectedItems: CapabilityRecommendation[];
  isLoading: boolean;
  showEmptyState: boolean;
  onApply: (item: CapabilityRecommendation) => void;
  onRemove: (item: CapabilityRecommendation) => void;
}

function CapabilityTypeIcon({
  type,
}: {
  type: CapabilityRecommendation["type"];
}) {
  if (type === "mcp") {
    return <Server className="size-4 text-primary" />;
  }
  return <Sparkles className="size-4 text-primary" />;
}

export function CapabilityRecommendations({
  recommendations,
  selectedItems,
  isLoading,
  showEmptyState,
  onApply,
  onRemove,
}: CapabilityRecommendationsProps) {
  const { t } = useT("translation");

  if (
    !isLoading &&
    recommendations.length === 0 &&
    selectedItems.length === 0 &&
    !showEmptyState
  ) {
    return null;
  }

  const selectedKeys = new Set(
    selectedItems.map((item) => `${item.type}:${item.id}`),
  );

  return (
    <div className="border-t border-border/60 px-4 py-3">
      <div className="space-y-3">
        {selectedItems.length > 0 ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <CheckCircle2 className="size-3.5" />
              <span>{t("hero.capabilityRecommendations.selectedTitle")}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedItems.map((item) => (
                <div
                  key={`${item.type}:${item.id}`}
                  className="inline-flex max-w-full items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1.5 text-sm"
                >
                  <CapabilityTypeIcon type={item.type} />
                  <span className="truncate">{item.name}</span>
                  <Badge variant="outline" className="text-[10px] uppercase">
                    {item.type === "mcp"
                      ? t("hero.capabilityRecommendations.mcpLabel")
                      : t("hero.capabilityRecommendations.skillLabel")}
                  </Badge>
                  <button
                    type="button"
                    onClick={() => onRemove(item)}
                    className="rounded-full p-0.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
                    aria-label={t("hero.capabilityRecommendations.remove", {
                      name: item.name,
                    })}
                    title={t("hero.capabilityRecommendations.remove", {
                      name: item.name,
                    })}
                  >
                    <X className="size-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <div className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              <Sparkles className="size-3.5" />
              <span>{t("hero.capabilityRecommendations.title")}</span>
            </div>
            {isLoading ? (
              <span className="text-xs text-muted-foreground">
                {t("hero.capabilityRecommendations.loading")}
              </span>
            ) : null}
          </div>

          {recommendations.length > 0 ? (
            <div className="space-y-2">
              {recommendations.map((item) => {
                const itemKey = `${item.type}:${item.id}`;
                const isSelected = selectedKeys.has(itemKey);

                return (
                  <div
                    key={itemKey}
                    className="flex flex-col gap-3 rounded-xl border border-border/60 bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <CapabilityTypeIcon type={item.type} />
                        <span className="truncate text-sm font-medium text-foreground">
                          {item.name}
                        </span>
                        <Badge
                          variant="outline"
                          className="text-[10px] uppercase"
                        >
                          {item.type === "mcp"
                            ? t("hero.capabilityRecommendations.mcpLabel")
                            : t("hero.capabilityRecommendations.skillLabel")}
                        </Badge>
                        {item.default_enabled ? (
                          <Badge
                            variant="secondary"
                            className="text-[10px] uppercase"
                          >
                            {t(
                              "hero.capabilityRecommendations.enabledByDefault",
                            )}
                          </Badge>
                        ) : null}
                      </div>
                      {item.description ? (
                        <p className="line-clamp-2 text-xs text-muted-foreground">
                          {item.description}
                        </p>
                      ) : (
                        <p className="text-xs text-muted-foreground">
                          {t("hero.capabilityRecommendations.noDescription")}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-shrink-0 items-center gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant={isSelected ? "secondary" : "outline"}
                        disabled={item.default_enabled || isSelected}
                        onClick={() => onApply(item)}
                      >
                        {isSelected
                          ? t("hero.capabilityRecommendations.added")
                          : item.default_enabled
                            ? t(
                                "hero.capabilityRecommendations.enabledByDefault",
                              )
                            : t("hero.capabilityRecommendations.useForTask")}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : showEmptyState && !isLoading ? (
            <div className="rounded-xl border border-dashed border-border/70 bg-muted/10 px-3 py-2 text-sm text-muted-foreground">
              {t("hero.capabilityRecommendations.empty")}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
