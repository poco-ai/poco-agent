"use client";

import { Badge } from "@/components/ui/badge";
import { CapabilitySourceAvatar } from "@/features/capabilities/components/capability-source-avatar";
import type { CapabilityRecommendation } from "@/features/task-composer/types/capability-recommendation";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface CapabilityRecommendationsProps {
  recommendations: CapabilityRecommendation[];
  trackedItems: CapabilityRecommendation[];
  isLoading: boolean;
  showEmptyState: boolean;
  isEnabled: (item: CapabilityRecommendation) => boolean;
  onToggle: (item: CapabilityRecommendation, enabled: boolean) => void;
  footerMode?: boolean;
}

function getCapabilityTypeLabel(
  item: CapabilityRecommendation,
  t: (key: string) => string,
) {
  return item.type === "mcp"
    ? t("hero.capabilityRecommendations.mcpLabel")
    : t("hero.capabilityRecommendations.skillLabel");
}

interface RecommendationCardProps {
  item: CapabilityRecommendation;
  enabled: boolean;
  onToggle: (item: CapabilityRecommendation, enabled: boolean) => void;
  t: (key: string, options?: Record<string, unknown>) => string;
}

function RecommendationCard({
  item,
  enabled,
  onToggle,
  t,
}: RecommendationCardProps) {
  const toggleLabel = enabled
    ? t("hero.capabilityRecommendations.remove", { name: item.name })
    : `${t("hero.capabilityRecommendations.useForTask")}: ${item.name}`;

  return (
    <button
      type="button"
      aria-pressed={enabled}
      aria-label={toggleLabel}
      onClick={() => onToggle(item, !enabled)}
      title={toggleLabel}
      className="group flex min-h-[72px] w-full flex-col justify-center rounded-xl border border-border/40 dark:border-border/80 bg-background/70 px-3 py-3 text-left transition-[border-color,background-color] hover:border-border/70 dark:hover:border-border hover:bg-muted/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
    >
      <div className="flex min-w-0 items-start gap-3">
        <CapabilitySourceAvatar
          name={item.name}
          status={enabled ? "active" : "inactive"}
          className="size-9"
          statusDotClassName={enabled ? "bg-primary" : undefined}
        />

        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 items-center justify-between gap-2">
            <span className="min-w-0 truncate text-sm font-medium text-foreground">
              {item.name}
            </span>
            <Badge
              variant="outline"
              className={cn(
                "shrink-0 text-xs",
                enabled
                  ? "border-primary/30 bg-primary/5 text-primary"
                  : "text-muted-foreground",
              )}
            >
              {getCapabilityTypeLabel(item, t)}
            </Badge>
          </div>

          <p className="mt-1 line-clamp-1 text-[11px] text-muted-foreground">
            {item.description ||
              t("hero.capabilityRecommendations.noDescription")}
          </p>
        </div>
      </div>
    </button>
  );
}

export function CapabilityRecommendations({
  recommendations,
  trackedItems,
  isLoading,
  showEmptyState,
  isEnabled,
  onToggle,
  footerMode = false,
}: CapabilityRecommendationsProps) {
  const { t } = useT("translation");
  const itemsToRender: CapabilityRecommendation[] = [];
  const seenKeys = new Set<string>();

  for (const item of recommendations) {
    const key = `${item.type}:${item.id}`;
    if (seenKeys.has(key)) continue;
    seenKeys.add(key);
    itemsToRender.push(item);
  }

  for (const item of trackedItems) {
    const key = `${item.type}:${item.id}`;
    if (seenKeys.has(key)) continue;
    seenKeys.add(key);
    itemsToRender.push(item);
  }

  if (!isLoading && itemsToRender.length === 0 && !showEmptyState) {
    return null;
  }

  return (
    <div
      className={cn(
        footerMode
          ? "py-3"
          : "border-t border-border/60 dark:border-border/90 px-4 py-2.5",
      )}
    >
      {itemsToRender.length > 0 ? (
        <>
          {/* Safari can oversize implicit fr rows here, so keep row height content-driven. */}
          <div className="grid grid-cols-3 gap-2">
            {itemsToRender.map((item, index) => (
              <div
                key={`${item.type}:${item.id}`}
                style={{
                  animationDelay: `${index * 80}ms`,
                  animationDuration: "300ms",
                  animationFillMode: "both",
                }}
                className="animate-in fade-in slide-in-from-bottom-2 duration-300"
              >
                <RecommendationCard
                  item={item}
                  enabled={isEnabled(item)}
                  onToggle={onToggle}
                  t={t}
                />
              </div>
            ))}
          </div>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            {t("hero.capabilityRecommendations.hint")}
          </p>
        </>
      ) : showEmptyState && !isLoading ? (
        <div className="rounded-lg border border-dashed border-border/70 dark:border-border/90 bg-muted/10 px-3 py-2 text-sm text-muted-foreground">
          {t("hero.capabilityRecommendations.empty")}
        </div>
      ) : null}
    </div>
  );
}
